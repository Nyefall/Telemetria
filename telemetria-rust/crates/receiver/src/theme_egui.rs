//! Conversão de temas para `egui::Color32`.

use egui::Color32;
use telemetry_core::theme::{self, Theme};

/// Tema convertido para tipos egui.
#[derive(Clone)]
#[allow(dead_code)]
pub struct EguiTheme {
    pub name: String,
    pub bg: Color32,
    pub panel: Color32,
    pub border: Color32,
    pub text: Color32,
    pub dim: Color32,
    pub title: Color32,
    pub cpu: Color32,
    pub gpu: Color32,
    pub ram: Color32,
    pub storage: Color32,
    pub network: Color32,
    pub mobo: Color32,
    pub warning: Color32,
    pub critical: Color32,
}

impl EguiTheme {
    /// Converte um [`Theme`] do core para [`EguiTheme`].
    pub fn from_core(t: &Theme) -> Self {
        Self {
            name: t.name.clone(),
            bg: hex_color(&t.bg),
            panel: hex_color(&t.panel),
            border: hex_color(&t.border),
            text: hex_color(&t.text),
            dim: hex_color(&t.dim),
            title: hex_color(&t.title),
            cpu: hex_color(&t.cpu),
            gpu: hex_color(&t.gpu),
            ram: hex_color(&t.ram),
            storage: hex_color(&t.storage),
            network: hex_color(&t.network),
            mobo: hex_color(&t.mobo),
            warning: hex_color(&t.warning),
            critical: hex_color(&t.critical),
        }
    }

    /// Retorna a cor de um componente pelo nome.
    #[allow(dead_code)]
    pub fn component_color(&self, component: &str) -> Color32 {
        match component {
            "cpu" => self.cpu,
            "gpu" => self.gpu,
            "ram" => self.ram,
            "storage" => self.storage,
            "network" => self.network,
            "mobo" => self.mobo,
            _ => self.text,
        }
    }

    /// Retorna a cor baseada em thresholds.
    pub fn value_color(&self, value: f32, warn: f32, crit: f32) -> Color32 {
        if value >= crit {
            self.critical
        } else if value >= warn {
            self.warning
        } else {
            self.text
        }
    }
}

fn hex_color(hex: &str) -> Color32 {
    let (r, g, b) = theme::hex_to_rgb(hex);
    Color32::from_rgb(r, g, b)
}

/// Carrega todos os temas disponíveis.
pub fn all_themes() -> Vec<EguiTheme> {
    theme::theme_names()
        .iter()
        .map(|name| EguiTheme::from_core(&theme::get_theme(name)))
        .collect()
}
