# 📡 Telemetria v2.0 — Rust Edition

> Sistema de monitoramento de hardware em tempo real, reescrito em Rust para máxima performance.

## Arquitetura

```
telemetria-rust/
├── crates/
│   ├── telemetry_core/     # Biblioteca compartilhada (tipos, protocolo, config)
│   ├── sender/             # Coleta de hardware + envio UDP
│   └── receiver/           # Dashboard GPU-accelerated (eframe/egui)
├── config.toml             # Configuração unificada
└── Cargo.toml              # Workspace root
```

## Stack Tecnológica

| Componente | Crate | Substitui |
|---|---|---|
| Protocolo | `serde` + `bincode` | JSON + GZIP |
| Monitoramento | `sysinfo` + `wmi` | `psutil` + `LibreHardwareMonitor.dll` |
| GUI | `eframe` / `egui` + `egui_plot` | `tkinter` |
| Rede | `std::net::UdpSocket` | `socket` (Python) |
| Config | `toml` | `json` |
| Logging | `tracing` | `print()` |

## Ganhos de Performance

| Métrica | Python | Rust |
|---|---|---|
| Payload UDP | ~600 bytes (JSON+GZIP) | ~150 bytes (bincode) |
| CPU Sender | 2-5% | <0.5% |
| CPU Receiver | 8-15% (Tkinter) | <2% (GPU-rendered) |
| Memória Receiver | 80-120 MB | 15-30 MB |
| Binário | Python + .NET + DLLs | 2-5 MB standalone |
| Startup | 3-5s | <100ms |

## Build

### Requisitos
- Rust 1.75+ (`rustup` instalado)
- Windows 10/11 (para WMI e sensores de hardware)

### Desenvolvimento
```bash
# Build debug (rápido)
cargo build

# Rodar testes
cargo test

# Rodar sender (requer admin para sensores)
cargo run -p telemetry_sender

# Rodar receiver (dashboard)
cargo run -p telemetry_receiver
```

### Release Otimizado
```bash
# Build com LTO, opt-level 3, strip symbols
cargo build --release

# Binários em: target/release/
#   telemetry_sender.exe   (~2-4 MB)
#   telemetry_receiver.exe (~4-6 MB)
```

## Configuração

Edite `config.toml` (criado automaticamente na primeira execução):

```toml
[sender]
mode = "broadcast"
dest_ip = "255.255.255.255"
port = 5005
interval_secs = 0.5

[receiver]
port = 5005
theme = "dark"    # dark, light, high_contrast, cyberpunk
```

## Atalhos do Dashboard

| Tecla | Ação |
|---|---|
| `G` | Toggle gráficos de histórico |
| `T` | Alternar tema |
| `F` / `F11` | Fullscreen |
| `Q` / `Esc` | Sair |

## Protocolo Binário

O protocolo v2 usa bincode com header de 2 bytes:

```
┌──────────┬─────────┬──────────────┐
│ 0x54 (T) │ Ver.(1) │ Payload (N)  │
└──────────┴─────────┴──────────────┘
```

- Magic byte `0x54` identifica pacotes Telemetria-Rust
- Sem compressão necessária (bincode já é compacto)
- Incompatível com versão Python (protocolo diferente)

## Licença

MIT — Desenvolvido por @Nyefall
