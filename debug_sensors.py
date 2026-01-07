"""
Script de debug para listar todos os sensores disponíveis no LibreHardwareMonitor.
Execute como administrador para ter acesso a todos os sensores.
"""
import os
import sys

# Arquivo de saída
output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sensors_output.txt")

class TeeOutput:
    def __init__(self, file_path):
        self.file = open(file_path, 'w', encoding='utf-8')
        self.stdout = sys.stdout
    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)
    def flush(self):
        self.file.flush()
        self.stdout.flush()
    def close(self):
        self.file.close()

sys.stdout = TeeOutput(output_file)

try:
    import clr
except ImportError:
    print("ERRO: pythonnet não instalado. Execute: pip install pythonnet")
    sys.exit(1)

# Caminho da DLL
base_path = os.path.dirname(os.path.abspath(__file__))
dll_path = os.path.join(base_path, "libs", "LibreHardwareMonitorLib.dll")

if not os.path.exists(dll_path):
    print(f"ERRO: DLL não encontrada em: {dll_path}")
    sys.exit(1)

clr.AddReference(dll_path)
from LibreHardwareMonitor import Hardware

# Inicializa o Computer
computer = Hardware.Computer()
computer.IsCpuEnabled = True
computer.IsGpuEnabled = True
computer.IsMemoryEnabled = True
computer.IsMotherboardEnabled = True
computer.IsStorageEnabled = True
computer.IsNetworkEnabled = True
computer.IsControllerEnabled = True

try:
    computer.Open()
    print("=" * 80)
    print("LISTAGEM COMPLETA DE SENSORES DO SISTEMA")
    print("(Execute como ADMINISTRADOR para ver todos os sensores)")
    print("=" * 80)
    
    for hardware in computer.Hardware:
        hardware.Update()
        hw_type = str(hardware.HardwareType).split('.')[-1]
        
        print(f"\n{'='*60}")
        print(f"HARDWARE: {hardware.Name}")
        print(f"TIPO: {hw_type}")
        print(f"{'='*60}")
        
        # Sensores do hardware principal
        if hardware.Sensors:
            print(f"\n  Sensores diretos ({len(list(hardware.Sensors))}):")
            for sensor in hardware.Sensors:
                s_type = str(sensor.SensorType).split('.')[-1]
                val = sensor.Value if sensor.Value else "N/A"
                print(f"    [{s_type:12}] {sensor.Name}: {val}")
        
        # Sub-hardware (importante para Motherboard/SuperIO)
        for subhw in hardware.SubHardware:
            subhw.Update()
            sub_type = str(subhw.HardwareType).split('.')[-1]
            
            print(f"\n  SUB-HARDWARE: {subhw.Name} ({sub_type})")
            
            if subhw.Sensors:
                for sensor in subhw.Sensors:
                    s_type = str(sensor.SensorType).split('.')[-1]
                    val = sensor.Value if sensor.Value else "N/A"
                    print(f"      [{s_type:12}] {sensor.Name}: {val}")
            
            # Sub-sub hardware (raro, mas possível)
            for subsub in subhw.SubHardware:
                subsub.Update()
                print(f"\n    SUB-SUB: {subsub.Name}")
                for sensor in subsub.Sensors:
                    s_type = str(sensor.SensorType).split('.')[-1]
                    val = sensor.Value if sensor.Value else "N/A"
                    print(f"        [{s_type:12}] {sensor.Name}: {val}")

    computer.Close()
    print("\n" + "=" * 80)
    print("FIM DA LISTAGEM")
    print(f"Saída salva em: {output_file}")
    print("=" * 80)
    
    sys.stdout.close()
    input("Pressione ENTER para sair...")

except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.close()
    input("Pressione ENTER para sair...")
