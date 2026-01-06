import psutil
import socket
import time
import json

# Tenta carregar módulo de Hardware Monitor (DLL)
try:
    import hardware_monitor
    HAS_HWMON = True
except ImportError:
    HAS_HWMON = False

# ========== CONFIGURAÇÕES ==========
DEST_IP = "192.168.10.137"  # IP do Notebook
PORTA = 5005
INTERVALO = 0.5  # Segundos entre envios
# ===================================

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Inicializa Monitor de Hardware via DLL
monitor = None
if HAS_HWMON:
    print("Inicializando HardwareMonitor (LibreHardwareMonitor DLL)...")
    monitor = hardware_monitor.HardwareMonitor()
    if not monitor.enabled:
        print("AVISO: DLL não carregou. Rodando com dados limitados (psutil).")
        monitor = None
else:
    print("Módulo 'hardware_monitor.py' não encontrado. Rodando com psutil apenas.")


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
        s.connect((host, 53))
        s.close()
        return round((time.time() - t1) * 1000, 1)
    except:
        return 0


print(f"\n=== SENTINELA DE TELEMETRIA ===")
print(f"Destino: {DEST_IP}:{PORTA}")
print(f"Intervalo: {INTERVALO}s")
print("Ctrl+C para sair.\n")

last_net = psutil.net_io_counters()
last_t = time.time()

try:
    while True:
        # 1. Dados via DLL (se disponível)
        hw = None
        if monitor and monitor.enabled:
            hw = monitor.fetch_data()
        
        # 2. Dados básicos via psutil (fallback/complemento)
        cpu_percent = psutil.cpu_percent(interval=INTERVALO)
        mem = psutil.virtual_memory()
        
        # 3. Rede
        up, down, last_net, last_t = calcular_rede(last_net, last_t)
        ping = medir_ping()
        
        # 4. Monta payload completo
        if hw:
            payload = {
                "cpu": {
                    "usage": cpu_percent,  # psutil é mais preciso para % global
                    "temp": round(hw["cpu"]["temp"], 1),
                    "voltage": round(hw["cpu"]["voltage"], 3),
                    "power": round(hw["cpu"]["power"], 1),
                    "clock": round(hw["cpu"]["clock"], 0)
                },
                "gpu": {
                    "load": round(hw["gpu"]["load"], 1),
                    "temp": round(hw["gpu"]["temp"], 1),
                    "voltage": round(hw["gpu"]["voltage"], 3),
                    "clock_core": round(hw["gpu"]["clock_core"], 0),
                    "clock_mem": round(hw["gpu"]["clock_mem"], 0),
                    "power": round(hw["gpu"]["power"], 1),
                    "fan": round(hw["gpu"]["fan"], 0)
                },
                "mobo": {
                    "temp": round(hw["mobo"]["temp"], 1),
                    "voltage_12v": round(hw["mobo"]["voltage_12v"], 2),
                    "voltage_5v": round(hw["mobo"]["voltage_5v"], 2),
                    "voltage_3v": round(hw["mobo"]["voltage_3v"], 2)
                },
                "ram": {
                    "percent": mem.percent,
                    "used_gb": round(mem.used / (1024**3), 2),
                    "total_gb": round(mem.total / (1024**3), 2)
                },
                "storage": hw["storage"],  # Lista de discos
                "fans": hw["fans"],         # Lista de ventoinhas
                "network": {
                    "down_kbps": round(down, 1),
                    "up_kbps": round(up, 1),
                    "ping_ms": ping
                }
            }
        else:
            # Modo limitado (sem DLL)
            payload = {
                "cpu": {
                    "usage": cpu_percent,
                    "temp": 0,
                    "voltage": 0,
                    "power": 0,
                    "clock": 0
                },
                "gpu": {
                    "load": 0,
                    "temp": 0,
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
                    "percent": mem.percent,
                    "used_gb": round(mem.used / (1024**3), 2),
                    "total_gb": round(mem.total / (1024**3), 2)
                },
                "storage": [],
                "fans": [],
                "network": {
                    "down_kbps": round(down, 1),
                    "up_kbps": round(up, 1),
                    "ping_ms": ping
                }
            }
        
        # Envia
        sock.sendto(json.dumps(payload).encode(), (DEST_IP, PORTA))

except KeyboardInterrupt:
    print("\nEncerrando...")
    if monitor:
        monitor.close()
    sock.close()
