//! Definição de tipos/structs para telemetria.
//!
//! Porta direta das classes Python para structs Rust com serde.
//! Serialização bincode reduz payload de ~600 bytes (JSON+GZIP) para ~150 bytes.

use serde::{Deserialize, Serialize};

// ──────────────────────────────────────────────
// CPU
// ──────────────────────────────────────────────

/// Dados de CPU coletados pelo Sender.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct CpuData {
    /// Uso total da CPU (0–100%)
    pub usage: f32,
    /// Temperatura do pacote/die (°C)
    pub temp: f32,
    /// Tensão do core (V)
    pub voltage: f32,
    /// Potência consumida (W)
    pub power: f32,
    /// Clock máximo observado (MHz)
    pub clock: f32,
}

// ──────────────────────────────────────────────
// GPU
// ──────────────────────────────────────────────

/// Dados de GPU coletados pelo Sender.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct GpuData {
    /// Carga do GPU core (0–100%)
    pub load: f32,
    /// Temperatura do core (°C)
    pub temp: f32,
    /// Tensão do core (V)
    pub voltage: f32,
    /// Clock do core (MHz)
    pub clock_core: f32,
    /// Clock da memória (MHz)
    pub clock_mem: f32,
    /// Velocidade do fan (RPM)
    pub fan: f32,
    /// VRAM dedicada em uso (MB)
    pub mem_used_mb: f32,
}

// ──────────────────────────────────────────────
// Motherboard
// ──────────────────────────────────────────────

/// Dados de motherboard.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct MoboData {
    /// Temperatura da placa-mãe (°C)
    pub temp: f32,
}

// ──────────────────────────────────────────────
// RAM
// ──────────────────────────────────────────────

/// Dados de memória RAM.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct RamData {
    /// Percentual de uso (0–100%)
    pub percent: f32,
    /// Memória usada (GB)
    pub used_gb: f32,
    /// Memória total (GB)
    pub total_gb: f32,
}

// ──────────────────────────────────────────────
// Storage
// ──────────────────────────────────────────────

/// Dados de um dispositivo de armazenamento.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct StorageData {
    /// Nome do dispositivo (ex: "Samsung SSD 970 EVO")
    pub name: String,
    /// Temperatura (°C)
    pub temp: f32,
    /// Saúde do SSD (0–100%)
    pub health: f32,
    /// Espaço usado (0–100%)
    pub used_space: f32,
    /// Atividade de leitura (%)
    pub read_activity: f32,
    /// Atividade de escrita (%)
    pub write_activity: f32,
    /// Atividade total (%)
    pub total_activity: f32,
    /// Taxa de leitura (bytes/s)
    pub read_rate: f32,
    /// Taxa de escrita (bytes/s)
    pub write_rate: f32,
    /// Total de dados lidos (GB)
    pub data_read_gb: f32,
    /// Total de dados escritos (GB)
    pub data_written_gb: f32,
}

// ──────────────────────────────────────────────
// Fans
// ──────────────────────────────────────────────

/// Dados de um ventilador.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct FanData {
    /// Nome do sensor (ex: "CPU Fan #1")
    pub name: String,
    /// Velocidade (RPM)
    pub rpm: f32,
}

// ──────────────────────────────────────────────
// Network
// ──────────────────────────────────────────────

/// Dados de rede.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct NetworkData {
    /// Download (KB/s)
    pub down_kbps: f32,
    /// Upload (KB/s)
    pub up_kbps: f32,
    /// Latência para 8.8.8.8 (ms)
    pub ping_ms: f32,
    /// Velocidade negociada do link (Mbps)
    pub link_speed_mbps: u32,
    /// Nome do adaptador de rede
    pub adapter_name: String,
}

// ──────────────────────────────────────────────
// Payload completo
// ──────────────────────────────────────────────

/// Payload completo de telemetria transmitido via UDP.
///
/// Corresponde exatamente ao dicionário Python `_build_payload()`.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct TelemetryPayload {
    pub cpu: CpuData,
    pub gpu: GpuData,
    pub mobo: MoboData,
    pub ram: RamData,
    pub storage: Vec<StorageData>,
    pub fans: Vec<FanData>,
    pub network: NetworkData,
}

// ──────────────────────────────────────────────
// Testes
// ──────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_payload_is_zeroed() {
        let p = TelemetryPayload::default();
        assert_eq!(p.cpu.usage, 0.0);
        assert_eq!(p.gpu.load, 0.0);
        assert!(p.storage.is_empty());
        assert!(p.fans.is_empty());
    }

    #[test]
    fn payload_roundtrip_bincode() {
        let payload = TelemetryPayload {
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
                name: "Samsung SSD 970 EVO Plus".into(),
                temp: 42.0,
                health: 97.0,
                used_space: 73.5,
                ..Default::default()
            }],
            fans: vec![FanData {
                name: "CPU Fan #1".into(),
                rpm: 1200.0,
            }],
            network: NetworkData {
                down_kbps: 5432.1,
                up_kbps: 1234.5,
                ping_ms: 8.2,
                link_speed_mbps: 1000,
                adapter_name: "Ethernet".into(),
            },
        };

        let encoded = bincode::serialize(&payload).unwrap();
        let decoded: TelemetryPayload = bincode::deserialize(&encoded).unwrap();

        assert_eq!(payload, decoded);
        // Binário deve ser muito menor que JSON (~150 bytes vs ~600)
        println!("Payload bincode size: {} bytes", encoded.len());
        assert!(encoded.len() < 300, "Bincode payload deve ser compacto");
    }

    #[test]
    fn f32_precision_preserved() {
        let cpu = CpuData {
            voltage: 1.123_456_7,
            ..Default::default()
        };
        let bytes = bincode::serialize(&cpu).unwrap();
        let decoded: CpuData = bincode::deserialize(&bytes).unwrap();
        assert_eq!(cpu.voltage, decoded.voltage);
    }
}
