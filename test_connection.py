"""
Teste de conexão UDP entre sender e receiver
"""
import socket
import json
import gzip
import time
import threading

PORTA = 5005

def test_sender():
    """Envia pacote de teste via broadcast."""
    print("[Sender] Iniciando teste...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    payload = {"test": True, "timestamp": time.time()}
    data = json.dumps(payload).encode()
    
    for i in range(5):
        sock.sendto(data, ("255.255.255.255", PORTA))
        print(f"[Sender] Enviado pacote {i+1}/5")
        time.sleep(0.5)
    
    sock.close()
    print("[Sender] Teste concluído")

def test_receiver():
    """Recebe pacotes UDP."""
    print("[Receiver] Iniciando teste...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORTA))
    sock.settimeout(5.0)
    
    print(f"[Receiver] Ouvindo em 0.0.0.0:{PORTA}...")
    
    received = 0
    start = time.time()
    
    while time.time() - start < 6:
        try:
            data, addr = sock.recvfrom(4096)
            
            # Tenta descompactar
            try:
                data = gzip.decompress(data)
            except:
                pass
            
            payload = json.loads(data.decode())
            print(f"[Receiver] Recebido de {addr}: {payload}")
            received += 1
            
        except socket.timeout:
            print("[Receiver] Timeout (sem dados)")
        except Exception as e:
            print(f"[Receiver] Erro: {e}")
    
    sock.close()
    print(f"[Receiver] Teste concluído - {received} pacotes recebidos")
    return received > 0

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python test_connection.py [sender|receiver|both]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "sender":
        test_sender()
    elif mode == "receiver":
        test_receiver()
    elif mode == "both":
        # Inicia receiver em thread
        recv_thread = threading.Thread(target=test_receiver, daemon=True)
        recv_thread.start()
        time.sleep(1)  # Espera receiver iniciar
        
        # Envia
        test_sender()
        
        # Espera receiver terminar
        recv_thread.join(timeout=8)
    else:
        print(f"Modo desconhecido: {mode}")
