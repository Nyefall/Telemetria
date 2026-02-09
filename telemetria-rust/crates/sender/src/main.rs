//! # Telemetria Sender (standalone)
//!
//! Thin wrapper que delega para `telemetry_sender::run_sender()`.
//!
//! ## Uso
//! ```bash
//! telemetry_sender.exe              # Normal (auto-eleva para admin)
//! telemetry_sender.exe --no-admin   # Debug sem elevação
//! ```

use telemetry_core::config::AppConfig;
use tracing::warn;

fn main() {
    telemetry_sender::init_logging();

    let skip_admin = std::env::args().any(|a| a == "--no-admin");

    let config_path = AppConfig::default_path();
    let config = AppConfig::load(&config_path);

    if !config_path.exists() {
        if let Err(e) = config.save(&config_path) {
            warn!("Não foi possível salvar config padrão: {e}");
        }
    }

    let runtime = telemetry_sender::SenderRuntime { skip_admin };
    telemetry_sender::run_sender(config, runtime);
}
