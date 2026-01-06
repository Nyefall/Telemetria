import os
import sys

# Tenta importar pythonnet (clr)
try:
    import clr
    HAS_PYTHONNET = True
except ImportError:
    HAS_PYTHONNET = False

# Enums do LibreHardwareMonitor (para referência)
# SensorType: Voltage, Clock, Temperature, Load, Frequency, Fan, Flow, Control, Level, Factor, Power, Data, SmallData, Throughput
# HardwareType: Motherboard, SuperIO, Cpu, Memory, GpuNvidia, GpuAmd, GpuIntel, Storage, Network, Cooler, EmbeddedController, Psu

class HardwareMonitor:
    def __init__(self):
        self.computer = None
        self.enabled = False
        self.Hardware = None  # Namespace reference
        
        # Caminho absoluto baseado na localização deste script
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.dll_path = os.path.join(base_path, "libs", "LibreHardwareMonitorLib.dll")

        if not HAS_PYTHONNET:
            print("[HardwareMonitor] 'pythonnet' não instalado. pip install pythonnet")
            return

        if not os.path.exists(self.dll_path):
            print(f"[HardwareMonitor] DLL não encontrada em: {self.dll_path}")
            print("[HardwareMonitor] Coloque 'LibreHardwareMonitorLib.dll' dentro da pasta 'libs'.")
            return

        try:
            clr.AddReference(self.dll_path)
            from LibreHardwareMonitor import Hardware
            self.Hardware = Hardware  # Guarda referência ao namespace
            
            self.computer = Hardware.Computer()
            self.computer.IsCpuEnabled = True
            self.computer.IsGpuEnabled = True
            self.computer.IsMemoryEnabled = True
            self.computer.IsMotherboardEnabled = True
            self.computer.IsStorageEnabled = True
            self.computer.IsNetworkEnabled = True
            self.computer.IsControllerEnabled = True
            
            self.computer.Open()
            self.enabled = True
            print("[HardwareMonitor] Inicializado com sucesso!")
            
        except Exception as e:
            print(f"[HardwareMonitor] Erro ao inicializar (Admin?): {e}")
            self.computer = None

    def _get_sensor_type_name(self, sensor):
        """Retorna o nome do tipo do sensor como string."""
        return str(sensor.SensorType).split('.')[-1]

    def _get_hardware_type_name(self, hardware):
        """Retorna o nome do tipo de hardware como string."""
        return str(hardware.HardwareType).split('.')[-1]

    def fetch_data(self):
        """
        Retorna dicionário completo com todos os sensores disponíveis.
        """
        data = {
            "cpu": {
                "temp": 0,
                "voltage": 0,
                "load": 0,
                "power": 0,
                "clock": 0
            },
            "gpu": {
                "temp": 0,
                "load": 0,
                "voltage": 0,
                "clock_core": 0,
                "clock_mem": 0,
                "power": 0,
                "fan": 0
            },
            "mobo": {
                "temp": 0,
                "voltage_12v": 0,
                "voltage_5v": 0,
                "voltage_3v": 0
            },
            "ram": {
                "load": 0,  # % usado (redundante com psutil mas vem da DLL)
                "used_gb": 0,
                "available_gb": 0
            },
            "storage": [],  # Lista de discos com temp e uso
            "fans": []      # Lista de ventoinhas
        }

        if not self.enabled or not self.computer:
            return data

        try:
            for hardware in self.computer.Hardware:
                hardware.Update()
                hw_type = self._get_hardware_type_name(hardware)
                
                # Também atualiza sub-hardwares (chipsets, super I/O, etc)
                for subhw in hardware.SubHardware:
                    subhw.Update()

                # === CPU ===
                if hw_type == "Cpu":
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        name = sensor.Name
                        val = sensor.Value or 0
                        
                        if s_type == "Temperature":
                            if "Package" in name or "Core" in name:
                                data["cpu"]["temp"] = max(data["cpu"]["temp"], val)
                        elif s_type == "Voltage":
                            if "Core" in name or "VCore" in name or "Vcore" in name:
                                data["cpu"]["voltage"] = max(data["cpu"]["voltage"], val)
                        elif s_type == "Load":
                            if "Total" in name:
                                data["cpu"]["load"] = val
                        elif s_type == "Power":
                            if "Package" in name:
                                data["cpu"]["power"] = val
                        elif s_type == "Clock":
                            if "Core" in name:
                                data["cpu"]["clock"] = max(data["cpu"]["clock"], val)

                # === GPU (Nvidia, AMD, Intel) ===
                elif "Gpu" in hw_type:
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        name = sensor.Name
                        val = sensor.Value or 0
                        
                        if s_type == "Temperature":
                            if "Core" in name or "GPU" in name:
                                data["gpu"]["temp"] = max(data["gpu"]["temp"], val)
                        elif s_type == "Load":
                            if "Core" in name or "GPU" in name:
                                data["gpu"]["load"] = max(data["gpu"]["load"], val)
                        elif s_type == "Voltage":
                            data["gpu"]["voltage"] = max(data["gpu"]["voltage"], val)
                        elif s_type == "Clock":
                            if "Core" in name:
                                data["gpu"]["clock_core"] = val
                            elif "Memory" in name:
                                data["gpu"]["clock_mem"] = val
                        elif s_type == "Power":
                            data["gpu"]["power"] = max(data["gpu"]["power"], val)
                        elif s_type == "Fan":
                            data["gpu"]["fan"] = val

                # === Motherboard ===
                elif hw_type == "Motherboard":
                    for subhw in hardware.SubHardware:
                        subhw.Update()
                        for sensor in subhw.Sensors:
                            s_type = self._get_sensor_type_name(sensor)
                            name = sensor.Name
                            val = sensor.Value or 0
                            
                            if s_type == "Temperature":
                                # Pega a maior temp da mobo
                                data["mobo"]["temp"] = max(data["mobo"]["temp"], val)
                            elif s_type == "Voltage":
                                if "+12V" in name or "12V" in name:
                                    data["mobo"]["voltage_12v"] = val
                                elif "+5V" in name or "5V" in name:
                                    data["mobo"]["voltage_5v"] = val
                                elif "+3.3V" in name or "3V" in name or "3.3V" in name:
                                    data["mobo"]["voltage_3v"] = val
                            elif s_type == "Fan":
                                if val > 0:
                                    data["fans"].append({"name": name, "rpm": val})

                # === RAM/Memory ===
                elif hw_type == "Memory":
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        name = sensor.Name
                        val = sensor.Value or 0
                        
                        if s_type == "Load":
                            data["ram"]["load"] = val
                        elif s_type == "Data":
                            if "Used" in name:
                                data["ram"]["used_gb"] = val
                            elif "Available" in name:
                                data["ram"]["available_gb"] = val

                # === Storage (SSDs, HDDs) ===
                elif hw_type == "Storage":
                    disk_info = {"name": hardware.Name, "temp": 0, "used": 0}
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        val = sensor.Value or 0
                        
                        if s_type == "Temperature":
                            disk_info["temp"] = max(disk_info["temp"], val)
                        elif s_type == "Load":
                            disk_info["used"] = val
                    
                    if disk_info["temp"] > 0 or disk_info["used"] > 0:
                        data["storage"].append(disk_info)

        except Exception as e:
            print(f"[HardwareMonitor] Erro na leitura: {e}")
            
        return data

    def close(self):
        if self.enabled and self.computer:
            self.computer.Close()
            print("[HardwareMonitor] Fechado.")
