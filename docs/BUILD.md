# Telemetry - Build Scripts

## Generating Executables

### Requirements
```bash
pip install pyinstaller
```

### Unified Build (Recommended)
```bash
python scripts/build_unified.py
```
Generates: `dist/Telemetria.exe`

### Legacy Builds

#### Sender Build (PC)
```bash
python scripts/build_sender.py
```
Generates: `dist/TelemetriaSender.exe`

#### Receiver Build (Laptop)
```bash
python scripts/build_receiver.py
```
Generates: `dist/TelemetriaReceiver.exe`

#### Build Both
```bash
python scripts/build_all.py
```

## Executables

- **Telemetria.exe** - Unified executable with mode selection (recommended)
- **TelemetriaSender.exe** - Run on PC (requires admin for sensors) [legacy]
- **TelemetriaReceiver.exe** - Run on laptop [legacy]

## Configuration

Edit `config.json` (sender) or press `S` on receiver to open settings.

## Output Structure

```
dist/
├── Telemetria.exe      # Main executable
├── config.json         # Sender configuration
├── libs/               # LibreHardwareMonitor DLLs
│   ├── LibreHardwareMonitorLib.dll
│   └── HidSharp.dll
└── README.txt          # Quick guide
```

## Troubleshooting

### "Module not found" errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Large executable size
PyInstaller bundles all dependencies. To reduce size:
- Use `--exclude-module` for unused modules
- Consider UPX compression (add `--upx-dir` flag)

### Missing DLLs
Ensure `libs/` folder is copied to `dist/` after build.
