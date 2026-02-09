//! AMD GPU monitoring via ADL (ATI Display Library) SDK.
//!
//! Carrega `atiadlxx.dll` (64-bit) ou `atiadlxy.dll` (32-bit) dinamicamente
//! do diretório do driver AMD. Sem DLL → desativado silenciosamente.
//!
//! ## API utilizada
//! - **ADL2** context API (thread-safe, recomendada pela AMD)
//! - **Overdrive 6** — compatível com GCN até RDNA2+ (fallback universal)
//!   - Temperatura (millidegrees C ÷ 1000)
//!   - Activity (load %, engine clock, memory clock em 10kHz ÷ 100 → MHz)
//!   - Fan speed (RPM)
//!
//! ## Referência
//! - AMD Display Library SDK: <https://gpuopen.com/adl/>
//! - Header: `adl_sdk.h`, `adl_structures.h`
//!
//! ## Limitações conhecidas
//! - VRAM (memória dedicada em uso) NÃO é exposta pelo Overdrive 6.
//!   Para isso seria necessário OverdriveN ou Performance Monitoring API,
//!   que variam por geração de GPU. O campo `mem_used_mb` fica 0.0.
//! - Voltage não é exposto pelo Overdrive 6 `CurrentStatus`.

#![allow(non_camel_case_types)]

use libloading::Library;
use std::ffi::c_void;
use telemetry_core::types::GpuData;
use tracing::{debug, info, warn};

// ──────────────────────────────────────────────
// Constantes ADL
// ──────────────────────────────────────────────

const ADL_OK: i32 = 0;

// ADL_DL_FANCTRL_SPEED_TYPE_RPM = 1 (pedir RPM, não %)
const ADL_DL_FANCTRL_SPEED_TYPE_RPM: i32 = 1;

// ──────────────────────────────────────────────
// Type aliases para ponteiros de função ADL2
// ──────────────────────────────────────────────

type ADL_CONTEXT_HANDLE = *mut c_void;

/// Callback que o ADL chama para alocar memória interna.
type ADL_MAIN_MALLOC_CALLBACK = extern "C" fn(i32) -> *mut c_void;

// ADL2 entry points
type FnADL2_Main_Control_Create =
    unsafe extern "C" fn(ADL_MAIN_MALLOC_CALLBACK, i32, *mut ADL_CONTEXT_HANDLE) -> i32;
type FnADL2_Main_Control_Destroy = unsafe extern "C" fn(ADL_CONTEXT_HANDLE) -> i32;
type FnADL2_Adapter_NumberOfAdapters_Get =
    unsafe extern "C" fn(ADL_CONTEXT_HANDLE, *mut i32) -> i32;
type FnADL2_Adapter_AdapterInfo_Get =
    unsafe extern "C" fn(ADL_CONTEXT_HANDLE, *mut AdapterInfo, i32) -> i32;
type FnADL2_Adapter_Active_Get =
    unsafe extern "C" fn(ADL_CONTEXT_HANDLE, i32, *mut i32) -> i32;
type FnADL2_Overdrive6_Temperature_Get =
    unsafe extern "C" fn(ADL_CONTEXT_HANDLE, i32, i32, *mut ADLTemperature) -> i32;
type FnADL2_Overdrive6_CurrentStatus_Get =
    unsafe extern "C" fn(ADL_CONTEXT_HANDLE, i32, *mut ADLOD6CurrentStatus) -> i32;
type FnADL2_Overdrive6_FanSpeed_Get =
    unsafe extern "C" fn(ADL_CONTEXT_HANDLE, i32, *mut ADLFanSpeedValue) -> i32;

// ──────────────────────────────────────────────
// Structs (repr(C) — layout idêntico ao SDK C)
// ──────────────────────────────────────────────

/// `AdapterInfo` — referência: adl_structures.h
/// O SDK define strings como `char[ADL_MAX_PATH]` (256 bytes).
#[repr(C)]
#[derive(Clone)]
struct AdapterInfo {
    /// Tamanho desta struct.
    i_size: i32,
    /// Índice interno do adapter.
    i_adapter_index: i32,
    /// UDID string.
    str_udid: [u8; 256],
    /// PCI bus number.
    i_bus_number: i32,
    /// PCI device number.
    i_device_number: i32,
    /// PCI function number.
    i_function_number: i32,
    /// Vendor ID.
    i_vendor_id: i32,
    /// Nome do adapter (ex: "AMD Radeon RX 7900 XTX").
    str_adapter_name: [u8; 256],
    /// Nome do display (ex: "\\.\DISPLAY1").
    str_display_name: [u8; 256],
    /// 1 se presente no sistema.
    i_present: i32,
    /// 1 se existe.
    #[cfg(windows)]
    i_exist: i32,
    /// Driver path.
    #[cfg(windows)]
    str_driver_path: [u8; 256],
    /// Driver path ext.
    #[cfg(windows)]
    str_driver_path_ext: [u8; 256],
    /// PNP string.
    #[cfg(windows)]
    str_pnp_string: [u8; 256],
    /// OS display index.
    i_os_display_index: i32,
}

impl Default for AdapterInfo {
    fn default() -> Self {
        // SAFETY: Struct é repr(C) com tipos primitivos e arrays de u8.
        // Zerar tudo é válido.
        unsafe { std::mem::zeroed() }
    }
}

impl AdapterInfo {
    fn adapter_name(&self) -> String {
        let end = self
            .str_adapter_name
            .iter()
            .position(|&b| b == 0)
            .unwrap_or(self.str_adapter_name.len());
        String::from_utf8_lossy(&self.str_adapter_name[..end])
            .trim()
            .to_string()
    }
}

/// `ADLTemperature` — temperatura em milligraus Celsius.
#[repr(C)]
#[derive(Clone, Copy, Default)]
struct ADLTemperature {
    /// Tamanho desta struct.
    i_size: i32,
    /// Temperatura × 1000 (ex: 65000 = 65.0°C).
    i_temperature: i32,
}

/// `ADLOD6CurrentStatus` — status do Overdrive 6.
#[repr(C)]
#[derive(Clone, Copy, Default)]
struct ADLOD6CurrentStatus {
    i_size: i32,
    /// Engine clock em 10kHz (÷100 → MHz).
    i_engine_clock: i32,
    /// Memory clock em 10kHz (÷100 → MHz).
    i_memory_clock: i32,
    /// VDDC (voltage, unidade varia, geralmente mV).
    i_vddc: i32,
    /// Atividade da GPU (0-100%).
    i_activity_percent: i32,
    i_current_performance_level: i32,
    i_current_bus_speed: i32,
    i_current_bus_lanes: i32,
    i_maximum_bus_lanes: i32,
    i_reserved: i32,
}

/// `ADLFanSpeedValue` — velocidade do fan.
#[repr(C)]
#[derive(Clone, Copy, Default)]
struct ADLFanSpeedValue {
    i_size: i32,
    /// Tipo solicitado: 1=RPM, 2=%.
    i_speed_type: i32,
    /// Valor retornado.
    i_fan_speed: i32,
    i_flags: i32,
}

// ──────────────────────────────────────────────
// Callback malloc (exigido pelo ADL)
// ──────────────────────────────────────────────

extern "C" fn adl_malloc(size: i32) -> *mut c_void {
    // SAFETY: libc::malloc é a alocação C standard.
    unsafe { libc::malloc(size as usize) }
}

// ──────────────────────────────────────────────
// Monitor AMD
// ──────────────────────────────────────────────

#[allow(dead_code)]
pub struct AmdGpuMonitor {
    /// Mantém a DLL carregada enquanto o monitor existir.
    _lib: Library,
    context: ADL_CONTEXT_HANDLE,
    // Ponteiros de função — armazenados para chamadas rápidas.
    fn_destroy: FnADL2_Main_Control_Destroy,
    fn_adapter_count: FnADL2_Adapter_NumberOfAdapters_Get,
    fn_adapter_info: FnADL2_Adapter_AdapterInfo_Get,
    fn_adapter_active: FnADL2_Adapter_Active_Get,
    fn_temperature: FnADL2_Overdrive6_Temperature_Get,
    fn_current_status: FnADL2_Overdrive6_CurrentStatus_Get,
    fn_fan_speed: FnADL2_Overdrive6_FanSpeed_Get,
    /// Índice real do adapter AMD ativo (resolve por bus_number).
    active_adapter_indices: Vec<i32>,
}

// SAFETY: ADL_CONTEXT_HANDLE é um ponteiro opaco criado por ADL2_Main_Control_Create.
// Toda chamada ADL passa o context — o ADL gerencia sincronização interna.
// Nosso uso é single-threaded (HardwareMonitor é usado em uma thread só).
unsafe impl Send for AmdGpuMonitor {}

impl Drop for AmdGpuMonitor {
    fn drop(&mut self) {
        if !self.context.is_null() {
            unsafe {
                let _ = (self.fn_destroy)(self.context);
            }
        }
    }
}

impl AmdGpuMonitor {
    /// Tenta inicializar o ADL. Retorna `None` se AMD driver não estiver instalado.
    pub fn try_new() -> Option<Self> {
        // Tenta 64-bit primeiro, depois 32-bit.
        let lib = unsafe { Library::new("atiadlxx.dll") }
            .or_else(|_| unsafe { Library::new("atiadlxy.dll") })
            .ok()?;

        unsafe {
            // ── Resolver ponteiros de função ──
            let fn_create: FnADL2_Main_Control_Create =
                *lib.get(b"ADL2_Main_Control_Create\0").ok()?;
            let fn_destroy: FnADL2_Main_Control_Destroy =
                *lib.get(b"ADL2_Main_Control_Destroy\0").ok()?;
            let fn_adapter_count: FnADL2_Adapter_NumberOfAdapters_Get =
                *lib.get(b"ADL2_Adapter_NumberOfAdapters_Get\0").ok()?;
            let fn_adapter_info: FnADL2_Adapter_AdapterInfo_Get =
                *lib.get(b"ADL2_Adapter_AdapterInfo_Get\0").ok()?;
            let fn_adapter_active: FnADL2_Adapter_Active_Get =
                *lib.get(b"ADL2_Adapter_Active_Get\0").ok()?;
            let fn_temperature: FnADL2_Overdrive6_Temperature_Get =
                *lib.get(b"ADL2_Overdrive6_Temperature_Get\0").ok()?;
            let fn_current_status: FnADL2_Overdrive6_CurrentStatus_Get =
                *lib.get(b"ADL2_Overdrive6_CurrentStatus_Get\0").ok()?;
            let fn_fan_speed: FnADL2_Overdrive6_FanSpeed_Get =
                *lib.get(b"ADL2_Overdrive6_FanSpeed_Get\0").ok()?;

            // ── Criar contexto ADL2 ──
            // Argumento 1 = enumerate only active adapters (attached to displays)
            let mut context: ADL_CONTEXT_HANDLE = std::ptr::null_mut();
            let res = fn_create(adl_malloc, 1, &mut context);
            if res != ADL_OK || context.is_null() {
                warn!("✗ ADL: init falhou (código {res})");
                return None;
            }

            // ── Enumerar adapters ──
            let mut total_count = 0i32;
            let res = fn_adapter_count(context, &mut total_count);
            if res != ADL_OK || total_count <= 0 {
                debug!("ADL: sem adapters (código {res}, count {total_count})");
                let _ = fn_destroy(context);
                return None;
            }

            // Buscar info de todos os adapters
            let mut infos = vec![AdapterInfo::default(); total_count as usize];
            let buf_size = (std::mem::size_of::<AdapterInfo>() * infos.len()) as i32;
            let res = fn_adapter_info(context, infos.as_mut_ptr(), buf_size);
            if res != ADL_OK {
                debug!("ADL: AdapterInfo_Get falhou ({res})");
                let _ = fn_destroy(context);
                return None;
            }

            // Filtrar apenas adapters ATIVOS e únicos (por bus_number,
            // pois o ADL lista um adapter por display conectado).
            let mut active_adapter_indices = Vec::new();
            let mut seen_buses = std::collections::HashSet::new();

            for info in &infos {
                if info.i_present == 0 {
                    continue;
                }
                // Checar se está ativo
                let mut active = 0i32;
                if fn_adapter_active(context, info.i_adapter_index, &mut active) == ADL_OK
                    && active != 0
                    && seen_buses.insert(info.i_bus_number)
                {
                    let name = info.adapter_name();
                    info!(
                        "✓ ADL GPU[{}]: {} (bus {})",
                        active_adapter_indices.len(),
                        name,
                        info.i_bus_number
                    );
                    active_adapter_indices.push(info.i_adapter_index);
                }
            }

            if active_adapter_indices.is_empty() {
                debug!("ADL: nenhum adapter ativo");
                let _ = fn_destroy(context);
                return None;
            }

            info!(
                "✓ ADL: {} GPU(s) AMD ativa(s)",
                active_adapter_indices.len()
            );

            Some(Self {
                _lib: lib,
                context,
                fn_destroy,
                fn_adapter_count,
                fn_adapter_info,
                fn_adapter_active,
                fn_temperature,
                fn_current_status,
                fn_fan_speed,
                active_adapter_indices,
            })
        }
    }

    /// Número de GPUs AMD detectadas.
    pub fn gpu_count(&self) -> u32 {
        self.active_adapter_indices.len() as u32
    }

    /// Coleta métricas da GPU no índice relativo (0 = primeira AMD ativa).
    pub fn query_gpu(&self, index: u32) -> GpuData {
        let mut data = GpuData::default();

        let Some(&adapter_idx) = self.active_adapter_indices.get(index as usize) else {
            return data;
        };

        unsafe {
            // ── Temperatura ──
            let mut temp = ADLTemperature {
                i_size: std::mem::size_of::<ADLTemperature>() as i32,
                i_temperature: 0,
            };
            if (self.fn_temperature)(self.context, adapter_idx, 0, &mut temp) == ADL_OK {
                // millidegrees → degrees
                data.temp = temp.i_temperature as f32 / 1000.0;
            }

            // ── Activity + Clocks ──
            let mut status = ADLOD6CurrentStatus {
                i_size: std::mem::size_of::<ADLOD6CurrentStatus>() as i32,
                ..Default::default()
            };
            if (self.fn_current_status)(self.context, adapter_idx, &mut status) == ADL_OK {
                data.load = status.i_activity_percent as f32;
                // 10kHz → MHz
                data.clock_core = status.i_engine_clock as f32 / 100.0;
                data.clock_mem = status.i_memory_clock as f32 / 100.0;
            }

            // ── Fan Speed (RPM) ──
            let mut fan = ADLFanSpeedValue {
                i_size: std::mem::size_of::<ADLFanSpeedValue>() as i32,
                i_speed_type: ADL_DL_FANCTRL_SPEED_TYPE_RPM,
                ..Default::default()
            };
            if (self.fn_fan_speed)(self.context, adapter_idx, &mut fan) == ADL_OK
                && fan.i_speed_type == ADL_DL_FANCTRL_SPEED_TYPE_RPM
            {
                data.fan = fan.i_fan_speed as f32;
            }
        }

        data
    }
}
