"""
Visualizador detalhado de um pacote de telemetria.
"""
import socket
import json
import gzip

print('='*60)
print('VISUALIZADOR DE PACOTE DETALHADO')
print('='*60)
print('Aguardando 1 pacote...')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', 5005))
sock.settimeout(5)

try:
    data, addr = sock.recvfrom(65535)
    
    # Descomprimir
    try:
        decompressed = gzip.decompress(data)
        payload = json.loads(decompressed.decode('utf-8'))
        print(f'\n✓ Pacote recebido de {addr[0]}:{addr[1]}')
        print(f'  Tamanho original: {len(decompressed)} bytes')
        print(f'  Tamanho comprimido: {len(data)} bytes')
    except:
        payload = json.loads(data.decode('utf-8'))
        print(f'\n✓ Pacote recebido de {addr[0]} (sem compressão)')
    
    print('\n' + '='*60)
    print('PAYLOAD COMPLETO:')
    print('='*60)
    print(json.dumps(payload, indent=2))
    
    print('\n' + '='*60)
    print('RESUMO DOS SENSORES:')
    print('='*60)
    
    # CPU
    cpu = payload.get('cpu', {})
    print('\n[CPU]')
    for k, v in cpu.items():
        print(f'  {k}: {v}')
    
    # GPU
    gpu = payload.get('gpu', {})
    print('\n[GPU]')
    for k, v in gpu.items():
        print(f'  {k}: {v}')
    
    # MOBO
    mobo = payload.get('mobo', {})
    print('\n[MOTHERBOARD]')
    for k, v in mobo.items():
        print(f'  {k}: {v}')
    
    # RAM
    ram = payload.get('ram', {})
    print('\n[RAM]')
    for k, v in ram.items():
        print(f'  {k}: {v}')
    
    # Storage
    storage = payload.get('storage', [])
    print('\n[STORAGE]')
    if storage:
        for i, disk in enumerate(storage):
            print(f'\n  Disco {i+1}: {disk.get("name", "N/A")}')
            for k, v in disk.items():
                if k != 'name':
                    print(f'    {k}: {v}')
    else:
        print('  Nenhum disco detectado')
    
    # Fans
    fans = payload.get('fans', [])
    print('\n[FANS]')
    if fans:
        for fan in fans:
            print(f'  {fan.get("name", "Fan")}: {fan.get("rpm", 0)} RPM')
    else:
        print('  Nenhum fan detectado')
    
    # Network
    net = payload.get('network', {})
    print('\n[NETWORK]')
    for k, v in net.items():
        print(f'  {k}: {v}')
    
except socket.timeout:
    print('\n✗ Timeout - nenhum pacote recebido')
    print('  O sender está rodando?')

sock.close()
print('\n' + '='*60)
