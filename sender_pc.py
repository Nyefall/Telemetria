"""
Telemetria - Sender (PC Principal)
===================================
Coleta métricas de hardware e envia via UDP para o Receiver.
Roda na bandeja do sistema (System Tray) após inicialização.

Requer privilégios de administrador para acessar sensores.
"""
from __future__ import annotations

import psutil
import socket
import time
import json
import sys
import os
import gzip
import ctypes
import threading
from typing import Optional, Any

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
        
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            f'"{script}" {params}', None, 1
        )
        sys.exit(0)

# Argumento --no-admin para desativar elevação (para debug)
SKIP_ADMIN = "--no-admin" in sys.argv

if not SKIP_ADMIN and not is_admin():
    print("=" * 50)
    print("ELEVANDO PRIVILÉGIOS PARA ADMINISTRADOR...")
    print("(Necessário para acessar sensores de hardware)")
    print("=" * 50)
    run_as_admin()
# ======================================================


# ========== IMPORTS PÓS-ELEVAÇÃO ==========
try:
    import hardware_monitor
    HAS_HWMON = True
except ImportError:
    HAS_HWMON = False

# System Tray (pystray)
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    print("[Aviso] pystray/PIL não instalados. System tray desativado.")


# ========== CONFIGURAÇÕES ==========
def carregar_config():
    """Carrega configurações do config.json ou usa padrões."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    config_padrao = {
        "modo": "broadcast",
        "dest_ip": "255.255.255.255",
        "porta": 5005,
        "intervalo": 0.5,
        "bind_ip": ""  # IP local para enviar (vazio = auto)
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key in config_padrao:
                    if key not in config:
                        config[key] = config_padrao[key]
                print(f"[Config] Carregado de {config_path}")
                return config
        except Exception as e:
            print(f"[Config] Erro: {e}")
    else:
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({
                    **config_padrao,
                    "comentarios": {
                        "modo": "Opções: 'broadcast' ou 'unicast'",
                        "dest_ip": "IP do notebook (ignorado em broadcast)",
                        "porta": "Porta UDP",
                        "intervalo": "Segundos entre envios"
                    }
                }, f, indent=4, ensure_ascii=False)
            print(f"[Config] Criado config.json padrão")
        except:
            pass
    
    return config_padrao

CONFIG = carregar_config()
DEST_IP = CONFIG["dest_ip"]
PORTA = CONFIG["porta"]
INTERVALO = CONFIG["intervalo"]
MODO = CONFIG["modo"]
BIND_IP = CONFIG.get("bind_ip", "")  # IP local para bind
# ==========================================


class TelemetrySender:
    """Sender de telemetria com suporte a System Tray."""
    
    def __init__(self):
        self.running = True
        self.paused = False
        self.monitor = None
        self.sock = None
        self.icon = None
        self.last_net = None
        self.last_t = None
        
        # Cache para link de rede (evita chamar PowerShell a cada ciclo)
        self.cached_link_info: dict = {"link_speed_mbps": 0, "adapter_name": ""}
        self.last_link_check: float = 0
        self.LINK_CHECK_INTERVAL: float = 10.0  # Verificar apenas a cada 10 segundos
        
        # Inicializa socket
        self._init_socket()
        
        # Inicializa hardware monitor
        self._init_hardware_monitor()
        
        # Inicializa rede
        self.last_net = psutil.net_io_counters()
        self.last_t = time.time()
    
    def _init_socket(self):
        """Configura socket UDP."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        if MODO == "broadcast" or DEST_IP == "255.255.255.255":
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print("[Socket] Modo BROADCAST ativado")
        else:
            print(f"[Socket] Modo UNICAST - {DEST_IP}")
        
        # Bind a uma interface específica se configurado
        if BIND_IP:
            try:
                self.sock.bind((BIND_IP, 0))
                print(f"[Socket] Bind na interface: {BIND_IP}")
            except Exception as e:
                print(f"[Socket] Erro ao bind em {BIND_IP}: {e}")
        else:
            print("[Socket] Usando interface padrão")
    
    def _init_hardware_monitor(self):
        """Inicializa LibreHardwareMonitor."""
        if HAS_HWMON:
            print("[HW] Inicializando LibreHardwareMonitor...")
            self.monitor = hardware_monitor.HardwareMonitor()
            if not self.monitor.enabled:
                print("[HW] AVISO: DLL não carregou. Dados limitados.")
                self.monitor = None
        else:
            print("[HW] hardware_monitor.py não encontrado.")
    
    def _create_tray_icon(self):
        """Cria ícone para System Tray."""
        # Cria imagem simples (círculo verde)
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse([4, 4, size-4, size-4], fill=(0, 200, 100, 255))
        draw.ellipse([20, 20, size-20, size-20], fill=(0, 100, 50, 255))
        
        return image
    
    def _tray_menu(self):
        """Menu do System Tray."""
        return pystray.Menu(
            pystray.MenuItem("⚡ Telemetria Ativa", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⏸️ Pausar" if not self.paused else "▶️ Retomar", self._toggle_pause),
            pystray.MenuItem("🔄 Reiniciar Monitor", self._restart_monitor),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Encerrar", self._quit)
        )
    
    def _toggle_pause(self, icon=None, item=None):
        """Pausa/retoma o envio."""
        self.paused = not self.paused
        status = "pausado" if self.paused else "ativo"
        print(f"[Sender] {status.upper()}")
        if self.icon:
            self.icon.update_menu()
    
    def _restart_monitor(self, icon=None, item=None):
        """Reinicia o hardware monitor."""
        print("[HW] Reiniciando monitor...")
        if self.monitor:
            try:
                self.monitor.close()
            except:
                pass
        self._init_hardware_monitor()
    
    def _quit(self, icon=None, item=None):
        """Encerra o sender."""
        print("\n[Sender] Encerrando...")
        self.running = False
        if self.icon:
            self.icon.stop()
    
    def _calcular_rede(self):
        """Calcula velocidade de rede."""
        now = time.time()
        net_io = psutil.net_io_counters()
        delta = now - self.last_t
        if delta <= 0:
            delta = 1
        
        sent = net_io.bytes_sent - self.last_net.bytes_sent
        recv = net_io.bytes_recv - self.last_net.bytes_recv
        
        self.last_net = net_io
        self.last_t = now
        
        return (sent/1024)/delta, (recv/1024)/delta
    
    def _medir_ping(self, host="8.8.8.8"):
        """Mede latência para host externo."""
        try:
            t1 = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((host, 53))
            s.close()
            return round((time.time() - t1) * 1000, 1)
        except:
            return 0
    
    def _build_payload(self, hw_data):
        """Monta payload de telemetria (unificado)."""
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        up, down = self._calcular_rede()
        ping = self._medir_ping()
        
        # Valores padrão
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
                "ping_ms": ping,
                "link_speed_mbps": 0,
                "adapter_name": ""
            }
        }
        
        # Sobrescreve com dados do hardware monitor se disponíveis
        if hw_data:
            payload["cpu"]["temp"] = round(hw_data["cpu"]["temp"], 1)
            payload["cpu"]["voltage"] = round(hw_data["cpu"]["voltage"], 3)
            payload["cpu"]["power"] = round(hw_data["cpu"]["power"], 1)
            payload["cpu"]["clock"] = round(hw_data["cpu"]["clock"], 0)
            
            payload["gpu"]["load"] = round(hw_data["gpu"]["load"], 1)
            payload["gpu"]["temp"] = round(hw_data["gpu"]["temp"], 1)
            payload["gpu"]["voltage"] = round(hw_data["gpu"]["voltage"], 3)
            payload["gpu"]["clock_core"] = round(hw_data["gpu"]["clock_core"], 0)
            payload["gpu"]["clock_mem"] = round(hw_data["gpu"]["clock_mem"], 0)
            payload["gpu"]["fan"] = round(hw_data["gpu"]["fan"], 0)
            payload["gpu"]["mem_used_mb"] = round(hw_data["gpu"]["mem_used"], 0)
            
            payload["mobo"]["temp"] = round(hw_data["mobo"]["temp"], 1)
            payload["storage"] = hw_data["storage"]
            payload["fans"] = hw_data["fans"]
        
        # Obter informações do adaptador de rede (velocidade do link) COM CACHE
        # A velocidade do link não muda frequentemente, só quando desconecta o cabo
        if self.monitor and self.monitor.enabled:
            try:
                current_time = time.time()
                # Só chama o PowerShell se passou o tempo do intervalo
                if current_time - self.last_link_check > self.LINK_CHECK_INTERVAL:
                    self.cached_link_info = self.monitor.get_network_link_info()
                    self.last_link_check = current_time
                
                # Usa os dados cacheados
                payload["network"]["link_speed_mbps"] = self.cached_link_info.get("link_speed_mbps", 0)
                payload["network"]["adapter_name"] = self.cached_link_info.get("adapter_name", "")
            except Exception:
                pass
        
        return payload
    
    def _sender_loop(self):
        """Loop principal de coleta e envio."""
        print(f"\n{'='*50}")
        print("   SENTINELA DE TELEMETRIA - ATIVO")
        print(f"{'='*50}")
        print(f"Destino: {'BROADCAST' if MODO == 'broadcast' else DEST_IP}:{PORTA}")
        print(f"Intervalo: {INTERVALO}s")
        print(f"{'='*50}\n")
        
        # Primeira leitura de CPU (prepara o contador)
        psutil.cpu_percent(interval=None)
        
        while self.running:
            if not self.paused:
                try:
                    # Coleta dados
                    hw_data = None
                    if self.monitor and self.monitor.enabled:
                        hw_data = self.monitor.fetch_data()
                    
                    # Monta payload
                    payload = self._build_payload(hw_data)
                    
                    # Serializa e compacta
                    data = json.dumps(payload).encode()
                    compressed = gzip.compress(data)
                    
                    # Magic byte: 0x01 = gzip, 0x00 = raw JSON
                    # Envia com prefixo indicando tipo de encoding
                    if len(compressed) < len(data):
                        sent = self.sock.sendto(b'\x01' + compressed, (DEST_IP, PORTA))
                        print(f"[Send] {sent} bytes para {DEST_IP}:{PORTA} (gzip)")
                    else:
                        sent = self.sock.sendto(b'\x00' + data, (DEST_IP, PORTA))
                        print(f"[Send] {sent} bytes para {DEST_IP}:{PORTA} (raw)")
                    
                except Exception as e:
                    print(f"[Erro] {e}")
            
            time.sleep(INTERVALO)
        
        # Cleanup
        if self.monitor:
            self.monitor.close()
        self.sock.close()
    
    def run(self):
        """Inicia o sender."""
        # Inicia thread de envio
        sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        sender_thread.start()
        
        if HAS_TRAY:
            # Minimiza console
            try:
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            except:
                pass
            
            # Cria ícone na bandeja
            self.icon = pystray.Icon(
                "Telemetria",
                self._create_tray_icon(),
                "Telemetria Sender",
                self._tray_menu()
            )
            
            print("[Tray] Rodando na bandeja do sistema...")
            self.icon.run()
        else:
            # Sem tray, roda no console
            print("[Console] Ctrl+C para sair...")
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self._quit()


def main():
    """Função principal do Sender"""
    sender = TelemetrySender()
    sender.run()


if __name__ == "__main__":
    main()
