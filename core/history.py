"""
Histórico persistente com SQLite para o Sistema de Telemetria
Armazena métricas para análise posterior
"""
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class MetricRecord:
    """Registro de uma métrica"""
    timestamp: datetime
    cpu_usage: float
    cpu_temp: float
    gpu_load: float
    gpu_temp: float
    ram_percent: float
    ping_ms: float
    net_down_kbps: float = 0
    net_up_kbps: float = 0


class TelemetryHistory:
    """
    Histórico de telemetria com SQLite
    
    Exemplo:
        history = TelemetryHistory(Path("logs/history.db"))
        history.record(telemetry_data)
        
        # Consultar última hora
        records = history.get_history("cpu_temp", hours=1)
    """
    
    def __init__(self, db_path: Path, retention_days: int = 7):
        """
        Inicializa o histórico
        
        Args:
            db_path: Caminho do banco SQLite
            retention_days: Dias para manter os dados
        """
        self.db_path = db_path
        self.retention_days = retention_days
        self._lock = threading.Lock()
        
        # Cria diretório se necessário
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Inicializa banco
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexão thread-safe"""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self) -> None:
        """Cria tabelas se não existirem"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    cpu_temp REAL,
                    gpu_load REAL,
                    gpu_temp REAL,
                    ram_percent REAL,
                    ping_ms REAL,
                    net_down_kbps REAL DEFAULT 0,
                    net_up_kbps REAL DEFAULT 0
                )
            """)
            
            # Índice para consultas por tempo
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON metrics(timestamp)
            """)
            
            conn.commit()
    
    def record(self, data: Dict[str, Any]) -> bool:
        """
        Registra dados de telemetria
        
        Args:
            data: Dicionário com dados de telemetria
        
        Returns:
            True se registrou com sucesso
        """
        try:
            cpu = data.get("cpu", {})
            gpu = data.get("gpu", {})
            ram = data.get("ram", {})
            net = data.get("network", {})
            
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO metrics (
                            cpu_usage, cpu_temp, gpu_load, gpu_temp,
                            ram_percent, ping_ms, net_down_kbps, net_up_kbps
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cpu.get("usage", 0),
                        cpu.get("temp", 0),
                        gpu.get("load", 0),
                        gpu.get("temp", 0),
                        ram.get("percent", 0),
                        net.get("ping_ms", 0),
                        net.get("down_kbps", 0),
                        net.get("up_kbps", 0)
                    ))
                    conn.commit()
            return True
        except Exception as e:
            print(f"[History] Erro ao registrar: {e}")
            return False
    
    def get_history(
        self,
        metric: str,
        hours: int = 1,
        limit: int = 1000
    ) -> List[Tuple[datetime, float]]:
        """
        Obtém histórico de uma métrica
        
        Args:
            metric: Nome da coluna (cpu_usage, cpu_temp, etc)
            hours: Horas de histórico
            limit: Máximo de registros
        
        Returns:
            Lista de (timestamp, valor)
        """
        valid_metrics = [
            "cpu_usage", "cpu_temp", "gpu_load", "gpu_temp",
            "ram_percent", "ping_ms", "net_down_kbps", "net_up_kbps"
        ]
        
        if metric not in valid_metrics:
            return []
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT timestamp, {metric}
                    FROM metrics
                    WHERE timestamp > datetime('now', '-{hours} hours')
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                return [
                    (datetime.fromisoformat(row['timestamp']), row[metric])
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            print(f"[History] Erro ao consultar: {e}")
            return []
    
    def get_stats(
        self,
        metric: str,
        hours: int = 1
    ) -> Dict[str, float]:
        """
        Obtém estatísticas de uma métrica
        
        Args:
            metric: Nome da coluna
            hours: Período em horas
        
        Returns:
            Dict com min, max, avg, count
        """
        valid_metrics = [
            "cpu_usage", "cpu_temp", "gpu_load", "gpu_temp",
            "ram_percent", "ping_ms", "net_down_kbps", "net_up_kbps"
        ]
        
        if metric not in valid_metrics:
            return {}
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT 
                        MIN({metric}) as min_val,
                        MAX({metric}) as max_val,
                        AVG({metric}) as avg_val,
                        COUNT(*) as count
                    FROM metrics
                    WHERE timestamp > datetime('now', '-{hours} hours')
                """)
                
                row = cursor.fetchone()
                if row:
                    return {
                        "min": row['min_val'] or 0,
                        "max": row['max_val'] or 0,
                        "avg": row['avg_val'] or 0,
                        "count": row['count'] or 0
                    }
        except Exception as e:
            print(f"[History] Erro ao calcular stats: {e}")
        
        return {"min": 0, "max": 0, "avg": 0, "count": 0}
    
    def get_all_stats(self, hours: int = 1) -> Dict[str, Dict[str, float]]:
        """
        Obtém estatísticas de todas as métricas
        
        Args:
            hours: Período em horas
        
        Returns:
            Dict com stats de cada métrica
        """
        metrics = [
            "cpu_usage", "cpu_temp", "gpu_load", "gpu_temp",
            "ram_percent", "ping_ms"
        ]
        
        return {metric: self.get_stats(metric, hours) for metric in metrics}
    
    def cleanup_old(self, days: Optional[int] = None) -> int:
        """
        Remove registros antigos
        
        Args:
            days: Dias a manter (usa retention_days se None)
        
        Returns:
            Número de registros removidos
        """
        days = days or self.retention_days
        
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.execute(f"""
                        DELETE FROM metrics
                        WHERE timestamp < datetime('now', '-{days} days')
                    """)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            print(f"[History] Erro ao limpar: {e}")
            return 0
    
    def get_size_info(self) -> Dict[str, Any]:
        """
        Obtém informações sobre o tamanho do banco
        
        Returns:
            Dict com tamanho em bytes e número de registros
        """
        try:
            size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM metrics")
                count = cursor.fetchone()['count']
            
            return {
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "record_count": count
            }
        except Exception as e:
            print(f"[History] Erro ao obter info: {e}")
            return {"size_bytes": 0, "size_mb": 0, "record_count": 0}
    
    def vacuum(self) -> None:
        """Otimiza o banco de dados"""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
        except Exception as e:
            print(f"[History] Erro ao otimizar: {e}")


# Instância global
_history: Optional[TelemetryHistory] = None


def get_history() -> Optional[TelemetryHistory]:
    """Retorna o histórico global"""
    return _history


def init_history(db_path: Path, retention_days: int = 7) -> TelemetryHistory:
    """
    Inicializa o histórico global
    
    Args:
        db_path: Caminho do banco
        retention_days: Dias de retenção
    
    Returns:
        TelemetryHistory inicializado
    """
    global _history
    _history = TelemetryHistory(db_path, retention_days)
    return _history
