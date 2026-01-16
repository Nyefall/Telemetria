"""
Validadores reutilizáveis para o Sistema de Telemetria
"""
import re
from typing import Tuple, Optional


def validate_ip(ip: str) -> Tuple[bool, Optional[str]]:
    """
    Valida um endereço IPv4
    
    Args:
        ip: String com endereço IP
    
    Returns:
        Tupla (válido, mensagem_erro)
    """
    if not ip:
        return False, "IP não pode ser vazio"
    
    # Permite broadcast
    if ip == "255.255.255.255":
        return True, None
    
    # Permite 0.0.0.0 (bind em todas interfaces)
    if ip == "0.0.0.0":
        return True, None
    
    parts = ip.split(".")
    
    if len(parts) != 4:
        return False, f"IP deve ter 4 octetos, encontrado {len(parts)}"
    
    for i, part in enumerate(parts):
        try:
            num = int(part)
            if num < 0 or num > 255:
                return False, f"Octeto {i+1} fora do range (0-255): {num}"
        except ValueError:
            return False, f"Octeto {i+1} não é um número: {part}"
    
    return True, None


def validate_port(port: int | str) -> Tuple[bool, Optional[str]]:
    """
    Valida uma porta de rede
    
    Args:
        port: Número da porta
    
    Returns:
        Tupla (válido, mensagem_erro)
    """
    try:
        port_num = int(port)
    except (ValueError, TypeError):
        return False, f"Porta deve ser um número: {port}"
    
    if port_num < 1 or port_num > 65535:
        return False, f"Porta deve estar entre 1 e 65535: {port_num}"
    
    # Aviso para portas privilegiadas
    if port_num < 1024:
        return True, "Portas abaixo de 1024 podem requerer privilégios de admin"
    
    return True, None


def validate_interval(interval: float | str) -> Tuple[bool, Optional[str]]:
    """
    Valida um intervalo de tempo em segundos
    
    Args:
        interval: Intervalo em segundos
    
    Returns:
        Tupla (válido, mensagem_erro)
    """
    try:
        interval_num = float(interval)
    except (ValueError, TypeError):
        return False, f"Intervalo deve ser um número: {interval}"
    
    if interval_num < 0.1:
        return False, f"Intervalo mínimo é 0.1 segundos: {interval_num}"
    
    if interval_num > 3600:
        return False, f"Intervalo máximo é 3600 segundos (1 hora): {interval_num}"
    
    return True, None


def validate_webhook_url(url: str, webhook_type: str = "generic") -> Tuple[bool, Optional[str]]:
    """
    Valida URL de webhook
    
    Args:
        url: URL do webhook
        webhook_type: Tipo ("telegram", "discord", "generic")
    
    Returns:
        Tupla (válido, mensagem_erro)
    """
    if not url:
        return True, None  # Webhook opcional
    
    if not url.startswith("https://"):
        return False, "URL deve começar com https://"
    
    if webhook_type == "discord":
        if "discord.com/api/webhooks/" not in url:
            return False, "URL de Discord webhook inválida"
    
    return True, None


def sanitize_string(value: str, max_length: int = 100) -> str:
    """
    Sanitiza uma string removendo caracteres perigosos
    
    Args:
        value: String a sanitizar
        max_length: Tamanho máximo
    
    Returns:
        String sanitizada
    """
    # Remove caracteres de controle
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    
    # Trunca se necessário
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def parse_ip_port(address: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Parseia uma string no formato IP:PORTA
    
    Args:
        address: String no formato "192.168.1.1:5005"
    
    Returns:
        Tupla (ip, porta) ou (None, None) se inválido
    """
    if not address or ":" not in address:
        return None, None
    
    parts = address.rsplit(":", 1)
    if len(parts) != 2:
        return None, None
    
    ip, port_str = parts
    
    ip_valid, _ = validate_ip(ip)
    if not ip_valid:
        return None, None
    
    try:
        port = int(port_str)
        port_valid, _ = validate_port(port)
        if not port_valid:
            return None, None
        return ip, port
    except ValueError:
        return None, None
