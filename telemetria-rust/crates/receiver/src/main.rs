//! # Telemetria Receiver (standalone)
//!
//! Thin wrapper que delega para `telemetry_receiver::run_receiver()`.
//!
//! ## Atalhos
//! - `F` / `F11`: Fullscreen
//! - `G`: Toggle gráficos
//! - `T`: Alternar tema
//! - `Q` / `Esc`: Sair

use telemetry_core::config::AppConfig;

fn main() -> eframe::Result<()> {
    telemetry_receiver::init_logging();

    let config_path = AppConfig::default_path();
    let config = AppConfig::load(&config_path);

    if !config_path.exists() {
        let _ = config.save(&config_path);
    }

    telemetry_receiver::run_receiver(config)
}
