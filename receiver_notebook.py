"""
Central de Telemetria - Receiver (Notebook)
============================================
Dashboard de monitoramento em tempo real.

Atalhos:
    G: Alternar gráficos
    F/F11: Fullscreen
    T: Alternar tema (escuro/claro)
    L: Ativar/desativar log CSV
    S: ⚙️ Configurações Gerais (Conexão, Aparência, Alertas, Notificações)
    I: Configurar IP do Sender (atalho para configurações)
    Q/ESC: Sair
"""
from __future__ import annotations

import socket
import json
import sys
import os
import gzip
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from collections import deque
import threading
import time
from datetime import datetime
from typing import Optional, Any, Deque

# ========== DPI AWARENESS (Windows) ==========
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# ========== NOTIFICAÇÕES WINDOWS ==========
try:
    from win10toast import ToastNotifier
    HAS_TOAST = True
except ImportError:
    HAS_TOAST = False
    print("[Aviso] win10toast não instalado. Notificações desativadas.")

# ========== MÓDULOS LOCAIS (se disponíveis) ==========
try:
    from ui.themes import get_legacy_colors, get_theme_names
    HAS_THEME_MODULE = True
except ImportError:
    HAS_THEME_MODULE = False

try:
    from core.sounds import get_sound_manager, AlertSound
    HAS_SOUND_MODULE = True
except ImportError:
    HAS_SOUND_MODULE = False


# ========== CONFIGURAÇÕES ==========
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receiver_config.json")


def carregar_config() -> dict[str, Any]:
    """Carrega configurações do receiver_config.json ou usa padrões."""
    config_padrao = {
        # === CONEXÃO ===
        "porta": 5005,
        "sender_ip": "",  # Vazio = broadcast/auto
        "modo": "auto",    # "auto" ou "manual"
        "expected_link_speed_mbps": 1000,  # Velocidade esperada: CAT5=100, CAT5e/6=1000, CAT6a/7=10000
        
        # === APARÊNCIA ===
        "tema": "dark",  # dark, light, high_contrast, cyberpunk
        "cores_customizadas": {
            "cpu": "",      # Vazio = usa cor do tema
            "gpu": "",
            "ram": "",
            "storage": "",
            "network": "",
            "mobo": ""
        },
        
        # === ALERTAS (Thresholds) ===
        "alertas": {
            "cpu_temp_warning": 70,
            "cpu_temp_critical": 85,
            "cpu_uso_warning": 70,
            "cpu_uso_critical": 90,
            "gpu_temp_warning": 75,
            "gpu_temp_critical": 90,
            "gpu_uso_warning": 80,
            "gpu_uso_critical": 95,
            "ram_warning": 70,
            "ram_critical": 90,
            "storage_temp_warning": 45,
            "storage_temp_critical": 55,
            "storage_uso_warning": 80,
            "storage_uso_critical": 95,
            "ping_warning": 50,
            "ping_critical": 100
        },
        
        # === SONS ===
        "sons": {
            "enabled": True,
            "cooldown_seconds": 10,
            "warning_sound": "warning",
            "critical_sound": "beep_urgent"
        },
        
        # === NOTIFICAÇÕES WEBHOOK ===
        "webhooks": {
            "enabled": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "discord_webhook_url": "",
            "ntfy_topic": "",
            "ntfy_server": "https://ntfy.sh",
            "cooldown_seconds": 300  # 5 minutos
        },
        
        # === HISTÓRICO ===
        "historico": {
            "csv_enabled": False,
            "auto_start_log": False,
            "retention_days": 7
        }
    }
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"[Config] Carregado de {CONFIG_PATH}")
                return {**config_padrao, **config}
        except Exception as e:
            print(f"[Config] Erro ao ler: {e}")
    
    # Tenta ler porta e expected_link_speed_mbps do config.json antigo
    old_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(old_config):
        try:
            with open(old_config, 'r', encoding='utf-8') as f:
                old = json.load(f)
                config_padrao["porta"] = old.get("porta", 5005)
                config_padrao["expected_link_speed_mbps"] = old.get("expected_link_speed_mbps", 1000)
        except:
            pass
    
    return config_padrao


def salvar_config(config: dict[str, Any]) -> bool:
    """Salva configurações do receiver."""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"[Config] Salvo em {CONFIG_PATH}")
        return True
    except Exception as e:
        print(f"[Config] Erro ao salvar: {e}")
        return False


CONFIG = carregar_config()
HOST = "0.0.0.0"
PORTA = CONFIG["porta"]
HISTORY_SIZE = 60
CONNECTION_TIMEOUT = 5  # segundos sem dados = desconectado
# ===================================


class TelemetryDashboard:
    """
    Dashboard principal de telemetria.
    
    Exibe métricas de hardware em tempo real recebidas via UDP.
    """
    
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Central de Telemetria")
        self.root.geometry("1366x700")
        self.root.minsize(1200, 600)
        
        # Estado
        self.is_fullscreen = False
        self.show_graphs = False
        self.dark_theme = True
        self.logging_enabled = False
        self.last_data_time = 0
        self.is_connected = False
        self.notified_critical = {}  # Evita spam de notificações
        
        # Configuração de conexão
        self.sender_ip = CONFIG.get("sender_ip", "")
        self.connection_mode = CONFIG.get("modo", "auto")
        self.porta = CONFIG.get("porta", 5005)
        self.restart_receiver = False  # Flag para reiniciar receiver
        
        # Dados (encapsulados na classe)
        self.current_data = {}
        self.data_lock = threading.Lock()
        self.history = {
            "cpu_usage": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
            "cpu_temp": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
            "gpu_load": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
            "gpu_temp": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
            "ram": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
            "net_down": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
            "net_up": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
            "ping": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
        }
        
        # Log CSV
        self.log_file = None
        self.log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        
        # Toast notifier
        self.toaster = ToastNotifier() if HAS_TOAST else None
        
        # Temas - usa módulo se disponível, senão fallback para inline
        if HAS_THEME_MODULE:
            self.themes = {
                "dark": get_legacy_colors(dark_mode=True),
                "light": get_legacy_colors(dark_mode=False)
            }
        else:
            self.themes = {
                "dark": {
                    "bg": "#0a0a0a",
                    "panel": "#1a1a1a",
                    "border": "#333333",
                    "title": "#00ffff",
                    "cpu": "#00bfff",
                    "gpu": "#00ff00",
                    "ram": "#ff00ff",
                    "mobo": "#ffaa00",
                    "storage": "#ff6600",
                    "network": "#00ffaa",
                    "warning": "#ffff00",
                    "critical": "#ff3333",
                    "text": "#ffffff",
                    "dim": "#888888"
                },
                "light": {
                    "bg": "#f0f0f0",
                    "panel": "#ffffff",
                    "border": "#cccccc",
                    "title": "#0066cc",
                    "cpu": "#0088cc",
                    "gpu": "#00aa00",
                    "ram": "#aa00aa",
                    "mobo": "#cc7700",
                    "storage": "#cc4400",
                    "network": "#00aa77",
                    "warning": "#cc9900",
                    "critical": "#cc0000",
                    "text": "#000000",
                    "dim": "#666666"
                }
            }
        self.colors = self.themes["dark"]
        
        # Configura janela
        self.root.configure(bg=self.colors["bg"])
        
        # Fontes
        self.font_title = tkfont.Font(family="Consolas", size=16, weight="bold")
        self.font_section = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.font_value = tkfont.Font(family="Consolas", size=12)
        self.font_small = tkfont.Font(family="Consolas", size=9)
        self.font_help = tkfont.Font(family="Consolas", size=8)
        
        # Cria interface
        self._create_ui()
        
        # Binds de teclado
        self._bind_keys()
        
        # Inicia thread de recebimento
        self.recv_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self.recv_thread.start()
        
        # Inicia loop de atualização
        self._update_ui()
    
    def _create_ui(self):
        """Cria todos os elementos da interface."""
        # Container principal
        self.main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Título
        self.title_label = tk.Label(
            self.main_frame, 
            text="⚡ CENTRAL DE TELEMETRIA ⚡", 
            font=self.font_title,
            fg=self.colors["title"],
            bg=self.colors["bg"]
        )
        self.title_label.pack(pady=(0, 5))
        
        # Status de conexão
        self.status_label = tk.Label(
            self.main_frame,
            text="○ Aguardando dados...",
            font=self.font_small,
            fg=self.colors["dim"],
            bg=self.colors["bg"]
        )
        self.status_label.pack()
        
        # Container para painéis
        self.panels_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        self.panels_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Row 1: CPU | GPU | RAM
        row1 = tk.Frame(self.panels_frame, bg=self.colors["bg"])
        row1.pack(fill=tk.X, pady=3)
        
        self.cpu_panel = self._create_panel(row1, "CPU", self.colors["cpu"])
        self.gpu_panel = self._create_panel(row1, "GPU", self.colors["gpu"])
        self.ram_panel = self._create_panel(row1, "RAM", self.colors["ram"])
        
        # Row 2: MOBO | STORAGE | NETWORK
        row2 = tk.Frame(self.panels_frame, bg=self.colors["bg"])
        row2.pack(fill=tk.X, pady=3)
        
        self.mobo_panel = self._create_panel(row2, "MOBO", self.colors["mobo"])
        self.storage_panel = self._create_panel(row2, "STORAGE", self.colors["storage"])
        self.network_panel = self._create_panel(row2, "NETWORK", self.colors["network"])
        
        # Pré-cria labels de storage para evitar recriação
        self._precreate_storage_labels()
        
        # Canvas para gráficos (oculto por padrão)
        self.graph_canvas = tk.Canvas(
            self.main_frame,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            height=150
        )
        
        # Help bar
        self.help_label = tk.Label(
            self.main_frame,
            text="[F] Fullscreen | [G] Gráficos | [T] Tema | [L] Log | [S] ⚙️ Configurações | [Q] Sair",
            font=self.font_help,
            fg=self.colors["dim"],
            bg=self.colors["bg"]
        )
        self.help_label.pack(side=tk.BOTTOM, pady=2)
    
    def _create_panel(self, parent, title, color):
        """Cria um painel individual."""
        frame = tk.Frame(
            parent,
            bg=self.colors["panel"],
            highlightthickness=2,
            highlightbackground=color
        )
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        
        title_lbl = tk.Label(
            frame,
            text=f"── {title} ──",
            font=self.font_section,
            fg=color,
            bg=self.colors["panel"]
        )
        title_lbl.pack(pady=(5, 3))
        
        values_frame = tk.Frame(frame, bg=self.colors["panel"])
        values_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        
        return {"frame": frame, "title": title_lbl, "values": values_frame, "labels": {}, "color": color}
    
    def _precreate_storage_labels(self):
        """Pré-cria labels de storage para evitar recriação a cada update."""
        for i in range(2):  # Max 2 discos
            self._update_value(self.storage_panel, f"disk{i}_name", f"Disco {i+1}", "-", "")
            self._update_value(self.storage_panel, f"disk{i}_temp", "  Temp", 0, "°C")
            self._update_value(self.storage_panel, f"disk{i}_health", "  Saúde", 0, "%")
            self._update_value(self.storage_panel, f"disk{i}_used", "  Usado", 0, "%")
    
    def _bind_keys(self):
        """Configura atalhos de teclado."""
        self.root.bind('<F>', self._toggle_fullscreen)
        self.root.bind('<f>', self._toggle_fullscreen)
        self.root.bind('<F11>', self._toggle_fullscreen)
        self.root.bind('<G>', self._toggle_graphs)
        self.root.bind('<g>', self._toggle_graphs)
        self.root.bind('<T>', self._toggle_theme)
        self.root.bind('<t>', self._toggle_theme)
        self.root.bind('<L>', self._toggle_logging)
        self.root.bind('<l>', self._toggle_logging)
        self.root.bind('<I>', self._show_ip_config)
        self.root.bind('<i>', self._show_ip_config)
        self.root.bind('<S>', self._show_settings)
        self.root.bind('<s>', self._show_settings)
        self.root.bind('<q>', self._quit_app)
        self.root.bind('<Q>', self._quit_app)
        self.root.bind('<Escape>', self._quit_app)
    
    def _receiver_loop(self):
        """Thread que recebe dados UDP."""
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((HOST, self.porta))
                sock.settimeout(1.0)
                
                mode_str = f"Manual ({self.sender_ip})" if self.sender_ip else "Auto (broadcast)"
                print(f"[Receiver] Ouvindo em {HOST}:{self.porta} - Modo: {mode_str}")
                
                self.restart_receiver = False
                
                while not self.restart_receiver:
                    try:
                        data, addr = sock.recvfrom(16384)
                        
                        # Debug: mostrar de onde veio o pacote
                        print(f"[Receiver] Pacote recebido de {addr[0]}:{addr[1]} ({len(data)} bytes)")
                        
                        # Se modo manual, filtra por IP
                        if self.sender_ip and addr[0] != self.sender_ip:
                            print(f"[Receiver] Ignorando pacote de {addr[0]} (esperado: {self.sender_ip})")
                            continue
                        
                        # Magic byte: 0x01 = gzip, 0x00 = raw JSON
                        # Retrocompatível: se não começar com 0x00 ou 0x01, tenta gzip
                        if len(data) > 0:
                            magic = data[0]
                            if magic == 0x01:  # GZIP
                                data = gzip.decompress(data[1:])
                            elif magic == 0x00:  # Raw JSON
                                data = data[1:]
                            else:
                                # Retrocompatibilidade: sem magic byte
                                try:
                                    data = gzip.decompress(data)
                                except:
                                    pass
                        
                        payload = json.loads(data.decode())
                        
                        # Debug: confirmar que o payload foi parseado
                        cpu_usage = payload.get("cpu", {}).get("usage", 0)
                        print(f"[Receiver] Payload OK - CPU: {cpu_usage}%")
                        
                        with self.data_lock:
                            self.current_data = payload
                            self.last_data_time = time.time()
                            
                            # Atualiza históricos
                            self.history["cpu_usage"].append(payload.get("cpu", {}).get("usage", 0))
                            self.history["cpu_temp"].append(payload.get("cpu", {}).get("temp", 0))
                            self.history["gpu_load"].append(payload.get("gpu", {}).get("load", 0))
                            self.history["gpu_temp"].append(payload.get("gpu", {}).get("temp", 0))
                            self.history["ram"].append(payload.get("ram", {}).get("percent", 0))
                            self.history["net_down"].append(payload.get("network", {}).get("down_kbps", 0))
                            self.history["net_up"].append(payload.get("network", {}).get("up_kbps", 0))
                            self.history["ping"].append(payload.get("network", {}).get("ping_ms", 0))
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[Receiver] Erro: {e}")
                
                sock.close()
                print("[Receiver] Reiniciando com novas configurações...")
                
            except Exception as e:
                print(f"[Receiver] Erro ao criar socket: {e}")
                time.sleep(2)
    
    def _update_value(self, panel, key, label, value, unit="", warn_threshold=None, crit_threshold=None):
        """Atualiza ou cria um valor em um painel."""
        if key not in panel["labels"]:
            row = tk.Frame(panel["values"], bg=self.colors["panel"])
            row.pack(fill=tk.X, pady=1)
            
            lbl_name = tk.Label(
                row,
                text=f"{label}:",
                font=self.font_small,
                fg=self.colors["dim"],
                bg=self.colors["panel"],
                anchor="w",
                width=10
            )
            lbl_name.pack(side=tk.LEFT)
            
            lbl_value = tk.Label(
                row,
                text="-",
                font=self.font_value,
                fg=self.colors["text"],
                bg=self.colors["panel"],
                anchor="e",
                width=12
            )
            lbl_value.pack(side=tk.RIGHT)
            
            panel["labels"][key] = {"name": lbl_name, "value": lbl_value, "row": row}
        
        lbl = panel["labels"][key]["value"]
        
        # Formata valor
        if isinstance(value, float):
            if unit == "V":
                text = f"{value:.3f}{unit}"
            elif unit in ["°C", "%", "W"]:
                text = f"{value:.1f}{unit}"
            else:
                text = f"{value:.1f}{unit}"
        else:
            text = f"{value}{unit}"
        
        lbl.config(text=text)
        
        # Cor baseada em thresholds
        if crit_threshold and isinstance(value, (int, float)) and value >= crit_threshold:
            lbl.config(fg=self.colors["critical"])
            self._notify_critical(key, label, value, unit)
        elif warn_threshold and isinstance(value, (int, float)) and value >= warn_threshold:
            lbl.config(fg=self.colors["warning"])
        else:
            lbl.config(fg=self.colors["text"])
    
    def _notify_critical(self, key: str, label: str, value: float, unit: str) -> None:
        """Envia notificação Windows e toca som para valores críticos."""
        now = time.time()
        last_notify = self.notified_critical.get(key, 0)
        
        # Notifica no máximo a cada 60 segundos por métrica
        if now - last_notify > 60:
            self.notified_critical[key] = now
            
            # Toca som de alerta crítico
            if HAS_SOUND_MODULE:
                try:
                    sound_manager = get_sound_manager()
                    sound_manager.play(AlertSound.BEEP_URGENT)
                except:
                    pass
            
            # Mostra notificação Windows
            if self.toaster:
                try:
                    self.toaster.show_toast(
                        "⚠️ Telemetria - Alerta Crítico",
                        f"{label}: {value:.1f}{unit}",
                        duration=5,
                        threaded=True
                    )
                except:
                    pass
    
    def _update_ui(self):
        """Atualiza a interface com os dados mais recentes."""
        try:
            with self.data_lock:
                data = self.current_data.copy() if self.current_data else None
                last_time = self.last_data_time
            
            now = time.time()
            time_diff = now - last_time if last_time else float('inf')
            
            # Debug: atualizar título para provar que UI está viva
            self.root.title(f"Central de Telemetria - {time.strftime('%H:%M:%S')}")
            
            # Debug: verificar estado
            if data:
                print(f"[UI] Dados disponíveis, time_diff={time_diff:.1f}s, timeout={CONNECTION_TIMEOUT}s")
            
            # Verifica timeout de conexão
            if data and (now - last_time) < CONNECTION_TIMEOUT:
                if not self.is_connected:
                    self.is_connected = True
                
                self.status_label.config(
                    text=f"● Conectado | Atualizado: {time.strftime('%H:%M:%S')}" + 
                         (f" | 📝 LOG" if self.logging_enabled else ""),
                    fg=self.colors["gpu"]
                )
                
                self._update_panels(data)
                
                # Log CSV
                if self.logging_enabled:
                    self._log_to_csv(data)
                
                # Gráficos
                if self.show_graphs:
                    self._draw_graphs()
            else:
                if self.is_connected:
                    self.is_connected = False
                
                mode_text = f" (IP: {self.sender_ip})" if self.sender_ip else " (broadcast)"
                self.status_label.config(
                    text=f"○ Desconectado - Aguardando dados...{mode_text} | [I] Config",
                    fg=self.colors["critical"]
                )
        
        except Exception as e:
            print(f"[UI] Erro na atualização: {e}")
        
        # Agenda próxima atualização (sempre, mesmo com erro)
        try:
            self.root.after(500, self._update_ui)
        except Exception as e:
            print(f"[UI] Erro ao agendar update: {e}")
    
    def _update_panels(self, data):
        """Atualiza todos os painéis com os dados."""
        # Obter thresholds das configurações
        alertas = CONFIG.get("alertas", {})
        
        # CPU
        cpu = data.get("cpu", {})
        self._update_value(self.cpu_panel, "usage", "Uso", cpu.get("usage", 0), "%", 
                          alertas.get("cpu_uso_warning", 70), alertas.get("cpu_uso_critical", 90))
        self._update_value(self.cpu_panel, "temp", "Temp", cpu.get("temp", 0), "°C", 
                          alertas.get("cpu_temp_warning", 70), alertas.get("cpu_temp_critical", 85))
        self._update_value(self.cpu_panel, "voltage", "Voltagem", cpu.get("voltage", 0), "V")
        self._update_value(self.cpu_panel, "power", "Consumo", cpu.get("power", 0), "W")
        self._update_value(self.cpu_panel, "clock", "Clock", cpu.get("clock", 0), " MHz")
        
        # GPU
        gpu = data.get("gpu", {})
        self._update_value(self.gpu_panel, "load", "Uso", gpu.get("load", 0), "%", 
                          alertas.get("gpu_uso_warning", 80), alertas.get("gpu_uso_critical", 95))
        self._update_value(self.gpu_panel, "temp", "Temp", gpu.get("temp", 0), "°C", 
                          alertas.get("gpu_temp_warning", 75), alertas.get("gpu_temp_critical", 90))
        self._update_value(self.gpu_panel, "voltage", "Voltagem", gpu.get("voltage", 0), "V")
        self._update_value(self.gpu_panel, "clock_core", "Core", gpu.get("clock_core", 0), " MHz")
        self._update_value(self.gpu_panel, "clock_mem", "Mem Clk", gpu.get("clock_mem", 0), " MHz")
        self._update_value(self.gpu_panel, "mem_used", "VRAM", gpu.get("mem_used_mb", 0), " MB")
        self._update_value(self.gpu_panel, "fan", "Fan", gpu.get("fan", 0), " RPM")
        
        # RAM
        ram = data.get("ram", {})
        self._update_value(self.ram_panel, "percent", "Uso", ram.get("percent", 0), "%", 
                          alertas.get("ram_warning", 70), alertas.get("ram_critical", 90))
        self._update_value(self.ram_panel, "used", "Usado", ram.get("used_gb", 0), " GB")
        self._update_value(self.ram_panel, "total", "Total", ram.get("total_gb", 0), " GB")
        
        # MOBO
        mobo = data.get("mobo", {})
        self._update_value(self.mobo_panel, "temp", "Temp", mobo.get("temp", 0), "°C", 50, 70)
        
        # Fans da MOBO
        fans = data.get("fans", [])
        for i in range(4):
            if i < len(fans):
                fan = fans[i]
                name = fan.get("name", f"Fan {i}")[:10]
                rpm = fan.get("rpm", 0)
                self._update_value(self.mobo_panel, f"fan{i}", name, rpm, " RPM")
        
        # STORAGE (usa labels pré-criados)
        storage = data.get("storage", [])
        for i in range(2):
            if i < len(storage):
                disk = storage[i]
                name = disk.get("name", f"Disk {i}")[:15]
                self._update_value(self.storage_panel, f"disk{i}_name", f"Disco {i+1}", name, "")
                self._update_value(self.storage_panel, f"disk{i}_temp", "  Temp", disk.get("temp", 0), "°C", 
                                  alertas.get("storage_temp_warning", 45), alertas.get("storage_temp_critical", 55))
                self._update_value(self.storage_panel, f"disk{i}_health", "  Saúde", disk.get("health", 100), "%")
                self._update_value(self.storage_panel, f"disk{i}_used", "  Usado", disk.get("used_space", 0), "%", 
                                  alertas.get("storage_uso_warning", 80), alertas.get("storage_uso_critical", 95))
            else:
                # Limpa dados de disco não existente
                self._update_value(self.storage_panel, f"disk{i}_name", f"Disco {i+1}", "-", "")
                self._update_value(self.storage_panel, f"disk{i}_temp", "  Temp", 0, "°C")
                self._update_value(self.storage_panel, f"disk{i}_health", "  Saúde", 0, "%")
                self._update_value(self.storage_panel, f"disk{i}_used", "  Usado", 0, "%")
        
        # NETWORK
        net = data.get("network", {})
        self._update_value(self.network_panel, "down", "Download", net.get("down_kbps", 0), " KB/s")
        self._update_value(self.network_panel, "up", "Upload", net.get("up_kbps", 0), " KB/s")
        self._update_value(self.network_panel, "ping", "Ping", net.get("ping_ms", 0), " ms", 
                          alertas.get("ping_warning", 50), alertas.get("ping_critical", 100))
        
        # Link Speed com verificação de saúde baseada na velocidade esperada
        link_speed = net.get("link_speed_mbps", 0)
        adapter = net.get("adapter_name", "N/A")
        expected_speed = CONFIG.get("expected_link_speed_mbps", 1000)
        
        # Determinar saúde do link baseado na velocidade ESPERADA (configurável)
        if link_speed >= expected_speed:
            link_status = "OK"
            link_color = self.colors['gpu']  # Verde
        elif link_speed >= expected_speed * 0.1:
            link_status = f"Esperado: {expected_speed}"
            link_color = self.colors['warning']  # Amarelo
        elif link_speed > 0:
            link_status = f"Esperado: {expected_speed}"
            link_color = self.colors['critical']  # Vermelho
        else:
            link_status = "N/A"
            link_color = self.colors['dim']  # Cinza
        
        self._update_value(self.network_panel, "link", "Link", link_speed, " Mbps", expected_speed * 0.5, expected_speed * 0.1)
        self._update_value(self.network_panel, "adapter", "Adaptador", adapter[:15] if adapter else "N/A", "")
    
    def _log_to_csv(self, data):
        """Salva dados em arquivo CSV."""
        if not self.log_file:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cpu = data.get("cpu", {})
            gpu = data.get("gpu", {})
            ram = data.get("ram", {})
            net = data.get("network", {})
            
            line = f"{timestamp},{cpu.get('usage', 0)},{cpu.get('temp', 0)},{gpu.get('load', 0)},{gpu.get('temp', 0)},{ram.get('percent', 0)},{net.get('ping_ms', 0)}\n"
            self.log_file.write(line)
            self.log_file.flush()
        except Exception as e:
            print(f"[Log] Erro ao escrever: {e}")
    
    def _draw_graphs(self):
        """Desenha gráficos no canvas."""
        self.graph_canvas.delete("all")
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        
        if w < 100 or h < 50:
            return
        
        padding = 20
        graph_w = w - 2 * padding
        graph_h = h - 2 * padding
        
        self._draw_line_graph(list(self.history["cpu_usage"]), padding, padding, graph_w // 2, graph_h // 2, self.colors["cpu"], "CPU %", 100)
        self._draw_line_graph(list(self.history["gpu_load"]), padding + graph_w // 2, padding, graph_w // 2, graph_h // 2, self.colors["gpu"], "GPU %", 100)
        self._draw_line_graph(list(self.history["cpu_temp"]), padding, padding + graph_h // 2, graph_w // 2, graph_h // 2, "#ff8800", "CPU Temp", 100)
        self._draw_line_graph(list(self.history["ping"]), padding + graph_w // 2, padding + graph_h // 2, graph_w // 2, graph_h // 2, self.colors["network"], "Ping ms", max(max(self.history["ping"]) * 1.2, 50))
    
    def _draw_line_graph(self, data, x, y, w, h, color, label, max_val):
        """Desenha um gráfico de linha."""
        if not data or w < 10 or h < 10:
            return
        
        self.graph_canvas.create_text(x + 5, y + 5, text=label, fill=color, anchor="nw", font=self.font_small)
        self.graph_canvas.create_rectangle(x, y, x + w, y + h, outline=self.colors["border"])
        
        if len(data) < 2:
            return
        
        points = []
        step_x = w / (len(data) - 1)
        for i, val in enumerate(data):
            px = x + i * step_x
            py = y + h - (val / max_val) * (h - 10) if max_val > 0 else y + h
            points.extend([px, py])
        
        if len(points) >= 4:
            self.graph_canvas.create_line(points, fill=color, width=2, smooth=True)
    
    def _toggle_fullscreen(self, event=None):
        """Alterna modo fullscreen."""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
    
    def _toggle_graphs(self, event=None):
        """Alterna exibição de gráficos."""
        self.show_graphs = not self.show_graphs
        if self.show_graphs:
            self.graph_canvas.pack(fill=tk.X, pady=5, before=self.help_label)
        else:
            self.graph_canvas.pack_forget()
    
    def _toggle_theme(self, event=None):
        """Alterna entre tema escuro e claro."""
        self.dark_theme = not self.dark_theme
        self.colors = self.themes["dark" if self.dark_theme else "light"]
        self._apply_theme()
    
    def _apply_theme(self):
        """Aplica o tema atual a todos os widgets."""
        self.root.configure(bg=self.colors["bg"])
        self.main_frame.configure(bg=self.colors["bg"])
        self.panels_frame.configure(bg=self.colors["bg"])
        self.title_label.configure(bg=self.colors["bg"], fg=self.colors["title"])
        self.status_label.configure(bg=self.colors["bg"])
        self.help_label.configure(bg=self.colors["bg"], fg=self.colors["dim"])
        self.graph_canvas.configure(bg=self.colors["panel"], highlightbackground=self.colors["border"])
        
        # Atualiza painéis
        for panel in [self.cpu_panel, self.gpu_panel, self.ram_panel, self.mobo_panel, self.storage_panel, self.network_panel]:
            panel["frame"].configure(bg=self.colors["panel"])
            panel["title"].configure(bg=self.colors["panel"], fg=panel["color"])
            panel["values"].configure(bg=self.colors["panel"])
            
            for key, label_dict in panel["labels"].items():
                label_dict["row"].configure(bg=self.colors["panel"])
                label_dict["name"].configure(bg=self.colors["panel"], fg=self.colors["dim"])
                label_dict["value"].configure(bg=self.colors["panel"])
        
        # Atualiza rows
        for child in self.panels_frame.winfo_children():
            try:
                child.configure(bg=self.colors["bg"])
            except:
                pass
    
    def _show_ip_config(self, event=None):
        """Mostra janela de configuração de IP do sender - LEGACY, redireciona para config geral."""
        self._show_settings(event)
    
    def _show_settings(self, event=None):
        """Mostra janela de configurações gerais com abas."""
        config_window = tk.Toplevel(self.root)
        config_window.title("⚙️ Configurações Gerais")
        config_window.geometry("600x650")
        config_window.resizable(False, False)
        config_window.configure(bg=self.colors["bg"])
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Centralizar na tela
        config_window.update_idletasks()
        x = (config_window.winfo_screenwidth() // 2) - 300
        y = (config_window.winfo_screenheight() // 2) - 325
        config_window.geometry(f"+{x}+{y}")
        
        # Título
        title = tk.Label(
            config_window,
            text="⚙️ Configurações Gerais",
            font=self.font_section,
            fg=self.colors["title"],
            bg=self.colors["bg"]
        )
        title.pack(pady=10)
        
        # Notebook (abas) com estilo customizado
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.TNotebook', background=self.colors["bg"], borderwidth=0)
        style.configure('Custom.TNotebook.Tab', 
                       background=self.colors["panel"], 
                       foreground=self.colors["text"],
                       padding=[15, 8],
                       font=('Consolas', 9))
        style.map('Custom.TNotebook.Tab',
                 background=[('selected', self.colors["cpu"])],
                 foreground=[('selected', '#000000')])
        
        notebook = ttk.Notebook(config_window, style='Custom.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # === ABA 1: CONEXÃO ===
        tab_conexao = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab_conexao, text="📡 Conexão")
        self._create_connection_tab(tab_conexao)
        
        # === ABA 2: APARÊNCIA ===
        tab_aparencia = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab_aparencia, text="🎨 Aparência")
        self._create_appearance_tab(tab_aparencia)
        
        # === ABA 3: ALERTAS ===
        tab_alertas = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab_alertas, text="🔔 Alertas")
        self._create_alerts_tab(tab_alertas)
        
        # === ABA 4: NOTIFICAÇÕES ===
        tab_notif = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab_notif, text="📱 Notificações")
        self._create_notifications_tab(tab_notif)
        
        # === ABA 5: HISTÓRICO ===
        tab_historico = tk.Frame(notebook, bg=self.colors["bg"])
        notebook.add(tab_historico, text="📊 Histórico")
        self._create_history_tab(tab_historico)
        
        # Status e Botões
        self.settings_status = tk.Label(
            config_window,
            text="",
            font=self.font_small,
            fg=self.colors["dim"],
            bg=self.colors["bg"]
        )
        self.settings_status.pack(pady=5)
        
        btn_frame = tk.Frame(config_window, bg=self.colors["bg"])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        cancel_btn = tk.Button(
            btn_frame,
            text="Cancelar",
            font=self.font_small,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            relief="flat",
            padx=20,
            pady=8,
            command=config_window.destroy
        )
        cancel_btn.pack(side=tk.LEFT)
        
        apply_btn = tk.Button(
            btn_frame,
            text="💾 Salvar Configurações",
            font=self.font_small,
            bg=self.colors["cpu"],
            fg="#000000",
            relief="flat",
            padx=20,
            pady=8,
            command=lambda: self._save_all_settings(config_window)
        )
        apply_btn.pack(side=tk.RIGHT)
        
        # Guardar referência da janela
        self.config_window = config_window
        
        # Binds
        config_window.bind('<Escape>', lambda e: config_window.destroy())
    
    def _create_connection_tab(self, parent):
        """Cria aba de configurações de conexão."""
        frame = tk.Frame(parent, bg=self.colors["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Modo de conexão
        mode_label = tk.Label(frame, text="Modo de Conexão:", font=self.font_small,
                             fg=self.colors["text"], bg=self.colors["bg"])
        mode_label.pack(anchor="w", pady=(0, 5))
        
        self.settings_mode_var = tk.StringVar(value="manual" if self.sender_ip else "auto")
        
        auto_radio = tk.Radiobutton(frame, text="🔍 Automático (Broadcast UDP - Auto-discovery)",
                                    variable=self.settings_mode_var, value="auto",
                                    font=self.font_small, fg=self.colors["text"], bg=self.colors["bg"],
                                    selectcolor=self.colors["panel"])
        auto_radio.pack(anchor="w", padx=10)
        
        manual_radio = tk.Radiobutton(frame, text="📍 Manual (Inserir IP específico)",
                                      variable=self.settings_mode_var, value="manual",
                                      font=self.font_small, fg=self.colors["text"], bg=self.colors["bg"],
                                      selectcolor=self.colors["panel"])
        manual_radio.pack(anchor="w", padx=10)
        
        # IP do Sender
        ip_label = tk.Label(frame, text="IP do Sender (PC):", font=self.font_small,
                           fg=self.colors["text"], bg=self.colors["bg"])
        ip_label.pack(anchor="w", pady=(15, 5))
        
        self.settings_ip_entry = tk.Entry(frame, font=self.font_value, bg=self.colors["panel"],
                                         fg=self.colors["text"], insertbackground=self.colors["text"],
                                         relief="flat", width=25)
        self.settings_ip_entry.pack(anchor="w", pady=2, ipady=5)
        self.settings_ip_entry.insert(0, self.sender_ip or "192.168.1.100")
        
        # Porta
        port_label = tk.Label(frame, text="Porta UDP:", font=self.font_small,
                             fg=self.colors["text"], bg=self.colors["bg"])
        port_label.pack(anchor="w", pady=(15, 5))
        
        self.settings_port_entry = tk.Entry(frame, font=self.font_value, bg=self.colors["panel"],
                                           fg=self.colors["text"], insertbackground=self.colors["text"],
                                           relief="flat", width=10)
        self.settings_port_entry.pack(anchor="w", pady=2, ipady=5)
        self.settings_port_entry.insert(0, str(self.porta))
        
        # Velocidade esperada do link
        speed_label = tk.Label(frame, text="Velocidade esperada do cabo (Mbps):", font=self.font_small,
                              fg=self.colors["text"], bg=self.colors["bg"])
        speed_label.pack(anchor="w", pady=(15, 5))
        
        speed_frame = tk.Frame(frame, bg=self.colors["bg"])
        speed_frame.pack(anchor="w")
        
        self.settings_speed_var = tk.StringVar(value=str(CONFIG.get("expected_link_speed_mbps", 1000)))
        
        speeds = [("CAT5 (100)", "100"), ("CAT5e/6 (1000)", "1000"), ("CAT6a/7 (10000)", "10000")]
        for text, val in speeds:
            rb = tk.Radiobutton(speed_frame, text=text, variable=self.settings_speed_var, value=val,
                               font=self.font_small, fg=self.colors["text"], bg=self.colors["bg"],
                               selectcolor=self.colors["panel"])
            rb.pack(side=tk.LEFT, padx=5)
        
        # Dica
        tip_label = tk.Label(frame, text="💡 Dica: No PC, execute 'ipconfig' para ver o IP local",
                            font=self.font_help, fg=self.colors["dim"], bg=self.colors["bg"])
        tip_label.pack(anchor="w", pady=(20, 0))
    
    def _create_appearance_tab(self, parent):
        """Cria aba de configurações de aparência."""
        frame = tk.Frame(parent, bg=self.colors["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Tema
        theme_label = tk.Label(frame, text="Tema:", font=self.font_small,
                              fg=self.colors["text"], bg=self.colors["bg"])
        theme_label.pack(anchor="w", pady=(0, 5))
        
        theme_names = ["dark", "light", "high_contrast", "cyberpunk"]
        self.settings_theme_var = tk.StringVar(value=CONFIG.get("tema", "dark"))
        
        theme_frame = tk.Frame(frame, bg=self.colors["bg"])
        theme_frame.pack(anchor="w", pady=5)
        
        for theme_name in theme_names:
            display = {"dark": "🌙 Escuro", "light": "☀️ Claro", 
                      "high_contrast": "⚫ Alto Contraste", "cyberpunk": "💜 Cyberpunk"}
            rb = tk.Radiobutton(theme_frame, text=display.get(theme_name, theme_name),
                               variable=self.settings_theme_var, value=theme_name,
                               font=self.font_small, fg=self.colors["text"], bg=self.colors["bg"],
                               selectcolor=self.colors["panel"])
            rb.pack(anchor="w", padx=10)
        
        # Cores customizadas por setor
        colors_label = tk.Label(frame, text="Cores Customizadas (deixe vazio para usar tema):",
                               font=self.font_small, fg=self.colors["text"], bg=self.colors["bg"])
        colors_label.pack(anchor="w", pady=(20, 5))
        
        cores_config = CONFIG.get("cores_customizadas", {})
        self.settings_colors = {}
        
        colors_frame = tk.Frame(frame, bg=self.colors["bg"])
        colors_frame.pack(anchor="w", fill=tk.X)
        
        setores = [("cpu", "CPU"), ("gpu", "GPU"), ("ram", "RAM"), 
                   ("storage", "Storage"), ("network", "Network"), ("mobo", "Mobo")]
        
        for i, (key, label) in enumerate(setores):
            row = tk.Frame(colors_frame, bg=self.colors["bg"])
            row.pack(fill=tk.X, pady=2)
            
            lbl = tk.Label(row, text=f"{label}:", font=self.font_small,
                          fg=self.colors["dim"], bg=self.colors["bg"], width=10, anchor="w")
            lbl.pack(side=tk.LEFT)
            
            entry = tk.Entry(row, font=self.font_small, bg=self.colors["panel"],
                           fg=self.colors["text"], insertbackground=self.colors["text"],
                           relief="flat", width=12)
            entry.pack(side=tk.LEFT, padx=5)
            entry.insert(0, cores_config.get(key, ""))
            self.settings_colors[key] = entry
            
            # Preview de cor
            preview = tk.Label(row, text="  ██  ", font=self.font_small,
                              fg=self.colors.get(key, "#ffffff"), bg=self.colors["bg"])
            preview.pack(side=tk.LEFT, padx=5)
        
        tip_label = tk.Label(frame, text="💡 Use códigos hex como #00ff00 ou #ff6600",
                            font=self.font_help, fg=self.colors["dim"], bg=self.colors["bg"])
        tip_label.pack(anchor="w", pady=(10, 0))
    
    def _create_alerts_tab(self, parent):
        """Cria aba de configurações de alertas/thresholds."""
        # Canvas com scroll para muitas opções
        canvas = tk.Canvas(parent, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors["bg"])
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        alertas_config = CONFIG.get("alertas", {})
        self.settings_alerts = {}
        
        # CPU
        self._create_threshold_group(scroll_frame, "🔥 CPU", [
            ("cpu_temp_warning", "Temp Aviso (°C)", alertas_config.get("cpu_temp_warning", 70)),
            ("cpu_temp_critical", "Temp Crítico (°C)", alertas_config.get("cpu_temp_critical", 85)),
            ("cpu_uso_warning", "Uso Aviso (%)", alertas_config.get("cpu_uso_warning", 70)),
            ("cpu_uso_critical", "Uso Crítico (%)", alertas_config.get("cpu_uso_critical", 90)),
        ])
        
        # GPU
        self._create_threshold_group(scroll_frame, "🎮 GPU", [
            ("gpu_temp_warning", "Temp Aviso (°C)", alertas_config.get("gpu_temp_warning", 75)),
            ("gpu_temp_critical", "Temp Crítico (°C)", alertas_config.get("gpu_temp_critical", 90)),
            ("gpu_uso_warning", "Uso Aviso (%)", alertas_config.get("gpu_uso_warning", 80)),
            ("gpu_uso_critical", "Uso Crítico (%)", alertas_config.get("gpu_uso_critical", 95)),
        ])
        
        # RAM
        self._create_threshold_group(scroll_frame, "💾 RAM", [
            ("ram_warning", "Uso Aviso (%)", alertas_config.get("ram_warning", 70)),
            ("ram_critical", "Uso Crítico (%)", alertas_config.get("ram_critical", 90)),
        ])
        
        # Storage
        self._create_threshold_group(scroll_frame, "💿 Storage", [
            ("storage_temp_warning", "Temp Aviso (°C)", alertas_config.get("storage_temp_warning", 45)),
            ("storage_temp_critical", "Temp Crítico (°C)", alertas_config.get("storage_temp_critical", 55)),
            ("storage_uso_warning", "Uso Aviso (%)", alertas_config.get("storage_uso_warning", 80)),
            ("storage_uso_critical", "Uso Crítico (%)", alertas_config.get("storage_uso_critical", 95)),
        ])
        
        # Network
        self._create_threshold_group(scroll_frame, "🌐 Network", [
            ("ping_warning", "Ping Aviso (ms)", alertas_config.get("ping_warning", 50)),
            ("ping_critical", "Ping Crítico (ms)", alertas_config.get("ping_critical", 100)),
        ])
        
        # Sons
        sons_config = CONFIG.get("sons", {})
        sons_frame = tk.LabelFrame(scroll_frame, text="🔊 Sons de Alerta", font=self.font_small,
                                   fg=self.colors["title"], bg=self.colors["bg"], bd=1)
        sons_frame.pack(fill=tk.X, pady=10)
        
        self.settings_sounds_enabled = tk.BooleanVar(value=sons_config.get("enabled", True))
        sound_check = tk.Checkbutton(sons_frame, text="Ativar sons de alerta",
                                     variable=self.settings_sounds_enabled,
                                     font=self.font_small, fg=self.colors["text"], bg=self.colors["bg"],
                                     selectcolor=self.colors["panel"])
        sound_check.pack(anchor="w", padx=10, pady=5)
        
        cooldown_frame = tk.Frame(sons_frame, bg=self.colors["bg"])
        cooldown_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(cooldown_frame, text="Cooldown (segundos):", font=self.font_small,
                fg=self.colors["dim"], bg=self.colors["bg"]).pack(side=tk.LEFT)
        
        self.settings_sound_cooldown = tk.Entry(cooldown_frame, font=self.font_small,
                                                bg=self.colors["panel"], fg=self.colors["text"],
                                                width=8, relief="flat")
        self.settings_sound_cooldown.pack(side=tk.LEFT, padx=5)
        self.settings_sound_cooldown.insert(0, str(sons_config.get("cooldown_seconds", 10)))
    
    def _create_threshold_group(self, parent, title, fields):
        """Cria um grupo de thresholds."""
        frame = tk.LabelFrame(parent, text=title, font=self.font_small,
                             fg=self.colors["title"], bg=self.colors["bg"], bd=1)
        frame.pack(fill=tk.X, pady=5)
        
        for key, label, default in fields:
            row = tk.Frame(frame, bg=self.colors["bg"])
            row.pack(fill=tk.X, padx=10, pady=2)
            
            lbl = tk.Label(row, text=f"{label}:", font=self.font_small,
                          fg=self.colors["dim"], bg=self.colors["bg"], width=20, anchor="w")
            lbl.pack(side=tk.LEFT)
            
            entry = tk.Entry(row, font=self.font_small, bg=self.colors["panel"],
                           fg=self.colors["text"], width=8, relief="flat")
            entry.pack(side=tk.LEFT, padx=5)
            entry.insert(0, str(default))
            self.settings_alerts[key] = entry
    
    def _create_notifications_tab(self, parent):
        """Cria aba de configurações de notificações/webhooks."""
        frame = tk.Frame(parent, bg=self.colors["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        webhooks_config = CONFIG.get("webhooks", {})
        
        # Enable webhooks
        self.settings_webhooks_enabled = tk.BooleanVar(value=webhooks_config.get("enabled", False))
        enable_check = tk.Checkbutton(frame, text="🔔 Ativar notificações via webhook",
                                      variable=self.settings_webhooks_enabled,
                                      font=self.font_section, fg=self.colors["text"], bg=self.colors["bg"],
                                      selectcolor=self.colors["panel"])
        enable_check.pack(anchor="w", pady=(0, 15))
        
        # Telegram
        tg_frame = tk.LabelFrame(frame, text="📱 Telegram", font=self.font_small,
                                fg=self.colors["title"], bg=self.colors["bg"], bd=1)
        tg_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(tg_frame, text="Bot Token:", font=self.font_small,
                fg=self.colors["dim"], bg=self.colors["bg"]).pack(anchor="w", padx=10, pady=(5, 0))
        self.settings_tg_token = tk.Entry(tg_frame, font=self.font_small, bg=self.colors["panel"],
                                         fg=self.colors["text"], width=45, relief="flat")
        self.settings_tg_token.pack(anchor="w", padx=10, pady=2)
        self.settings_tg_token.insert(0, webhooks_config.get("telegram_bot_token", ""))
        
        tk.Label(tg_frame, text="Chat ID:", font=self.font_small,
                fg=self.colors["dim"], bg=self.colors["bg"]).pack(anchor="w", padx=10, pady=(5, 0))
        self.settings_tg_chat = tk.Entry(tg_frame, font=self.font_small, bg=self.colors["panel"],
                                        fg=self.colors["text"], width=20, relief="flat")
        self.settings_tg_chat.pack(anchor="w", padx=10, pady=(2, 10))
        self.settings_tg_chat.insert(0, webhooks_config.get("telegram_chat_id", ""))
        
        # Discord
        dc_frame = tk.LabelFrame(frame, text="🎮 Discord", font=self.font_small,
                                fg=self.colors["title"], bg=self.colors["bg"], bd=1)
        dc_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(dc_frame, text="Webhook URL:", font=self.font_small,
                fg=self.colors["dim"], bg=self.colors["bg"]).pack(anchor="w", padx=10, pady=(5, 0))
        self.settings_dc_webhook = tk.Entry(dc_frame, font=self.font_small, bg=self.colors["panel"],
                                           fg=self.colors["text"], width=55, relief="flat")
        self.settings_dc_webhook.pack(anchor="w", padx=10, pady=(2, 10))
        self.settings_dc_webhook.insert(0, webhooks_config.get("discord_webhook_url", ""))
        
        # ntfy.sh
        ntfy_frame = tk.LabelFrame(frame, text="📲 ntfy.sh (Push gratuito)", font=self.font_small,
                                  fg=self.colors["title"], bg=self.colors["bg"], bd=1)
        ntfy_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(ntfy_frame, text="Topic (ex: meu-pc-telemetria):", font=self.font_small,
                fg=self.colors["dim"], bg=self.colors["bg"]).pack(anchor="w", padx=10, pady=(5, 0))
        self.settings_ntfy_topic = tk.Entry(ntfy_frame, font=self.font_small, bg=self.colors["panel"],
                                           fg=self.colors["text"], width=30, relief="flat")
        self.settings_ntfy_topic.pack(anchor="w", padx=10, pady=(2, 10))
        self.settings_ntfy_topic.insert(0, webhooks_config.get("ntfy_topic", ""))
        
        # Cooldown
        cooldown_frame = tk.Frame(frame, bg=self.colors["bg"])
        cooldown_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(cooldown_frame, text="Cooldown entre notificações (segundos):", font=self.font_small,
                fg=self.colors["dim"], bg=self.colors["bg"]).pack(side=tk.LEFT)
        
        self.settings_webhook_cooldown = tk.Entry(cooldown_frame, font=self.font_small,
                                                  bg=self.colors["panel"], fg=self.colors["text"],
                                                  width=8, relief="flat")
        self.settings_webhook_cooldown.pack(side=tk.LEFT, padx=5)
        self.settings_webhook_cooldown.insert(0, str(webhooks_config.get("cooldown_seconds", 300)))
        
        # Dica
        tip_label = tk.Label(frame, 
                            text="💡 ntfy.sh: Instale o app no celular e assine seu topic",
                            font=self.font_help, fg=self.colors["dim"], bg=self.colors["bg"])
        tip_label.pack(anchor="w", pady=(10, 0))
    
    def _create_history_tab(self, parent):
        """Cria aba de configurações de histórico."""
        frame = tk.Frame(parent, bg=self.colors["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        historico_config = CONFIG.get("historico", {})
        
        # CSV
        csv_frame = tk.LabelFrame(frame, text="📄 Log CSV", font=self.font_small,
                                 fg=self.colors["title"], bg=self.colors["bg"], bd=1)
        csv_frame.pack(fill=tk.X, pady=10)
        
        self.settings_auto_log = tk.BooleanVar(value=historico_config.get("auto_start_log", False))
        auto_check = tk.Checkbutton(csv_frame, text="Iniciar log automaticamente ao conectar",
                                    variable=self.settings_auto_log,
                                    font=self.font_small, fg=self.colors["text"], bg=self.colors["bg"],
                                    selectcolor=self.colors["panel"])
        auto_check.pack(anchor="w", padx=10, pady=5)
        
        ret_frame = tk.Frame(csv_frame, bg=self.colors["bg"])
        ret_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(ret_frame, text="Retenção (dias):", font=self.font_small,
                fg=self.colors["dim"], bg=self.colors["bg"]).pack(side=tk.LEFT)
        
        self.settings_retention = tk.Entry(ret_frame, font=self.font_small,
                                          bg=self.colors["panel"], fg=self.colors["text"],
                                          width=8, relief="flat")
        self.settings_retention.pack(side=tk.LEFT, padx=5)
        self.settings_retention.insert(0, str(historico_config.get("retention_days", 7)))
        
        # Info sobre log atual
        log_info = tk.Label(csv_frame, 
                           text=f"📁 Pasta de logs: {self.log_dir}",
                           font=self.font_help, fg=self.colors["dim"], bg=self.colors["bg"])
        log_info.pack(anchor="w", padx=10, pady=5)
        
        status_text = "📝 Log ativo" if self.logging_enabled else "⏸️ Log desativado"
        log_status = tk.Label(csv_frame, text=status_text,
                             font=self.font_small, 
                             fg=self.colors["gpu"] if self.logging_enabled else self.colors["dim"],
                             bg=self.colors["bg"])
        log_status.pack(anchor="w", padx=10, pady=5)
        
        # Atalho
        tip_label = tk.Label(frame, 
                            text="💡 Use a tecla [L] para ativar/desativar o log manualmente",
                            font=self.font_help, fg=self.colors["dim"], bg=self.colors["bg"])
        tip_label.pack(anchor="w", pady=(20, 0))
    
    def _save_all_settings(self, window):
        """Salva todas as configurações."""
        try:
            # === CONEXÃO ===
            mode = self.settings_mode_var.get()
            ip = self.settings_ip_entry.get().strip()
            port_str = self.settings_port_entry.get().strip()
            speed = self.settings_speed_var.get()
            
            # Validar porta
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError
            except:
                self.settings_status.config(text="❌ Porta inválida!", fg=self.colors["critical"])
                return
            
            # Validar IP se modo manual
            if mode == "manual":
                parts = ip.split(".")
                if len(parts) != 4:
                    self.settings_status.config(text="❌ IP inválido!", fg=self.colors["critical"])
                    return
                try:
                    for part in parts:
                        n = int(part)
                        if n < 0 or n > 255:
                            raise ValueError
                except:
                    self.settings_status.config(text="❌ IP inválido!", fg=self.colors["critical"])
                    return
            
            # === ALERTAS ===
            alertas = {}
            for key, entry in self.settings_alerts.items():
                try:
                    alertas[key] = int(entry.get())
                except:
                    alertas[key] = 0
            
            # === SONS ===
            try:
                sound_cooldown = int(self.settings_sound_cooldown.get())
            except:
                sound_cooldown = 10
            
            # === WEBHOOKS ===
            try:
                webhook_cooldown = int(self.settings_webhook_cooldown.get())
            except:
                webhook_cooldown = 300
            
            # === HISTÓRICO ===
            try:
                retention = int(self.settings_retention.get())
            except:
                retention = 7
            
            # === CORES CUSTOMIZADAS ===
            cores = {}
            for key, entry in self.settings_colors.items():
                cores[key] = entry.get().strip()
            
            # Montar config completa
            new_config = {
                "porta": port,
                "sender_ip": ip if mode == "manual" else "",
                "modo": mode,
                "expected_link_speed_mbps": int(speed),
                "tema": self.settings_theme_var.get(),
                "cores_customizadas": cores,
                "alertas": alertas,
                "sons": {
                    "enabled": self.settings_sounds_enabled.get(),
                    "cooldown_seconds": sound_cooldown,
                    "warning_sound": "warning",
                    "critical_sound": "beep_urgent"
                },
                "webhooks": {
                    "enabled": self.settings_webhooks_enabled.get(),
                    "telegram_bot_token": self.settings_tg_token.get().strip(),
                    "telegram_chat_id": self.settings_tg_chat.get().strip(),
                    "discord_webhook_url": self.settings_dc_webhook.get().strip(),
                    "ntfy_topic": self.settings_ntfy_topic.get().strip(),
                    "ntfy_server": "https://ntfy.sh",
                    "cooldown_seconds": webhook_cooldown
                },
                "historico": {
                    "csv_enabled": self.logging_enabled,
                    "auto_start_log": self.settings_auto_log.get(),
                    "retention_days": retention
                }
            }
            
            # Atualizar CONFIG global
            global CONFIG
            CONFIG.update(new_config)
            
            # Salvar em arquivo
            if salvar_config(new_config):
                # Aplicar mudanças
                self.sender_ip = new_config["sender_ip"]
                self.connection_mode = mode
                self.porta = port
                
                # Aplicar tema
                self._apply_new_theme(new_config["tema"], new_config["cores_customizadas"])
                
                # Sinalizar reinício do receiver se porta/IP mudou
                self.restart_receiver = True
                
                self.settings_status.config(text="✅ Configurações salvas!", fg=self.colors["gpu"])
                window.after(1500, window.destroy)
            else:
                self.settings_status.config(text="❌ Erro ao salvar!", fg=self.colors["critical"])
        
        except Exception as e:
            self.settings_status.config(text=f"❌ Erro: {str(e)[:30]}", fg=self.colors["critical"])
            print(f"[Config] Erro ao salvar: {e}")
    
    def _apply_new_theme(self, theme_name, custom_colors):
        """Aplica novo tema e cores customizadas."""
        if HAS_THEME_MODULE:
            from ui.themes import get_theme
            theme = get_theme(theme_name)
            new_colors = theme.to_dict()
        else:
            # Fallback para temas inline
            new_colors = self.themes.get(theme_name, self.themes["dark"]).copy()
        
        # Aplicar cores customizadas
        for key, color in custom_colors.items():
            if color and color.startswith("#"):
                new_colors[key] = color
        
        self.colors = new_colors
        self.dark_theme = theme_name in ["dark", "cyberpunk", "high_contrast"]
        self._apply_theme()
    
    def _toggle_logging(self, event=None):
        """Ativa/desativa log CSV."""
        self.logging_enabled = not self.logging_enabled
        
        if self.logging_enabled:
            try:
                os.makedirs(self.log_dir, exist_ok=True)
                filename = f"telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = os.path.join(self.log_dir, filename)
                self.log_file = open(filepath, 'w', encoding='utf-8')
                self.log_file.write("timestamp,cpu_usage,cpu_temp,gpu_load,gpu_temp,ram_percent,ping_ms\n")
                print(f"[Log] Iniciado: {filepath}")
            except Exception as e:
                print(f"[Log] Erro ao criar arquivo: {e}")
                self.logging_enabled = False
        else:
            if self.log_file:
                self.log_file.close()
                self.log_file = None
                print("[Log] Encerrado")
    
    def _quit_app(self, event=None):
        """Encerra a aplicação."""
        if self.log_file:
            self.log_file.close()
        self.root.quit()
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Inicia o loop principal."""
        self.root.mainloop()


def main():
    """Função principal do Receiver"""
    print("=" * 50)
    print("   CENTRAL DE TELEMETRIA - RECEIVER")
    print("=" * 50)
    print(f"Porta UDP: {PORTA}")
    sender_ip = CONFIG.get("sender_ip", "")
    if sender_ip:
        print(f"Modo: Manual - IP do Sender: {sender_ip}")
    else:
        print("Modo: Automático (broadcast UDP)")
    print("Atalhos: [F]ullscreen [G]ráficos [T]ema [L]og [S]ettings [Q]uit")
    print("=" * 50)
    print()
    
    app = TelemetryDashboard()
    app.run()


if __name__ == "__main__":
    main()
