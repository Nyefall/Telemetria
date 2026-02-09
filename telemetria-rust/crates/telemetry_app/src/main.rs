//! # Telemetria – Unified Binary
//!
//! Combina Sender + Receiver em um único executável.
//!
//! ## Uso
//! ```bash
//! telemetria.exe sender             # Apenas sender
//! telemetria.exe receiver           # Apenas receiver
//! telemetria.exe both               # Sender + Receiver simultâneo
//! telemetria.exe sender --no-admin  # Sem elevação de admin
//! telemetria.exe sender --no-lhm   # Sem LHM WMI
//! telemetria.exe sender --gpu amd   # Forçar GPU AMD (ADL)
//! telemetria.exe sender --gpu-index 1  # GPU secundária
//! ```

use telemetry_core::config::AppConfig;
use tracing::{error, info};

fn main() {
    // ── Logging ──
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    // ── Parse CLI ──
    let args: Vec<String> = std::env::args().collect();
    let mode = args.get(1).map(|s| s.as_str()).unwrap_or("help");

    // Flags
    let no_admin = args.iter().any(|a| a == "--no-admin");
    let no_lhm = args.iter().any(|a| a == "--no-lhm");
    let no_smart = args.iter().any(|a| a == "--no-smart");
    let gpu_backend = args
        .iter()
        .position(|a| a == "--gpu")
        .and_then(|i| args.get(i + 1))
        .map(|s| s.as_str());
    let gpu_index = args
        .iter()
        .position(|a| a == "--gpu-index")
        .and_then(|i| args.get(i + 1))
        .and_then(|s| s.parse::<u32>().ok());

    // ── Config ──
    let config_path = AppConfig::default_path();
    let mut config = AppConfig::load(&config_path);

    if !config_path.exists() {
        let _ = config.save(&config_path);
    }

    // Apply CLI overrides to config
    if no_lhm {
        config.sender.use_lhm = false;
    }
    if no_smart {
        config.sender.use_smart = false;
    }
    if let Some(gpu) = gpu_backend {
        config.sender.gpu_backend = gpu.to_string();
    }
    if let Some(idx) = gpu_index {
        config.sender.gpu_index = idx;
    }

    match mode {
        "sender" | "s" => {
            let runtime = telemetry_sender::SenderRuntime {
                skip_admin: no_admin,
            };
            telemetry_sender::run_sender(config, runtime);
        }
        "receiver" | "r" => {
            if let Err(e) = telemetry_receiver::run_receiver(config) {
                error!("Receiver falhou: {e}");
            }
        }
        "both" | "b" => {
            let config_sender = config.clone();
            let skip_admin = no_admin;

            // Sender em thread separada
            let sender_handle = std::thread::Builder::new()
                .name("sender".into())
                .spawn(move || {
                    let runtime = telemetry_sender::SenderRuntime {
                        skip_admin,
                    };
                    telemetry_sender::run_sender(config_sender, runtime);
                })
                .expect("Falha ao iniciar thread do sender");

            info!("Sender iniciado em thread separada");

            // Receiver na thread principal (GUI precisa da main thread)
            if let Err(e) = telemetry_receiver::run_receiver(config) {
                error!("Receiver falhou: {e}");
            }

            // Se o receiver fechar, esperar o sender (nunca retorna, mas...)
            let _ = sender_handle.join();
        }
        _ => {
            println!();
            println!("══════════════════════════════════════════════════════");
            println!("   ⚡ TELEMETRIA v{} – Unified Binary", env!("CARGO_PKG_VERSION"));
            println!("══════════════════════════════════════════════════════");
            println!();
            println!("  USO:");
            println!("    telemetria sender     Inicia o Sender (coleta + broadcast)");
            println!("    telemetria receiver   Inicia o Receiver (dashboard GUI)");
            println!("    telemetria both       Inicia ambos simultaneamente");
            println!();
            println!("  FLAGS (sender):");
            println!("    --no-admin            Não tenta elevar para admin");
            println!("    --no-lhm              Desativa LHM WMI (Tier 2)");
            println!("    --no-smart            Desativa S.M.A.R.T.");
            println!("    --gpu <backend>       auto | nvidia | amd | lhm | off");
            println!("    --gpu-index <n>       Índice da GPU (0 = padrão)");
            println!();
            println!("  EXEMPLOS:");
            println!("    telemetria sender --gpu amd");
            println!("    telemetria both --no-lhm --gpu nvidia");
            println!("    telemetria receiver");
            println!();
        }
    }
}
