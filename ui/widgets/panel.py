"""
Widget de painel reutilizável para exibição de métricas
"""
import tkinter as tk
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class PanelValue:
    """Representa um valor exibido no painel"""
    label: str
    value: Any
    unit: str = ""
    warn_threshold: Optional[float] = None
    crit_threshold: Optional[float] = None
    color: Optional[str] = None


class TelemetryPanel:
    """
    Widget de painel para exibir métricas de telemetria
    
    Exemplo:
        panel = TelemetryPanel(parent, "CPU", "#00ff88", colors)
        panel.update_value("usage", "Uso", 45.5, "%", warn=70, crit=90)
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        accent_color: str,
        colors: Dict[str, str],
        font_section: tuple = ('Segoe UI', 11, 'bold'),
        font_small: tuple = ('Segoe UI', 9),
        font_value: tuple = ('Consolas', 11, 'bold'),
        on_critical: Optional[Callable[[str, str, float, str], None]] = None
    ):
        """
        Inicializa o painel
        
        Args:
            parent: Widget pai (Frame)
            title: Título do painel
            accent_color: Cor de destaque do painel
            colors: Dicionário de cores do tema
            font_section: Fonte do título
            font_small: Fonte dos labels
            font_value: Fonte dos valores
            on_critical: Callback para valores críticos (key, label, value, unit)
        """
        self.parent = parent
        self.title_text = title
        self.accent_color = accent_color
        self.colors = colors
        self.font_section = font_section
        self.font_small = font_small
        self.font_value = font_value
        self.on_critical = on_critical
        
        self.labels: Dict[str, Dict[str, tk.Widget]] = {}
        
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Cria os widgets do painel"""
        self.frame = tk.Frame(
            self.parent,
            bg=self.colors["panel"],
            highlightthickness=2,
            highlightbackground=self.accent_color
        )
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        
        self.title_label = tk.Label(
            self.frame,
            text=f"── {self.title_text} ──",
            font=self.font_section,
            fg=self.accent_color,
            bg=self.colors["panel"]
        )
        self.title_label.pack(pady=(5, 3))
        
        self.values_frame = tk.Frame(self.frame, bg=self.colors["panel"])
        self.values_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
    
    def update_value(
        self,
        key: str,
        label: str,
        value: Any,
        unit: str = "",
        warn_threshold: Optional[float] = None,
        crit_threshold: Optional[float] = None
    ) -> None:
        """
        Atualiza ou cria um valor no painel
        
        Args:
            key: Chave única do valor
            label: Label descritivo
            value: Valor a exibir
            unit: Unidade (%, °C, etc)
            warn_threshold: Threshold para warning
            crit_threshold: Threshold para critical
        """
        # Cria labels se não existirem
        if key not in self.labels:
            self._create_value_row(key, label)
        
        # Formata valor
        text = self._format_value(value, unit)
        
        # Atualiza texto
        self.labels[key]["value"].config(text=text)
        
        # Determina cor baseada em thresholds
        color = self._get_value_color(value, warn_threshold, crit_threshold)
        self.labels[key]["value"].config(fg=color)
        
        # Callback para valores críticos
        if (crit_threshold and 
            isinstance(value, (int, float)) and 
            value >= crit_threshold and 
            self.on_critical):
            self.on_critical(key, label, value, unit)
    
    def _create_value_row(self, key: str, label: str) -> None:
        """Cria uma nova linha de valor"""
        row = tk.Frame(self.values_frame, bg=self.colors["panel"])
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
        
        self.labels[key] = {
            "name": lbl_name,
            "value": lbl_value,
            "row": row
        }
    
    def _format_value(self, value: Any, unit: str) -> str:
        """Formata valor para exibição"""
        if isinstance(value, float):
            if unit == "V":
                return f"{value:.3f}{unit}"
            elif unit in ["°C", "%", "W"]:
                return f"{value:.1f}{unit}"
            else:
                return f"{value:.1f}{unit}"
        return f"{value}{unit}"
    
    def _get_value_color(
        self,
        value: Any,
        warn_threshold: Optional[float],
        crit_threshold: Optional[float]
    ) -> str:
        """Determina cor baseada em thresholds"""
        if not isinstance(value, (int, float)):
            return self.colors["text"]
        
        if crit_threshold and value >= crit_threshold:
            return self.colors["critical"]
        elif warn_threshold and value >= warn_threshold:
            return self.colors["warning"]
        
        return self.colors["text"]
    
    def apply_theme(self, colors: Dict[str, str]) -> None:
        """Aplica novo tema ao painel"""
        self.colors = colors
        
        self.frame.configure(bg=colors["panel"])
        self.title_label.configure(bg=colors["panel"], fg=self.accent_color)
        self.values_frame.configure(bg=colors["panel"])
        
        for label_dict in self.labels.values():
            label_dict["row"].configure(bg=colors["panel"])
            label_dict["name"].configure(bg=colors["panel"], fg=colors["dim"])
            label_dict["value"].configure(bg=colors["panel"])
    
    def clear(self) -> None:
        """Limpa todos os valores"""
        for key in self.labels:
            self.labels[key]["value"].config(text="-", fg=self.colors["text"])
    
    def destroy(self) -> None:
        """Destrói o painel"""
        self.frame.destroy()
