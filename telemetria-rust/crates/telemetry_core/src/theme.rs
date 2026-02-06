//! Definição de temas visuais para o dashboard.
//!
//! Portado diretamente do `ui/themes.py` do Python.

use serde::{Deserialize, Serialize};

/// Definição completa de um tema de cores.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Theme {
    pub name: String,
    // Cores de fundo
    pub bg: Color32Hex,
    pub panel: Color32Hex,
    pub border: Color32Hex,
    // Cores de texto
    pub text: Color32Hex,
    pub dim: Color32Hex,
    pub title: Color32Hex,
    // Cores por componente
    pub cpu: Color32Hex,
    pub gpu: Color32Hex,
    pub ram: Color32Hex,
    pub storage: Color32Hex,
    pub network: Color32Hex,
    pub mobo: Color32Hex,
    // Cores de alerta
    pub warning: Color32Hex,
    pub critical: Color32Hex,
}

/// Cor em formato hex string (ex: "#00ff88") para serialização.
/// A conversão para `egui::Color32` é feita no receiver.
pub type Color32Hex = String;

/// Converte uma string hex "#RRGGBB" para tupla (r, g, b).
pub fn hex_to_rgb(hex: &str) -> (u8, u8, u8) {
    let hex = hex.trim_start_matches('#');
    if hex.len() != 6 {
        return (255, 255, 255); // fallback branco
    }
    let r = u8::from_str_radix(&hex[0..2], 16).unwrap_or(255);
    let g = u8::from_str_radix(&hex[2..4], 16).unwrap_or(255);
    let b = u8::from_str_radix(&hex[4..6], 16).unwrap_or(255);
    (r, g, b)
}

/// Tema Escuro (padrão).
pub fn dark_theme() -> Theme {
    Theme {
        name: "dark".into(),
        bg: "#1a1a1a".into(),
        panel: "#252525".into(),
        border: "#333333".into(),
        text: "#ffffff".into(),
        dim: "#666666".into(),
        title: "#00d9ff".into(),
        cpu: "#00ff88".into(),
        gpu: "#00ff88".into(),
        ram: "#ffa500".into(),
        storage: "#ff6b6b".into(),
        network: "#00d9ff".into(),
        mobo: "#bb86fc".into(),
        warning: "#ffcc00".into(),
        critical: "#ff3333".into(),
    }
}

/// Tema Claro.
pub fn light_theme() -> Theme {
    Theme {
        name: "light".into(),
        bg: "#f5f5f5".into(),
        panel: "#ffffff".into(),
        border: "#cccccc".into(),
        text: "#333333".into(),
        dim: "#888888".into(),
        title: "#0066cc".into(),
        cpu: "#00aa55".into(),
        gpu: "#00aa55".into(),
        ram: "#cc7700".into(),
        storage: "#cc4444".into(),
        network: "#0066cc".into(),
        mobo: "#7744aa".into(),
        warning: "#cc9900".into(),
        critical: "#cc2222".into(),
    }
}

/// Tema High Contrast (acessibilidade).
pub fn high_contrast_theme() -> Theme {
    Theme {
        name: "high_contrast".into(),
        bg: "#000000".into(),
        panel: "#1a1a1a".into(),
        border: "#ffffff".into(),
        text: "#ffffff".into(),
        dim: "#cccccc".into(),
        title: "#00ffff".into(),
        cpu: "#00ff00".into(),
        gpu: "#00ff00".into(),
        ram: "#ffff00".into(),
        storage: "#ff6600".into(),
        network: "#00ffff".into(),
        mobo: "#ff00ff".into(),
        warning: "#ffff00".into(),
        critical: "#ff0000".into(),
    }
}

/// Tema Cyberpunk.
pub fn cyberpunk_theme() -> Theme {
    Theme {
        name: "cyberpunk".into(),
        bg: "#0a0a1a".into(),
        panel: "#1a1a2e".into(),
        border: "#4a4a6a".into(),
        text: "#e0e0ff".into(),
        dim: "#6a6a9a".into(),
        title: "#ff00ff".into(),
        cpu: "#00ffff".into(),
        gpu: "#00ffff".into(),
        ram: "#ff6600".into(),
        storage: "#ff3366".into(),
        network: "#ff00ff".into(),
        mobo: "#9933ff".into(),
        warning: "#ffff00".into(),
        critical: "#ff0033".into(),
    }
}

/// Retorna tema pelo nome.
pub fn get_theme(name: &str) -> Theme {
    match name.to_lowercase().as_str() {
        "light" => light_theme(),
        "high_contrast" => high_contrast_theme(),
        "cyberpunk" => cyberpunk_theme(),
        _ => dark_theme(),
    }
}

/// Nomes de temas disponíveis.
pub fn theme_names() -> Vec<&'static str> {
    vec!["dark", "light", "high_contrast", "cyberpunk"]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hex_to_rgb_valid() {
        assert_eq!(hex_to_rgb("#ff0000"), (255, 0, 0));
        assert_eq!(hex_to_rgb("#00ff88"), (0, 255, 136));
        assert_eq!(hex_to_rgb("1a1a1a"), (26, 26, 26));
    }

    #[test]
    fn all_themes_load() {
        for name in theme_names() {
            let t = get_theme(name);
            assert_eq!(t.name, name);
        }
    }

    #[test]
    fn unknown_theme_returns_dark() {
        let t = get_theme("nonexistent");
        assert_eq!(t.name, "dark");
    }
}
