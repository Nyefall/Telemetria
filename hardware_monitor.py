import os
import sys

# Tenta importar pythonnet (clr)
try:
    import clr
    HAS_PYTHONNET = True
except ImportError:
    HAS_PYTHONNET = False

class HardwareMonitor:
    def __init__(self):
        self.computer = None
        self.handle = None
        self.enabled = False
        # Caminho absoluto baseado na localização deste script, não onde o terminal abriu
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.dll_path = os.path.join(base_path, "libs", "LibreHardwareMonitorLib.dll")

        if not HAS_PYTHONNET:
            print("[HardwareMonitor] 'pythonnet' não instalado. Rodando em modo limitado.")
            return

        if not os.path.exists(self.dll_path):
            print(f"[HardwareMonitor] DLL não encontrada em: {self.dll_path}")
            print("[HardwareMonitor] Baixe o LibreHardwareMonitor, e coloque 'LibreHardwareMonitorLib.dll' dentro da pasta 'libs'.")
            return

        try:
            # Carrega a DLL
            clr.AddReference(self.dll_path)
            from LibreHardwareMonitor import Hardware
            
            self.computer = Hardware.Computer()
            self.computer.IsCpuEnabled = True
            self.computer.IsGpuEnabled = True
            self.computer.IsMemoryEnabled = True
            self.computer.IsMotherboardEnabled = True
            self.computer.IsControllerEnabled = True
            self.computer.IsNetworkEnabled = True
            self.computer.IsStorageEnabled = True
            
            try:
                self.computer.Open()
                self.enabled = True
                print("[HardwareMonitor] DLL carregada com sucesso! Acesso direto ao hardware ativo.")
            except Exception as e:
                print(f"[HardwareMonitor] Erro ao abrir hardware (Precisa de Admin?): {e}")
                self.computer = None
                
        except Exception as e:
            print(f"[HardwareMonitor] Falha geral ao carregar DLL: {e}")

    def fetch_data(self):
        """
        Retorna um dicionário com cpu_temp, cpu_voltage, gpu_temp, gpu_load, etc.
        """
        data = {
            "cpu_temp": 0,
            "cpu_voltage": 0,
            "cpu_load": 0,
            "cpu_pwr": 0,
            "gpu_temp": 0,
            "gpu_load": 0,
            "gpu_core_clock": 0,
            "gpu_mem_clock": 0
        }

        if not self.enabled or not self.computer:
            return data

        try:
            # É necessário chamar Accept em cada hardware para atualizar sensores
            # O LibreHardwareMonitor usa um padrão Visitor, mas podemos iterar direto
            
            for hardware in self.computer.Hardware:
                hardware.Update() # Atualiza leituras
                
                # --- CPU ---
                if hardware.HardwareType == self.computer.Hardware[0].HardwareType.Cpu: # Comparação genérica
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == sensor.SensorType.Temperature and "Package" in sensor.Name:
                            data["cpu_temp"] = max(data["cpu_temp"], sensor.Value or 0)
                        elif sensor.SensorType == sensor.SensorType.Load and "Total" in sensor.Name:
                            data["cpu_load"] = sensor.Value or 0
                        elif sensor.SensorType == sensor.SensorType.Voltage and "Vcore" in sensor.Name:
                            data["cpu_voltage"] = max(data["cpu_voltage"], sensor.Value or 0)
                        elif sensor.SensorType == sensor.SensorType.Power and "Package" in sensor.Name:
                            data["cpu_pwr"] = sensor.Value or 0

                # --- GPU ---
                # Suporta Amd, Nvidia, Intel
                elif "Gpu" in str(hardware.HardwareType):
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == sensor.SensorType.Temperature and "Core" in sensor.Name:
                             data["gpu_temp"] = max(data["gpu_temp"], sensor.Value or 0)
                        elif sensor.SensorType == sensor.SensorType.Load and "Core" in sensor.Name:
                             data["gpu_load"] = max(data["gpu_load"], sensor.Value or 0)
                        elif sensor.SensorType == sensor.SensorType.Clock and "Core" in sensor.Name:
                             data["gpu_core_clock"] = sensor.Value or 0

        except Exception as e:
            # Em caso de erro na leitura (concorrência, acesso negado repentino)
            pass
            
        return data

    def close(self):
        if self.enabled and self.computer:
            self.computer.Close()
