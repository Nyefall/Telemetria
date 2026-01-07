"""
Teste rápido do HardwareMonitor
Execute como administrador para acesso completo aos sensores.
"""
import json
import os
from hardware_monitor import HardwareMonitor

# Arquivo de saída
output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output.txt")

print("Inicializando HardwareMonitor...")
monitor = HardwareMonitor()

output_lines = []

def log(msg):
    print(msg)
    output_lines.append(msg)

if not monitor.enabled:
    log("ERRO: Monitor não habilitado!")
else:
    log("\nColetando dados...")
    data = monitor.fetch_data()
    
    log("\n" + "=" * 60)
    log("DADOS COLETADOS:")
    log("=" * 60)
    log(json.dumps(data, indent=2))
    
    log("\n" + "=" * 60)
    log("RESUMO:")
    log("=" * 60)
    log(f"CPU Temp: {data['cpu']['temp']}°C")
    log(f"CPU Voltage: {data['cpu']['voltage']}V")
    log(f"CPU Power: {data['cpu']['power']}W")
    log(f"CPU Clock: {data['cpu']['clock']}MHz")
    log("")
    log(f"GPU Temp: {data['gpu']['temp']}°C")
    log(f"GPU Load: {data['gpu']['load']}%")
    log(f"GPU Voltage: {data['gpu']['voltage']}V")
    log(f"GPU Clock Core: {data['gpu']['clock_core']}MHz")
    log(f"GPU Power: {data['gpu']['power']}W")
    log(f"GPU Fan: {data['gpu']['fan']}RPM")
    log("")
    log(f"MOBO Temp: {data['mobo']['temp']}°C")
    log(f"MOBO +12V: {data['mobo']['voltage_12v']}V")
    log(f"MOBO +5V: {data['mobo']['voltage_5v']}V")
    log(f"MOBO +3.3V: {data['mobo']['voltage_3v']}V")
    log("")
    log(f"Storage: {len(data['storage'])} disco(s) detectado(s)")
    for disk in data['storage']:
        log(f"  - {disk['name']}: Temp={disk['temp']}°C, Health={disk['health']}%")
    log("")
    log(f"Fans: {len(data['fans'])} ventoinhas detectadas")
    for fan in data['fans']:
        log(f"  - {fan['name']}: {fan['rpm']}RPM")
    
    monitor.close()
    
    # Salva em arquivo
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print(f"\nSaída salva em: {output_file}")

input("\nPressione ENTER para sair...")
