"""
Sistema de alertas via webhook para o Sistema de Telemetria
Suporta Telegram, Discord e webhooks genéricos
"""
import json
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from enum import Enum
from urllib.request import Request, urlopen
from urllib.error import URLError


class AlertLevel(Enum):
    """Níveis de alerta"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertConfig:
    """Configuração de alertas"""
    enabled: bool = False
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # Discord
    discord_webhook_url: str = ""
    
    # ntfy.sh (push notifications gratuitas)
    ntfy_topic: str = ""  # Ex: "meu-pc-telemetria" (será a URL ntfy.sh/SEU_TOPIC)
    ntfy_server: str = "https://ntfy.sh"  # Pode usar servidor próprio
    
    # Webhook genérico
    generic_webhook_url: str = ""
    
    # Configurações
    cooldown_seconds: int = 300  # 5 minutos entre alertas do mesmo tipo
    min_level: AlertLevel = AlertLevel.WARNING
    
    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)
    
    @property
    def discord_enabled(self) -> bool:
        return bool(self.discord_webhook_url)
    
    @property
    def ntfy_enabled(self) -> bool:
        return bool(self.ntfy_topic)
    
    @property
    def any_enabled(self) -> bool:
        return self.enabled and (self.telegram_enabled or self.discord_enabled or self.ntfy_enabled)


class AlertManager:
    """
    Gerenciador de alertas
    
    Exemplo:
        config = AlertConfig(
            enabled=True,
            telegram_bot_token="123:ABC",
            telegram_chat_id="987654321"
        )
        alerts = AlertManager(config)
        alerts.send_alert("cpu_temp", "CPU Temp", 95.5, "°C", AlertLevel.CRITICAL)
    """
    
    def __init__(self, config: AlertConfig):
        """
        Inicializa o gerenciador
        
        Args:
            config: Configuração de alertas
        """
        self.config = config
        self.last_alerts: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def send_alert(
        self,
        metric_key: str,
        metric_name: str,
        value: float,
        unit: str,
        level: AlertLevel = AlertLevel.WARNING,
        extra_info: str = ""
    ) -> bool:
        """
        Envia alerta se possível (respeitando cooldown)
        
        Args:
            metric_key: Chave única da métrica
            metric_name: Nome legível da métrica
            value: Valor atual
            unit: Unidade de medida
            level: Nível do alerta
            extra_info: Informação adicional
        
        Returns:
            True se o alerta foi enviado
        """
        if not self.config.any_enabled:
            return False
        
        # Verifica nível mínimo
        if self._level_value(level) < self._level_value(self.config.min_level):
            return False
        
        # Verifica cooldown
        with self._lock:
            now = time.time()
            last_time = self.last_alerts.get(metric_key, 0)
            
            if now - last_time < self.config.cooldown_seconds:
                return False
            
            self.last_alerts[metric_key] = now
        
        # Monta mensagem
        emoji = self._get_emoji(level)
        level_text = level.value.upper()
        message = f"{emoji} ALERTA {level_text}: {metric_name} = {value:.1f}{unit}"
        
        if extra_info:
            message += f"\n{extra_info}"
        
        # Envia em thread separada para não bloquear
        thread = threading.Thread(
            target=self._send_all,
            args=(message, level),
            daemon=True
        )
        thread.start()
        
        return True
    
    def test_connection(self) -> Dict[str, bool]:
        """
        Testa conexão com todos os serviços configurados
        
        Returns:
            Dict com status de cada serviço
        """
        results = {}
        
        if self.config.telegram_enabled:
            results["telegram"] = self._test_telegram()
        
        if self.config.discord_enabled:
            results["discord"] = self._test_discord()
        
        if self.config.ntfy_enabled:
            results["ntfy"] = self._test_ntfy()
        
        return results
    
    def _send_all(self, message: str, level: AlertLevel) -> None:
        """Envia para todos os serviços configurados"""
        if self.config.telegram_enabled:
            self._send_telegram(message)
        
        if self.config.discord_enabled:
            self._send_discord(message, level)
        
        if self.config.ntfy_enabled:
            self._send_ntfy(message, level)
    
    def _send_telegram(self, message: str) -> bool:
        """Envia mensagem via Telegram Bot API"""
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.config.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }).encode('utf-8')
            
            request = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            print(f"[Alerts] Erro ao enviar Telegram: {e}")
            return False
    
    def _send_discord(self, message: str, level: AlertLevel) -> bool:
        """Envia mensagem via Discord Webhook"""
        try:
            # Cores do Discord (decimal)
            colors = {
                AlertLevel.INFO: 3447003,      # Azul
                AlertLevel.WARNING: 16776960,  # Amarelo
                AlertLevel.CRITICAL: 15158332  # Vermelho
            }
            
            data = json.dumps({
                "embeds": [{
                    "title": "📊 Telemetria - Alerta",
                    "description": message,
                    "color": colors.get(level, 3447003),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }]
            }).encode('utf-8')
            
            request = Request(
                self.config.discord_webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urlopen(request, timeout=10) as response:
                return response.status in (200, 204)
        except Exception as e:
            print(f"[Alerts] Erro ao enviar Discord: {e}")
            return False
    
    def _send_ntfy(self, message: str, level: AlertLevel) -> bool:
        """
        Envia notificação via ntfy.sh
        
        ntfy.sh é um serviço gratuito de push notifications.
        Basta instalar o app ntfy no celular e se inscrever no tópico.
        
        Docs: https://ntfy.sh
        """
        try:
            url = f"{self.config.ntfy_server}/{self.config.ntfy_topic}"
            
            # Prioridades do ntfy: 1=min, 2=low, 3=default, 4=high, 5=urgent
            priorities = {
                AlertLevel.INFO: "3",
                AlertLevel.WARNING: "4",
                AlertLevel.CRITICAL: "5"
            }
            
            # Tags (emojis) do ntfy
            tags = {
                AlertLevel.INFO: "information_source",
                AlertLevel.WARNING: "warning",
                AlertLevel.CRITICAL: "rotating_light,skull"
            }
            
            headers = {
                "Title": "Telemetria - Alerta",
                "Priority": priorities.get(level, "3"),
                "Tags": tags.get(level, "computer"),
            }
            
            # Adiciona ação de clique se for crítico
            if level == AlertLevel.CRITICAL:
                headers["Actions"] = "view, Ver Dashboard, http://localhost:8080"
            
            request = Request(url, data=message.encode('utf-8'), headers=headers)
            with urlopen(request, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            print(f"[Alerts] Erro ao enviar ntfy: {e}")
            return False
    
    def _test_telegram(self) -> bool:
        """Testa conexão com Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/getMe"
            with urlopen(url, timeout=10) as response:
                return response.status == 200
        except:
            return False
    
    def _test_discord(self) -> bool:
        """Testa conexão com Discord"""
        try:
            request = Request(self.config.discord_webhook_url, method="GET")
            with urlopen(request, timeout=10) as response:
                return response.status == 200
        except:
            return False
    
    def _test_ntfy(self) -> bool:
        """Testa conexão com ntfy.sh"""
        try:
            # Envia mensagem de teste silenciosa (priority 1 = min)
            url = f"{self.config.ntfy_server}/{self.config.ntfy_topic}"
            headers = {
                "Title": "Telemetria - Teste",
                "Priority": "1",  # Mínima para não incomodar
                "Tags": "white_check_mark"
            }
            request = Request(url, data=b"Conexao OK!", headers=headers)
            with urlopen(request, timeout=10) as response:
                return response.status == 200
        except:
            return False
    
    def _get_emoji(self, level: AlertLevel) -> str:
        """Retorna emoji para o nível"""
        emojis = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.CRITICAL: "🚨"
        }
        return emojis.get(level, "📊")
    
    def _level_value(self, level: AlertLevel) -> int:
        """Retorna valor numérico do nível para comparação"""
        values = {
            AlertLevel.INFO: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.CRITICAL: 3
        }
        return values.get(level, 0)
    
    def clear_cooldowns(self) -> None:
        """Limpa todos os cooldowns"""
        with self._lock:
            self.last_alerts.clear()
    
    def update_config(self, config: AlertConfig) -> None:
        """Atualiza configuração"""
        self.config = config


# Instância global (singleton)
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> Optional[AlertManager]:
    """Retorna o gerenciador global de alertas"""
    return _alert_manager


def init_alerts(config: AlertConfig) -> AlertManager:
    """
    Inicializa o gerenciador global de alertas
    
    Args:
        config: Configuração de alertas
    
    Returns:
        AlertManager inicializado
    """
    global _alert_manager
    _alert_manager = AlertManager(config)
    return _alert_manager
