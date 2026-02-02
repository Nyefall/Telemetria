# 📡 Sistema de Telemetria de Hardware

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Sistema de monitoramento em tempo real de hardware via rede local. Coleta métricas de CPU, GPU, RAM e Storage de um PC e transmite via UDP para visualização em outros dispositivos.

## 🎯 O Que o Projeto Faz

```
┌─────────────────┐         UDP          ┌─────────────────┐
│   PC GAMER      │  ───────────────────▶│   NOTEBOOK      │
│   (Sender)      │    porta 5005        │   (Receiver)    │
│                 │                      │                 │
│ • CPU 65°C      │                      │ • Dashboard     │
│ • GPU 72°C      │                      │ • Gráficos      │
│ • RAM 68%       │                      │ • Alertas       │
└─────────────────┘                      └─────────────────┘
```

**Principais recursos:**
- Monitoramento em tempo real de CPU, GPU, RAM, Storage e Rede
- Interface gráfica desktop (Tkinter) e web (FastAPI)
- Alertas via som, Telegram, Discord e ntfy.sh
- Histórico em CSV e SQLite
- Temas: Dark, Light, High Contrast, Cyberpunk

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Função | Justificativa |
|------------|--------|---------------|
| **Python 3.10+** | Linguagem principal | Prototipagem rápida e integração nativa com Windows |
| **LibreHardwareMonitor** | Leitura de sensores | Única solução open-source para sensores de hardware no Windows |
| **pythonnet** | Bridge .NET → Python | Permite consumir a DLL do LibreHardwareMonitor |
| **tkinter** | GUI desktop | Incluso no Python, zero dependências externas |
| **FastAPI** | Interface Web | Framework leve e moderno para API REST |
| **SQLite** | Persistência | Banco embutido, não requer instalação |
| **gzip** | Compressão UDP | Reduz ~60% do tamanho dos pacotes |

## 🚀 Como Rodar o Projeto

### Pré-requisitos
- Windows 10/11
- Python 3.10+
- Privilégios de Administrador (Sender)

### Instalação

```bash
git clone https://github.com/Nyefall/Telemetria.git
cd Telemetria
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Execução

```bash
# Launcher com seleção de modo
python telemetria.py

# Ou diretamente:
python sender_pc.py           # PC monitorado (requer Admin)
python receiver_notebook.py   # Dashboard
```

### Interface Web (opcional)

```bash
pip install fastapi uvicorn
python -m web.server
# Acesse http://localhost:8080
```

## 📁 Estrutura do Projeto

```
Telemetria/
├── telemetria.py           # Launcher unificado
├── sender_pc.py            # Coleta e transmissão de dados
├── receiver_notebook.py    # Dashboard Tkinter
├── hardware_monitor.py     # Interface LibreHardwareMonitor
├── core/                   # Módulos: config, protocol, alerts, history
├── ui/                     # Temas e widgets
├── web/                    # Servidor FastAPI
├── libs/                   # DLLs LibreHardwareMonitor
└── config.json             # Configurações
```

## ⚙️ Configuração

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
        "ntfy_topic": "meu-pc"
    }
}
```

## ⌨️ Atalhos (Receiver)

| Tecla | Função |
|-------|--------|
| `S` | Configurações |
| `T` | Alternar tema |
| `G` | Mostrar/ocultar gráficos |
| `F` | Fullscreen |
| `L` | Ativar log CSV |
| `Q` | Sair |

## 📊 Métricas Coletadas

| Componente | Dados |
|------------|-------|
| **CPU** | Uso, Temperatura, Clock, Potência |
| **GPU** | Carga, Temperatura, VRAM, Fan RPM |
| **RAM** | Uso percentual, GB utilizados |
| **Storage** | Temperatura, Saúde, Throughput |
| **Rede** | Download/Upload, Ping |

## 🔧 Build do Executável

```bash
pip install pyinstaller
python scripts/build_unified.py
# Gera dist/Telemetria.exe (~29 MB)
```

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

## 👤 Autor

[@Nyefall](https://github.com/Nyefall)
