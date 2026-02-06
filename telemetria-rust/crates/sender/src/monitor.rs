//! Hardware Monitor – Coleta multi-fonte com fallback chain.
//!
//! **Tier 1 — Pure Rust (sempre disponível com admin, ~80% dos sensores):**
//! - `sysinfo` — CPU usage, RAM, disco (espaço), rede (bytes)
//! - `nvml-wrapper` — GPU NVIDIA: temp, uso, clocks, fan, VRAM
//! - `DeviceIoControl` S.M.A.R.T. — Storage: temperatura (NVMe + SATA)
//! - Standard WMI — CPU clock, link speed, ACPI temp
//!
//! **Tier 2 — LHM opcional (+20% "luxury sensors"):**
//! - LibreHardwareMonitor WMI — CPU voltage/power, Mobo temp, Fans, GPU voltage

use sysinfo::{Components, CpuRefreshKind, Disks, MemoryRefreshKind, Networks, RefreshKind, System};
use telemetry_core::types::*;
use tracing::{debug, info, warn};

#[cfg(windows)]
use {
    crate::lhm_sensors,
    crate::nvml_gpu::NvmlMonitor,
    crate::smart_storage,
    crate::wmi_sensors,
    wmi::{COMLibrary, WMIConnection},
};

/// Monitor de hardware principal.
pub struct HardwareMonitor {
    sys: System,
    disks: Disks,
    networks: Networks,
    components: Components,
    /// Bytes de rede do último ciclo (sent, recv, timestamp)
    last_net: Option<(u64, u64, std::time::Instant)>,

    // ── Fontes avançadas (Windows) ──
    #[cfg(windows)]
    nvml: Option<NvmlMonitor>,
    #[cfg(windows)]
    wmi_lhm: Option<WMIConnection>,
    #[cfg(windows)]
    wmi_cimv2: Option<WMIConnection>,
    #[cfg(windows)]
    wmi_acpi: Option<WMIConnection>,
}

impl HardwareMonitor {
    /// Cria um novo monitor e detecta fontes de sensores disponíveis.
    pub fn new() -> Self {
        let sys = System::new_with_specifics(
            RefreshKind::nothing()
                .with_cpu(CpuRefreshKind::everything())
                .with_memory(MemoryRefreshKind::everything()),
        );

        // ── Inicializar fontes avançadas (Windows) ──
        #[cfg(windows)]
        let nvml = NvmlMonitor::try_new();

        #[cfg(windows)]
        let (wmi_lhm, wmi_cimv2, wmi_acpi) = init_wmi_connections();

        #[cfg(windows)]
        {
            let initial_smart = smart_storage::query_drive_temperatures();
            if initial_smart.is_empty() {
                warn!("✗ S.M.A.R.T.: nenhum drive acessível (requer admin)");
            } else {
                info!("✓ S.M.A.R.T.: {} drives detectados", initial_smart.len());
                for d in &initial_smart {
                    info!("  PhysicalDrive{}: {} ({:.0}°C)", d.drive_index, d.model, d.temp_celsius);
                }
            }
        }

        Self {
            sys,
            disks: Disks::new_with_refreshed_list(),
            networks: Networks::new_with_refreshed_list(),
            components: Components::new_with_refreshed_list(),
            last_net: None,
            #[cfg(windows)]
            nvml,
            #[cfg(windows)]
            wmi_lhm,
            #[cfg(windows)]
            wmi_cimv2,
            #[cfg(windows)]
            wmi_acpi,
        }
    }

    /// Atualiza todos os sensores e retorna o payload completo.
    pub fn collect(&mut self) -> TelemetryPayload {
        // Refresh subsistemas sysinfo
        self.sys.refresh_cpu_all();
        self.sys.refresh_memory();
        self.networks.refresh(true);
        self.components.refresh(true);
        self.disks.refresh(true);

        let mut payload = TelemetryPayload::default();

        // ── Básicos (sysinfo – sempre disponível) ──
        payload.cpu.usage = self.sys.global_cpu_usage();
        payload.cpu.temp = self.cpu_temp_from_components();
        payload.ram = self.collect_ram();
        payload.network = self.collect_network();
        payload.storage = self.collect_storage();
        payload.fans = self.fans_from_components();

        // ── Fontes avançadas (Windows) ──
        #[cfg(windows)]
        self.enrich_windows(&mut payload);

        payload
    }

    // ──────────────────────────────────────────
    // Coleta básica via sysinfo
    // ──────────────────────────────────────────

    /// Busca a temperatura da CPU nos components do sysinfo.
    fn cpu_temp_from_components(&self) -> f32 {
        let mut temp = 0.0_f32;
        for comp in self.components.iter() {
            let label = comp.label().to_lowercase();
            if label.contains("cpu")
                || label.contains("tctl")
                || label.contains("tdie")
                || label.contains("package")
                || label.contains("core")
            {
                if let Some(t) = comp.temperature() {
                    if t > temp && t < 150.0 {
                        temp = t;
                    }
                }
            }
        }
        temp
    }

    fn collect_ram(&self) -> RamData {
        let total = self.sys.total_memory() as f64;
        let used = self.sys.used_memory() as f64;
        let total_gb = total / (1024.0 * 1024.0 * 1024.0);
        let used_gb = used / (1024.0 * 1024.0 * 1024.0);
        let percent = if total > 0.0 {
            (used / total * 100.0) as f32
        } else {
            0.0
        };

        RamData {
            percent,
            used_gb: used_gb as f32,
            total_gb: total_gb as f32,
        }
    }

    fn collect_network(&mut self) -> NetworkData {
        let mut total_sent: u64 = 0;
        let mut total_recv: u64 = 0;

        for (_name, data) in self.networks.iter() {
            total_sent += data.total_transmitted();
            total_recv += data.total_received();
        }

        let now = std::time::Instant::now();
        let (down_kbps, up_kbps) = if let Some((last_sent, last_recv, last_time)) = self.last_net {
            let dt = now.duration_since(last_time).as_secs_f64();
            if dt > 0.0 {
                let sent_delta = total_sent.saturating_sub(last_sent) as f64;
                let recv_delta = total_recv.saturating_sub(last_recv) as f64;
                (
                    (recv_delta / 1024.0 / dt) as f32,
                    (sent_delta / 1024.0 / dt) as f32,
                )
            } else {
                (0.0, 0.0)
            }
        } else {
            (0.0, 0.0)
        };

        self.last_net = Some((total_sent, total_recv, now));

        NetworkData {
            down_kbps,
            up_kbps,
            ping_ms: measure_ping(),
            link_speed_mbps: 0,
            adapter_name: String::new(),
        }
    }

    fn collect_storage(&self) -> Vec<StorageData> {
        let mut storages = Vec::new();

        for disk in self.disks.iter() {
            let total = disk.total_space() as f64;
            let available = disk.available_space() as f64;
            let used = total - available;
            let used_pct = if total > 0.0 {
                (used / total * 100.0) as f32
            } else {
                0.0
            };

            let name = disk.name().to_string_lossy().to_string();
            if name.is_empty() && total == 0.0 {
                continue;
            }

            storages.push(StorageData {
                name: if name.is_empty() {
                    disk.mount_point().to_string_lossy().to_string()
                } else {
                    name
                },
                temp: 0.0,
                health: 100.0,
                used_space: used_pct,
                ..Default::default()
            });
        }

        storages
    }

    fn fans_from_components(&self) -> Vec<FanData> {
        let mut fans = Vec::new();
        for comp in self.components.iter() {
            let label = comp.label().to_lowercase();
            if label.contains("fan") {
                if let Some(rpm) = comp.temperature() {
                    if rpm > 100.0 {
                        fans.push(FanData {
                            name: comp.label().to_string(),
                            rpm,
                        });
                    }
                }
            }
        }
        fans
    }

    // ──────────────────────────────────────────
    // Enriquecimento com fontes avançadas (Windows)
    // ──────────────────────────────────────────

    #[cfg(windows)]
    fn enrich_windows(&mut self, payload: &mut TelemetryPayload) {
        let mut gpu_from_lhm = false;

        // ── S.M.A.R.T. nativo: storage temps (pure Rust, sem CLR) ──
        {
            let smart_temps = smart_storage::query_drive_temperatures();
            if !smart_temps.is_empty() {
                let tuples: Vec<(String, f32)> = smart_temps
                    .iter()
                    .map(|d| (d.model.clone(), d.temp_celsius))
                    .collect();
                apply_storage_temps(&mut payload.storage, &tuples);
            }
        }

        // ── Priority 1: LibreHardwareMonitor WMI (luxury sensors) ──
        if let Some(ref wmi_lhm) = self.wmi_lhm {
            match lhm_sensors::query_all(wmi_lhm) {
                Ok(lhm) => {
                    // CPU
                    if lhm.cpu_temp > 0.0 {
                        payload.cpu.temp = lhm.cpu_temp;
                    }
                    if lhm.cpu_voltage > 0.0 {
                        payload.cpu.voltage = lhm.cpu_voltage;
                    }
                    if lhm.cpu_power > 0.0 {
                        payload.cpu.power = lhm.cpu_power;
                    }
                    if lhm.cpu_clock > 0.0 {
                        payload.cpu.clock = lhm.cpu_clock;
                    }

                    // GPU
                    if lhm.gpu_temp > 0.0 || lhm.gpu_load > 0.0 {
                        gpu_from_lhm = true;
                        if lhm.gpu_temp > 0.0 {
                            payload.gpu.temp = lhm.gpu_temp;
                        }
                        if lhm.gpu_load > 0.0 {
                            payload.gpu.load = lhm.gpu_load;
                        }
                        if lhm.gpu_voltage > 0.0 {
                            payload.gpu.voltage = lhm.gpu_voltage;
                        }
                        if lhm.gpu_clock_core > 0.0 {
                            payload.gpu.clock_core = lhm.gpu_clock_core;
                        }
                        if lhm.gpu_clock_mem > 0.0 {
                            payload.gpu.clock_mem = lhm.gpu_clock_mem;
                        }
                        if lhm.gpu_fan_rpm > 0.0 {
                            payload.gpu.fan = lhm.gpu_fan_rpm;
                        }
                        if lhm.gpu_mem_used_mb > 0.0 {
                            payload.gpu.mem_used_mb = lhm.gpu_mem_used_mb;
                        }
                    }

                    // Mobo
                    if lhm.mobo_temp > 0.0 {
                        payload.mobo.temp = lhm.mobo_temp;
                    }

                    // Storage temps
                    apply_storage_temps(&mut payload.storage, &lhm.storage_temps);

                    // Fans (substitui os do sysinfo)
                    if !lhm.fans.is_empty() {
                        payload.fans = lhm
                            .fans
                            .iter()
                            .map(|(n, r)| FanData {
                                name: n.clone(),
                                rpm: *r,
                            })
                            .collect();
                    }

                    debug!(
                        "LHM: CPU {:.1}°C {:.2}V {:.1}W | GPU {:.1}°C {:.0}% | Mobo {:.1}°C | {} fans",
                        lhm.cpu_temp,
                        lhm.cpu_voltage,
                        lhm.cpu_power,
                        lhm.gpu_temp,
                        lhm.gpu_load,
                        lhm.mobo_temp,
                        lhm.fans.len(),
                    );
                }
                Err(e) => debug!("LHM query falhou: {e}"),
            }
        }

        // ── Priority 2: NVML (GPU fallback se LHM não forneceu GPU) ──
        if !gpu_from_lhm {
            if let Some(ref nvml) = self.nvml {
                let gpu = nvml.query_gpu(0);
                if gpu.temp > 0.0 || gpu.load > 0.0 {
                    payload.gpu = gpu;
                    debug!(
                        "NVML: GPU {:.1}°C {:.0}% {:.0}/{:.0}MHz {:.0}MB",
                        payload.gpu.temp,
                        payload.gpu.load,
                        payload.gpu.clock_core,
                        payload.gpu.clock_mem,
                        payload.gpu.mem_used_mb,
                    );
                }
            }
        }

        // ── Priority 3: Standard WMI ──
        if let Some(ref wmi_std) = self.wmi_cimv2 {
            // Link speed (LHM não fornece)
            let (link, adapter) = wmi_sensors::query_link_speed(wmi_std);
            if link > 0 {
                payload.network.link_speed_mbps = link;
                payload.network.adapter_name = adapter;
            }

            // CPU clock fallback
            if payload.cpu.clock == 0.0 {
                payload.cpu.clock = wmi_sensors::query_cpu_clock(wmi_std);
            }
        }

        // ── Priority 4: ACPI temp fallback ──
        if payload.cpu.temp == 0.0 {
            if let Some(ref wmi_acpi) = self.wmi_acpi {
                payload.cpu.temp = wmi_sensors::query_acpi_temp(wmi_acpi);
            }
        }
    }
}

// ──────────────────────────────────────────────
// Inicialização de conexões WMI
// ──────────────────────────────────────────────

#[cfg(windows)]
fn init_wmi_connections() -> (
    Option<WMIConnection>,
    Option<WMIConnection>,
    Option<WMIConnection>,
) {
    // ── LHM WMI (root\LibreHardwareMonitor) ──
    let wmi_lhm = COMLibrary::new()
        .ok()
        .and_then(|com| {
            WMIConnection::with_namespace_path("root\\LibreHardwareMonitor", com).ok()
        })
        .and_then(|wmi| {
            if lhm_sensors::check_available(&wmi) {
                let count = lhm_sensors::sensor_count(&wmi);
                info!("✓ LHM WMI: {count} sensores disponíveis");
                Some(wmi)
            } else {
                None
            }
        });

    if wmi_lhm.is_none() {
        warn!("✗ LHM WMI: não detectado");
        warn!("  → Para sensores completos (CPU temp/voltage/power, GPU, Mobo, Storage temp):");
        warn!("    Instale LibreHardwareMonitor e rode como admin ou serviço Windows");
    }

    // ── Standard WMI (root\CIMv2) ──
    let wmi_cimv2 = COMLibrary::new()
        .ok()
        .and_then(|com| WMIConnection::new(com).ok());

    if wmi_cimv2.is_some() {
        info!("✓ Standard WMI: disponível (CPU clock, link speed)");
    }

    // ── ACPI WMI (root\WMI) ──
    let wmi_acpi = COMLibrary::new()
        .ok()
        .and_then(|com| WMIConnection::with_namespace_path("root\\WMI", com).ok());

    (wmi_lhm, wmi_cimv2, wmi_acpi)
}

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

/// Aplica temperaturas do LHM aos StorageData do sysinfo.
#[cfg(windows)]
fn apply_storage_temps(storages: &mut [StorageData], lhm_temps: &[(String, f32)]) {
    for (drive_name, temp) in lhm_temps {
        let mut matched = false;

        // Tentar match por nome
        for storage in storages.iter_mut() {
            if storage.temp == 0.0 && storage_names_match(&storage.name, drive_name) {
                storage.temp = *temp;
                matched = true;
                break;
            }
        }

        // Fallback: aplicar ao primeiro storage sem temperatura
        if !matched {
            for storage in storages.iter_mut() {
                if storage.temp == 0.0 {
                    storage.temp = *temp;
                    break;
                }
            }
        }
    }
}

/// Compara nomes de disco de forma fuzzy.
#[cfg(windows)]
fn storage_names_match(sysinfo_name: &str, lhm_name: &str) -> bool {
    if sysinfo_name.is_empty() || lhm_name.is_empty() {
        return false;
    }
    let a = sysinfo_name.to_lowercase();
    let b = lhm_name.to_lowercase();
    a.contains(&b) || b.contains(&a)
}

/// Mede latência TCP para 8.8.8.8:53.
fn measure_ping() -> f32 {
    use std::net::{SocketAddr, TcpStream};
    use std::time::{Duration, Instant};

    let addr: SocketAddr = "8.8.8.8:53".parse().unwrap();
    let start = Instant::now();
    match TcpStream::connect_timeout(&addr, Duration::from_secs(1)) {
        Ok(_stream) => {
            let elapsed = start.elapsed();
            elapsed.as_secs_f32() * 1000.0
        }
        Err(_) => 0.0,
    }
}
