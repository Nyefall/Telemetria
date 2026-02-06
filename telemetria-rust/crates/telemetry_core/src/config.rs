//! Configuração unificada via TOML.
//!
//! Substitui os múltiplos JSON do Python por um único `config.toml`.

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use tracing::{info, warn};

/// Configuração do Sender (PC principal).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct SenderConfig {
    /// Modo de envio: "broadcast" ou "unicast"
    pub mode: String,
    /// IP de destino (255.255.255.255 para broadcast)
    pub dest_ip: String,
    /// Porta UDP
    pub port: u16,
    /// Intervalo de envio em segundos
    pub interval_secs: f64,
    /// IP local para bind (vazio = auto)
    pub bind_ip: String,
    /// Intervalo para checar link de rede (segundos)
    pub link_check_interval_secs: f64,
}

impl Default for SenderConfig {
    fn default() -> Self {
        Self {
            mode: "broadcast".into(),
            dest_ip: "255.255.255.255".into(),
            port: 5005,
            interval_secs: 0.5,
            bind_ip: String::new(),
            link_check_interval_secs: 10.0,
        }
    }
}

/// Thresholds de alerta para o Receiver.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct AlertThresholds {
    pub cpu_temp_warning: f32,
    pub cpu_temp_critical: f32,
    pub cpu_usage_warning: f32,
    pub cpu_usage_critical: f32,
    pub gpu_temp_warning: f32,
    pub gpu_temp_critical: f32,
    pub gpu_usage_warning: f32,
    pub gpu_usage_critical: f32,
    pub ram_warning: f32,
    pub ram_critical: f32,
    pub storage_temp_warning: f32,
    pub storage_temp_critical: f32,
    pub storage_usage_warning: f32,
    pub storage_usage_critical: f32,
    pub ping_warning: f32,
    pub ping_critical: f32,
}

impl Default for AlertThresholds {
    fn default() -> Self {
        Self {
            cpu_temp_warning: 70.0,
            cpu_temp_critical: 85.0,
            cpu_usage_warning: 70.0,
            cpu_usage_critical: 90.0,
            gpu_temp_warning: 75.0,
            gpu_temp_critical: 90.0,
            gpu_usage_warning: 80.0,
            gpu_usage_critical: 95.0,
            ram_warning: 70.0,
            ram_critical: 90.0,
            storage_temp_warning: 45.0,
            storage_temp_critical: 55.0,
            storage_usage_warning: 80.0,
            storage_usage_critical: 95.0,
            ping_warning: 50.0,
            ping_critical: 100.0,
        }
    }
}

/// Configuração de sons de alerta.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct SoundConfig {
    pub enabled: bool,
    pub cooldown_seconds: f64,
    pub warning_sound: String,
    pub critical_sound: String,
}

impl Default for SoundConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            cooldown_seconds: 10.0,
            warning_sound: "warning".into(),
            critical_sound: "beep_urgent".into(),
        }
    }
}

/// Configuração de webhooks (Telegram, Discord, ntfy).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct WebhookConfig {
    pub enabled: bool,
    pub telegram_bot_token: String,
    pub telegram_chat_id: String,
    pub discord_webhook_url: String,
    pub ntfy_topic: String,
    pub ntfy_server: String,
    pub cooldown_seconds: u64,
}

impl Default for WebhookConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            telegram_bot_token: String::new(),
            telegram_chat_id: String::new(),
            discord_webhook_url: String::new(),
            ntfy_topic: String::new(),
            ntfy_server: "https://ntfy.sh".into(),
            cooldown_seconds: 300,
        }
    }
}

/// Configuração de histórico.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct HistoryConfig {
    pub csv_enabled: bool,
    pub auto_start_log: bool,
    pub retention_days: u32,
}

impl Default for HistoryConfig {
    fn default() -> Self {
        Self {
            csv_enabled: false,
            auto_start_log: false,
            retention_days: 7,
        }
    }
}

/// Cores customizadas por componente (override do tema).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct CustomColors {
    pub cpu: String,
    pub gpu: String,
    pub ram: String,
    pub storage: String,
    pub network: String,
    pub mobo: String,
}

/// Configuração do Receiver (Dashboard).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct ReceiverConfig {
    /// Porta UDP para escutar
    pub port: u16,
    /// IP do sender (vazio = broadcast/auto)
    pub sender_ip: String,
    /// Modo: "auto" ou "manual"
    pub mode: String,
    /// Velocidade esperada do link (Mbps)
    pub expected_link_speed_mbps: u32,
    /// Tema: "dark", "light", "high_contrast", "cyberpunk"
    pub theme: String,
    /// Cores customizadas
    pub custom_colors: CustomColors,
    /// Thresholds de alerta
    pub alerts: AlertThresholds,
    /// Sons
    pub sounds: SoundConfig,
    /// Webhooks
    pub webhooks: WebhookConfig,
    /// Histórico
    pub history: HistoryConfig,
}

impl Default for ReceiverConfig {
    fn default() -> Self {
        Self {
            port: 5005,
            sender_ip: String::new(),
            mode: "auto".into(),
            expected_link_speed_mbps: 1000,
            theme: "dark".into(),
            custom_colors: CustomColors::default(),
            alerts: AlertThresholds::default(),
            sounds: SoundConfig::default(),
            webhooks: WebhookConfig::default(),
            history: HistoryConfig::default(),
        }
    }
}

/// Configuração raiz do aplicativo (unifica sender e receiver).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct AppConfig {
    pub sender: SenderConfig,
    pub receiver: ReceiverConfig,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            sender: SenderConfig::default(),
            receiver: ReceiverConfig::default(),
        }
    }
}

impl AppConfig {
    /// Carrega configuração de um arquivo TOML.
    pub fn load(path: &Path) -> Self {
        if path.exists() {
            match std::fs::read_to_string(path) {
                Ok(content) => match toml::from_str::<AppConfig>(&content) {
                    Ok(config) => {
                        info!("Configuração carregada de {}", path.display());
                        return config;
                    }
                    Err(e) => {
                        warn!("Erro ao parsear {}: {}", path.display(), e);
                    }
                },
                Err(e) => {
                    warn!("Erro ao ler {}: {}", path.display(), e);
                }
            }
        }

        info!("Usando configuração padrão");
        AppConfig::default()
    }

    /// Salva configuração em arquivo TOML.
    pub fn save(&self, path: &Path) -> Result<(), String> {
        let content = toml::to_string_pretty(self).map_err(|e| e.to_string())?;
        std::fs::write(path, content).map_err(|e| e.to_string())?;
        info!("Configuração salva em {}", path.display());
        Ok(())
    }

    /// Retorna o caminho padrão do config.toml.
    pub fn default_path() -> PathBuf {
        let exe_dir = std::env::current_exe()
            .map(|p| p.parent().unwrap_or(Path::new(".")).to_path_buf())
            .unwrap_or_else(|_| PathBuf::from("."));
        exe_dir.join("config.toml")
    }

    /// Valida a configuração e retorna lista de erros.
    pub fn validate(&self) -> Vec<String> {
        let mut errors = Vec::new();

        if self.sender.port == 0 {
            errors.push("Porta do sender não pode ser 0".into());
        }
        if self.sender.interval_secs < 0.1 || self.sender.interval_secs > 60.0 {
            errors.push(format!(
                "Intervalo do sender inválido: {} (0.1–60.0)",
                self.sender.interval_secs
            ));
        }
        if self.receiver.port == 0 {
            errors.push("Porta do receiver não pode ser 0".into());
        }

        errors
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_config_is_valid() {
        let config = AppConfig::default();
        let errors = config.validate();
        assert!(errors.is_empty(), "Erros: {:?}", errors);
    }

    #[test]
    fn roundtrip_toml() {
        let config = AppConfig::default();
        let toml_str = toml::to_string_pretty(&config).unwrap();
        let parsed: AppConfig = toml::from_str(&toml_str).unwrap();
        assert_eq!(config.sender.port, parsed.sender.port);
        assert_eq!(config.receiver.theme, parsed.receiver.theme);
    }

    #[test]
    fn partial_toml_uses_defaults() {
        let partial = r#"
[sender]
port = 9999
"#;
        let config: AppConfig = toml::from_str(partial).unwrap();
        assert_eq!(config.sender.port, 9999);
        // Outros campos devem ter valor padrão
        assert_eq!(config.sender.interval_secs, 0.5);
        assert_eq!(config.receiver.port, 5005);
    }
}
