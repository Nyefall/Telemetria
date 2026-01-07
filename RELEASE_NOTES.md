# 📡 Telemetria v2.0 - Executável Unificado

## 🎯 Novidades

- **Executável único** - Um único `Telemetria.exe` com seleção de modo (Sender/Receiver)
- **Interface de seleção** - Launcher gráfico para escolher entre PC Principal ou Dashboard
- **Auto-elevação inteligente** - Solicita privilégios de Admin apenas para o Sender
- **Tamanho otimizado** - 29 MB (antes eram 51 MB em 2 arquivos separados)

## 📦 Conteúdo do Download

```
Telemetria-v2.0-Windows.zip
├── Telemetria.exe    # Executável unificado
├── config.json       # Configuração do Sender
├── libs/             # DLLs do LibreHardwareMonitor
└── README.txt        # Guia rápido de uso
```

## 🚀 Como Usar

### No PC Principal (Sender)
1. Extraia o ZIP
2. Execute `Telemetria.exe`
3. Clique em **"SENDER (PC Principal)"**
4. Aceite a solicitação de privilégios de Administrador
5. O programa ficará na bandeja do sistema

### No Notebook/Outro PC (Receiver)
1. Copie `Telemetria.exe` para o dispositivo
2. Execute e clique em **"RECEIVER (Dashboard)"**
3. Pressione `I` para configurar o IP do PC (se necessário)

## ⌨️ Atalhos do Dashboard

| Tecla | Função |
|-------|--------|
| `I` | Configurar IP/Porta do Sender |
| `T` | Alternar tema (escuro/claro) |
| `L` | Ativar/desativar log CSV |
| `G` | Mostrar/ocultar gráficos |
| `F` | Fullscreen |
| `Q` / `ESC` | Sair |

## 📊 Sensores Monitorados

- **CPU**: Uso, Temperatura, Voltagem, Clock, Potência
- **GPU**: Carga, Temperatura, Clock, VRAM, Fan RPM
- **RAM**: Uso percentual, Usada/Total
- **Storage**: Temperatura, Saúde, Atividade, Throughput
- **Rede**: Download/Upload, Ping

## ⚠️ Requisitos

- Windows 10/11
- Mesma rede local (ou configuração manual de IP)
- Porta UDP 5005 liberada no firewall
- Privilégios de Administrador no Sender

## 🔧 Configuração Avançada

### Forçar interface de rede (VPN ativa)
Edite `config.json` e configure `bind_ip` com o IP da interface Ethernet:
```json
{
    "bind_ip": "192.168.10.101"
}
```

---

**Desenvolvido por [@Nyefall](https://github.com/Nyefall)**
