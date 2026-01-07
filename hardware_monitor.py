import os
import sys
import math

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
            print(f"[HardwareMonitor] Erro ao inicializar (Rode como Admin!): {e}")
            self.computer = None

    def _get_sensor_type_name(self, sensor):
        """Retorna o nome do tipo do sensor como string."""
        return str(sensor.SensorType).split('.')[-1]

    def _get_hardware_type_name(self, hardware):
        """Retorna o nome do tipo de hardware como string."""
        return str(hardware.HardwareType).split('.')[-1]
    
    def _safe_value(self, val):
        """Retorna 0 se valor for None, NaN ou inválido."""
        if val is None:
            return 0
        try:
            if math.isnan(val) or math.isinf(val):
                return 0
            return float(val)
        except:
            return 0

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
                "load": 0,
                "used_gb": 0,
                "available_gb": 0
            },
            "storage": [],
            "fans": []
        }

        if not self.enabled or not self.computer:
            return data

        try:
            for hardware in self.computer.Hardware:
                hardware.Update()
                hw_type = self._get_hardware_type_name(hardware)
                
                # Atualiza sub-hardwares
                for subhw in hardware.SubHardware:
                    subhw.Update()

                # === CPU ===
                if hw_type == "Cpu":
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        name = sensor.Name
                        val = self._safe_value(sensor.Value)
                        
                        if s_type == "Temperature":
                            # AMD: Tctl/Tdie, Intel: Package/Core
                            if val > 0:
                                data["cpu"]["temp"] = max(data["cpu"]["temp"], val)
                        elif s_type == "Voltage":
                            # AMD: SVI2 TFN, VID | Intel: VCore
                            # Filtra voltagens válidas (< 2V tipicamente)
                            if val > 0 and val < 2:
                                data["cpu"]["voltage"] = max(data["cpu"]["voltage"], val)
                        elif s_type == "Load":
                            if "Total" in name and val > 0:
                                data["cpu"]["load"] = val
                        elif s_type == "Power":
                            if val > 0:
                                data["cpu"]["power"] = max(data["cpu"]["power"], val)
                        elif s_type == "Clock":
                            if val > 0:
                                data["cpu"]["clock"] = max(data["cpu"]["clock"], val)

                # === GPU (Nvidia, AMD, Intel) ===
                elif "Gpu" in hw_type:
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        name = sensor.Name
                        val = self._safe_value(sensor.Value)
                        
                        if s_type == "Temperature":
                            # GPU Core (não Hot Spot ou Memory para principal)
                            if "Core" in name and val > 0:
                                data["gpu"]["temp"] = val
                        elif s_type == "Load":
                            # GPU Core load (não D3D)
                            if "Core" in name and "D3D" not in name and val > 0:
                                data["gpu"]["load"] = val
                        elif s_type == "Voltage":
                            if "Core" in name and val > 0:
                                data["gpu"]["voltage"] = val
                        elif s_type == "Clock":
                            if "Core" in name and val > 0:
                                data["gpu"]["clock_core"] = val
                            elif "Memory" in name and val > 0:
                                data["gpu"]["clock_mem"] = val
                        elif s_type == "Power":
                            if "Package" in name and val > 0:
                                data["gpu"]["power"] = val
                        elif s_type == "Fan":
                            if val > 0:
                                data["gpu"]["fan"] = val

                # === Motherboard ===
                elif hw_type == "Motherboard":
                    # Sensores da motherboard geralmente estão em sub-hardware (SuperIO)
                    for subhw in hardware.SubHardware:
                        subhw.Update()
                        for sensor in subhw.Sensors:
                            s_type = self._get_sensor_type_name(sensor)
                            name = sensor.Name
                            val = self._safe_value(sensor.Value)
                            
                            if s_type == "Temperature":
                                if val > 0 and val < 150:  # Temp válida
                                    data["mobo"]["temp"] = max(data["mobo"]["temp"], val)
                            elif s_type == "Voltage":
                                name_lower = name.lower()
                                # Verifica padrões de voltagem
                                if "12v" in name_lower or "+12" in name_lower or "12 v" in name_lower:
                                    if val > 0:
                                        data["mobo"]["voltage_12v"] = val
                                elif "5v" in name_lower or "+5" in name_lower or "5 v" in name_lower:
                                    if val > 0 and "3" not in name_lower:  # Evita 3.5v confundir
                                        data["mobo"]["voltage_5v"] = val
                                elif "3.3v" in name_lower or "3v" in name_lower or "+3" in name_lower or "3.3 v" in name_lower:
                                    if val > 0:
                                        data["mobo"]["voltage_3v"] = val
                                # Se não encontrar voltagens padrão, usa Vcore como fallback para voltagem geral
                                elif "vcore" in name_lower and data["mobo"]["voltage_3v"] == 0:
                                    # Não faz nada aqui, Vcore da CPU já é capturado
                                    pass
                            elif s_type == "Fan":
                                if val > 100:  # RPM válido (ignora leituras erradas)
                                    data["fans"].append({"name": name, "rpm": val})

                # === RAM/Memory ===
                elif hw_type == "Memory":
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        name = sensor.Name
                        val = self._safe_value(sensor.Value)
                        
                        if s_type == "Load":
                            if "Memory" in name and "Virtual" not in name:
                                data["ram"]["load"] = val
                        elif s_type == "Data":
                            if "Used" in name and "Virtual" not in name:
                                data["ram"]["used_gb"] = val
                            elif "Available" in name and "Virtual" not in name:
                                data["ram"]["available_gb"] = val

                # === Storage (SSDs, HDDs) ===
                elif hw_type == "Storage":
                    disk_info = {"name": hardware.Name, "temp": 0, "health": 100}  # Default 100% se não tiver sensor
                    has_health = False
                    for sensor in hardware.Sensors:
                        s_type = self._get_sensor_type_name(sensor)
                        name = sensor.Name
                        val = self._safe_value(sensor.Value)
                        
                        if s_type == "Temperature" and val > 0:
                            disk_info["temp"] = max(disk_info["temp"], val)
                        elif s_type == "Level":
                            # "Available Spare" indica saúde do SSD (100% = novo)
                            # "Percentage Used" indica desgaste (0% = novo, 100% = fim de vida)
                            if "Available Spare" in name and val > 0:
                                disk_info["health"] = val
                                has_health = True
                            elif "Percentage Used" in name and not has_health:
                                # Converte desgaste para saúde (100 - usado = saúde)
                                disk_info["health"] = max(0, 100 - val)
                                has_health = True
                    
                    # Adiciona disco se tiver algum sensor válido
                    if disk_info["temp"] > 0 or has_health:
                        data["storage"].append(disk_info)

        except Exception as e:
            print(f"[HardwareMonitor] Erro na leitura: {e}")
            
        return data

    def close(self):
        if self.enabled and self.computer:
            self.computer.Close()
            print("[HardwareMonitor] Fechado.")
