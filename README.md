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
Pressione `I` na interface para configurar:
- Modo: Automático (broadcast) ou Manual (IP fixo)
- IP do Sender
- Porta UDP

## ⌨️ Atalhos do Receiver

| Tecla | Função |
|-------|--------|
| `F` / `F11` | Fullscreen |
| `G` | Mostrar/ocultar gráficos |
| `T` | Alternar tema (escuro/claro) |
| `L` | Ativar/desativar log CSV |
| `I` | Configurar IP/Porta |
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
