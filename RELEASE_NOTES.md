# 📡 Telemetry v2.0 - Unified Executable

## 🎯 What's New

- **Single executable** - One `Telemetria.exe` with mode selection (Sender/Receiver)
- **Selection interface** - Graphical launcher to choose between Main PC or Dashboard
- **Smart auto-elevation** - Requests Admin privileges only for Sender
- **Optimized size** - 29 MB (previously 51 MB in 2 separate files)

## 📦 Download Contents

```
Telemetria-v2.0-Windows.zip
├── Telemetria.exe    # Unified executable
├── config.json       # Sender configuration
├── libs/             # LibreHardwareMonitor DLLs
└── README.txt        # Quick start guide
```

## 🚀 How to Use

### On Main PC (Sender)
1. Extract the ZIP
2. Run `Telemetria.exe`
3. Click **"SENDER (Main PC)"**
4. Accept the Administrator privileges request
5. The program will minimize to the system tray

### On Laptop/Other PC (Receiver)
1. Copy `Telemetria.exe` to the device
2. Run and click **"RECEIVER (Dashboard)"**
3. Press `I` to configure the PC's IP (if needed)

## ⌨️ Dashboard Shortcuts

| Key | Function |
|-----|----------|
| `I` | Configure Sender IP/Port |
| `T` | Toggle theme (dark/light) |
| `L` | Enable/disable CSV logging |
| `G` | Show/hide graphs |
| `F` | Fullscreen |
| `Q` / `ESC` | Quit |

## 📊 Monitored Sensors

- **CPU**: Usage, Temperature, Voltage, Clock, Power
- **GPU**: Load, Temperature, Clock, VRAM, Fan RPM
- **RAM**: Usage percentage, Used/Total
- **Storage**: Temperature, Health, Activity, Throughput
- **Network**: Download/Upload, Ping

## ⚠️ Requirements

- Windows 10/11
- Same local network (or manual IP configuration)
- UDP port 5005 allowed in firewall
- Administrator privileges on Sender

## 🔧 Advanced Configuration

### Force network interface (VPN active)
Edit `config.json` and set `bind_ip` to your Ethernet interface IP:
```json
{
    "bind_ip": "192.168.10.101"
}
```

---

**Developed by [@Nyefall](https://github.com/Nyefall)**
