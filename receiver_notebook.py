"""
Central de Telemetria - Receiver (Notebook)
============================================
Modo padrão: Exibição numérica (menos poluído)
Tecla 'G': Alterna para modo gráfico
Tecla 'F': Alterna fullscreen
Tecla 'Q' ou ESC: Sair
"""

import socket
import json
import sys
import tkinter as tk
from tkinter import font as tkfont
from collections import deque
import threading
import time

# ========== CONFIGURAÇÕES ==========
HOST = "0.0.0.0"
PORTA = 5005
HISTORY_SIZE = 60
# ===================================

# Dados mais recentes
current_data = {}
data_lock = threading.Lock()

# Histórico para gráficos
history = {
    "cpu_usage": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "cpu_temp": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "gpu_load": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "gpu_temp": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "ram": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "net_down": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "net_up": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
    "ping": deque([0]*HISTORY_SIZE, maxlen=HISTORY_SIZE),
}


def receiver_thread():
    """Thread que recebe dados UDP em background."""
    global current_data
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORTA))
    sock.settimeout(1.0)
    
    print(f"[Receiver] Ouvindo em {HOST}:{PORTA}...")
    
    while True:
        try:
            data, addr = sock.recvfrom(8192)
            payload = json.loads(data.decode())
            
            with data_lock:
                current_data = payload
                
                # Atualiza históricos
                history["cpu_usage"].append(payload.get("cpu", {}).get("usage", 0))
                history["cpu_temp"].append(payload.get("cpu", {}).get("temp", 0))
                history["gpu_load"].append(payload.get("gpu", {}).get("load", 0))
                history["gpu_temp"].append(payload.get("gpu", {}).get("temp", 0))
                history["ram"].append(payload.get("ram", {}).get("percent", 0))
                history["net_down"].append(payload.get("network", {}).get("down_kbps", 0))
                history["net_up"].append(payload.get("network", {}).get("up_kbps", 0))
                history["ping"].append(payload.get("network", {}).get("ping_ms", 0))
                
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[Receiver] Erro: {e}")


class TelemetryDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Central de Telemetria")
        self.root.configure(bg='#0a0a0a')
        self.root.geometry("1366x700")
        self.root.minsize(1200, 600)
        
        self.is_fullscreen = False
        self.show_graphs = False
        
        # Fontes (reduzidas para 1366x768)
        self.font_title = tkfont.Font(family="Consolas", size=16, weight="bold")
        self.font_section = tkfont.Font(family="Consolas", size=10, weight="bold")
        self.font_value = tkfont.Font(family="Consolas", size=12)
        self.font_small = tkfont.Font(family="Consolas", size=9)
        self.font_help = tkfont.Font(family="Consolas", size=8)
        
        # Cores
        self.colors = {
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
        }
        
        # Container principal com scroll
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
        self.title_label.pack(pady=(0, 10))
        
        # Status de conexão
        self.status_label = tk.Label(
            self.main_frame,
            text="Aguardando dados...",
            font=self.font_small,
            fg=self.colors["dim"],
            bg=self.colors["bg"]
        )
        self.status_label.pack()
        
        # Container para painéis
        self.panels_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        self.panels_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Cria painéis
        self.create_panels()
        
        # Canvas para gráficos (oculto por padrão)
        self.graph_canvas = tk.Canvas(
            self.main_frame,
            bg=self.colors["panel"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            height=150  # Altura reduzida para 1366x768
        )
        
        # Help bar
        self.help_label = tk.Label(
            self.main_frame,
            text="[F] Fullscreen  |  [G] Gráficos  |  [Q/ESC] Sair",
            font=self.font_help,
            fg=self.colors["dim"],
            bg=self.colors["bg"]
        )
        self.help_label.pack(side=tk.BOTTOM, pady=2)
        
        # Binds de teclado
        self.root.bind('<F>', self.toggle_fullscreen)
        self.root.bind('<f>', self.toggle_fullscreen)
        self.root.bind('<G>', self.toggle_graphs)
        self.root.bind('<g>', self.toggle_graphs)
        self.root.bind('<q>', self.quit_app)
        self.root.bind('<Q>', self.quit_app)
        self.root.bind('<Escape>', self.quit_app)
        self.root.bind('<F11>', self.toggle_fullscreen)
        
        # Inicia thread de recebimento
        self.recv_thread = threading.Thread(target=receiver_thread, daemon=True)
        self.recv_thread.start()
        
        # Inicia loop de atualização da UI
        self.update_ui()
        
    def create_panels(self):
        """Cria os painéis de exibição."""
        # Row 1: CPU | GPU | RAM
        row1 = tk.Frame(self.panels_frame, bg=self.colors["bg"])
        row1.pack(fill=tk.X, pady=5)
        
        self.cpu_panel = self.create_panel(row1, "CPU", self.colors["cpu"])
        self.gpu_panel = self.create_panel(row1, "GPU", self.colors["gpu"])
        self.ram_panel = self.create_panel(row1, "RAM", self.colors["ram"])
        
        # Row 2: MOBO | STORAGE | NETWORK
        row2 = tk.Frame(self.panels_frame, bg=self.colors["bg"])
        row2.pack(fill=tk.X, pady=5)
        
        self.mobo_panel = self.create_panel(row2, "MOBO", self.colors["mobo"])
        self.storage_panel = self.create_panel(row2, "STORAGE", self.colors["storage"])
        self.network_panel = self.create_panel(row2, "NETWORK", self.colors["network"])
        
    def create_panel(self, parent, title, color):
        """Cria um painel individual."""
        frame = tk.Frame(
            parent,
            bg=self.colors["panel"],
            highlightthickness=2,
            highlightbackground=color
        )
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        
        # Título do painel
        title_lbl = tk.Label(
            frame,
            text=f"── {title} ──",
            font=self.font_section,
            fg=color,
            bg=self.colors["panel"]
        )
        title_lbl.pack(pady=(5, 3))
        
        # Container para valores
        values_frame = tk.Frame(frame, bg=self.colors["panel"])
        values_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        
        return {"frame": frame, "values": values_frame, "labels": {}}
    
    def update_panel_value(self, panel, key, label, value, unit="", warn_threshold=None, crit_threshold=None):
        """Atualiza ou cria um valor em um painel."""
        if key not in panel["labels"]:
            # Cria linha
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
                width=12  # Largura fixa para evitar movimento
            )
            lbl_value.pack(side=tk.RIGHT)
            
            panel["labels"][key] = lbl_value
        
        # Atualiza valor
        lbl = panel["labels"][key]
        
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
        elif warn_threshold and isinstance(value, (int, float)) and value >= warn_threshold:
            lbl.config(fg=self.colors["warning"])
        else:
            lbl.config(fg=self.colors["text"])
    
    def update_ui(self):
        """Atualiza a interface com os dados mais recentes."""
        with data_lock:
            data = current_data.copy() if current_data else None
        
        if data:
            self.status_label.config(
                text=f"● Conectado | Última atualização: {time.strftime('%H:%M:%S')}",
                fg=self.colors["gpu"]
            )
            
            # CPU
            cpu = data.get("cpu", {})
            self.update_panel_value(self.cpu_panel, "usage", "Uso", cpu.get("usage", 0), "%", 70, 90)
            self.update_panel_value(self.cpu_panel, "temp", "Temp", cpu.get("temp", 0), "°C", 70, 85)
            self.update_panel_value(self.cpu_panel, "voltage", "Voltagem", cpu.get("voltage", 0), "V")
            self.update_panel_value(self.cpu_panel, "power", "Consumo", cpu.get("power", 0), "W")
            self.update_panel_value(self.cpu_panel, "clock", "Clock", cpu.get("clock", 0), " MHz")
            
            # GPU
            gpu = data.get("gpu", {})
            self.update_panel_value(self.gpu_panel, "load", "Uso", gpu.get("load", 0), "%", 80, 95)
            self.update_panel_value(self.gpu_panel, "temp", "Temp", gpu.get("temp", 0), "°C", 75, 90)
            self.update_panel_value(self.gpu_panel, "voltage", "Voltagem", gpu.get("voltage", 0), "V")
            self.update_panel_value(self.gpu_panel, "clock_core", "Core", gpu.get("clock_core", 0), " MHz")
            self.update_panel_value(self.gpu_panel, "clock_mem", "Mem Clk", gpu.get("clock_mem", 0), " MHz")
            self.update_panel_value(self.gpu_panel, "mem_used", "VRAM", gpu.get("mem_used_mb", 0), " MB")
            self.update_panel_value(self.gpu_panel, "fan", "Fan", gpu.get("fan", 0), " RPM")
            
            # RAM
            ram = data.get("ram", {})
            self.update_panel_value(self.ram_panel, "percent", "Uso", ram.get("percent", 0), "%", 70, 90)
            self.update_panel_value(self.ram_panel, "used", "Usado", ram.get("used_gb", 0), " GB")
            self.update_panel_value(self.ram_panel, "total", "Total", ram.get("total_gb", 0), " GB")
            
            # MOBO
            mobo = data.get("mobo", {})
            self.update_panel_value(self.mobo_panel, "temp", "Temp", mobo.get("temp", 0), "°C", 50, 70)
            
            # Fans da MOBO
            fans = data.get("fans", [])
            for i, fan in enumerate(fans[:4]):  # Max 4 fans
                name = fan.get("name", f"Fan {i}")[:10]
                rpm = fan.get("rpm", 0)
                self.update_panel_value(self.mobo_panel, f"fan{i}", name, rpm, " RPM")
            
            # STORAGE
            storage = data.get("storage", [])
            # Limpa labels antigos de storage
            for key in list(self.storage_panel["labels"].keys()):
                if key.startswith("disk"):
                    self.storage_panel["labels"][key].master.destroy()
                    del self.storage_panel["labels"][key]
            
            for i, disk in enumerate(storage[:2]):  # Max 2 discos para caber mais info
                name = disk.get("name", f"Disk {i}")[:15]
                temp = disk.get("temp", 0)
                health = disk.get("health", 100)
                used_space = disk.get("used_space", 0)
                activity = disk.get("total_activity", 0)
                
                # Nome do disco como cabeçalho
                self.update_panel_value(self.storage_panel, f"disk{i}_name", f"Disco {i+1}", name, "")
                self.update_panel_value(self.storage_panel, f"disk{i}_temp", "  Temp", temp, "°C", 45, 55)
                self.update_panel_value(self.storage_panel, f"disk{i}_health", "  Saúde", health, "%")
                self.update_panel_value(self.storage_panel, f"disk{i}_used", "  Usado", used_space, "%", 80, 95)
            
            if not storage:
                self.update_panel_value(self.storage_panel, "disk_na", "Status", "N/A", "")
            
            # NETWORK
            net = data.get("network", {})
            self.update_panel_value(self.network_panel, "down", "Download", net.get("down_kbps", 0), " KB/s")
            self.update_panel_value(self.network_panel, "up", "Upload", net.get("up_kbps", 0), " KB/s")
            self.update_panel_value(self.network_panel, "ping", "Ping", net.get("ping_ms", 0), " ms", 50, 100)
            
            # Gráficos (se ativados)
            if self.show_graphs:
                self.draw_graphs()
        else:
            self.status_label.config(
                text="○ Aguardando dados...",
                fg=self.colors["warning"]
            )
        
        # Agenda próxima atualização
        self.root.after(500, self.update_ui)
    
    def draw_graphs(self):
        """Desenha gráficos simples no canvas."""
        self.graph_canvas.delete("all")
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        
        if w < 100 or h < 50:
            return
        
        padding = 20
        graph_w = w - 2 * padding
        graph_h = h - 2 * padding
        
        # Desenha CPU Usage
        self.draw_line_graph(
            list(history["cpu_usage"]),
            padding, padding,
            graph_w // 2, graph_h // 2,
            self.colors["cpu"],
            "CPU %",
            100
        )
        
        # Desenha GPU Load
        self.draw_line_graph(
            list(history["gpu_load"]),
            padding + graph_w // 2, padding,
            graph_w // 2, graph_h // 2,
            self.colors["gpu"],
            "GPU %",
            100
        )
        
        # Desenha Temps
        self.draw_line_graph(
            list(history["cpu_temp"]),
            padding, padding + graph_h // 2,
            graph_w // 2, graph_h // 2,
            "#ff8800",
            "CPU Temp",
            100
        )
        
        # Desenha Ping
        self.draw_line_graph(
            list(history["ping"]),
            padding + graph_w // 2, padding + graph_h // 2,
            graph_w // 2, graph_h // 2,
            self.colors["network"],
            "Ping ms",
            max(max(history["ping"]) * 1.2, 50)
        )
    
    def draw_line_graph(self, data, x, y, w, h, color, label, max_val):
        """Desenha um gráfico de linha simples."""
        if not data or w < 10 or h < 10:
            return
        
        # Label
        self.graph_canvas.create_text(
            x + 5, y + 5,
            text=label,
            fill=color,
            anchor="nw",
            font=self.font_small
        )
        
        # Borda
        self.graph_canvas.create_rectangle(
            x, y, x + w, y + h,
            outline=self.colors["border"]
        )
        
        # Linha do gráfico
        if len(data) < 2:
            return
        
        points = []
        step_x = w / (len(data) - 1)
        for i, val in enumerate(data):
            px = x + i * step_x
            py = y + h - (val / max_val) * (h - 10)
            points.extend([px, py])
        
        if len(points) >= 4:
            self.graph_canvas.create_line(points, fill=color, width=2, smooth=True)
    
    def toggle_fullscreen(self, event=None):
        """Alterna modo fullscreen."""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        
    def toggle_graphs(self, event=None):
        """Alterna exibição de gráficos."""
        self.show_graphs = not self.show_graphs
        if self.show_graphs:
            self.graph_canvas.pack(fill=tk.X, pady=10, before=self.help_label)
        else:
            self.graph_canvas.pack_forget()
    
    def quit_app(self, event=None):
        """Encerra a aplicação."""
        self.root.quit()
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Inicia o loop principal."""
        self.root.mainloop()


if __name__ == "__main__":
    print("Iniciando Central de Telemetria...")
    print(f"Porta UDP: {PORTA}")
    print("Pressione 'F' para fullscreen, 'G' para gráficos, 'Q' para sair.\n")
    
    app = TelemetryDashboard()
    app.run()
