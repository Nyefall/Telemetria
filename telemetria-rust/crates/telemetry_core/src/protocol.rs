//! Protocolo de comunicação binário.
//!
//! Substitui o esquema JSON+GZIP do Python por bincode puro.
//! Formato do frame:
//!
//! ```text
//! ┌──────────┬─────────┬──────────────┐
//! │ Magic(1) │ Ver.(1) │ Payload (N)  │
//! └──────────┴─────────┴──────────────┘
//! ```
//!
//! - Magic byte `0xTE` (0x54) identifica pacote Telemetria-Rust
//! - Versão do protocolo (1 byte)
//! - Payload serializado com bincode (sem compressão necessária)

use crate::types::TelemetryPayload;

/// Magic byte que identifica pacotes do protocolo Rust.
/// Diferente do `0x00`/`0x01` do Python para evitar colisão.
pub const MAGIC_BYTE: u8 = 0x54; // 'T'

/// Versão atual do protocolo.
pub const PROTOCOL_VERSION: u8 = 1;

/// Tamanho do header (magic + version).
const HEADER_SIZE: usize = 2;

/// Tamanho máximo de pacote UDP seguro (sem fragmentação).
pub const MAX_UDP_PAYLOAD: usize = 65507;

/// Erros do protocolo.
#[derive(Debug, thiserror::Error)]
pub enum ProtocolError {
    #[error("Pacote muito curto ({0} bytes, mínimo {HEADER_SIZE})")]
    TooShort(usize),

    #[error("Magic byte inválido: 0x{0:02X} (esperado 0x{MAGIC_BYTE:02X})")]
    InvalidMagic(u8),

    #[error("Versão incompatível: {0} (suportada: {PROTOCOL_VERSION})")]
    VersionMismatch(u8),

    #[error("Erro de serialização: {0}")]
    Serialize(String),

    #[error("Erro de deserialização: {0}")]
    Deserialize(String),
}

/// Codifica um [`TelemetryPayload`] para transmissão UDP.
///
/// Retorna bytes no formato: `[MAGIC][VERSION][bincode_payload...]`
pub fn encode_payload(payload: &TelemetryPayload) -> Result<Vec<u8>, ProtocolError> {
    let body = bincode::serialize(payload).map_err(|e| ProtocolError::Serialize(e.to_string()))?;

    let mut frame = Vec::with_capacity(HEADER_SIZE + body.len());
    frame.push(MAGIC_BYTE);
    frame.push(PROTOCOL_VERSION);
    frame.extend_from_slice(&body);

    Ok(frame)
}

/// Decodifica bytes recebidos via UDP em [`TelemetryPayload`].
///
/// Valida magic byte e versão antes de deserializar.
pub fn decode_payload(data: &[u8]) -> Result<TelemetryPayload, ProtocolError> {
    if data.len() < HEADER_SIZE {
        return Err(ProtocolError::TooShort(data.len()));
    }

    let magic = data[0];
    if magic != MAGIC_BYTE {
        return Err(ProtocolError::InvalidMagic(magic));
    }

    let version = data[1];
    if version != PROTOCOL_VERSION {
        return Err(ProtocolError::VersionMismatch(version));
    }

    let payload_bytes = &data[HEADER_SIZE..];
    bincode::deserialize(payload_bytes).map_err(|e| ProtocolError::Deserialize(e.to_string()))
}

/// Retorna estatísticas do payload para debug.
pub fn payload_stats(payload: &TelemetryPayload) -> PayloadStats {
    let encoded = encode_payload(payload).unwrap_or_default();
    // Para comparação: simula o tamanho JSON
    let json_estimate = 600; // Estimativa baseada no Python original
    PayloadStats {
        binary_size: encoded.len(),
        json_estimate,
        reduction_percent: if json_estimate > 0 {
            ((1.0 - encoded.len() as f64 / json_estimate as f64) * 100.0) as f32
        } else {
            0.0
        },
    }
}

/// Estatísticas de tamanho de payload.
#[derive(Debug, Clone)]
pub struct PayloadStats {
    pub binary_size: usize,
    pub json_estimate: usize,
    pub reduction_percent: f32,
}

// ──────────────────────────────────────────────
// Testes
// ──────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::*;

    fn sample_payload() -> TelemetryPayload {
        TelemetryPayload {
            cpu: CpuData {
                usage: 45.5,
                temp: 72.3,
                voltage: 1.125,
                power: 88.4,
                clock: 4500.0,
            },
            gpu: GpuData {
                load: 95.0,
                temp: 78.0,
                voltage: 0.987,
                clock_core: 2100.0,
                clock_mem: 8000.0,
                fan: 1800.0,
                mem_used_mb: 6144.0,
            },
            mobo: MoboData { temp: 38.5 },
            ram: RamData {
                percent: 65.0,
                used_gb: 20.8,
                total_gb: 32.0,
            },
            storage: vec![StorageData {
                name: "Samsung SSD 970 EVO".into(),
                temp: 42.0,
                health: 97.0,
                used_space: 73.5,
                ..Default::default()
            }],
            fans: vec![FanData {
                name: "CPU Fan".into(),
                rpm: 1200.0,
            }],
            network: NetworkData {
                down_kbps: 5432.1,
                up_kbps: 1234.5,
                ping_ms: 8.2,
                link_speed_mbps: 1000,
                adapter_name: "Ethernet".into(),
            },
        }
    }

    #[test]
    fn encode_decode_roundtrip() {
        let original = sample_payload();
        let encoded = encode_payload(&original).unwrap();
        let decoded = decode_payload(&encoded).unwrap();
        assert_eq!(original, decoded);
    }

    #[test]
    fn header_is_correct() {
        let payload = TelemetryPayload::default();
        let encoded = encode_payload(&payload).unwrap();
        assert_eq!(encoded[0], MAGIC_BYTE);
        assert_eq!(encoded[1], PROTOCOL_VERSION);
    }

    #[test]
    fn rejects_invalid_magic() {
        let payload = TelemetryPayload::default();
        let mut encoded = encode_payload(&payload).unwrap();
        encoded[0] = 0xFF;
        assert!(matches!(
            decode_payload(&encoded),
            Err(ProtocolError::InvalidMagic(0xFF))
        ));
    }

    #[test]
    fn rejects_short_packet() {
        assert!(matches!(
            decode_payload(&[0x54]),
            Err(ProtocolError::TooShort(1))
        ));
    }

    #[test]
    fn rejects_wrong_version() {
        let payload = TelemetryPayload::default();
        let mut encoded = encode_payload(&payload).unwrap();
        encoded[1] = 99;
        assert!(matches!(
            decode_payload(&encoded),
            Err(ProtocolError::VersionMismatch(99))
        ));
    }

    #[test]
    fn binary_is_compact() {
        let payload = sample_payload();
        let stats = payload_stats(&payload);
        println!(
            "Binary: {} bytes | JSON estimate: {} bytes | Reduction: {:.1}%",
            stats.binary_size, stats.json_estimate, stats.reduction_percent
        );
        assert!(
            stats.binary_size < 300,
            "Payload bincode deveria ser < 300 bytes, got {}",
            stats.binary_size
        );
    }

    #[test]
    fn empty_payload_roundtrip() {
        let original = TelemetryPayload::default();
        let encoded = encode_payload(&original).unwrap();
        let decoded = decode_payload(&encoded).unwrap();
        assert_eq!(original, decoded);
    }
}
