//! Standard WMI queries (fallback quando LHM não está disponível).
//!
//! Fontes:
//! - `root\CIMv2`: CPU clock (`Win32_Processor`), link speed (`Win32_NetworkAdapter`)
//! - `root\WMI`: temperatura ACPI (`MSAcpi_ThermalZoneTemperature`)
//!
//! Estas queries funcionam sem software extra, mas fornecem dados limitados.

use serde::Deserialize;
use tracing::debug;
use wmi::WMIConnection;

// ──────────────────────────────────────────────
// WMI Query structs
// ──────────────────────────────────────────────

#[derive(Deserialize, Debug)]
#[serde(rename = "Win32_Processor")]
#[serde(rename_all = "PascalCase")]
struct ProcessorInfo {
    current_clock_speed: Option<u32>,
}

#[derive(Deserialize, Debug)]
#[serde(rename = "Win32_NetworkAdapter")]
#[serde(rename_all = "PascalCase")]
struct NetworkAdapter {
    name: Option<String>,
    speed: Option<u64>,
    net_connection_id: Option<String>,
}

#[derive(Deserialize, Debug)]
#[serde(rename = "MSAcpi_ThermalZoneTemperature")]
#[serde(rename_all = "PascalCase")]
struct ThermalZone {
    current_temperature: u32, // decikelvin
}

// ──────────────────────────────────────────────
// API pública
// ──────────────────────────────────────────────

/// Consulta clock atual da CPU (MHz) via `Win32_Processor`.
pub fn query_cpu_clock(wmi: &WMIConnection) -> f32 {
    match wmi.raw_query::<ProcessorInfo>("SELECT CurrentClockSpeed FROM Win32_Processor") {
        Ok(procs) => procs
            .iter()
            .filter_map(|p| p.current_clock_speed)
            .max()
            .unwrap_or(0) as f32,
        Err(e) => {
            debug!("WMI Win32_Processor: {e}");
            0.0
        }
    }
}

/// Consulta velocidade de link do adaptador de rede ativo.
/// Retorna `(link_mbps, adapter_name)`.
pub fn query_link_speed(wmi: &WMIConnection) -> (u32, String) {
    match wmi.raw_query::<NetworkAdapter>(
        "SELECT Name, Speed, NetConnectionID FROM Win32_NetworkAdapter WHERE NetConnectionStatus = 2",
    ) {
        Ok(adapters) => {
            // Preferir Ethernet/LAN sobre Wi-Fi
            let best = adapters
                .iter()
                .find(|a| {
                    a.net_connection_id
                        .as_deref()
                        .unwrap_or("")
                        .to_lowercase()
                        .contains("ethernet")
                })
                .or_else(|| {
                    adapters.iter().find(|a| {
                        a.net_connection_id
                            .as_deref()
                            .unwrap_or("")
                            .to_lowercase()
                            .contains("lan")
                    })
                })
                .or(adapters.first());

            if let Some(adapter) = best {
                let link = adapter.speed.map(|s| (s / 1_000_000) as u32).unwrap_or(0);
                let name = adapter
                    .net_connection_id
                    .clone()
                    .or(adapter.name.clone())
                    .unwrap_or_default();
                (link, name)
            } else {
                (0, String::new())
            }
        }
        Err(e) => {
            debug!("WMI Win32_NetworkAdapter: {e}");
            (0, String::new())
        }
    }
}

/// Consulta temperatura ACPI (fallback para CPU temp quando LHM e sysinfo não fornecem).
pub fn query_acpi_temp(wmi: &WMIConnection) -> f32 {
    match wmi.raw_query::<ThermalZone>(
        "SELECT CurrentTemperature FROM MSAcpi_ThermalZoneTemperature",
    ) {
        Ok(zones) => {
            let mut max_temp = 0.0_f32;
            for zone in &zones {
                // Converte decikelvin → Celsius: (val / 10) - 273.15
                let temp_c = (zone.current_temperature as f32 / 10.0) - 273.15;
                if temp_c > 0.0 && temp_c < 150.0 {
                    max_temp = max_temp.max(temp_c);
                }
            }
            max_temp
        }
        Err(e) => {
            debug!("WMI MSAcpi_ThermalZoneTemperature (requer Admin): {e}");
            0.0
        }
    }
}
