# Telemetria - Build Scripts

## Gerando executáveis

### Requisitos
```bash
pip install pyinstaller
```

### Build do Sender (PC)
```bash
python scripts/build_sender.py
```
Gera: `dist/TelemetriaSender.exe`

### Build do Receiver (Notebook)
```bash
python scripts/build_receiver.py
```
Gera: `dist/TelemetriaReceiver.exe`

### Build ambos
```bash
python scripts/build_all.py
```

## Executáveis
- **TelemetriaSender.exe** - Execute no PC (requer admin para sensores)
- **TelemetriaReceiver.exe** - Execute no notebook

## Configuração
Edite `config.json` (sender) ou use tecla `I` no receiver para configurar IP/porta.
