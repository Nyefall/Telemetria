"""
Configuração centralizada do Sistema de Telemetria
Usa dataclass para type safety e validação
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any
import json
import os


@dataclass
class TelemetryConfig:
    """Configuração unificada para Sender e Receiver"""
    
    # Modo de operação
    modo: str = "sender"  # "sender" ou "receiver"
    
    # Configurações de rede
    porta: int = 5005
    dest_ip: str = "255.255.255.255"  # Broadcast por padrão
    bind_ip: str = "0.0.0.0"
    sender_ip: str = ""  # IP do sender (para receiver em modo manual)
    
    # Intervalos (em segundos)
    intervalo: float = 1.0  # Intervalo de envio de telemetria
    link_check_interval: float = 10.0  # Intervalo para verificar link de rede
    
    # Thresholds de alerta
    expected_link_speed_mbps: int = 1000
    cpu_temp_warning: int = 70
    cpu_temp_critical: int = 85
    gpu_temp_warning: int = 75
    gpu_temp_critical: int = 90
    
    # Alertas webhook
    alerts_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    alert_cooldown_seconds: int = 300  # 5 minutos
    
    # Histórico
    history_enabled: bool = True
    history_retention_days: int = 7
    
    # UI
    dark_theme: bool = True
    show_graphs: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TelemetryConfig":
        """Cria instância a partir de dicionário"""
        # Filtra apenas campos válidos
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def validate(self) -> list[str]:
        """Valida a configuração e retorna lista de erros"""
        errors = []
        
        if self.porta < 1 or self.porta > 65535:
            errors.append(f"Porta inválida: {self.porta}")
        
        if self.intervalo < 0.1 or self.intervalo > 60:
            errors.append(f"Intervalo inválido: {self.intervalo}")
        
        if self.modo not in ("sender", "receiver"):
            errors.append(f"Modo inválido: {self.modo}")
        
        return errors


def get_config_path(config_name: str = "config.json") -> Path:
    """Retorna o caminho do arquivo de configuração"""
    # Verifica se está rodando como executável empacotado
    import sys
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent
    
    return base_path / config_name


def load_config(config_path: Optional[Path] = None, config_name: str = "config.json") -> TelemetryConfig:
    """
    Carrega configuração do arquivo JSON
    
    Args:
        config_path: Caminho opcional do arquivo
        config_name: Nome do arquivo de config
    
    Returns:
        TelemetryConfig com valores carregados ou padrões
    """
    if config_path is None:
        config_path = get_config_path(config_name)
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return TelemetryConfig.from_dict(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Config] Erro ao carregar {config_path}: {e}")
    
    return TelemetryConfig()


def save_config(config: TelemetryConfig, config_path: Optional[Path] = None, config_name: str = "config.json") -> bool:
    """
    Salva configuração em arquivo JSON
    
    Args:
        config: Configuração a salvar
        config_path: Caminho opcional do arquivo
        config_name: Nome do arquivo de config
    
    Returns:
        True se salvou com sucesso
    """
    if config_path is None:
        config_path = get_config_path(config_name)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"[Config] Erro ao salvar {config_path}: {e}")
        return False


# Configuração global (singleton)
_global_config: Optional[TelemetryConfig] = None


def get_global_config() -> TelemetryConfig:
    """Retorna a configuração global (carrega se necessário)"""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def set_global_config(config: TelemetryConfig) -> None:
    """Define a configuração global"""
    global _global_config
    _global_config = config
