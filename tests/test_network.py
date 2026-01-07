"""
Teste de comunicação ponta a ponta entre sender e receiver.
Simula o cenário real: sender neste PC, receiver em outro dispositivo.

Este script:
1. Inicia o sender por alguns segundos
2. Verifica se os pacotes estão sendo enviados corretamente
3. Mostra informações de rede para debug
"""
import socket
import json
import gzip
import time
import threading
import os
import sys
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_network_info():
    """Obtém informações de rede do computador."""
    print("\n" + "="*60)
    print("INFORMAÇÕES DE REDE")
    print("="*60)
    
    hostname = socket.gethostname()
    print(f"  Hostname: {hostname}")
    
    # Obter todos os IPs locais
    try:
        # Método 1: gethostbyname_ex
        _, _, ips = socket.gethostbyname_ex(hostname)
        print(f"  IPs locais: {', '.join(ips)}")
    except:
        pass
    
    # Método 2: conectar a um IP externo para descobrir o IP local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"  IP principal: {local_ip}")
    except:
        local_ip = "127.0.0.1"
    
    # Carregar config
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"\n  Modo: {config.get('modo', 'broadcast')}")
        print(f"  IP Destino: {config.get('dest_ip', '255.255.255.255')}")
        print(f"  Porta: {config.get('porta', 5005)}")
    except:
        print("  ⚠ Não foi possível ler config.json")
    
    return local_ip

def receiver_thread(duration=10):
    """Thread que recebe pacotes UDP."""
    received_packets = []
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 5005))
    sock.settimeout(1)
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        try:
            data, addr = sock.recvfrom(65535)
            
            # Tentar descomprimir
            try:
                decompressed = gzip.decompress(data)
                payload = json.loads(decompressed.decode('utf-8'))
            except:
                payload = json.loads(data.decode('utf-8'))
            
            received_packets.append({
                "time": time.time() - start_time,
                "addr": addr,
                "payload": payload
            })
            
        except socket.timeout:
            continue
        except Exception as e:
            print(f"  Erro ao receber: {e}")
    
    sock.close()
    return received_packets

def sender_thread(duration=10):
    """Thread que envia pacotes UDP (simulando o sender)."""
    import hardware_monitor
    import psutil
    
    # Carregar config
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    dest_ip = config.get('dest_ip', '255.255.255.255')
    porta = config.get('porta', 5005)
    intervalo = config.get('intervalo', 0.5)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Inicializar monitor
    monitor = hardware_monitor.HardwareMonitor()
    
    sent_count = 0
    start_time = time.time()
    
    while time.time() - start_time < duration:
        try:
            # Coletar dados
            hw_data = monitor.fetch_data() if monitor.enabled else None
            mem = psutil.virtual_memory()
            
            payload = {
                "cpu": {
                    "usage": psutil.cpu_percent(),
                    "temp": hw_data["cpu"]["temp"] if hw_data else 0,
                    "voltage": hw_data["cpu"]["voltage"] if hw_data else 0,
                    "power": hw_data["cpu"]["power"] if hw_data else 0,
                    "clock": hw_data["cpu"]["clock"] if hw_data else 0
                },
                "gpu": {
                    "load": hw_data["gpu"]["load"] if hw_data else 0,
                    "temp": hw_data["gpu"]["temp"] if hw_data else 0,
                    "voltage": hw_data["gpu"]["voltage"] if hw_data else 0,
                    "clock_core": hw_data["gpu"]["clock_core"] if hw_data else 0,
                    "clock_mem": hw_data["gpu"]["clock_mem"] if hw_data else 0,
                    "fan": hw_data["gpu"]["fan"] if hw_data else 0,
                    "mem_used_mb": hw_data["gpu"]["mem_used"] if hw_data else 0
                },
                "mobo": {
                    "temp": hw_data["mobo"]["temp"] if hw_data else 0
                },
                "ram": {
                    "percent": mem.percent,
                    "used_gb": round(mem.used / (1024**3), 2),
                    "total_gb": round(mem.total / (1024**3), 2)
                },
                "storage": hw_data["storage"] if hw_data else [],
                "fans": hw_data["fans"] if hw_data else [],
                "network": {
                    "down_kbps": 0,
                    "up_kbps": 0,
                    "ping_ms": 0
                }
            }
            
            # Comprimir e enviar
            json_data = json.dumps(payload).encode('utf-8')
            compressed = gzip.compress(json_data)
            sock.sendto(compressed, (dest_ip, porta))
            sent_count += 1
            
            time.sleep(intervalo)
            
        except Exception as e:
            print(f"  Erro ao enviar: {e}")
    
    sock.close()
    if monitor.enabled:
        monitor.close()
    return sent_count

def main():
    print("="*60)
    print("TESTE DE COMUNICAÇÃO PONTA A PONTA")
    print("="*60)
    
    admin_status = is_admin()
    print(f"\nExecutando como Administrador: {'SIM ✓' if admin_status else 'NÃO ✗'}")
    
    if not admin_status:
        print("⚠ Para valores reais dos sensores, execute como administrador!")
    
    # Info de rede
    local_ip = get_network_info()
    
    print("\n" + "="*60)
    print("INICIANDO TESTE (10 segundos)")
    print("="*60)
    print("\nEnviando e recebendo pacotes simultaneamente...")
    print("(No cenário real, o receiver estará em outro dispositivo)")
    
    # Iniciar threads
    recv_thread = threading.Thread(target=lambda: setattr(recv_thread, 'result', receiver_thread(10)))
    send_thread = threading.Thread(target=lambda: setattr(send_thread, 'result', sender_thread(10)))
    
    recv_thread.start()
    time.sleep(0.5)  # Dar tempo pro receiver iniciar
    send_thread.start()
    
    # Aguardar
    for i in range(10, 0, -1):
        print(f"  Testando... {i}s restantes", end='\r')
        time.sleep(1)
    
    send_thread.join()
    recv_thread.join()
    
    sent = getattr(send_thread, 'result', 0)
    received = getattr(recv_thread, 'result', [])
    
    print("\n\n" + "="*60)
    print("RESULTADOS DO TESTE")
    print("="*60)
    
    print(f"\n  Pacotes enviados: {sent}")
    print(f"  Pacotes recebidos: {len(received)}")
    
    if len(received) > 0:
        print(f"\n✓ COMUNICAÇÃO UDP FUNCIONANDO!")
        print(f"\n  Último pacote recebido:")
        last = received[-1]
        print(f"    De: {last['addr']}")
        print(f"    Tempo: {last['time']:.2f}s após início")
        
        # Analisar payload
        payload = last['payload']
        print(f"\n  --- Dados do Payload ---")
        
        for category, sensors in payload.items():
            non_zero = sum(1 for v in sensors.values() if v != 0)
            total = len(sensors)
            print(f"    {category.upper()}: {non_zero}/{total} sensores com valores")
        
        # Verificar se sensores estão funcionando
        total_sensors = sum(len(s) for s in payload.values())
        non_zero_sensors = sum(
            sum(1 for v in s.values() if v != 0) 
            for s in payload.values()
        )
        
        print(f"\n  Total: {non_zero_sensors}/{total_sensors} sensores funcionando")
        
        if non_zero_sensors < total_sensors * 0.5:
            print("\n  ⚠ Menos de 50% dos sensores estão retornando valores.")
            if not admin_status:
                print("  → Execute como ADMINISTRADOR para acesso completo aos sensores!")
        else:
            print("\n  ✓ Maioria dos sensores funcionando corretamente!")
    else:
        print(f"\n✗ NENHUM PACOTE RECEBIDO!")
        print("  Possíveis causas:")
        print("  - Firewall bloqueando UDP porta 5005")
        print("  - Antivírus interferindo")
        print("  - Problema no hardware_monitor")
    
    print("\n" + "="*60)
    print("INSTRUÇÕES PARA O NOTEBOOK (RECEIVER)")
    print("="*60)
    print(f"\n  1. Certifique-se de que o notebook está na mesma rede")
    print(f"  2. O IP deste PC é: {local_ip}")
    print(f"  3. No notebook, execute: python receiver_notebook.py")
    print(f"  4. O receiver deve detectar automaticamente via broadcast")
    print(f"\n  Se não funcionar:")
    print(f"  - Verifique se a porta 5005 UDP está liberada no firewall")
    print(f"  - Teste se os dispositivos conseguem se comunicar (ping)")
    
    print("\n")
    input("Pressione ENTER para sair...")

if __name__ == "__main__":
    main()
