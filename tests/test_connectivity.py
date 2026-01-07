"""
Teste de conectividade de rede.
Execute no NOTEBOOK para verificar se consegue receber do PC.
"""
import socket
import time

def test_connection():
    print("="*50)
    print("TESTE DE CONECTIVIDADE - RECEIVER")
    print("="*50)
    
    # Configurações
    porta = 5005
    sender_ip = input("Digite o IP do Sender (PC): ").strip() or "192.168.10.101"
    
    print(f"\nTestando recepção de {sender_ip}:{porta}")
    print("Aguardando pacotes por 30 segundos...")
    print("(Certifique-se de que o sender está rodando no PC)")
    print()
    
    # Criar socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', porta))
    sock.settimeout(2)
    
    received = 0
    start = time.time()
    
    try:
        while time.time() - start < 30:
            try:
                data, addr = sock.recvfrom(65535)
                received += 1
                print(f"[{received}] Recebido {len(data)} bytes de {addr[0]}:{addr[1]}")
                
                if addr[0] == sender_ip:
                    print(f"    ✓ IP confere com o sender!")
                else:
                    print(f"    ⚠ IP diferente do sender configurado")
                    
            except socket.timeout:
                elapsed = int(time.time() - start)
                print(f"... aguardando ({elapsed}s)", end='\r')
                
    except KeyboardInterrupt:
        pass
    
    sock.close()
    
    print("\n" + "="*50)
    if received > 0:
        print(f"✓ SUCESSO! Recebidos {received} pacotes")
    else:
        print("✗ NENHUM PACOTE RECEBIDO")
        print("\nPossíveis causas:")
        print("1. Sender não está rodando no PC")
        print("2. Firewall bloqueando porta 5005")
        print("3. Dispositivos em redes diferentes")
        print("\nPara verificar a rede:")
        print(f"  - No notebook, tente: ping {sender_ip}")
        print(f"  - Verifique se a porta 5005 UDP está liberada")
    print("="*50)

if __name__ == "__main__":
    test_connection()
