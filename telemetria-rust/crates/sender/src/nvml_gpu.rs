//! NVIDIA GPU monitoring via NVML (nvidia-ml).
//!
//! Carrega `nvml.dll` dinamicamente — funciona com qualquer driver NVIDIA.
//! Sem GPU NVIDIA? `try_new()` retorna `None` e o módulo é desativado.

use nvml_wrapper::enum_wrappers::device::{Clock, TemperatureSensor};
use nvml_wrapper::Nvml;
use telemetry_core::types::GpuData;
use tracing::{debug, info};

/// Monitor de GPU NVIDIA via NVML.
pub struct NvmlMonitor {
    nvml: Nvml,
}

impl NvmlMonitor {
    /// Tenta inicializar NVML. Retorna `None` se não houver GPU NVIDIA.
    pub fn try_new() -> Option<Self> {
        match Nvml::init() {
            Ok(nvml) => {
                let count = nvml.device_count().unwrap_or(0);
                if count > 0 {
                    if let Ok(dev) = nvml.device_by_index(0) {
                        let name = dev.name().unwrap_or_else(|_| "Unknown".into());
                        info!("✓ NVML: {name} ({count} GPU(s))");
                    } else {
                        info!("✓ NVML: {count} GPU(s) NVIDIA");
                    }
                    Some(Self { nvml })
                } else {
                    debug!("NVML init OK mas nenhuma GPU encontrada");
                    None
                }
            }
            Err(e) => {
                debug!("NVML não disponível: {e}");
                None
            }
        }
    }

    /// Coleta métricas da GPU no índice especificado (geralmente 0).
    pub fn query_gpu(&self, index: u32) -> GpuData {
        let mut data = GpuData::default();

        let Ok(device) = self.nvml.device_by_index(index) else {
            return data;
        };

        // Temperatura (°C)
        if let Ok(temp) = device.temperature(TemperatureSensor::Gpu) {
            data.temp = temp as f32;
        }

        // Utilização (%)
        if let Ok(util) = device.utilization_rates() {
            data.load = util.gpu as f32;
        }

        // Clocks (MHz)
        if let Ok(clock) = device.clock_info(Clock::Graphics) {
            data.clock_core = clock as f32;
        }
        if let Ok(clock) = device.clock_info(Clock::Memory) {
            data.clock_mem = clock as f32;
        }

        // Fan speed (NVML retorna % 0-100, NÃO RPM)
        if let Ok(fan_pct) = device.fan_speed(0) {
            data.fan = fan_pct as f32;
        }

        // VRAM (bytes → MB)
        if let Ok(mem) = device.memory_info() {
            data.mem_used_mb = (mem.used as f64 / (1024.0 * 1024.0)) as f32;
        }

        // NVML não fornece voltagem da GPU (LHM pode)

        data
    }
}
