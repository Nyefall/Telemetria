//! # Telemetry Core
//!
//! Crate compartilhada que define as estruturas de dados, protocolo de
//! serialização binária (bincode), configuração TOML e constantes do
//! sistema de Telemetria.
//!
//! ## Módulos
//! - [`types`] – Structs de telemetria (CPU, GPU, RAM, Storage, Network…)
//! - [`protocol`] – Encode/decode binário com magic byte
//! - [`config`] – Configuração unificada via TOML
//! - [`theme`] – Definição de temas (Dark, Light, Cyberpunk…)
//! - [`alerts`] – Thresholds e níveis de alerta

pub mod types;
pub mod protocol;
pub mod config;
pub mod theme;
pub mod alerts;

// Re-exports convenientes
pub use types::TelemetryPayload;
pub use protocol::{encode_payload, decode_payload, PROTOCOL_VERSION};
pub use config::{AppConfig, SenderConfig, ReceiverConfig};
