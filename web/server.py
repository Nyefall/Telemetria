"""
Servidor Web FastAPI para o Sistema de Telemetria
Permite acessar o dashboard de qualquer dispositivo na rede
"""
from __future__ import annotations

import json
import threading
import time
import socket
import gzip
from pathlib import Path
from typing import Optional, Any, Dict
from dataclasses import dataclass, asdict

# FastAPI imports (opcional)
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("[Web] FastAPI não instalado. pip install fastapi uvicorn")


@dataclass
class WebConfig:
    """Configuração do servidor web"""
    host: str = "0.0.0.0"
    port: int = 8080
    udp_port: int = 5005  # Porta para receber telemetria
    title: str = "Telemetria Dashboard"
    refresh_interval_ms: int = 1000


class TelemetryWebServer:
    """
    Servidor web para dashboard de telemetria
    
    Exemplo:
        server = TelemetryWebServer()
        server.run()  # Acesse http://localhost:8080
    """
    
    def __init__(self, config: Optional[WebConfig] = None):
        self.config = config or WebConfig()
        self.current_data: Dict[str, Any] = {}
        self.last_update: float = 0
        self.connected_clients: list = []
        self._running = False
        self._udp_thread: Optional[threading.Thread] = None
        
        if HAS_FASTAPI:
            self.app = self._create_app()
        else:
            self.app = None
    
    def _create_app(self) -> FastAPI:
        """Cria a aplicação FastAPI"""
        app = FastAPI(
            title=self.config.title,
            description="Dashboard de telemetria em tempo real",
            version="1.0.0"
        )
        
        @app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Página principal do dashboard"""
            return self._get_dashboard_html()
        
        @app.get("/api/telemetry")
        async def get_telemetry():
            """Retorna dados de telemetria atuais"""
            return JSONResponse({
                "data": self.current_data,
                "last_update": self.last_update,
                "connected": time.time() - self.last_update < 5
            })
        
        @app.get("/api/status")
        async def get_status():
            """Retorna status do servidor"""
            return JSONResponse({
                "status": "online",
                "uptime": time.time(),
                "clients": len(self.connected_clients),
                "udp_port": self.config.udp_port
            })
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket para atualizações em tempo real"""
            await websocket.accept()
            self.connected_clients.append(websocket)
            
            try:
                while True:
                    # Envia dados a cada segundo
                    await websocket.send_json({
                        "data": self.current_data,
                        "timestamp": time.time()
                    })
                    await asyncio.sleep(self.config.refresh_interval_ms / 1000)
            except WebSocketDisconnect:
                self.connected_clients.remove(websocket)
        
        return app
    
    def _get_dashboard_html(self) -> str:
        """Retorna HTML do dashboard"""
        return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telemetria Dashboard</title>
    <style>
        :root {
            --bg: #0a0a0a;
            --panel: #1a1a1a;
            --border: #333;
            --text: #fff;
            --dim: #888;
            --cpu: #00bfff;
            --gpu: #00ff00;
            --ram: #ff00ff;
            --warning: #ffff00;
            --critical: #ff3333;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Consolas', 'Monaco', monospace;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .header h1 {
            color: #00ffff;
            font-size: 1.8em;
            margin-bottom: 5px;
        }
        
        .status {
            font-size: 0.9em;
            color: var(--dim);
        }
        
        .status.connected { color: var(--gpu); }
        .status.disconnected { color: var(--critical); }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .panel {
            background: var(--panel);
            border: 2px solid var(--border);
            border-radius: 8px;
            padding: 15px;
        }
        
        .panel h2 {
            font-size: 1em;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid var(--border);
        }
        
        .panel.cpu { border-color: var(--cpu); }
        .panel.cpu h2 { color: var(--cpu); }
        
        .panel.gpu { border-color: var(--gpu); }
        .panel.gpu h2 { color: var(--gpu); }
        
        .panel.ram { border-color: var(--ram); }
        .panel.ram h2 { color: var(--ram); }
        
        .panel.network { border-color: #00ffaa; }
        .panel.network h2 { color: #00ffaa; }
        
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 0.9em;
        }
        
        .metric-label { color: var(--dim); }
        .metric-value { font-weight: bold; }
        
        .metric-value.warning { color: var(--warning); }
        .metric-value.critical { color: var(--critical); }
        
        .bar-container {
            background: #333;
            border-radius: 4px;
            height: 8px;
            margin-top: 5px;
            overflow: hidden;
        }
        
        .bar {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .bar.cpu { background: var(--cpu); }
        .bar.gpu { background: var(--gpu); }
        .bar.ram { background: var(--ram); }
        
        @media (max-width: 600px) {
            body { padding: 10px; }
            .header h1 { font-size: 1.4em; }
            .panel { padding: 10px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Telemetria Dashboard</h1>
        <div id="status" class="status disconnected">● Desconectado</div>
    </div>
    
    <div class="grid">
        <div class="panel cpu">
            <h2>💻 CPU</h2>
            <div class="metric">
                <span class="metric-label">Uso:</span>
                <span id="cpu-usage" class="metric-value">--%</span>
            </div>
            <div class="bar-container">
                <div id="cpu-bar" class="bar cpu" style="width: 0%"></div>
            </div>
            <div class="metric">
                <span class="metric-label">Temperatura:</span>
                <span id="cpu-temp" class="metric-value">--°C</span>
            </div>
            <div class="metric">
                <span class="metric-label">Clock:</span>
                <span id="cpu-clock" class="metric-value">-- MHz</span>
            </div>
            <div class="metric">
                <span class="metric-label">Consumo:</span>
                <span id="cpu-power" class="metric-value">-- W</span>
            </div>
        </div>
        
        <div class="panel gpu">
            <h2>🎮 GPU</h2>
            <div class="metric">
                <span class="metric-label">Uso:</span>
                <span id="gpu-load" class="metric-value">--%</span>
            </div>
            <div class="bar-container">
                <div id="gpu-bar" class="bar gpu" style="width: 0%"></div>
            </div>
            <div class="metric">
                <span class="metric-label">Temperatura:</span>
                <span id="gpu-temp" class="metric-value">--°C</span>
            </div>
            <div class="metric">
                <span class="metric-label">Core Clock:</span>
                <span id="gpu-clock" class="metric-value">-- MHz</span>
            </div>
            <div class="metric">
                <span class="metric-label">VRAM:</span>
                <span id="gpu-mem" class="metric-value">-- MB</span>
            </div>
            <div class="metric">
                <span class="metric-label">Fan:</span>
                <span id="gpu-fan" class="metric-value">-- RPM</span>
            </div>
        </div>
        
        <div class="panel ram">
            <h2>🧠 RAM</h2>
            <div class="metric">
                <span class="metric-label">Uso:</span>
                <span id="ram-percent" class="metric-value">--%</span>
            </div>
            <div class="bar-container">
                <div id="ram-bar" class="bar ram" style="width: 0%"></div>
            </div>
            <div class="metric">
                <span class="metric-label">Usado:</span>
                <span id="ram-used" class="metric-value">-- GB</span>
            </div>
            <div class="metric">
                <span class="metric-label">Total:</span>
                <span id="ram-total" class="metric-value">-- GB</span>
            </div>
        </div>
        
        <div class="panel network">
            <h2>🌐 Rede</h2>
            <div class="metric">
                <span class="metric-label">Download:</span>
                <span id="net-down" class="metric-value">-- KB/s</span>
            </div>
            <div class="metric">
                <span class="metric-label">Upload:</span>
                <span id="net-up" class="metric-value">-- KB/s</span>
            </div>
            <div class="metric">
                <span class="metric-label">Ping:</span>
                <span id="net-ping" class="metric-value">-- ms</span>
            </div>
            <div class="metric">
                <span class="metric-label">Link:</span>
                <span id="net-link" class="metric-value">-- Mbps</span>
            </div>
        </div>
    </div>
    
    <script>
        const API_URL = '/api/telemetry';
        const REFRESH_MS = 1000;
        
        function getClass(value, warn, crit) {
            if (value >= crit) return 'critical';
            if (value >= warn) return 'warning';
            return '';
        }
        
        function updateUI(data) {
            if (!data || !data.cpu) return;
            
            // CPU
            const cpuUsage = data.cpu.usage || 0;
            document.getElementById('cpu-usage').textContent = cpuUsage.toFixed(1) + '%';
            document.getElementById('cpu-usage').className = 'metric-value ' + getClass(cpuUsage, 70, 90);
            document.getElementById('cpu-bar').style.width = cpuUsage + '%';
            
            const cpuTemp = data.cpu.temp || 0;
            document.getElementById('cpu-temp').textContent = cpuTemp.toFixed(1) + '°C';
            document.getElementById('cpu-temp').className = 'metric-value ' + getClass(cpuTemp, 70, 85);
            
            document.getElementById('cpu-clock').textContent = (data.cpu.clock || 0).toFixed(0) + ' MHz';
            document.getElementById('cpu-power').textContent = (data.cpu.power || 0).toFixed(1) + ' W';
            
            // GPU
            const gpuLoad = data.gpu?.load || 0;
            document.getElementById('gpu-load').textContent = gpuLoad.toFixed(1) + '%';
            document.getElementById('gpu-bar').style.width = gpuLoad + '%';
            
            const gpuTemp = data.gpu?.temp || 0;
            document.getElementById('gpu-temp').textContent = gpuTemp.toFixed(1) + '°C';
            document.getElementById('gpu-temp').className = 'metric-value ' + getClass(gpuTemp, 75, 90);
            
            document.getElementById('gpu-clock').textContent = (data.gpu?.clock_core || 0).toFixed(0) + ' MHz';
            document.getElementById('gpu-mem').textContent = (data.gpu?.mem_used_mb || 0).toFixed(0) + ' MB';
            document.getElementById('gpu-fan').textContent = (data.gpu?.fan || 0).toFixed(0) + ' RPM';
            
            // RAM
            const ramPercent = data.ram?.percent || 0;
            document.getElementById('ram-percent').textContent = ramPercent.toFixed(1) + '%';
            document.getElementById('ram-percent').className = 'metric-value ' + getClass(ramPercent, 70, 90);
            document.getElementById('ram-bar').style.width = ramPercent + '%';
            document.getElementById('ram-used').textContent = (data.ram?.used_gb || 0).toFixed(1) + ' GB';
            document.getElementById('ram-total').textContent = (data.ram?.total_gb || 0).toFixed(1) + ' GB';
            
            // Network
            document.getElementById('net-down').textContent = (data.network?.down_kbps || 0).toFixed(1) + ' KB/s';
            document.getElementById('net-up').textContent = (data.network?.up_kbps || 0).toFixed(1) + ' KB/s';
            
            const ping = data.network?.ping_ms || 0;
            document.getElementById('net-ping').textContent = ping.toFixed(0) + ' ms';
            document.getElementById('net-ping').className = 'metric-value ' + getClass(ping, 50, 100);
            
            document.getElementById('net-link').textContent = (data.network?.link_speed_mbps || 0) + ' Mbps';
        }
        
        async function fetchData() {
            try {
                const response = await fetch(API_URL);
                const result = await response.json();
                
                const statusEl = document.getElementById('status');
                if (result.connected) {
                    statusEl.textContent = '● Conectado - ' + new Date().toLocaleTimeString();
                    statusEl.className = 'status connected';
                    updateUI(result.data);
                } else {
                    statusEl.textContent = '○ Aguardando dados...';
                    statusEl.className = 'status disconnected';
                }
            } catch (e) {
                console.error('Erro:', e);
            }
        }
        
        // Inicia polling
        fetchData();
        setInterval(fetchData, REFRESH_MS);
    </script>
</body>
</html>'''
    
    def _start_udp_receiver(self) -> None:
        """Inicia thread para receber dados UDP"""
        def receiver_loop():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", self.config.udp_port))
            sock.settimeout(1.0)
            
            print(f"[Web] Receptor UDP ouvindo na porta {self.config.udp_port}")
            
            while self._running:
                try:
                    data, addr = sock.recvfrom(16384)
                    
                    # Decodifica (magic byte)
                    if len(data) > 0:
                        magic = data[0]
                        if magic == 0x01:  # GZIP
                            data = gzip.decompress(data[1:])
                        elif magic == 0x00:  # Raw JSON
                            data = data[1:]
                        else:
                            try:
                                data = gzip.decompress(data)
                            except:
                                pass
                    
                    payload = json.loads(data.decode())
                    self.current_data = payload
                    self.last_update = time.time()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[Web] Erro UDP: {e}")
            
            sock.close()
        
        self._udp_thread = threading.Thread(target=receiver_loop, daemon=True)
        self._udp_thread.start()
    
    def run(self, block: bool = True) -> None:
        """
        Inicia o servidor web
        
        Args:
            block: Se True, bloqueia a thread principal
        """
        if not HAS_FASTAPI:
            print("[Web] FastAPI não disponível. Instale com: pip install fastapi uvicorn")
            return
        
        self._running = True
        self._start_udp_receiver()
        
        print(f"[Web] Dashboard disponível em http://{self.config.host}:{self.config.port}")
        print(f"[Web] Acesse de qualquer dispositivo na rede!")
        
        if block:
            uvicorn.run(
                self.app,
                host=self.config.host,
                port=self.config.port,
                log_level="warning"
            )
        else:
            thread = threading.Thread(
                target=uvicorn.run,
                kwargs={
                    "app": self.app,
                    "host": self.config.host,
                    "port": self.config.port,
                    "log_level": "warning"
                },
                daemon=True
            )
            thread.start()
    
    def stop(self) -> None:
        """Para o servidor"""
        self._running = False


def create_app(config: Optional[WebConfig] = None) -> Optional[FastAPI]:
    """
    Cria aplicação FastAPI para o dashboard
    
    Args:
        config: Configuração opcional
    
    Returns:
        Aplicação FastAPI ou None se não disponível
    """
    if not HAS_FASTAPI:
        return None
    
    server = TelemetryWebServer(config)
    return server.app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    udp_port: int = 5005
) -> None:
    """
    Inicia o servidor web
    
    Args:
        host: Host para bind
        port: Porta HTTP
        udp_port: Porta UDP para receber telemetria
    """
    config = WebConfig(host=host, port=port, udp_port=udp_port)
    server = TelemetryWebServer(config)
    server.run()


# Para uso direto: python -m web.server
if __name__ == "__main__":
    import asyncio
    run_server()
