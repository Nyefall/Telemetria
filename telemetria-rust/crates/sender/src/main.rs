//! # Telemetria Sender
//!
//! Coleta métricas de hardware e envia via UDP broadcast.
//! Requer privilégios de administrador para acesso a sensores térmicos.
//!
//! ## Uso
//! ```bash
//! telemetry_sender.exe              # Normal (auto-eleva para admin)
//! telemetry_sender.exe --no-admin   # Debug sem elevação
//! ```

mod monitor;
#[cfg(windows)]
pub(crate) mod lhm_sensors;
#[cfg(windows)]
pub(crate) mod nvml_gpu;
#[cfg(windows)]
pub(crate) mod smart_storage;
#[cfg(windows)]
pub(crate) mod wmi_sensors;

use monitor::HardwareMonitor;
use std::net::UdpSocket;
use std::time::{Duration, Instant};
use telemetry_core::config::AppConfig;
use telemetry_core::protocol::encode_payload;
use tracing::{error, info, warn};

fn main() {
    // ── Logging ──
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    // ── Verificar Admin (Windows) ──
    #[cfg(windows)]
    {
        let skip_admin = std::env::args().any(|a| a == "--no-admin");
        if !skip_admin && !is_admin() {
            info!("Elevando privilégios para Administrador...");
            if elevate_to_admin() {
                return; // Novo processo foi lançado
            }
            warn!("Falha ao elevar privilégios. Continuando sem admin (sensores limitados).");
        }
    }

    // ── Carregar config ──
    let config_path = AppConfig::default_path();
    let config = AppConfig::load(&config_path);

    // Salva config padrão se não existir
    if !config_path.exists() {
        if let Err(e) = config.save(&config_path) {
            warn!("Não foi possível salvar config padrão: {e}");
        }
    }

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
        sock.set_broadcast(true).expect("Falha ao habilitar broadcast");
        info!("Modo BROADCAST ativado");
    } else {
        info!("Modo UNICAST → {dest_ip}");
    }

    let dest_addr = format!("{dest_ip}:{port}");

    // ── Hardware Monitor ──
    let mut hw = HardwareMonitor::new();
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
    println!("  Protocolo: bincode v{}", telemetry_core::PROTOCOL_VERSION);
    println!("══════════════════════════════════════════════");
    println!();

    // ── Loop principal ──
    loop {
        let cycle_start = Instant::now();

        let payload = hw.collect();
        match encode_payload(&payload) {
            Ok(frame) => {
                match sock.send_to(&frame, &dest_addr) {
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
                }
            }
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
fn is_admin() -> bool {
    use windows::Win32::Foundation::HANDLE;
    use windows::Win32::Security::{GetTokenInformation, TokenElevation, TOKEN_ELEVATION, TOKEN_QUERY};
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
fn elevate_to_admin() -> bool {
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
        // ShellExecuteW retorna > 32 se sucesso
        result.0 as usize > 32
    }
}

#[cfg(not(windows))]
fn is_admin() -> bool {
    unsafe { libc::geteuid() == 0 }
}

#[cfg(not(windows))]
fn elevate_to_admin() -> bool {
    eprintln!("Execute com sudo para acesso a sensores térmicos.");
    false
}
