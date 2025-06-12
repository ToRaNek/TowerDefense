# gameplay/managers/sound_manager.py
"""
Gestionnaire de sons pour Steam Defense
Gère la musique de fond, les effets sonores et les paramètres audio
"""

import pygame
import os
from typing import Dict, Optional
import logging


class SoundManager:
    """
    Gestionnaire centralisé pour tous les sons du jeu
    """
    
    # Instance singleton
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not SoundManager._initialized:
            self.logger = logging.getLogger(__name__)
            
            # Initialiser pygame mixer si pas encore fait
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                    pygame.mixer.init()
                    self.logger.info("Pygame mixer initialisé")
                except pygame.error as e:
                    self.logger.error(f"Erreur lors de l'initialisation du mixer: {e}")
                    self._audio_enabled = False
                    return
            
            self._audio_enabled = True
            
            # Dictionnaires pour stocker les sons et musiques
            self.sounds: Dict[str, pygame.mixer.Sound] = {}
            self.music_tracks: Dict[str, str] = {}
            
            # État audio
            self.master_volume = 1.0
            self.music_volume = 0.7
            self.sfx_volume = 0.8
            self.music_enabled = True
            self.sfx_enabled = True
            
            # État de la musique
            self.current_music = None
            self.music_paused = False
            
            # Chemins des ressources audio
            self.sounds_path = "assets/sounds/"
            self.music_path = "assets/music/"
            
            # Charger les sons par défaut
            self._load_default_sounds()
            
            SoundManager._initialized = True
            self.logger.info("SoundManager initialisé")
    
    def _load_default_sounds(self):
        """
        Charge les sons par défaut du jeu
        Crée des sons de substitution si les fichiers n'existent pas
        """
        # Sons de base attendus
        default_sounds = {
            'button_click': 'click.wav',
            'button_hover': 'hover.wav',
            'game_pause': 'pause.wav',
            'game_start': 'start.wav',
            'game_over': 'game_over.wav',
            'victory': 'victory.wav',
            'tower_place': 'tower_place.wav',
            'tower_shoot': 'shoot.wav',
            'enemy_death': 'enemy_death.wav',
            'enemy_damage': 'damage.wav'
        }
        
        for sound_name, filename in default_sounds.items():
            self.load_sound(sound_name, filename, create_if_missing=True)
        
        # Musiques par défaut
        default_music = {
            'menu': 'menu_music.ogg',
            'gameplay': 'gameplay_music.ogg',
            'victory': 'victory_music.ogg',
            'defeat': 'defeat_music.ogg'
        }
        
        for music_name, filename in default_music.items():
            self.load_music(music_name, filename)
    
    def _create_dummy_sound(self, duration_ms: int = 100, frequency: int = 440) -> pygame.mixer.Sound:
        """
        Crée un son de substitution si le fichier n'existe pas
        
        Args:
            duration_ms: Durée en millisecondes
            frequency: Fréquence du son
            
        Returns:
            Son pygame généré
        """
        try:
            import numpy as np
            
            sample_rate = 22050
            frames = int(duration_ms * sample_rate / 1000)
            
            # Générer une onde sinusoïdale simple
            t = np.linspace(0, duration_ms / 1000, frames)
            wave = np.sin(2 * np.pi * frequency * t)
            
            # Appliquer un fade pour éviter les clics
            fade_frames = frames // 10
            wave[:fade_frames] *= np.linspace(0, 1, fade_frames)
            wave[-fade_frames:] *= np.linspace(1, 0, fade_frames)
            
            # Convertir en format pygame
            wave = (wave * 32767).astype(np.int16)
            wave = np.repeat(wave.reshape(frames, 1), 2, axis=1)  # Stéréo
            
            return pygame.sndarray.make_sound(wave)
            
        except ImportError:
            # Si numpy n'est pas disponible, créer un son silencieux
            return pygame.mixer.Sound(buffer=b'\x00' * (duration_ms * 44))
        except Exception as e:
            self.logger.warning(f"Impossible de créer un son de substitution: {e}")
            return pygame.mixer.Sound(buffer=b'\x00' * 1000)
    
    def load_sound(self, name: str, filename: str, create_if_missing: bool = False) -> bool:
        """
        Charge un effet sonore
        
        Args:
            name: Nom du son pour référence
            filename: Nom du fichier audio
            create_if_missing: Crée un son de substitution si le fichier n'existe pas
            
        Returns:
            True si le son a été chargé avec succès
        """
        if not self._audio_enabled:
            return False
        
        filepath = os.path.join(self.sounds_path, filename)
        
        try:
            if os.path.exists(filepath):
                self.sounds[name] = pygame.mixer.Sound(filepath)
                self.logger.debug(f"Son chargé: {name} ({filename})")
                return True
            elif create_if_missing:
                # Créer un son de substitution
                self.sounds[name] = self._create_dummy_sound()
                self.logger.warning(f"Fichier son manquant, son de substitution créé: {name}")
                return True
            else:
                self.logger.warning(f"Fichier son non trouvé: {filepath}")
                return False
                
        except pygame.error as e:
            self.logger.error(f"Erreur lors du chargement du son {name}: {e}")
            if create_if_missing:
                self.sounds[name] = self._create_dummy_sound()
                return True
            return False
    
    def load_music(self, name: str, filename: str) -> bool:
        """
        Enregistre un fichier de musique
        
        Args:
            name: Nom de la musique pour référence
            filename: Nom du fichier audio
            
        Returns:
            True si la musique a été enregistrée
        """
        filepath = os.path.join(self.music_path, filename)
        
        if os.path.exists(filepath):
            self.music_tracks[name] = filepath
            self.logger.debug(f"Musique enregistrée: {name} ({filename})")
            return True
        else:
            self.logger.warning(f"Fichier musique non trouvé: {filepath}")
            return False
    
    @classmethod
    def play_sound(cls, name: str, volume: Optional[float] = None) -> bool:
        """
        Joue un effet sonore
        
        Args:
            name: Nom du son à jouer
            volume: Volume spécifique (0.0 à 1.0), None pour volume par défaut
            
        Returns:
            True si le son a été joué
        """
        instance = cls()
        
        if not instance._audio_enabled or not instance.sfx_enabled:
            return False
        
        if name in instance.sounds:
            try:
                sound = instance.sounds[name]
                if volume is not None:
                    sound.set_volume(volume * instance.sfx_volume * instance.master_volume)
                else:
                    sound.set_volume(instance.sfx_volume * instance.master_volume)
                
                sound.play()
                return True
            except pygame.error as e:
                instance.logger.error(f"Erreur lors de la lecture du son {name}: {e}")
        else:
            instance.logger.warning(f"Son non trouvé: {name}")
        
        return False
    
    @classmethod
    def play_music(cls, name: str, loops: int = -1, fade_in_ms: int = 0) -> bool:
        """
        Joue une musique de fond
        
        Args:
            name: Nom de la musique à jouer
            loops: Nombre de répétitions (-1 pour infini)
            fade_in_ms: Durée du fade-in en millisecondes
            
        Returns:
            True si la musique a été lancée
        """
        instance = cls()
        
        if not instance._audio_enabled or not instance.music_enabled:
            return False
        
        if name in instance.music_tracks:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(instance.music_tracks[name])
                pygame.mixer.music.set_volume(instance.music_volume * instance.master_volume)
                
                if fade_in_ms > 0:
                    pygame.mixer.music.play(loops, fade_in_ms / 1000.0)
                else:
                    pygame.mixer.music.play(loops)
                
                instance.current_music = name
                instance.music_paused = False
                instance.logger.debug(f"Musique lancée: {name}")
                return True
                
            except pygame.error as e:
                instance.logger.error(f"Erreur lors de la lecture de la musique {name}: {e}")
        else:
            instance.logger.warning(f"Musique non trouvée: {name}")
        
        return False
    
    @classmethod
    def stop_music(cls, fade_out_ms: int = 0):
        """
        Arrête la musique
        
        Args:
            fade_out_ms: Durée du fade-out en millisecondes
        """
        instance = cls()
        
        if not instance._audio_enabled:
            return
        
        try:
            if fade_out_ms > 0:
                pygame.mixer.music.fadeout(fade_out_ms)
            else:
                pygame.mixer.music.stop()
            
            instance.current_music = None
            instance.music_paused = False
            
        except pygame.error as e:
            instance.logger.error(f"Erreur lors de l'arrêt de la musique: {e}")
    
    @classmethod
    def pause_music(cls):
        """Pause la musique"""
        instance = cls()
        
        if not instance._audio_enabled or instance.music_paused:
            return
        
        try:
            pygame.mixer.music.pause()
            instance.music_paused = True
        except pygame.error as e:
            instance.logger.error(f"Erreur lors de la pause de la musique: {e}")
    
    @classmethod
    def resume_music(cls):
        """Reprend la musique"""
        instance = cls()
        
        if not instance._audio_enabled or not instance.music_paused:
            return
        
        try:
            pygame.mixer.music.unpause()
            instance.music_paused = False
        except pygame.error as e:
            instance.logger.error(f"Erreur lors de la reprise de la musique: {e}")
    
    @classmethod
    def set_master_volume(cls, volume: float):
        """
        Définit le volume principal
        
        Args:
            volume: Volume de 0.0 à 1.0
        """
        instance = cls()
        instance.master_volume = max(0.0, min(1.0, volume))
        
        # Mettre à jour le volume de la musique actuelle
        if instance.current_music and instance._audio_enabled:
            pygame.mixer.music.set_volume(instance.music_volume * instance.master_volume)
    
    @classmethod
    def set_music_volume(cls, volume: float):
        """
        Définit le volume de la musique
        
        Args:
            volume: Volume de 0.0 à 1.0
        """
        instance = cls()
        instance.music_volume = max(0.0, min(1.0, volume))
        
        if instance.current_music and instance._audio_enabled:
            pygame.mixer.music.set_volume(instance.music_volume * instance.master_volume)
    
    @classmethod
    def set_sfx_volume(cls, volume: float):
        """
        Définit le volume des effets sonores
        
        Args:
            volume: Volume de 0.0 à 1.0
        """
        instance = cls()
        instance.sfx_volume = max(0.0, min(1.0, volume))
    
    @classmethod
    def toggle_music(cls) -> bool:
        """
        Active/désactive la musique
        
        Returns:
            Nouvel état de la musique
        """
        instance = cls()
        instance.music_enabled = not instance.music_enabled
        
        if not instance.music_enabled and instance.current_music:
            cls.stop_music()
        
        return instance.music_enabled
    
    @classmethod
    def toggle_sfx(cls) -> bool:
        """
        Active/désactive les effets sonores
        
        Returns:
            Nouvel état des effets sonores
        """
        instance = cls()
        instance.sfx_enabled = not instance.sfx_enabled
        return instance.sfx_enabled
    
    @classmethod
    def cleanup(cls):
        """Nettoie les ressources audio"""
        instance = cls()
        
        if instance._audio_enabled:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        
        instance.sounds.clear()
        instance.music_tracks.clear()
        instance.logger.info("SoundManager nettoyé")