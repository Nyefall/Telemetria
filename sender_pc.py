import psutil
import socket
import time
import json
import sys
import os
import ctypes

# ========== AUTO-ELEVAÇÃO PARA ADMINISTRADOR ==========
def is_admin():
    """Verifica se o script está rodando como administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Reinicia o script com privilégios de administrador."""
    if sys.platform == 'win32':
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # Usa ShellExecuteW para solicitar elevação
        ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # operação (runas = executar como admin)
            sys.executable, # programa (python.exe)
            f'"{script}" {params}',  # parâmetros
            None,           # diretório
            1               # SW_SHOWNORMAL
        )
        sys.exit(0)

# Verifica e eleva privilégios se necessário
if not is_admin():
    print("=" * 50)
    print("ELEVANDO PRIVILÉGIOS PARA ADMINISTRADOR...")
    print("(Necessário para acessar sensores de hardware)")
    print("=" * 50)
    run_as_admin()
# ======================================================

# Tenta carregar módulo de Hardware Monitor (DLL)
try:
    import hardware_monitor
    HAS_HWMON = True
except ImportError:
    HAS_HWMON = False

# ========== CONFIGURAÇÕES ==========
def carregar_config():
    """Carrega configurações do config.json ou usa padrões."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    config_padrao = {
        "modo": "broadcast",
        "dest_ip": "255.255.255.255",
        "porta": 5005,
        "intervalo": 0.5
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Mescla com padrões para garantir que todas as chaves existam
                for key in config_padrao:
                    if key not in config:
                        config[key] = config_padrao[key]
                print(f"[Config] Carregado de {config_path}")
                return config
        except Exception as e:
            print(f"[Config] Erro ao ler config.json: {e}")
            print("[Config] Usando configurações padrão (broadcast)")
    else:
        # Cria config.json padrão
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "modo": "broadcast",
                    "dest_ip": "255.255.255.255",
                    "porta": 5005,
                    "intervalo": 0.5,
                    "comentarios": {
                        "modo": "Opções: 'broadcast' (auto-descoberta) ou 'unicast' (IP fixo)",
                        "dest_ip": "Use '255.255.255.255' para broadcast ou o IP do notebook para unicast",
                        "porta": "Porta UDP para comunicação (deve ser igual no sender e receiver)",
                        "intervalo": "Intervalo entre envios em segundos"
                    }
                }, f, indent=4, ensure_ascii=False)
            print(f"[Config] Criado config.json padrão em {config_path}")
        except:
            pass
    
    return config_padrao

CONFIG = carregar_config()
DEST_IP = CONFIG["dest_ip"]
PORTA = CONFIG["porta"]
INTERVALO = CONFIG["intervalo"]
MODO = CONFIG["modo"]
# ===================================

# Configura socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Habilita broadcast se necessário
if MODO == "broadcast" or DEST_IP == "255.255.255.255":
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    print("[Socket] Modo BROADCAST ativado - auto-descoberta na rede")
else:
    print(f"[Socket] Modo UNICAST - enviando para {DEST_IP}")

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
if MODO == "broadcast":
    print(f"Destino: BROADCAST (255.255.255.255:{PORTA})")
else:
    print(f"Destino: {DEST_IP}:{PORTA}")
print(f"Intervalo: {INTERVALO}s")
print("Ctrl+C para sair.\n")

# Minimiza/esconde o console após inicialização bem-sucedida
try:
    import ctypes
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE = 6
        print("[Console] Minimizado para a barra de tarefas")
except:
    pass

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
                    "fan": round(hw["gpu"]["fan"], 0),
                    "mem_used_mb": round(hw["gpu"]["mem_used"], 0)
                },
                "mobo": {
                    "temp": round(hw["mobo"]["temp"], 1)
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
                    "fan": 0,
                    "mem_used_mb": 0
                },
                "mobo": {
                    "temp": 0
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
