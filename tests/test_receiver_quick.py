"""
Receptor rápido para testar o sender.
"""
import socket
import json
import gzip
import time

print('='*60)
print('RECEPTOR DE TESTE - CAPTURANDO PACOTES DO SENDER')
print('='*60)
print('Aguardando pacotes na porta 5005...')
print('(Pressione Ctrl+C para parar)')
print()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', 5005))
sock.settimeout(2)

count = 0
start = time.time()

try:
    while count < 10:  # Captura 10 pacotes
        try:
            data, addr = sock.recvfrom(65535)
            
            # Magic byte: 0x01 = gzip, 0x00 = raw JSON
            if len(data) > 0:
                magic = data[0]
                if magic == 0x01:  # GZIP
                    payload = json.loads(gzip.decompress(data[1:]).decode('utf-8'))
                elif magic == 0x00:  # Raw JSON
                    payload = json.loads(data[1:].decode('utf-8'))
                else:
                    # Retrocompatibilidade
                    try:
                        payload = json.loads(gzip.decompress(data).decode('utf-8'))
                    except:
                        payload = json.loads(data.decode('utf-8'))
            
            count += 1
            cpu = payload.get('cpu', {})
            gpu = payload.get('gpu', {})
            ram = payload.get('ram', {})
            storage = payload.get('storage', [])
            fans = payload.get('fans', [])
            
            print(f'[{count}] Recebido de {addr[0]}:{addr[1]}')
            print(f'    CPU: usage={cpu.get("usage", 0):.1f}% | temp={cpu.get("temp", 0):.1f}°C | power={cpu.get("power", 0):.1f}W | clock={cpu.get("clock", 0):.0f}MHz')
            print(f'    GPU: load={gpu.get("load", 0):.1f}% | temp={gpu.get("temp", 0):.1f}°C | fan={gpu.get("fan", 0):.0f}RPM')
            print(f'    RAM: {ram.get("used_gb", 0):.1f}/{ram.get("total_gb", 0):.1f}GB ({ram.get("percent", 0):.1f}%)')
            print(f'    Storage: {len(storage)} disco(s) | Fans: {len(fans)}')
            print()
            
        except socket.timeout:
            print('.', end='', flush=True)
            
except KeyboardInterrupt:
    pass

sock.close()
print()
print('='*60)
print(f'RESULTADO: {count} pacotes recebidos em {time.time()-start:.1f}s')

if count > 0:
    print()
    print('ANALISE DOS SENSORES (ultimo pacote):')
    
    # Contar sensores funcionando
    sensors_ok = 0
    sensors_zero = 0
    
    for name, val in [
        ('CPU temp', cpu.get('temp', 0)),
        ('CPU power', cpu.get('power', 0)),
        ('CPU clock', cpu.get('clock', 0)),
        ('GPU temp', gpu.get('temp', 0)),
        ('GPU fan', gpu.get('fan', 0)),
    ]:
        if val > 0:
            print(f'    [OK] {name}: {val}')
            sensors_ok += 1
        else:
            print(f'    [!!] {name}: {val} (zerado)')
            sensors_zero += 1
    
    print()
    if sensors_zero > 2:
        print(f'AVISO: {sensors_zero} sensores zerados!')
        print('       O sender esta rodando como ADMINISTRADOR?')
    else:
        print('Sensores funcionando corretamente!')
        
print('='*60)
