"""
Definição de temas para a interface do Sistema de Telemetria
Usa dataclass para type safety e fácil extensão
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass(frozen=True)
class Theme:
    """Definição de um tema de cores"""
    
    name: str
    
    # Cores de fundo
    bg: str
    panel: str
    border: str
    
    # Cores de texto
    text: str
    dim: str
    title: str
    
    # Cores por componente
    cpu: str
    gpu: str
    ram: str
    storage: str
    network: str
    mobo: str
    
    # Cores de alerta
    warning: str
    critical: str
    
    def to_dict(self) -> Dict[str, str]:
        """Converte para dicionário (compatível com código legado)"""
        result = asdict(self)
        # Remove o nome para compatibilidade
        del result['name']
        return result
    
    def get_color(self, key: str, default: str = "#ffffff") -> str:
        """Obtém uma cor pelo nome"""
        return getattr(self, key, default)


# Tema Escuro (padrão)
DARK_THEME = Theme(
    name="dark",
    bg="#1a1a1a",
    panel="#252525",
    border="#333333",
    text="#ffffff",
    dim="#666666",
    title="#00d9ff",
    cpu="#00ff88",
    gpu="#00ff88",
    ram="#ffa500",
    storage="#ff6b6b",
    network="#00d9ff",
    mobo="#bb86fc",
    warning="#ffcc00",
    critical="#ff3333",
)

# Tema Claro
LIGHT_THEME = Theme(
    name="light",
    bg="#f5f5f5",
    panel="#ffffff",
    border="#cccccc",
    text="#333333",
    dim="#888888",
    title="#0066cc",
    cpu="#00aa55",
    gpu="#00aa55",
    ram="#cc7700",
    storage="#cc4444",
    network="#0066cc",
    mobo="#7744aa",
    warning="#cc9900",
    critical="#cc2222",
)

# Tema High Contrast (acessibilidade)
HIGH_CONTRAST_THEME = Theme(
    name="high_contrast",
    bg="#000000",
    panel="#1a1a1a",
    border="#ffffff",
    text="#ffffff",
    dim="#cccccc",
    title="#00ffff",
    cpu="#00ff00",
    gpu="#00ff00",
    ram="#ffff00",
    storage="#ff6600",
    network="#00ffff",
    mobo="#ff00ff",
    warning="#ffff00",
    critical="#ff0000",
)

# Tema Cyberpunk
CYBERPUNK_THEME = Theme(
    name="cyberpunk",
    bg="#0a0a1a",
    panel="#1a1a2e",
    border="#4a4a6a",
    text="#e0e0ff",
    dim="#6a6a9a",
    title="#ff00ff",
    cpu="#00ffff",
    gpu="#00ffff",
    ram="#ff6600",
    storage="#ff3366",
    network="#ff00ff",
    mobo="#9933ff",
    warning="#ffff00",
    critical="#ff0033",
)

# Registro de temas disponíveis
THEMES: Dict[str, Theme] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
    "cyberpunk": CYBERPUNK_THEME,
}


def get_theme(name: str = "dark") -> Theme:
    """
    Obtém um tema pelo nome
    
    Args:
        name: Nome do tema
    
    Returns:
        Theme correspondente ou DARK_THEME se não encontrado
    """
    return THEMES.get(name.lower(), DARK_THEME)


def get_theme_names() -> list[str]:
    """Retorna lista de nomes de temas disponíveis"""
    return list(THEMES.keys())


def create_custom_theme(
    name: str,
    base_theme: str = "dark",
    **overrides: str
) -> Theme:
    """
    Cria um tema customizado baseado em outro
    
    Args:
        name: Nome do novo tema
        base_theme: Nome do tema base
        **overrides: Cores a sobrescrever
    
    Returns:
        Novo Theme customizado
    """
    base = get_theme(base_theme)
    base_dict = asdict(base)
    base_dict['name'] = name
    base_dict.update(overrides)
    
    return Theme(**base_dict)


# Compatibilidade com código legado
def get_legacy_colors(dark_mode: bool = True) -> Dict[str, str]:
    """
    Retorna cores no formato legado (dicionário simples)
    
    Args:
        dark_mode: Se True, retorna tema escuro
    
    Returns:
        Dicionário de cores compatível com código antigo
    """
    theme = DARK_THEME if dark_mode else LIGHT_THEME
    colors = theme.to_dict()
    
    # Adiciona aliases para compatibilidade
    colors['good'] = colors['gpu']  # 'good' era usado como alias
    colors['label'] = colors['dim']  # 'label' era usado como alias
    
    return colors
