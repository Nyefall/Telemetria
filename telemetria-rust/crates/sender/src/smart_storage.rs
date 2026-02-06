//! S.M.A.R.T. native — leitura de temperatura de disco via `DeviceIoControl`.
//!
//! Acesso direto ao hardware sem CLR/.NET. Requer admin para abrir handles de `\\.\PhysicalDriveN`.
//!
//! Pipeline:
//! 1. `IOCTL_STORAGE_QUERY_PROPERTY` + `StorageDeviceTemperatureProperty` (NVMe + SATA moderno, Win10+)
//! 2. Fallback: SMART attributes via `SMART_RCV_DRIVE_DATA` (SATA legado, attribute 194)

use std::ffi::OsStr;
use std::os::windows::ffi::OsStrExt;
use tracing::debug;
use windows::core::PCWSTR;
use windows::Win32::Foundation::{CloseHandle, HANDLE};
use windows::Win32::Storage::FileSystem::{
    CreateFileW, FILE_FLAGS_AND_ATTRIBUTES, FILE_SHARE_READ, FILE_SHARE_WRITE, OPEN_EXISTING,
};
use windows::Win32::System::IO::DeviceIoControl;

// ──────────────────────────────────────────────
// IOCTL Constants
// ──────────────────────────────────────────────

/// `CTL_CODE(FILE_DEVICE_MASS_STORAGE, 0x0500, METHOD_BUFFERED, FILE_ANY_ACCESS)`
const IOCTL_STORAGE_QUERY_PROPERTY: u32 = 0x002D_1400;

/// `CTL_CODE(FILE_DEVICE_DISK, 0x0022, METHOD_BUFFERED, FILE_READ_ACCESS|FILE_WRITE_ACCESS)`
const SMART_RCV_DRIVE_DATA: u32 = 0x0007_C088;

/// `STORAGE_PROPERTY_ID::StorageDeviceProperty`
const STORAGE_DEVICE_PROPERTY: u32 = 0;

/// `STORAGE_PROPERTY_ID::StorageDeviceTemperatureProperty` (Win10 1607+)
const STORAGE_DEVICE_TEMPERATURE_PROPERTY: u32 = 18;

/// `STORAGE_QUERY_TYPE::PropertyStandardQuery`
const PROPERTY_STANDARD_QUERY: u32 = 0;

/// ATA SMART command byte
const SMART_CMD: u8 = 0xB0;

/// SMART sub-command: read attributes
const READ_ATTRIBUTES: u8 = 0xD0;

// ──────────────────────────────────────────────
// Structures (repr(C) – layout compatível com Windows)
// ──────────────────────────────────────────────

#[repr(C)]
struct StoragePropertyQuery {
    property_id: u32,
    query_type: u32,
    additional_parameters: [u8; 4],
}

#[repr(C)]
struct StorageDeviceDescriptor {
    version: u32,
    size: u32,
    device_type: u8,
    device_type_modifier: u8,
    removable_media: u8,
    command_queueing: u8,
    vendor_id_offset: u32,
    product_id_offset: u32,
    product_revision_offset: u32,
    serial_number_offset: u32,
    bus_type: u32,
    raw_properties_length: u32,
    raw_device_properties: [u8; 1],
}

#[repr(C)]
struct StorageTemperatureInfo {
    index: u16,
    temperature: i16,
    over_threshold: i16,
    under_threshold: i16,
    over_threshold_changeable: u8,
    under_threshold_changeable: u8,
    event_generated: u8,
    _reserved0: u8,
    _reserved1: u32,
}

#[repr(C)]
struct StorageTemperatureDataDescriptor {
    version: u32,
    size: u32,
    critical_temperature: i16,
    warning_temperature: i16,
    info_count: u16,
    _reserved: [u8; 2],
    // TemperatureInfo array follows
}

// ──────────────────────────────────────────────
// API pública
// ──────────────────────────────────────────────

/// Temperatura de um drive físico.
#[derive(Debug)]
pub struct DriveTemperature {
    pub model: String,
    pub temp_celsius: f32,
    pub drive_index: u32,
}

/// Enumera todas as drives físicas e lê temperaturas.
///
/// Tenta até 16 drives (`\\.\PhysicalDrive0` a `\\.\PhysicalDrive15`).
/// Requer privilégios de administrador.
pub fn query_drive_temperatures() -> Vec<DriveTemperature> {
    let mut results = Vec::new();

    for index in 0..16u32 {
        let path = format!("\\\\.\\PhysicalDrive{index}");

        let handle = match open_drive(&path) {
            Some(h) => h,
            None => continue,
        };

        let model = get_drive_model(handle, index);

        // Pipeline: Temperature Property → SMART fallback
        let temp = query_temperature_property(handle)
            .or_else(|| query_smart_temperature(handle, index as u8));

        unsafe {
            let _ = CloseHandle(handle);
        }

        if let Some(temp_c) = temp {
            if temp_c > 0.0 && temp_c < 100.0 {
                debug!(
                    "S.M.A.R.T. Drive{index}: {model} = {temp_c:.0}°C"
                );
                results.push(DriveTemperature {
                    model,
                    temp_celsius: temp_c,
                    drive_index: index,
                });
            }
        }
    }

    results
}

// ──────────────────────────────────────────────
// Abertura de handle
// ──────────────────────────────────────────────

fn open_drive(path: &str) -> Option<HANDLE> {
    let wide: Vec<u16> = OsStr::new(path)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    unsafe {
        CreateFileW(
            PCWSTR(wide.as_ptr()),
            0xC000_0000u32, // GENERIC_READ | GENERIC_WRITE
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAGS_AND_ATTRIBUTES(0),
            None,
        )
        .ok()
    }
}

// ──────────────────────────────────────────────
// Identificação do modelo
// ──────────────────────────────────────────────

fn get_drive_model(handle: HANDLE, index: u32) -> String {
    let mut buffer = vec![0u8; 1024];
    let query = StoragePropertyQuery {
        property_id: STORAGE_DEVICE_PROPERTY,
        query_type: PROPERTY_STANDARD_QUERY,
        additional_parameters: [0; 4],
    };

    let mut bytes_returned = 0u32;
    let ok = unsafe {
        DeviceIoControl(
            handle,
            IOCTL_STORAGE_QUERY_PROPERTY,
            Some(std::ptr::from_ref(&query).cast()),
            size_of::<StoragePropertyQuery>() as u32,
            Some(buffer.as_mut_ptr().cast()),
            buffer.len() as u32,
            Some(&mut bytes_returned),
            None,
        )
    };

    if ok.is_err() || (bytes_returned as usize) < size_of::<StorageDeviceDescriptor>() {
        return format!("PhysicalDrive{index}");
    }

    let desc = unsafe { &*(buffer.as_ptr() as *const StorageDeviceDescriptor) };

    let mut model = String::new();

    // Vendor ID
    if desc.vendor_id_offset > 0 && (desc.vendor_id_offset as usize) < buffer.len() {
        let s = extract_string(&buffer, desc.vendor_id_offset as usize);
        let s = s.trim();
        if !s.is_empty() {
            model.push_str(s);
        }
    }

    // Product ID
    if desc.product_id_offset > 0 && (desc.product_id_offset as usize) < buffer.len() {
        let s = extract_string(&buffer, desc.product_id_offset as usize);
        let s = s.trim();
        if !s.is_empty() {
            if !model.is_empty() {
                model.push(' ');
            }
            model.push_str(s);
        }
    }

    if model.is_empty() {
        format!("PhysicalDrive{index}")
    } else {
        model
    }
}

fn extract_string(buffer: &[u8], offset: usize) -> String {
    if offset >= buffer.len() {
        return String::new();
    }
    let bytes = &buffer[offset..];
    let end = bytes.iter().position(|&b| b == 0).unwrap_or(bytes.len());
    String::from_utf8_lossy(&bytes[..end]).to_string()
}

// ──────────────────────────────────────────────
// Método 1: StorageDeviceTemperatureProperty
//   Funciona para NVMe + SATA moderno (Win10 1607+)
// ──────────────────────────────────────────────

fn query_temperature_property(handle: HANDLE) -> Option<f32> {
    let buf_size = size_of::<StorageTemperatureDataDescriptor>()
        + 4 * size_of::<StorageTemperatureInfo>();
    let mut buffer = vec![0u8; buf_size];

    let query = StoragePropertyQuery {
        property_id: STORAGE_DEVICE_TEMPERATURE_PROPERTY,
        query_type: PROPERTY_STANDARD_QUERY,
        additional_parameters: [0; 4],
    };

    let mut bytes_returned = 0u32;
    let ok = unsafe {
        DeviceIoControl(
            handle,
            IOCTL_STORAGE_QUERY_PROPERTY,
            Some(std::ptr::from_ref(&query).cast()),
            size_of::<StoragePropertyQuery>() as u32,
            Some(buffer.as_mut_ptr().cast()),
            buffer.len() as u32,
            Some(&mut bytes_returned),
            None,
        )
    };

    if ok.is_err() {
        return None;
    }

    if (bytes_returned as usize) < size_of::<StorageTemperatureDataDescriptor>() {
        return None;
    }

    let desc = unsafe { &*(buffer.as_ptr() as *const StorageTemperatureDataDescriptor) };

    if desc.info_count == 0 {
        return None;
    }

    // Primeira TemperatureInfo segue o descriptor header
    let info_offset = size_of::<StorageTemperatureDataDescriptor>();
    if info_offset + size_of::<StorageTemperatureInfo>() > buffer.len() {
        return None;
    }

    let info = unsafe { &*(buffer.as_ptr().add(info_offset) as *const StorageTemperatureInfo) };
    let temp = info.temperature as f32;

    if temp > 0.0 && temp < 100.0 {
        Some(temp)
    } else {
        None
    }
}

// ──────────────────────────────────────────────
// Método 2: SMART Attributes (SATA legado)
//   Lê attribute 194 (Temperature) ou 190 (Airflow)
// ──────────────────────────────────────────────

fn query_smart_temperature(handle: HANDLE, drive_number: u8) -> Option<f32> {
    // ── Input: SENDCMDINPARAMS ──
    // Layout: cBufferSize(4) + IDEREGS(8) + bDriveNumber(1) + bReserved(3) + dwReserved(16) = 32 bytes
    let mut in_buf = [0u8; 32];

    // cBufferSize = 512 (esperado no output)
    in_buf[0..4].copy_from_slice(&512u32.to_le_bytes());

    // IDEREGS at offset 4:
    in_buf[4] = READ_ATTRIBUTES; // bFeaturesReg
    in_buf[5] = 1; // bSectorCountReg
    in_buf[6] = 1; // bSectorNumberReg
    in_buf[7] = 0x4F; // bCylLowReg
    in_buf[8] = 0xC2; // bCylHighReg
    in_buf[9] = 0xA0 | ((drive_number & 1) << 4); // bDriveHeadReg
    in_buf[10] = SMART_CMD; // bCommandReg

    // bDriveNumber at offset 12
    in_buf[12] = drive_number;

    // ── Output: SENDCMDOUTPARAMS ──
    // Layout: cBufferSize(4) + DRIVERSTATUS(12) + bBuffer(512) = 528 bytes
    let mut out_buf = [0u8; 528];
    let mut bytes_returned = 0u32;

    let ok = unsafe {
        DeviceIoControl(
            handle,
            SMART_RCV_DRIVE_DATA,
            Some(in_buf.as_ptr().cast()),
            in_buf.len() as u32,
            Some(out_buf.as_mut_ptr().cast()),
            out_buf.len() as u32,
            Some(&mut bytes_returned),
            None,
        )
    };

    if ok.is_err() || bytes_returned < 32 {
        return None;
    }

    // SMART data começa no offset 16 (após cBufferSize + DRIVERSTATUS)
    let smart_data = &out_buf[16..];
    parse_smart_temp_attribute(smart_data)
}

/// Varre os SMART attributes procurando temperatura (ID 194 ou 190).
fn parse_smart_temp_attribute(smart_data: &[u8]) -> Option<f32> {
    // Offset 0-1: revision number (skip)
    // Offset 2+: 30 attributes × 12 bytes cada
    let attr_start = 2;
    let attr_size = 12;

    for i in 0..30 {
        let offset = attr_start + i * attr_size;
        if offset + attr_size > smart_data.len() {
            break;
        }

        let attr_id = smart_data[offset];

        // Attribute 194 = HDD/SSD Temperature
        // Attribute 190 = Airflow Temperature
        if attr_id == 194 || attr_id == 190 {
            // Raw value está no offset +5 (6 bytes raw, o 1º byte é a temperatura)
            let raw_temp = smart_data[offset + 5] as f32;
            if raw_temp > 0.0 && raw_temp < 100.0 {
                return Some(raw_temp);
            }
        }
    }

    None
}
