"""
Core - Módulos centrais do Sistema de Telemetria
"""
from .config import TelemetryConfig, load_config, save_config, get_global_config
from .protocol import MagicByte, encode_payload, decode_payload
from .validators import validate_ip, validate_port, validate_interval
from .logging_config import setup_logger, get_logger, LogLevel
from .alerts import AlertConfig, AlertManager, AlertLevel, init_alerts, get_alert_manager
from .history import TelemetryHistory, init_history, get_history
from .sounds import SoundConfig, SoundManager, AlertSound, init_sounds, get_sound_manager, play_warning, play_critical

__all__ = [
    # Config
    "TelemetryConfig",
    "load_config", 
    "save_config",
    "get_global_config",
    # Protocol
    "MagicByte",
    "encode_payload",
    "decode_payload",
    # Validators
    "validate_ip",
    "validate_port",
    "validate_interval",
    # Logging
    "setup_logger",
    "get_logger",
    "LogLevel",
    # Alerts
    "AlertConfig",
    "AlertManager",
    "AlertLevel",
    "init_alerts",
    "get_alert_manager",
    # History
    "TelemetryHistory",
    "init_history",
    "get_history",
    # Sounds
    "SoundConfig",
    "SoundManager",
    "AlertSound",
    "init_sounds",
    "get_sound_manager",
    "play_warning",
    "play_critical",
]
