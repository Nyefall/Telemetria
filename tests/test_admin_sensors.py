"""
Teste de sensores com permissões de administrador.
Este script deve ser executado como administrador para testar todos os sensores.
"""
import sys
import os
import ctypes
import json
import socket
import time

def is_admin():
    """Verifica se está rodando como administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def test_hardware_monitor():
    """Testa o hardware_monitor com todos os sensores."""
    print("\n" + "="*60)
    print("TESTE DE SENSORES - HARDWARE MONITOR")
    print("="*60)
    
    try:
        import hardware_monitor
        print("✓ hardware_monitor importado com sucesso")
        
        # Inicializar monitor (classe HardwareMonitor)
        monitor = hardware_monitor.HardwareMonitor()
        
        if not monitor.enabled:
            print("⚠ Monitor NÃO habilitado!")
            print("  - Verifique se está rodando como ADMINISTRADOR")
            print("  - Verifique se a DLL está presente em libs/")
            return False, None
        
        print("✓ HardwareMonitor inicializado e habilitado!")
        
        # Buscar dados
        data = monitor.fetch_data()
        
        # Mostrar CPU
        print("\n--- CPU ---")
        for key, value in data["cpu"].items():
            status = "✓" if value != 0 else "⚠ (zero)"
            print(f"  {key}: {value} {status}")
        
        # Mostrar GPU
        print("\n--- GPU ---")
        for key, value in data["gpu"].items():
            status = "✓" if value != 0 else "⚠ (zero)"
            print(f"  {key}: {value} {status}")
        
        # Mostrar MOBO
        print("\n--- MOTHERBOARD ---")
        for key, value in data["mobo"].items():
            status = "✓" if value != 0 else "⚠ (zero)"
            print(f"  {key}: {value} {status}")
        
        # Mostrar RAM
        print("\n--- RAM ---")
        for key, value in data["ram"].items():
            status = "✓" if value != 0 else "⚠ (zero)"
            print(f"  {key}: {value} {status}")
        
        # Mostrar Storage
        print("\n--- STORAGE ---")
        if data["storage"]:
            for disk in data["storage"]:
                print(f"  Disco: {disk.get('name', 'N/A')}")
                for key, value in disk.items():
                    if key != 'name':
                        status = "✓" if value != 0 else "⚠"
                        print(f"    {key}: {value} {status}")
        else:
            print("  ⚠ Nenhum disco detectado")
        
        # Mostrar Fans
        print("\n--- FANS ---")
        if data["fans"]:
            for fan in data["fans"]:
                print(f"  {fan['name']}: {fan['rpm']} RPM ✓")
        else:
            print("  ⚠ Nenhum fan detectado")
        
        monitor.close()
        return True, data
        
    except Exception as e:
        print(f"✗ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_udp_broadcast():
    """Testa o envio UDP broadcast."""
    print("\n" + "="*60)
    print("TESTE DE UDP BROADCAST")
    print("="*60)
    
    try:
        # Carregar config
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        dest_ip = config.get('dest_ip', '255.255.255.255')
        porta = config.get('porta', 5005)
        modo = config.get('modo', 'broadcast')
        
        print(f"  Modo: {modo}")
        print(f"  IP Destino: {dest_ip}")
        print(f"  Porta: {porta}")
        
        # Criar socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2)
        
        # Enviar pacote de teste
        test_data = {"test": "admin_sensor_test", "timestamp": time.time()}
        message = json.dumps(test_data).encode('utf-8')
        
        sock.sendto(message, (dest_ip, porta))
        print(f"✓ Pacote de teste enviado para {dest_ip}:{porta}")
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"✗ Erro no UDP: {e}")
        return False

def test_full_sender_payload():
    """Testa a criação do payload completo como o sender faz."""
    print("\n" + "="*60)
    print("TESTE DE PAYLOAD COMPLETO (COMO O SENDER)")
    print("="*60)
    
    try:
        import psutil
        import hardware_monitor
        import gzip
        
        # Inicializar monitor
        monitor = hardware_monitor.HardwareMonitor()
        
        if not monitor.enabled:
            print("⚠ Monitor não habilitado - usando valores zerados")
            hw_data = None
        else:
            print("✓ Monitor habilitado!")
            hw_data = monitor.fetch_data()
        
        # Montar payload como o sender real faz
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
        
        # Serializar e comprimir
        json_data = json.dumps(payload).encode('utf-8')
        compressed = gzip.compress(json_data)
        
        print(f"\n✓ Payload criado com sucesso")
        print(f"  Tamanho JSON: {len(json_data)} bytes")
        print(f"  Tamanho comprimido: {len(compressed)} bytes")
        print(f"  Taxa de compressão: {(1 - len(compressed)/len(json_data))*100:.1f}%")
        
        print("\n--- RESUMO DO PAYLOAD ---")
        print(f"  CPU: usage={payload['cpu']['usage']}%, temp={payload['cpu']['temp']}°C, power={payload['cpu']['power']}W")
        print(f"  GPU: load={payload['gpu']['load']}%, temp={payload['gpu']['temp']}°C, fan={payload['gpu']['fan']}RPM")
        print(f"  MOBO: temp={payload['mobo']['temp']}°C")
        print(f"  RAM: {payload['ram']['used_gb']}/{payload['ram']['total_gb']}GB ({payload['ram']['percent']}%)")
        print(f"  Storage: {len(payload['storage'])} disco(s)")
        print(f"  Fans: {len(payload['fans'])} fan(s)")
        
        # Contar sensores funcionando
        sensors_ok = 0
        sensors_total = 0
        
        for cat in ['cpu', 'gpu', 'mobo']:
            for val in payload[cat].values():
                sensors_total += 1
                if val != 0:
                    sensors_ok += 1
        
        print(f"\n--- STATUS DOS SENSORES ---")
        print(f"  Sensores funcionando: {sensors_ok}/{sensors_total}")
        
        if sensors_ok < sensors_total * 0.5:
            print("\n  ⚠ AVISO: Menos de 50% dos sensores funcionando!")
            if not is_admin():
                print("  → Execute como ADMINISTRADOR para acesso completo!")
        else:
            print("\n  ✓ Maioria dos sensores funcionando!")
        
        if monitor.enabled:
            monitor.close()
        
        return True, payload
        
    except Exception as e:
        print(f"✗ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    print("="*60)
    print("TESTE COMPLETO DE TELEMETRIA - PERMISSÕES DE ADMIN")
    print("="*60)
    
    # Verificar admin
    admin_status = is_admin()
    print(f"\nExecutando como Administrador: {'SIM ✓' if admin_status else 'NÃO ✗'}")
    
    if not admin_status:
        print("\n⚠ AVISO: Este script NÃO está rodando como administrador!")
        print("  Alguns sensores podem retornar valores zerados.")
        print("  Para teste completo, execute como administrador.")
    
    # Executar testes
    print("\n")
    
    # Teste 1: Hardware Monitor
    hw_ok, hw_data = test_hardware_monitor()
    
    # Teste 2: UDP Broadcast
    udp_ok = test_udp_broadcast()
    
    # Teste 3: Payload completo
    payload_ok, payload = test_full_sender_payload()
    
    # Resumo final
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    print(f"  Hardware Monitor: {'✓ OK' if hw_ok else '✗ FALHOU'}")
    print(f"  UDP Broadcast: {'✓ OK' if udp_ok else '✗ FALHOU'}")
    print(f"  Payload Completo: {'✓ OK' if payload_ok else '✗ FALHOU'}")
    print(f"  Permissões Admin: {'✓ SIM' if admin_status else '✗ NÃO'}")
    
    if all([hw_ok, udp_ok, payload_ok]):
        if admin_status:
            print("\n✓ TODOS OS TESTES PASSARAM COM ADMIN!")
            print("  O sender está pronto para uso completo.")
        else:
            print("\n⚠ Testes passaram, mas sem admin alguns sensores podem estar zerados.")
    else:
        print("\n✗ ALGUNS TESTES FALHARAM!")
    
    print("\n")
    input("Pressione ENTER para sair...")

if __name__ == "__main__":
    main()
