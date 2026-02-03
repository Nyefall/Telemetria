# Changelog - Telemetry System

## v1.2.0 - January 2026 - General Settings

### 🎯 Main Changes

**General Settings (Receiver)**
- ✨ **NEW**: Tabbed settings panel (press `S`)
- 🎨 **Appearance Tab**: 4 themes (Dark, Light, High Contrast, Cyberpunk) + custom colors per sector
- 🔔 **Alerts Tab**: Customizable thresholds for CPU, GPU, RAM, Storage, Ping temperature/usage
- 📱 **Notifications Tab**: Integration with Telegram, Discord, and ntfy.sh (free push)
- 📊 **History Tab**: CSV logging and retention configuration

**Alerts and Notifications**
- ✨ Configurable warning and critical thresholds per metric
- ✨ Configurable cooldown for sounds and webhooks
- ✨ ntfy.sh support for free mobile push notifications

**Appearance**
- ✨ New themes: High Contrast (accessibility) and Cyberpunk
- ✨ Custom colors per sector (CPU, GPU, RAM, etc.) via hex code
- 🎨 Themes persistently saved in `receiver_config.json`

**Files**
- ✨ **NEW**: `receiver_config.example.json` - configuration example
- 📝 Expanded `receiver_config.json` structure with all options

### ⌨️ New Shortcuts

| Key | Function |
|-----|----------|
| `S` | ⚙️ General Settings (new!) |
| `I` | Now opens General Settings (kept for compatibility) |

---

## v1.1.0 - January 2026 - Unified Executable

### 🎯 Main Changes

**Unified Executable**
- ✨ **NEW**: `Telemetria.exe` - single executable with mode selection
- 📱 Graphical launcher interface to choose between Sender or Receiver
- 🎨 Modern design with colored buttons and clear descriptions
- 💾 Optimized size: 29 MB (vs 35+16 MB before)

**Architecture**
- ✨ **NEW**: `telemetria.py` - main launcher
- 🔧 Refactoring: `sender_pc.py` and `receiver_notebook.py` now export `main()`
- 📦 Unified build scripts in `scripts/build_unified.py`

**Documentation**
- 📝 README.md updated with new structure
- 🗑️ Removed README.old.md (obsolete backup)
- 📋 README.txt in dist folder updated for single executable
- ✨ New CHANGELOG.md file for version tracking

**Scripts**
- ✨ **NEW**: `scripts/build_unified.py` - unified executable build
- ✨ **NEW**: `scripts/RUN_TELEMETRIA.bat` - batch launcher
- 📁 Legacy build scripts kept for compatibility

**.gitignore**
- 🧹 Added *.old and *.old.* to ignore backups
- 🧹 Added *.tmp for Windows temp files
- 🧹 General organization improvement

### 📊 Version Comparison

| Aspect | v1.0.0 (Legacy) | v1.1.0 (Unified) |
|--------|-----------------|------------------|
| Executables | 2 separate files | 1 single file |
| Total Size | 51 MB | 29 MB |
| Mode Selection | Manual (2 .exe) | Graphical interface |
| Distribution | Copy 2 files | Copy 1 file |
| Experience | Technical | User-friendly |

### 🔄 Migration from v1.0.0 to v1.1.0

**End users:**
- Replace `TelemetriaSender.exe` and `TelemetriaReceiver.exe` with `Telemetria.exe`
- Keep `config.json` and `libs/` in the same location
- Run and choose the desired mode

**Developers:**
- Source code remains compatible
- New imports: `import sender_pc` and `import receiver_notebook`
- Build: `python scripts/build_unified.py`

### 🐛 Bug Fixes

- No bugs reported in v1.0

### 📦 Release Files

```
dist/
├── Telemetria.exe          ⭐ NEW - Unified executable (29 MB)
├── config.json             Sender configuration
├── libs/                   LibreHardwareMonitor DLLs
├── README.txt              Updated usage guide
├── TelemetriaSender.exe    [LEGACY] Kept for compatibility
└── TelemetriaReceiver.exe  [LEGACY] Kept for compatibility
```

---

## v1.0.0 - January 2026 - Initial Release

### Features

- ✅ Complete hardware monitoring (CPU, GPU, RAM, Storage, Network)
- ✅ LibreHardwareMonitor via pythonnet
- ✅ UDP communication (broadcast + manual IP)
- ✅ Magic byte protocol (0x01 gzip, 0x00 raw)
- ✅ Gzip compression (~50% reduction)
- ✅ System Tray on sender (pystray)
- ✅ Dashboard with light/dark themes
- ✅ CSV history logging
- ✅ Windows notifications (win10toast)
- ✅ Network interface configuration (bind_ip)
- ✅ Auto-elevation to Admin (sender)

### Files

- `sender_pc.py` - Standalone Sender
- `receiver_notebook.py` - Standalone Receiver
- `hardware_monitor.py` - Sensor interface
- `config.json` - Configuration
- `receiver_config.json` - Dynamic receiver config (key I)

### Build

- `scripts/build_sender.py` - Sender build
- `scripts/build_receiver.py` - Receiver build
- `scripts/build_all.py` - Build both

### Tests

- `tests/test_admin_sensors.py` - Sensor verification
- `tests/test_connectivity.py` - UDP network test
- `tests/test_receiver_quick.py` - Reception test

---

## Future Roadmap

### v1.3.0 (Next)
- [ ] Add custom icon to executable
- [ ] WebSocket support for real-time web updates
