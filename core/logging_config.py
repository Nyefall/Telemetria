"""
Configuração de logging estruturado para o Sistema de Telemetria
Substitui prints por logging com níveis e formatação
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import IntEnum


class LogLevel(IntEnum):
    """Níveis de log personalizados"""
    DEBUG = logging.DEBUG      # 10
    INFO = logging.INFO        # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR      # 40
    CRITICAL = logging.CRITICAL  # 50


# Cores ANSI para terminal (Windows 10+)
COLORS = {
    'DEBUG': '\033[36m',     # Cyan
    'INFO': '\033[32m',      # Green
    'WARNING': '\033[33m',   # Yellow
    'ERROR': '\033[31m',     # Red
    'CRITICAL': '\033[35m',  # Magenta
    'RESET': '\033[0m',      # Reset
    'DIM': '\033[2m',        # Dim
}


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para terminal"""
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime('%H:%M:%S')
        level = record.levelname
        name = record.name
        message = record.getMessage()
        
        if self.use_colors:
            color = COLORS.get(level, '')
            reset = COLORS['RESET']
            dim = COLORS['DIM']
            return f"{dim}{timestamp}{reset} {color}[{level[:4]}]{reset} {dim}({name}){reset} {message}"
        else:
            return f"{timestamp} [{level[:4]}] ({name}) {message}"


class FileFormatter(logging.Formatter):
    """Formatter para arquivo (sem cores)"""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level = record.levelname
        name = record.name
        message = record.getMessage()
        
        # Inclui traceback se houver exceção
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            return f"{timestamp} [{level}] ({name}) {message}\n{exc_text}"
        
        return f"{timestamp} [{level}] ({name}) {message}"


# Cache de loggers
_loggers: dict[str, logging.Logger] = {}
_initialized: bool = False


def setup_logger(
    name: str = "telemetry",
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    console_output: bool = True,
    use_colors: bool = True
) -> logging.Logger:
    """
    Configura e retorna um logger
    
    Args:
        name: Nome do logger
        level: Nível mínimo de log
        log_file: Caminho opcional para arquivo de log
        console_output: Se True, imprime no console
        use_colors: Se True, usa cores no console
    
    Returns:
        Logger configurado
    """
    global _initialized
    
    # Habilita cores no Windows
    if sys.platform == 'win32' and use_colors:
        import os
        os.system('')  # Habilita ANSI no Windows 10+
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove handlers existentes para evitar duplicação
    logger.handlers.clear()
    
    # Handler de console
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ColoredFormatter(use_colors))
        logger.addHandler(console_handler)
    
    # Handler de arquivo
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(FileFormatter())
        logger.addHandler(file_handler)
    
    # Evita propagação para root logger
    logger.propagate = False
    
    _loggers[name] = logger
    _initialized = True
    
    return logger


def get_logger(name: str = "telemetry") -> logging.Logger:
    """
    Obtém um logger existente ou cria um novo
    
    Args:
        name: Nome do logger
    
    Returns:
        Logger
    """
    if name in _loggers:
        return _loggers[name]
    
    # Cria logger filho se o pai existe
    parts = name.split('.')
    if len(parts) > 1:
        parent_name = '.'.join(parts[:-1])
        if parent_name in _loggers:
            child_logger = _loggers[parent_name].getChild(parts[-1])
            _loggers[name] = child_logger
            return child_logger
    
    # Cria novo logger com configurações padrão
    return setup_logger(name)


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """
    Loga uma exceção com stack trace
    
    Args:
        logger: Logger a usar
        message: Mensagem descritiva
        exc: Exceção a logar
    """
    logger.error(f"{message}: {type(exc).__name__}: {exc}", exc_info=True)


# Funções de conveniência para o logger principal
def debug(message: str) -> None:
    get_logger().debug(message)

def info(message: str) -> None:
    get_logger().info(message)

def warning(message: str) -> None:
    get_logger().warning(message)

def error(message: str) -> None:
    get_logger().error(message)

def critical(message: str) -> None:
    get_logger().critical(message)
