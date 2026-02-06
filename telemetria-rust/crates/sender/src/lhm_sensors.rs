//! Sensores detalhados via LibreHardwareMonitor WMI.
//!
//! Quando o LHM roda como admin ou serviço Windows, ele expõe **todos** os
//! sensores de hardware via WMI em `root\LibreHardwareMonitor`.
//!
//! Cobre: CPU temp/voltage/power/clock, GPU completo, Mobo temp, Storage temp, Fans.
//!
//! ## Instalação do LHM como serviço
//! 1. Baixe LibreHardwareMonitor: <https://github.com/LibreHardwareMonitor/LibreHardwareMonitor>
//! 2. Execute como admin → Options → "Run On Windows Startup"
//!    **OU** instale como serviço via `sc create` / tarefa agendada.

use serde::Deserialize;
use std::collections::HashMap;
use tracing::debug;
use wmi::WMIConnection;

// ──────────────────────────────────────────────
// Dados retornados
// ──────────────────────────────────────────────

/// Dados coletados do LibreHardwareMonitor.
#[derive(Debug, Default)]
pub struct LhmData {
    // CPU
    pub cpu_temp: f32,
    pub cpu_voltage: f32,
    pub cpu_power: f32,
    pub cpu_clock: f32,

    // GPU
    pub gpu_temp: f32,
    pub gpu_load: f32,
    pub gpu_voltage: f32,
    pub gpu_clock_core: f32,
    pub gpu_clock_mem: f32,
    pub gpu_fan_rpm: f32,
    pub gpu_mem_used_mb: f32,

    // Motherboard
    pub mobo_temp: f32,

    // Fans (name, rpm)
    pub fans: Vec<(String, f32)>,

    // Storage temps (drive_name, temp_c)
    pub storage_temps: Vec<(String, f32)>,
}

// ──────────────────────────────────────────────
// WMI structs de deserialização
// ──────────────────────────────────────────────

#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct LhmSensor {
    identifier: String,
    sensor_type: String,
    value: f32,
    name: String,
    parent: String,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "PascalCase")]
struct LhmHardware {
    identifier: String,
    name: String,
    #[allow(dead_code)]
    hardware_type: String,
}

// ──────────────────────────────────────────────
// API pública
// ──────────────────────────────────────────────

/// Verifica se o LHM WMI está acessível e possui dados.
pub fn check_available(wmi: &WMIConnection) -> bool {
    match wmi.raw_query::<LhmHardware>(
        "SELECT Identifier, Name, HardwareType FROM Hardware",
    ) {
        Ok(hw) => !hw.is_empty(),
        Err(_) => false,
    }
}

/// Conta o número de sensores disponíveis (para logging).
pub fn sensor_count(wmi: &WMIConnection) -> usize {
    wmi.raw_query::<LhmSensor>(
        "SELECT Identifier, SensorType, Value, Name, Parent FROM Sensor",
    )
    .map(|v| v.len())
    .unwrap_or(0)
}

/// Consulta todos os sensores do LHM e retorna dados estruturados.
pub fn query_all(wmi: &WMIConnection) -> Result<LhmData, String> {
    let mut data = LhmData::default();

    // Hardware names → mapeia identifier → nome amigável
    let hw_names: HashMap<String, String> = wmi
        .raw_query::<LhmHardware>("SELECT Identifier, Name, HardwareType FROM Hardware")
        .unwrap_or_default()
        .into_iter()
        .map(|h| (h.identifier, h.name))
        .collect();

    // Query todos os sensores em uma única chamada
    let sensors: Vec<LhmSensor> = wmi
        .raw_query("SELECT Identifier, SensorType, Value, Name, Parent FROM Sensor")
        .map_err(|e| format!("LHM Sensor query: {e}"))?;

    debug!("LHM: {} sensores, {} hardware entries", sensors.len(), hw_names.len());

    for s in &sensors {
        let id = s.identifier.to_lowercase();
        let nm = s.name.to_lowercase();

        match s.sensor_type.as_str() {
            "Temperature" => parse_temperature(&id, &nm, s.value, &s.parent, &hw_names, &mut data),
            "Voltage" => parse_voltage(&id, &nm, s.value, &mut data),
            "Power" => parse_power(&id, &nm, s.value, &mut data),
            "Load" => parse_load(&id, &nm, s.value, &mut data),
            "Clock" => parse_clock(&id, &nm, s.value, &mut data),
            "Fan" => parse_fan(&id, s.value, &s.name, &mut data),
            "SmallData" | "Data" => parse_data(&id, &nm, s.value, &mut data),
            _ => {}
        }
    }

    Ok(data)
}

// ──────────────────────────────────────────────
// Helpers de classificação por Identifier
// ──────────────────────────────────────────────

fn is_cpu(id: &str) -> bool {
    id.contains("cpu") // matches /intelcpu/, /amdcpu/
}

fn is_gpu(id: &str) -> bool {
    id.contains("gpu") // matches /nvidiagpu/, /atigpu/, /amdgpu/
}

fn is_mobo(id: &str) -> bool {
    id.contains("/lpc/") || id.contains("/ec/") || id.contains("/motherboard")
}

fn is_storage(id: &str) -> bool {
    id.contains("/nvme/") || id.contains("/hdd/") || id.contains("/ssd/")
}

// ──────────────────────────────────────────────
// Parsers por tipo de sensor
// ──────────────────────────────────────────────

fn parse_temperature(
    id: &str,
    nm: &str,
    value: f32,
    parent: &str,
    hw_names: &HashMap<String, String>,
    data: &mut LhmData,
) {
    if !(value > 0.0 && value < 150.0) {
        return;
    }

    if is_cpu(id) {
        // Preferir "CPU Package", "Tdie", "Tctl"
        if nm.contains("package") || nm.contains("tdie") || nm.contains("tctl") {
            data.cpu_temp = value;
        } else if data.cpu_temp == 0.0 {
            data.cpu_temp = data.cpu_temp.max(value);
        }
    } else if is_gpu(id) {
        data.gpu_temp = data.gpu_temp.max(value);
    } else if is_mobo(id) {
        if nm.contains("system") || nm.contains("motherboard") || data.mobo_temp == 0.0 {
            data.mobo_temp = value;
        }
    } else if is_storage(id) {
        let drive = hw_names
            .get(parent)
            .cloned()
            .unwrap_or_else(|| parent.to_string());
        data.storage_temps.push((drive, value));
    }
}

fn parse_voltage(id: &str, nm: &str, value: f32, data: &mut LhmData) {
    if is_cpu(id) && (nm.contains("core") || nm.contains("vcore")) && data.cpu_voltage == 0.0 {
        data.cpu_voltage = value;
    } else if is_gpu(id) && data.gpu_voltage == 0.0 {
        data.gpu_voltage = value;
    }
}

fn parse_power(id: &str, nm: &str, value: f32, data: &mut LhmData) {
    if is_cpu(id) && (nm.contains("package") || data.cpu_power == 0.0) {
        data.cpu_power = value;
    }
}

fn parse_load(id: &str, nm: &str, value: f32, data: &mut LhmData) {
    if is_gpu(id) && (nm.contains("core") || nm.contains("d3d") || data.gpu_load == 0.0) {
        data.gpu_load = value;
    }
}

fn parse_clock(id: &str, nm: &str, value: f32, data: &mut LhmData) {
    if is_cpu(id) {
        // Pega o maior clock entre todos os cores
        data.cpu_clock = data.cpu_clock.max(value);
    } else if is_gpu(id) {
        if nm.contains("core") {
            data.gpu_clock_core = value;
        } else if nm.contains("memory") {
            data.gpu_clock_mem = value;
        }
    }
}

fn parse_fan(id: &str, value: f32, original_name: &str, data: &mut LhmData) {
    if is_gpu(id) {
        data.gpu_fan_rpm = value;
    } else {
        // Fans da mobo/case
        data.fans.push((original_name.to_string(), value));
    }
}

fn parse_data(id: &str, nm: &str, value: f32, data: &mut LhmData) {
    if is_gpu(id) && nm.contains("memory used") {
        data.gpu_mem_used_mb = value;
    }
}
