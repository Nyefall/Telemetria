import psutil
import socket
import time
import json
import threading
import sys

# Tenta carregar módulo de Hardware Monitor (DLL)
try:
    import hardware_monitor
    HAS_HWMON = True
except ImportError:
    HAS_HWMON = False

# Configurações de Rede
DEST_IP = "192.168.10.137" 
PORTA = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Inicializa Monitor de Hardware via DLL
monitor = None
if HAS_HWMON:
    print("Inicializando HardwareMonitor...")
    monitor = hardware_monitor.HardwareMonitor()
else:
    print("Módulo 'hardware_monitor.py' não encontrado.")

# --- Fallbacks (Legacy) ---
# Tenta importar pyadl para AMD (caso DLL falhe)
try:
    from pyadl import ADLManager
    HAS_PYADL = True
except:
    HAS_PYADL = False

def obter_gpu_fallback():
    """Fallback para GPU AMD via pyadl se DLL falhar."""
    load = 0
    temp = 0
    if HAS_PYADL:
        try:
            devices = ADLManager.getDevices()
            if devices:
                gpu = devices[0]
                temp = float(gpu.getCurrentTemperature())
        except:
            pass
    return load, temp

def calcular_rede(last_net_io, last_time):
    now = time.time()
    net_io = psutil.net_io_counters()
    delta = now - last_time
    if delta <= 0: delta = 1
    
    sent = net_io.bytes_sent - last_net_io.bytes_sent
    recv = net_io.bytes_recv - last_net_io.bytes_recv
    
    return (sent/1024)/delta, (recv/1024)/delta, net_io, now

def medir_ping(host="8.8.8.8"):
    try:
        t1 = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        # Tenta conectar no Google DNS (porta 53)
        s.connect((host, 53)) 
        s.close()
        return round((time.time() - t1) * 1000, 1)
    except:
        return 0

print(f"Sentinela iniciada. Destino: {DEST_IP}:{PORTA}")
print("Ctrl+C para sair.")

last_net = psutil.net_io_counters()
last_t = time.time()

try:
    while True:
        # 1. Dados Básicos (PSUtil é rápido e confiável para uso global)
        cpu_usage_psutil = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        
        # 2. Dados Avançados (DLL)
        hw_data = {"cpu_temp": 0, "cpu_voltage": 0, "gpu_temp": 0, "gpu_load": 0}
        if monitor and monitor.enabled:
            hw_data = monitor.fetch_data()
        
        # Consolidação de dados (DLL tem prioridade, depois Fallbacks)
        
        # CPU
        final_cpu_temp = hw_data["cpu_temp"]
        final_cpu_volt = hw_data["cpu_voltage"]
        
        # GPU (Se DLL retornar 0, tenta fallback)
        final_gpu_temp = hw_data["gpu_temp"]
        final_gpu_load = hw_data["gpu_load"]
        
        if final_gpu_temp == 0 and HAS_PYADL:
            _, t_fallback = obter_gpu_fallback()
            final_gpu_temp = t_fallback

        # 3. Rede
        up, down, last_net, last_t = calcular_rede(last_net, last_t)
        ping = medir_ping()
        
        payload = {
            "cpu": {
                "usage": cpu_usage_psutil, # PSUtil é melhor para % global
                "temp": final_cpu_temp,
                "voltage": final_cpu_volt
            },
            "gpu": {
                "load": final_gpu_load,
                "temp": final_gpu_temp
            },
            "ram": {
                "percent": ram.percent
            },
            "network": {
                "down_kbps": round(down, 1),
                "up_kbps": round(up, 1),
                "ping_ms": ping
            }
        }
        
        sock.sendto(json.dumps(payload).encode(), (DEST_IP, PORTA))

except KeyboardInterrupt:
    print("\nParando...")
    if monitor:
        monitor.close()
    sock.close()
