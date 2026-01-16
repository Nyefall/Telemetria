"""
Sistema de sons de alerta para o Sistema de Telemetria
Usa winsound nativo do Windows - sem dependências externas
"""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Optional
import sys

# winsound só existe no Windows
if sys.platform == 'win32':
    import winsound
    HAS_WINSOUND = True
else:
    HAS_WINSOUND = False


class AlertSound(Enum):
    """Sons de alerta disponíveis"""
    # Sons do sistema Windows (não precisam de arquivo)
    BEEP = "beep"              # Beep simples
    WARNING = "warning"        # Som de aviso do Windows
    CRITICAL = "critical"      # Som de erro crítico
    INFO = "info"              # Som de informação
    QUESTION = "question"      # Som de pergunta
    
    # Beeps customizados (frequência, duração)
    BEEP_LOW = "beep_low"      # Tom grave
    BEEP_HIGH = "beep_high"    # Tom agudo
    BEEP_URGENT = "beep_urgent"  # Padrão urgente (3 beeps)


class SoundConfig:
    """Configuração do sistema de sons"""
    
    def __init__(
        self,
        enabled: bool = True,
        volume_percent: int = 100,  # Não usado no winsound, mas reservado
        cooldown_seconds: float = 10.0,  # Intervalo mínimo entre sons do mesmo tipo
        warning_sound: AlertSound = AlertSound.WARNING,
        critical_sound: AlertSound = AlertSound.BEEP_URGENT
    ):
        self.enabled = enabled
        self.volume_percent = volume_percent
        self.cooldown_seconds = cooldown_seconds
        self.warning_sound = warning_sound
        self.critical_sound = critical_sound


class SoundManager:
    """
    Gerenciador de sons de alerta
    
    Exemplo:
        sounds = SoundManager()
        sounds.play(AlertSound.WARNING)
        sounds.play_critical()  # Toca padrão urgente
    """
    
    # Mapeamento de sons do sistema Windows
    SYSTEM_SOUNDS = {
        AlertSound.WARNING: "SystemExclamation",
        AlertSound.CRITICAL: "SystemHand",
        AlertSound.INFO: "SystemAsterisk",
        AlertSound.QUESTION: "SystemQuestion",
    }
    
    # Frequências para beeps customizados (Hz)
    BEEP_FREQUENCIES = {
        AlertSound.BEEP: 800,
        AlertSound.BEEP_LOW: 400,
        AlertSound.BEEP_HIGH: 1200,
    }
    
    def __init__(self, config: Optional[SoundConfig] = None):
        """
        Inicializa o gerenciador de sons
        
        Args:
            config: Configuração de sons (usa padrão se None)
        """
        self.config = config or SoundConfig()
        self.last_played: dict[str, float] = {}
        self._lock = threading.Lock()
    
    def play(self, sound: AlertSound, async_play: bool = True) -> bool:
        """
        Toca um som de alerta
        
        Args:
            sound: Som a tocar
            async_play: Se True, toca em thread separada
        
        Returns:
            True se o som foi tocado (ou agendado)
        """
        if not self.config.enabled or not HAS_WINSOUND:
            return False
        
        # Verifica cooldown
        with self._lock:
            now = time.time()
            last_time = self.last_played.get(sound.value, 0)
            
            if now - last_time < self.config.cooldown_seconds:
                return False
            
            self.last_played[sound.value] = now
        
        if async_play:
            thread = threading.Thread(target=self._play_sound, args=(sound,), daemon=True)
            thread.start()
            return True
        else:
            return self._play_sound(sound)
    
    def _play_sound(self, sound: AlertSound) -> bool:
        """Toca o som (interno)"""
        try:
            if sound in self.SYSTEM_SOUNDS:
                # Som do sistema Windows
                winsound.PlaySound(
                    self.SYSTEM_SOUNDS[sound],
                    winsound.SND_ALIAS | winsound.SND_ASYNC
                )
                return True
            
            elif sound in self.BEEP_FREQUENCIES:
                # Beep com frequência específica
                freq = self.BEEP_FREQUENCIES[sound]
                winsound.Beep(freq, 200)  # 200ms
                return True
            
            elif sound == AlertSound.BEEP_URGENT:
                # Padrão urgente: 3 beeps rápidos
                for _ in range(3):
                    winsound.Beep(1000, 150)
                    time.sleep(0.1)
                return True
            
            else:
                # Beep genérico
                winsound.Beep(800, 200)
                return True
                
        except Exception as e:
            print(f"[Sound] Erro ao tocar som: {e}")
            return False
    
    def play_warning(self) -> bool:
        """Toca som de aviso"""
        return self.play(self.config.warning_sound)
    
    def play_critical(self) -> bool:
        """Toca som crítico"""
        return self.play(self.config.critical_sound)
    
    def play_beep(self, frequency: int = 800, duration_ms: int = 200) -> bool:
        """
        Toca beep customizado
        
        Args:
            frequency: Frequência em Hz (37-32767)
            duration_ms: Duração em milissegundos
        """
        if not self.config.enabled or not HAS_WINSOUND:
            return False
        
        try:
            # Limita frequência ao range válido
            frequency = max(37, min(32767, frequency))
            winsound.Beep(frequency, duration_ms)
            return True
        except Exception:
            return False
    
    def test_all_sounds(self) -> None:
        """Testa todos os sons disponíveis (para debug)"""
        if not HAS_WINSOUND:
            print("[Sound] winsound não disponível nesta plataforma")
            return
        
        print("[Sound] Testando sons...")
        
        for sound in AlertSound:
            print(f"  - {sound.name}...")
            self._play_sound(sound)
            time.sleep(0.5)
        
        print("[Sound] Teste concluído!")
    
    def update_config(self, config: SoundConfig) -> None:
        """Atualiza configuração"""
        self.config = config
    
    def clear_cooldowns(self) -> None:
        """Limpa todos os cooldowns"""
        with self._lock:
            self.last_played.clear()


# Instância global (singleton)
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """Retorna o gerenciador global de sons"""
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager


def init_sounds(config: Optional[SoundConfig] = None) -> SoundManager:
    """
    Inicializa o gerenciador global de sons
    
    Args:
        config: Configuração opcional
    
    Returns:
        SoundManager inicializado
    """
    global _sound_manager
    _sound_manager = SoundManager(config)
    return _sound_manager


# Funções de conveniência
def play_warning() -> bool:
    """Toca som de aviso"""
    return get_sound_manager().play_warning()


def play_critical() -> bool:
    """Toca som crítico"""
    return get_sound_manager().play_critical()


def play_beep(frequency: int = 800, duration_ms: int = 200) -> bool:
    """Toca beep customizado"""
    return get_sound_manager().play_beep(frequency, duration_ms)
