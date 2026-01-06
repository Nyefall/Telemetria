import socket
import json
import sys
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# Configurações
HOST = "0.0.0.0"
PORTA = 5005
HISTORY_SIZE = 60 # 60 pontos de dados (aprox 30-60 segundos dependendo do sender)

# Setup Socket (Non-blocking para UI não travar)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORTA))
sock.setblocking(False)

# Dados para gráficos (Buffers circulares)
data_store = {
    "cpu_usage": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "gpu_load":  deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "ram_usage": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "net_down":  deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "net_up":    deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "ping":      deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "temp_cpu":  deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "temp_gpu":  deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE)
}

# Texto de status atual
status_text = {
    "cpu": "CPU: -",
    "gpu": "GPU: -",
    "ram": "RAM: -",
    "net": "Net: -",
    "ping": "Ping: -"
}

# Configuração da Figura Matplotlib
plt.style.use('dark_background')
fig = plt.figure(figsize=(12, 8))
fig.suptitle("Central de Telemetria Integrada", fontsize=16, color='cyan')

# Layout: 2x2 Grid + Texto
# [0,0] Uso CPU/GPU  [0,1] Temps
# [1,0] Rede         [1,1] Ping/Estabilidade

ax1 = plt.subplot(221)
ax1.set_title("Uso de Recursos (%)")
ax1.set_ylim(0, 100)
line_cpu, = ax1.plot([], [], label="CPU", color="cyan")
line_gpu, = ax1.plot([], [], label="GPU", color="lime")
line_ram, = ax1.plot([], [], label="RAM", color="magenta")
ax1.legend(loc="lower left")
ax1.grid(True, alpha=0.2)

ax2 = plt.subplot(222)
ax2.set_title("Temperaturas (°C)")
ax2.set_ylim(30, 100) # Ajuste conforme necessário
line_t_cpu, = ax2.plot([], [], label="CPU Temp", color="orange")
line_t_gpu, = ax2.plot([], [], label="GPU Temp", color="red")
ax2.legend(loc="lower left")
ax2.grid(True, alpha=0.2)

ax3 = plt.subplot(223)
ax3.set_title("Rede (KB/s)")
line_down, = ax3.plot([], [], label="Download", color="dodgerblue")
line_up,  = ax3.plot([], [], label="Upload", color="yellow")
ax3.legend(loc="upper left")
ax3.grid(True, alpha=0.2)

ax4 = plt.subplot(224)
ax4.set_title("Latência (ms)")
line_ping, = ax4.plot([], [], label="Ping", color="white")
ax4.legend(loc="upper left")
ax4.grid(True, alpha=0.2)

def update(frame):
    # 1. Tenta ler todos os pacotes pendentes (flush) para pegar o mais recente
    last_data = None
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            last_data = data
        except BlockingIOError:
            break
        except Exception as e:
            print(f"Erro socket: {e}")
            break
    
    # 2. Se houver dados novos, processa
    if last_data:
        try:
            payload = json.loads(last_data.decode())
            
            # Anexa aos deques
            data_store["cpu_usage"].append(payload["cpu"]["usage"])
            data_store["gpu_load"].append(payload["gpu"]["load"])
            data_store["ram_usage"].append(payload["ram"]["percent"])
            
            # Temperaturas (Se for 0, mantem o anterior ou 0)
            data_store["temp_cpu"].append(payload["cpu"]["temp"])
            data_store["temp_gpu"].append(payload["gpu"]["temp"])
            
            # Rede
            data_store["net_down"].append(payload["network"]["down_kbps"])
            data_store["net_up"].append(payload["network"]["up_kbps"])
            data_store["ping"].append(payload["network"]["ping_ms"])
            
            # Atualiza textos (Labels do gráfico ou print no console se quiser)
            # Vamos por titulos dinâmicos nos eixos
            ax1.set_xlabel(f"CPU: {payload['cpu']['usage']}% | GPU: {payload['gpu']['load']}% | RAM: {payload['ram']['percent']}%")
            ax2.set_xlabel(f"CPU: {payload['cpu']['temp']}°C | GPU: {payload['gpu']['temp']}°C | Volt: {payload['cpu']['voltage']}V")
            ax3.set_xlabel(f"Down: {payload['network']['down_kbps']} KB/s | Up: {payload['network']['up_kbps']} KB/s")
            ax4.set_xlabel(f"Ping: {payload['network']['ping_ms']} ms")

        except json.JSONDecodeError:
            pass
        except KeyError:
            pass

    # 3. Atualiza Linhas do Gráfico
    x = range(len(data_store["cpu_usage"]))
    
    line_cpu.set_data(x, data_store["cpu_usage"])
    line_gpu.set_data(x, data_store["gpu_load"])
    line_ram.set_data(x, data_store["ram_usage"])
    ax1.set_xlim(0, len(data_store["cpu_usage"]))
    
    line_t_cpu.set_data(x, data_store["temp_cpu"])
    line_t_gpu.set_data(x, data_store["temp_gpu"])
    ax2.set_xlim(0, len(data_store["temp_cpu"]))
    
    line_down.set_data(x, data_store["net_down"])
    line_up.set_data(x, data_store["net_up"])
    ax3.set_xlim(0, len(data_store["net_down"]))
    # Auto-scale eixo Y da rede pois varia muito
    if len(data_store["net_down"]) > 0:
        ma = max(max(data_store["net_down"]), max(data_store["net_up"]), 10)
        ax3.set_ylim(0, ma * 1.1)
        
    line_ping.set_data(x, data_store["ping"])
    ax4.set_xlim(0, len(data_store["ping"]))
    
    return line_cpu, line_gpu, line_ram, line_t_cpu, line_t_gpu, line_down, line_up, line_ping

print("Iniciando Dashboard...")
ani = animation.FuncAnimation(fig, update, interval=500, blit=False)
plt.show()
