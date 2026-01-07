# ⚡ Central de Telemetria (PC → Notebook)

Sistema de monitoramento em tempo real que exibe métricas do seu PC Principal em um dashboard dedicado no Notebook, via rede local UDP.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Funcionalidades

### Monitoramento em Tempo Real
- **CPU**: Uso, Temperatura, Voltagem, Consumo (W), Clock
- **GPU**: Uso, Temperatura, Voltagem, Clock Core/Memory, VRAM, Fan RPM
- **RAM**: Uso percentual, GB Usado/Total
- **Storage**: Temperatura, Saúde, Espaço Usado (múltiplos discos)
- **Motherboard**: Temperatura, Fans RPM
- **Rede**: Upload/Download (KB/s), Ping

### Interface
- 🖥️ Dashboard responsivo com 6 painéis
- 📊 Gráficos históricos (últimos 60 segundos)
- 🌙 Tema escuro/claro (tecla `T`)
- 🔔 Notificações Windows para alertas críticos
- 📝 Log de histórico em CSV

### Rede
- 📡 **Broadcast UDP**: Auto-descoberta na rede (zero config!)
- 🔒 **Unicast**: Modo IP fixo disponível
- 📦 **Compactação**: Payload gzip para menor tráfego

## 📋 Pré-requisitos

- **Python 3.8+** em ambas as máquinas
- **Windows 10/11** (usa APIs nativas)
- **Rede local**: Ethernet ou Wi-Fi na mesma rede

## 🚀 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/Nyefall/Telemetria.git
cd Telemetria
```

### 2. Crie um ambiente virtual (recomendado)
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Baixe a DLL do LibreHardwareMonitor
Execute o script auxiliar ou baixe manualmente:
```bash
python download_deps.py
```
> Coloque `LibreHardwareMonitorLib.dll` na pasta `libs/`

## ⚙️ Configuração

O arquivo `config.json` é criado automaticamente na primeira execução:

```json
{
    "modo": "broadcast",
    "dest_ip": "255.255.255.255",
    "porta": 5005,
    "intervalo": 0.5
}
```

| Parâmetro | Descrição |
|-----------|-----------|
| `modo` | `"broadcast"` (auto-descoberta) ou `"unicast"` (IP fixo) |
| `dest_ip` | IP do notebook (ignorado em broadcast) |
| `porta` | Porta UDP (deve ser igual em ambos) |
| `intervalo` | Segundos entre atualizações |

> 💡 **Modo Broadcast**: Não precisa configurar IPs! Sender e Receiver se encontram automaticamente na rede.

## 🎮 Como Usar

### No PC Principal (Sender)

**Opção 1**: Clique duplo no `run_sender_admin.bat` (solicita admin)

**Opção 2**: Execute via terminal como administrador:
```bash
python sender_pc.py
```

> ⚠️ **Importante**: Precisa rodar como administrador para acessar sensores de hardware.

O sender minimiza automaticamente para a **bandeja do sistema** (System Tray).

### No Notebook (Receiver)
```bash
python receiver_notebook.py
```

## ⌨️ Atalhos de Teclado (Receiver)

| Tecla | Ação |
|-------|------|
| `F` ou `F11` | Alternar Fullscreen |
| `G` | Mostrar/Ocultar Gráficos |
| `T` | Alternar Tema (Escuro/Claro) |
| `L` | Ativar/Desativar Log CSV |
| `Q` ou `ESC` | Sair |

## 📁 Estrutura do Projeto

```
Telemetria/
├── sender_pc.py           # Coleta e envia dados (PC)
├── receiver_notebook.py   # Dashboard de exibição (Notebook)
├── hardware_monitor.py    # Interface com LibreHardwareMonitor
├── config.json           # Configurações de rede
├── requirements.txt      # Dependências Python
├── run_sender_admin.bat  # Launcher com elevação admin
├── libs/
│   └── LibreHardwareMonitorLib.dll
└── logs/                 # Logs CSV (criado automaticamente)
```

## 🔧 Solução de Problemas

### "Aguardando dados..." no Receiver
1. Verifique se o Sender está rodando
2. Confira se ambos estão na mesma rede
3. Libere a porta UDP 5005 no Firewall do Windows

### Temperaturas zeradas
- Execute o Sender como **Administrador**
- Verifique se a DLL está em `libs/`

### Interface borrada no notebook
- O DPI Awareness já está habilitado, mas se persistir, ajuste a escala do Windows

## 📜 Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes.

---

Desenvolvido com ☕ e Python
