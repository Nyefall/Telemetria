//! Telemetria Receiver – library crate.
//!
//! Expõe `run_receiver()` para uso tanto pelo binário standalone
//! quanto pelo unified `telemetry_app`.

pub mod dashboard;
pub mod net_thread;
pub mod panels;
pub mod theme_egui;

use dashboard::TelemetryDashboard;
use telemetry_core::config::AppConfig;

/// Inicializa logging (deve ser chamado apenas uma vez por processo).
pub fn init_logging() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();
}

/// Ponto de entrada principal do receiver.
pub fn run_receiver(config: AppConfig) -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_title("⚡ Telemetry Center ⚡")
            .with_inner_size([1366.0, 768.0])
            .with_min_inner_size([1024.0, 600.0]),
        ..Default::default()
    };

    eframe::run_native(
        "Telemetry Center",
        options,
        Box::new(move |cc| Ok(Box::new(TelemetryDashboard::new(cc, config)))),
    )
}
