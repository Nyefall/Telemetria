"""
Widget de barra de status reutilizável
"""
import tkinter as tk
from typing import Dict, Optional
from enum import Enum


class ConnectionStatus(Enum):
    """Estados possíveis de conexão"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


class StatusBar:
    """
    Barra de status para o dashboard
    
    Exemplo:
        status = StatusBar(parent, colors)
        status.set_connected("10:30:45")
        status.set_logging(True)
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        colors: Dict[str, str],
        font: tuple = ('Consolas', 10)
    ):
        """
        Inicializa a barra de status
        
        Args:
            parent: Widget pai
            colors: Dicionário de cores do tema
            font: Fonte do texto
        """
        self.parent = parent
        self.colors = colors
        self.font = font
        
        self.status = ConnectionStatus.DISCONNECTED
        self.logging_enabled = False
        self.extra_info = ""
        
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Cria os widgets da barra"""
        self.label = tk.Label(
            self.parent,
            text="○ Aguardando conexão...",
            font=self.font,
            fg=self.colors.get("dim", "#666666"),
            bg=self.colors.get("bg", "#1a1a1a")
        )
        self.label.pack(side=tk.TOP, pady=3)
    
    def set_connected(self, timestamp: str) -> None:
        """
        Define status como conectado
        
        Args:
            timestamp: Horário da última atualização
        """
        self.status = ConnectionStatus.CONNECTED
        self._update_display(
            f"● Conectado | Atualizado: {timestamp}",
            self.colors.get("gpu", "#00ff88")
        )
    
    def set_disconnected(self, mode_text: str = "") -> None:
        """
        Define status como desconectado
        
        Args:
            mode_text: Texto adicional sobre o modo
        """
        self.status = ConnectionStatus.DISCONNECTED
        text = f"○ Desconectado - Aguardando dados...{mode_text}"
        self._update_display(text, self.colors.get("critical", "#ff3333"))
    
    def set_connecting(self) -> None:
        """Define status como conectando"""
        self.status = ConnectionStatus.CONNECTING
        self._update_display(
            "◐ Conectando...",
            self.colors.get("warning", "#ffcc00")
        )
    
    def set_error(self, message: str) -> None:
        """
        Define status como erro
        
        Args:
            message: Mensagem de erro
        """
        self.status = ConnectionStatus.ERROR
        self._update_display(
            f"✕ Erro: {message}",
            self.colors.get("critical", "#ff3333")
        )
    
    def set_logging(self, enabled: bool) -> None:
        """
        Atualiza indicador de logging
        
        Args:
            enabled: Se logging está ativo
        """
        self.logging_enabled = enabled
        self._refresh_display()
    
    def set_extra_info(self, info: str) -> None:
        """
        Define informação extra na barra
        
        Args:
            info: Texto adicional
        """
        self.extra_info = info
        self._refresh_display()
    
    def _update_display(self, text: str, color: str) -> None:
        """Atualiza o display da barra"""
        full_text = text
        
        if self.logging_enabled:
            full_text += " | 📝 LOG"
        
        if self.extra_info:
            full_text += f" | {self.extra_info}"
        
        self.label.config(text=full_text, fg=color)
    
    def _refresh_display(self) -> None:
        """Reaplica o display atual com novos flags"""
        # Reconstrói baseado no status atual
        if self.status == ConnectionStatus.CONNECTED:
            # Mantém a cor verde
            current_text = self.label.cget("text").split(" | ")[0]
            self._update_display(current_text, self.colors.get("gpu", "#00ff88"))
        elif self.status == ConnectionStatus.DISCONNECTED:
            current_text = self.label.cget("text").split(" | ")[0]
            self._update_display(current_text, self.colors.get("critical", "#ff3333"))
    
    def apply_theme(self, colors: Dict[str, str]) -> None:
        """
        Aplica novo tema à barra
        
        Args:
            colors: Novo dicionário de cores
        """
        self.colors = colors
        self.label.configure(bg=colors.get("bg", "#1a1a1a"))
        self._refresh_display()
    
    def get_status(self) -> ConnectionStatus:
        """Retorna o status atual"""
        return self.status
