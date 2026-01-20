# 📡 Sistema de Telemetria de Hardware

Sistema de monitoramento em tempo real de hardware (CPU, GPU, RAM, Storage) com comunicação UDP entre dispositivos Windows.

## 🎯 Características

- ✅ **Executável unificado** - Um único .exe com seleção de modo (Sender/Receiver)
- ✅ Monitoramento em tempo real via LibreHardwareMonitor
- ✅ Comunicação UDP (broadcast ou IP fixo)
- ✅ Compressão gzip com magic byte protocol
- ✅ Interface gráfica com temas claro/escuro
- ✅ System Tray no sender
- ✅ Log CSV de histórico
- ✅ Notificações Windows
- ✅ Standalone - não requer instalação de Python

## 📁 Estrutura do Projeto

```
Telemetria/
├── telemetria.py             # Launcher unificado (ponto de entrada)
├── sender_pc.py              # Código do Sender
├── receiver_notebook.py      # Código do Receiver
├── hardware_monitor.py       # Interface LibreHardwareMonitor
├── config.json               # Configuração do sender
├── requirements.txt          # Dependências Python
├── README.md                 # Este arquivo
│
├── libs/                     # DLLs do LibreHardwareMonitor
├── logs/                     # Logs CSV (gerados)
│
├── scripts/                  # Scripts de build e execução
│   ├── build_unified.py      # Build do executável
│   └── RUN_TELEMETRIA.bat    # Launcher batch
│
├── tests/                    # Scripts de teste e debug
│   ├── test_admin_sensors.py
│   ├── test_connectivity.py
│   └── ...
│
├── docs/                     # Documentação
│   └── BUILD.md
│
└── dist/                     # Executável gerado
    ├── Telemetria.exe        # Executável unificado (29 MB)
    ├── config.json           # Config do Sender
    └── libs/                 # DLLs necessárias
```

## 🚀 Início Rápido

### Usando o Executável Unificado (.exe)

1. **Execute `Telemetria.exe`**
2. **Selecione o modo:**
   - 💻 **SENDER** - Para o PC que será monitorado (requer Admin)
   - 📊 **RECEIVER** - Para o dispositivo que exibirá o dashboard

**No PC (Sender):**
- Clique em "SENDER (PC Principal)"
- Aceite a solicitação de privilégios de Administrador
- O programa ficará na bandeja do sistema

**No Notebook (Receiver):**
- Clique em "RECEIVER (Dashboard)"
- Pressione `I` para configurar o IP do PC (se necessário)

### Usando Python (Desenvolvimento)

**Instalação:**
```bash
git clone https://github.com/Nyefall/Telemetria.git
cd Telemetria
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Executar:**
```bash
# Launcher unificado
python telemetria.py

# Ou diretamente
python sender_pc.py      # Sender
python receiver_notebook.py  # Receiver
```

## ⚙️ Configuração

### Sender (PC)
Edite `config.json`:
```json
{
    "modo": "broadcast",
    "dest_ip": "255.255.255.255",
    "porta": 5005,
    "intervalo": 0.5,
    "bind_ip": "192.168.10.101"
}
```

- `bind_ip`: IP da interface local para enviar (força Ethernet vs VPN)
- `modo`: "broadcast" (auto) ou "unicast" (IP fixo)

### Receiver (Notebook)
Pressione `S` na interface para abrir as **Configurações Gerais**, ou edite `receiver_config.json`:

```json
{
    "porta": 5005,
    "sender_ip": "",
    "modo": "auto",
    "expected_link_speed_mbps": 1000,
    
    "tema": "dark",
    "cores_customizadas": {
        "cpu": "#00ff88",
        "gpu": "",
        "ram": "#ffa500"
    },
    
    "alertas": {
        "cpu_temp_warning": 70,
        "cpu_temp_critical": 85,
        "gpu_temp_warning": 75,
        "gpu_temp_critical": 90
    },
    
    "webhooks": {
        "enabled": true,
        "telegram_bot_token": "123:ABC...",
        "telegram_chat_id": "987654321",
        "discord_webhook_url": "",
        "ntfy_topic": "meu-pc-telemetria"
    },
    
    "sons": {
        "enabled": true,
        "cooldown_seconds": 10
    }
}
```

#### Opções de Configuração do Receiver

| Categoria | Opção | Descrição |
|-----------|-------|-----------|
| **Conexão** | `modo` | `auto` (broadcast) ou `manual` (IP fixo) |
| | `sender_ip` | IP do PC sender (vazio para broadcast) |
| | `porta` | Porta UDP (padrão: 5005) |
| **Aparência** | `tema` | `dark`, `light`, `high_contrast`, `cyberpunk` |
| | `cores_customizadas` | Cores hex por setor (ex: `#00ff88`) |
| **Alertas** | `cpu_temp_warning/critical` | Thresholds de temperatura CPU |
| | `gpu_temp_warning/critical` | Thresholds de temperatura GPU |
| | `ram_warning/critical` | Thresholds de uso RAM |
| **Sons** | `enabled` | Ativar sons de alerta |
| | `cooldown_seconds` | Intervalo mínimo entre sons |
| **Webhooks** | `telegram_bot_token` | Token do bot Telegram |
| | `discord_webhook_url` | URL do webhook Discord |
| | `ntfy_topic` | Topic do ntfy.sh (push gratuito) |

## ⌨️ Atalhos do Receiver

| Tecla | Função |
|-------|--------|
| `F` / `F11` | Fullscreen |
| `G` | Mostrar/ocultar gráficos |
| `T` | Alternar tema (escuro/claro) |
| `L` | Ativar/desativar log CSV |
| `S` | ⚙️ **Configurações Gerais** (Conexão, Aparência, Alertas, Notificações) |
| `I` | Configurar IP/Porta (atalho para configurações) |
| `Q` / `ESC` | Sair |

## 🔧 Build do Executável

**Instalar PyInstaller:**
```bash
pip install pyinstaller
```

**Build do executável unificado:**
```bash
python scripts/build_unified.py
```

Gera um único `Telemetria.exe` (~29 MB) com seleção de modo Sender/Receiver.

Os executáveis ficam em `dist/`

## 🧪 Testes

```bash
# Teste de sensores (requer admin)
scripts\run_test_admin.bat

# Teste de conectividade
python tests/test_connectivity.py

# Teste de recepção rápida
python tests/test_receiver_quick.py
```

## 📊 Sensores Monitorados

### CPU
- Uso (%)
- Temperatura (°C)
- Voltagem (V)
- Clock (MHz)
- Potência (W)

### GPU
- Carga (%)
- Temperatura (°C)
- Clock Core/Memory (MHz)
- VRAM Usada (MB)
- Velocidade do Fan (RPM)

### RAM
- Uso (%)
- Usada/Total (GB)

### Storage
- Temperatura (°C)
- Saúde (%)
- Atividade de leitura/escrita (%)
- Throughput (KB/s)

### Rede
- Download/Upload (KB/s)
- Ping (ms)

## 🛠️ Tecnologias

- **Python 3.8+**
- **LibreHardwareMonitor** (sensores de hardware)
- **pythonnet** (interface .NET)
- **psutil** (métricas de sistema)
- **tkinter** (interface gráfica)
- **pystray** (system tray)
- **win10toast** (notificações Windows)
- **gzip** (compressão de dados)

## 📝 Protocolo de Comunicação

**Magic Byte:**
- `0x01` + dados → Payload comprimido com gzip
- `0x00` + dados → Payload JSON raw

**Payload JSON:**
```json
{
  "cpu": {"usage": 45.2, "temp": 62.0, ...},
  "gpu": {"load": 30.0, "temp": 55.0, ...},
  "ram": {"percent": 72.5, ...},
  "storage": [...],
  "network": {"ping_ms": 12.0, ...}
}
```

## ⚠️ Requisitos

- **Windows** (LibreHardwareMonitor é Windows-only)
- **Privilégios de Administrador** no sender (para sensores de hardware)
- **Mesma rede local** (ou configurar IP manual)
- **Porta UDP 5005** liberada no firewall

## 📄 Licença

MIT License

## 👤 Autor

Desenvolvido por [@Nyefall](https://github.com/Nyefall)

---

**Dica:** Para debug, use os scripts em `tests/` para verificar sensores, conectividade e recepção de pacotes.
