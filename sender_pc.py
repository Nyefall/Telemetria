import psutil
import socket
import time
import json
import threading

# Configurações de Rede
# Para teste local, use "127.0.0.1". 
# Se for monitorar OUTRO PC, coloque o IP do PC que está rodando o receiver_notebook.py
DEST_IP = "192.168.10.137"  # IP do Notebook
PORTA = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Tenta importar pyadl para AMD
try:
    from pyadl import ADLManager
    HAS_PYADL = True
except ImportError:
    HAS_PYADL = False
except Exception: 
    HAS_PYADL = False

def obter_metrica_gpu():
    """Retorna (load_percent, temp_celsius) da GPU."""
    load = 0
    temp = 0
    if HAS_PYADL:
        try:
            devices = ADLManager.getDevices()
            if devices:
                gpu = devices[0]
                temp = float(gpu.getCurrentTemperature())
                # pyadl pode não fornecer load facilmente, ou pode variar. 
                # Se não tiver metodo direto, deixamos 0 ou tentamos algo se a lib suportar.
                # Para simplificar e evitar erros, vamos assumir 0 se não achar.
                load = 0 
        except Exception:
            pass
    return load, temp

def calcular_rede(last_net_io, last_time):
    """Calcula velocidade de Upload/Download em KB/s."""
    now = time.time()
    net_io = psutil.net_io_counters()
    
    delta_time = now - last_time
    if delta_time <= 0: delta_time = 1
    
    # Bytes novos - bytes antigos
    sent_bytes = net_io.bytes_sent - last_net_io.bytes_sent
    recv_bytes = net_io.bytes_recv - last_net_io.bytes_recv
    
    # Converte para KB/s
    up_kbps = (sent_bytes / 1024) / delta_time
    down_kbps = (recv_bytes / 1024) / delta_time
    
    return up_kbps, down_kbps, net_io, now

def medir_ping(host="8.8.8.8"):
    """Mede latência simples via socket connect (TCP) para estimativa."""
    try:
        t1 = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, 53)) # Porta DNS geralmente aberta
        s.close()
        t2 = time.time()
        return round((t2 - t1) * 1000, 1) # ms
    except:
        return 0

print(f"Sentinela iniciada. Enviando dados para {DEST_IP}:{PORTA}...")
print("Pressione Ctrl+C para parar.")

# Estado inicial para cálculo de rede
last_net_io = psutil.net_io_counters()
last_time = time.time()

try:
    while True:
        # 1. Coleta CPU e RAM
        cpu_usage = psutil.cpu_percent(interval=0.5) # Bloqueia por 0.5s para medir
        ram_percent = psutil.virtual_memory().percent
        
        # 2. Coleta GPU
        gpu_load, gpu_temp = obter_metrica_gpu()
        
        # 3. Coleta Rede
        up_kbps, down_kbps, last_net_io, last_time = calcular_rede(last_net_io, last_time)
        
        # 4. Coleta Ping (pode demorar um pouco, idealmente seria async, mas aqui é simples)
        ping_ms = medir_ping()
        
        # 5. Tenta estimar temperatura da CPU (Difícil no Windows sem libs extras/admin)
        # psutil.sensors_temperatures() funciona bem no Linux. No Windows retorna vazio frequentemente.
        cpu_temp = 0
        temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
        if temps and 'coretemp' in temps:
             cpu_temp = temps['coretemp'][0].current
        
        # Monta o JSON compatível com o receiver
        payload = {
            "cpu": {
                "usage": cpu_usage,
                "temp": cpu_temp,
                "voltage": 0 # Difícil ler sem driver específico
            },
            "gpu": {
                "load": gpu_load,
                "temp": gpu_temp
            },
            "ram": {
                "percent": ram_percent
            },
            "network": {
                "down_kbps": round(down_kbps, 1),
                "up_kbps": round(up_kbps, 1),
                "ping_ms": ping_ms
            }
        }
        
        # Envia
        msg = json.dumps(payload)
        sock.sendto(msg.encode(), (DEST_IP, PORTA))
        
        # O intervalo de loop já tem o cpu_percent(0.5) + ping + overhead
        # Então não precisa de sleep muito longo
        # time.sleep(0.5) 

except KeyboardInterrupt:
    print("\nEncerrando sentinela.")
    sock.close()
