# 📡 Hardware Telemetry System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Real-time hardware monitoring system over local network. Collects CPU, GPU, RAM, and Storage metrics from a PC and transmits them via UDP for visualization on other devices.

## 🎯 What This Project Does

```
┌─────────────────┐         UDP          ┌─────────────────┐
│   GAMING PC     │  ───────────────────▶│    LAPTOP       │
│   (Sender)      │     port 5005        │   (Receiver)    │
│                 │                      │                 │
│ • CPU 65°C      │                      │ • Dashboard     │
│ • GPU 72°C      │                      │ • Graphs        │
│ • RAM 68%       │                      │ • Alerts        │
└─────────────────┘                      └─────────────────┘
```

<img width="1707" height="861" alt="Captura de tela 2026-02-02 234353" src="https://github.com/user-attachments/assets/fbde002a-d855-43dc-b0d5-0c1e2268d2ac" /> <img width="596" height="646" alt="image" src="https://github.com/user-attachments/assets/dbc6b20f-5d70-4a3f-89a4-b1175092efef" /> <img width="594" height="644" alt="Captura de tela 2026-02-02 234521" src="https://github.com/user-attachments/assets/9e31a4e2-580f-440f-886d-4a42df060038" /> <img width="597" height="646" alt="Captura de tela 2026-02-02 234504" src="https://github.com/user-attachments/assets/4039fb5a-293c-4e9e-b560-0c93055939eb" /> <img width="598" height="647" alt="Captura de tela 2026-02-02 234437" src="https://github.com/user-attachments/assets/ff4cafc8-346c-4d53-b19f-6c9223aaf87f" /> <img width="596" height="650" alt="Captura de tela 2026-02-02 234412" src="https://github.com/user-attachments/assets/81c4f4c3-a108-4a30-b166-28515df55e54" />

**Key Features:**
- Real-time monitoring of CPU, GPU, RAM, Storage, and Network
- Desktop GUI (Tkinter) and Web interface (FastAPI)
- Alerts via sound, Telegram, Discord, and ntfy.sh
- History logging in CSV and SQLite
- Themes: Dark, Light, High Contrast, Cyberpunk

## 🛠️ Technologies Used

| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **Python 3.10+** | Main language | Fast prototyping and native Windows integration |
| **LibreHardwareMonitor** | Sensor reading | Only open-source solution for hardware sensors on Windows |
| **pythonnet** | .NET → Python bridge | Required to consume LibreHardwareMonitor DLL |
| **tkinter** | Desktop GUI | Bundled with Python, zero external dependencies |
| **FastAPI** | Web interface | Lightweight and modern REST API framework |
| **SQLite** | Persistence | Embedded database, no installation required |
| **gzip** | UDP compression | Reduces packet size by ~60% |

<img width="405" height="406" alt="image" src="https://github.com/user-attachments/assets/30d1177a-e11d-4c03-8a01-e1086691b1d1" />

## 🚀 How to Run

### Prerequisites
- Windows 10/11
- Python 3.10+
- Administrator privileges (Sender)

### Installation

```bash
git clone https://github.com/Nyefall/Telemetria.git
cd Telemetria
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Execution

```bash
# Launcher with mode selection
python telemetria.py

# Or directly:
python sender_pc.py           # Monitored PC (requires Admin)
python receiver_notebook.py   # Dashboard
```

### Web Interface (optional)

```bash
pip install fastapi uvicorn
python -m web.server
# Access http://localhost:8080
```

## 📁 Project Structure

```
Telemetria/
├── telemetria.py           # Unified launcher
├── sender_pc.py            # Data collection and transmission
├── receiver_notebook.py    # Tkinter dashboard
├── hardware_monitor.py     # LibreHardwareMonitor interface
├── core/                   # Modules: config, protocol, alerts, history
├── ui/                     # Themes and widgets
├── web/                    # FastAPI server
├── libs/                   # LibreHardwareMonitor DLLs
└── config.json             # Configuration
```

## ⚙️ Configuration

### Sender (`config.json`)
```json
{
    "modo": "broadcast",
    "porta": 5005,
    "intervalo": 0.5,
    "bind_ip": "192.168.10.101"
}
```

### Receiver (`receiver_config.json`)
```json
{
    "porta": 5005,
    "tema": "dark",
    "alertas": {
        "cpu_temp_critical": 85,
        "gpu_temp_critical": 90
    },
    "webhooks": {
        "telegram_bot_token": "TOKEN",
        "ntfy_topic": "my-pc"
    }
}
```

## ⌨️ Keyboard Shortcuts (Receiver)

| Key | Function |
|-----|----------|
| `S` | Settings |
| `T` | Toggle theme |
| `G` | Show/hide graphs |
| `F` | Fullscreen |
| `L` | Enable CSV logging |
| `Q` | Quit |

## 📊 Collected Metrics

| Component | Data |
|-----------|------|
| **CPU** | Usage, Temperature, Clock, Power |
| **GPU** | Load, Temperature, VRAM, Fan RPM |
| **RAM** | Usage percentage, GB used |
| **Storage** | Temperature, Health, Throughput |
| **Network** | Download/Upload, Ping |

## 🔧 Building the Executable

```bash
pip install pyinstaller
python scripts/build_unified.py
# Generates dist/Telemetria.exe (~29 MB)
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

### Third-Party Notice

This software uses the [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) library, licensed under [MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/).

## 👤 Author

[@Nyefall](https://github.com/Nyefall)
