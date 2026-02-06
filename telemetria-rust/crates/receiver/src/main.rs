//! # Telemetria Receiver
//!
//! Dashboard de monitoramento de hardware em tempo real com GUI
//! acelerada por GPU via eframe/egui.
//!
//! Recebe dados do Sender via UDP e renderiza painéis interativos
//! com gráficos de histórico em tempo real.
//!
//! ## Atalhos
//! - `F` / `F11`: Fullscreen
//! - `G`: Toggle gráficos
//! - `T`: Alternar tema
//! - `Q` / `Esc`: Sair

mod dashboard;
mod net_thread;
mod panels;
mod theme_egui;

use dashboard::TelemetryDashboard;
use telemetry_core::config::AppConfig;

fn main() -> eframe::Result<()> {
    // ── Logging ──
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    // ── Config ──
    let config_path = AppConfig::default_path();
    let config = AppConfig::load(&config_path);

    if !config_path.exists() {
        let _ = config.save(&config_path);
    }

    // ── Janela eframe ──
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
