//! Telemetria Sender – library crate.
//!
//! Expõe `run_sender()` para uso tanto pelo binário standalone
//! quanto pelo unified `telemetry_app`.

pub mod monitor;
#[cfg(windows)]
pub mod amd_gpu;
#[cfg(windows)]
pub mod lhm_sensors;
#[cfg(windows)]
pub mod nvml_gpu;
#[cfg(windows)]
pub mod smart_storage;
#[cfg(windows)]
pub mod wmi_sensors;

use monitor::{GpuBackend, HardwareMonitor, MonitorOptions};
use std::net::UdpSocket;
use std::time::{Duration, Instant};
use telemetry_core::config::AppConfig;
use telemetry_core::protocol::encode_payload;
use tracing::{error, info, warn};

/// Opções de runtime para o sender.
#[derive(Debug, Clone, Default)]
pub struct SenderRuntime {
    /// Pular elevação de privilégios.
    pub skip_admin: bool,
}

/// Inicializa logging (deve ser chamado apenas uma vez por processo).
pub fn init_logging() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();
}

/// Ponto de entrada principal do sender.
pub fn run_sender(config: AppConfig, runtime: SenderRuntime) {
    // ── Verificar Admin (Windows) ──
    #[cfg(windows)]
    {
        if !runtime.skip_admin && !is_admin() {
            info!("Elevando privilégios para Administrador...");
            if elevate_to_admin() {
                return; // Novo processo foi lançado
            }
            warn!("Falha ao elevar privilégios. Continuando sem admin (sensores limitados).");
        }
    }
    #[cfg(not(windows))]
    let _ = &runtime;

    let sender_cfg = &config.sender;
    let dest_ip = &sender_cfg.dest_ip;
    let port = sender_cfg.port;
    let interval = Duration::from_secs_f64(sender_cfg.interval_secs);

    // ── Socket UDP ──
    let sock = UdpSocket::bind(if sender_cfg.bind_ip.is_empty() {
        "0.0.0.0:0".to_string()
    } else {
        format!("{}:0", sender_cfg.bind_ip)
    })
    .expect("Falha ao criar socket UDP");

    if sender_cfg.mode == "broadcast" || dest_ip == "255.255.255.255" {
        sock.set_broadcast(true)
            .expect("Falha ao habilitar broadcast");
        info!("Modo BROADCAST ativado");
    } else {
        info!("Modo UNICAST → {dest_ip}");
    }

    let dest_addr = format!("{dest_ip}:{port}");

    // ── Monitor Options from config ──
    let options = MonitorOptions {
        use_lhm: sender_cfg.use_lhm,
        use_smart: sender_cfg.use_smart,
        gpu_backend: GpuBackend::from_str(&sender_cfg.gpu_backend),
        gpu_index: sender_cfg.gpu_index,
    };

    // ── Hardware Monitor ──
    let mut hw = HardwareMonitor::new_with_options(options);
    info!("Hardware monitor inicializado");

    // Primeira leitura para inicializar contadores
    let _ = hw.collect();

    // ── Banner ──
    println!();
    println!("══════════════════════════════════════════════");
    println!("   ⚡ TELEMETRIA SENDER – ATIVO (Rust)");
    println!("══════════════════════════════════════════════");
    println!("  Destino:   {dest_addr}");
    println!("  Intervalo: {:.1}s", sender_cfg.interval_secs);
    println!(
        "  Protocolo: bincode v{}",
        telemetry_core::PROTOCOL_VERSION
    );
    println!("  GPU:       {:?}", options.gpu_backend);
    println!("  LHM:       {}", if options.use_lhm { "ON" } else { "OFF" });
    println!("  S.M.A.R.T: {}", if options.use_smart { "ON" } else { "OFF" });
    println!("══════════════════════════════════════════════");
    println!();

    // ── Loop principal ──
    loop {
        let cycle_start = Instant::now();

        let payload = hw.collect();
        match encode_payload(&payload) {
            Ok(frame) => match sock.send_to(&frame, &dest_addr) {
                Ok(sent) => {
                    info!(
                        "→ {} bytes para {} | CPU {:.1}% {:.0}°C | GPU {:.1}% {:.0}°C | RAM {:.0}%",
                        sent,
                        dest_addr,
                        payload.cpu.usage,
                        payload.cpu.temp,
                        payload.gpu.load,
                        payload.gpu.temp,
                        payload.ram.percent
                    );
                }
                Err(e) => error!("Erro ao enviar UDP: {e}"),
            },
            Err(e) => error!("Erro ao serializar payload: {e}"),
        }

        // Dormir pelo tempo restante do intervalo
        let elapsed = cycle_start.elapsed();
        if elapsed < interval {
            std::thread::sleep(interval - elapsed);
        }
    }
}

// ──────────────────────────────────────────────
// Windows: Verificação e elevação de admin
// ──────────────────────────────────────────────

#[cfg(windows)]
pub fn is_admin() -> bool {
    use windows::Win32::Foundation::HANDLE;
    use windows::Win32::Security::{
        GetTokenInformation, TokenElevation, TOKEN_ELEVATION, TOKEN_QUERY,
    };
    use windows::Win32::System::Threading::{GetCurrentProcess, OpenProcessToken};

    unsafe {
        let mut token = HANDLE::default();
        if OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut token).is_err() {
            return false;
        }

        let mut elevation = TOKEN_ELEVATION::default();
        let mut size = 0u32;
        let result = GetTokenInformation(
            token,
            TokenElevation,
            Some(&mut elevation as *mut _ as *mut _),
            std::mem::size_of::<TOKEN_ELEVATION>() as u32,
            &mut size,
        );

        let _ = windows::Win32::Foundation::CloseHandle(token);
        result.is_ok() && elevation.TokenIsElevated != 0
    }
}

#[cfg(windows)]
pub fn elevate_to_admin() -> bool {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    use windows::Win32::UI::Shell::ShellExecuteW;
    use windows::core::PCWSTR;

    let exe = std::env::current_exe().unwrap_or_default();
    let exe_wide: Vec<u16> = OsStr::new(exe.as_os_str())
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    let verb: Vec<u16> = OsStr::new("runas")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    let params: Vec<u16> = OsStr::new("")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    unsafe {
        let result = ShellExecuteW(
            None,
            PCWSTR(verb.as_ptr()),
            PCWSTR(exe_wide.as_ptr()),
            PCWSTR(params.as_ptr()),
            PCWSTR::null(),
            windows::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL,
        );
        result.0 as usize > 32
    }
}

#[cfg(not(windows))]
pub fn is_admin() -> bool {
    false
}

#[cfg(not(windows))]
pub fn elevate_to_admin() -> bool {
    eprintln!("Execute com sudo para acesso a sensores térmicos.");
    false
}
