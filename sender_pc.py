import psutil
import socket
import time

# Tenta importar pyadl para AMD. Se falhar, define como None para tratamento de erro.
try:
    from pyadl import ADLManager
    HAS_PYADL = True
except ImportError:
    HAS_PYADL = False
except Exception: 
    # as vezes pyadl falha ao inicializar se não tiver GPU AMD
    HAS_PYADL = False

# Configurações de Rede (Cabo CAT5e/CAT6)
# IMPORTANTE: Substitua pelo IP real do seu notebook
NOTEBOOK_IP = "192.168.10.137" 
PORTA = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def obter_dados_gpu():
    if not HAS_PYADL:
        return "N/A (pyadl missing)"
        
    try:
        devices = ADLManager.getDevices()
        if devices:
            gpu = devices[0]
            # Algumas placas AMD podem exigir índices específicos para temp
            return f"{gpu.getCurrentTemperature()}°C"
    except Exception as e:
        # Silenciosamente falha ou retorna N/A para não travar o loop
        return "N/A"
    return "N/A"

print(f"Sentinela ativa. Alvo: {NOTEBOOK_IP}:{PORTA}")
print("Pressione Ctrl+C para parar.")

try:
    while True:
        # Coleta de dados do sistema
        cpu_uso = psutil.cpu_percent(interval=None) # Interval=None para não bloquear, chama a cada loop
        ram_uso = psutil.virtual_memory().percent
        gpu_temp = obter_dados_gpu()
        
        # Montagem da "Petição" de dados (String formatada)
        # Exemplo: "15.5|45.2|62°C"
        payload = f"{cpu_uso}|{ram_uso}|{gpu_temp}"
        
        sock.sendto(payload.encode(), (NOTEBOOK_IP, PORTA))
        time.sleep(1) # Frequência de atualização: 1 segundo
except KeyboardInterrupt:
    print("\nEncerrando sentinela.")
    sock.close()
