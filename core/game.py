# core/game.py
"""
Steam Defense - Classe Game principale
Gère la boucle de jeu principale et coordination entre les systèmes
"""

import arcade
import time
import logging
from typing import Optional

from core.state_manager import StateManager, GameStateType
from core.resource_manager import ResourceManager
from core.timer import GameTimer
from core.event_system import EventSystem
from graphics.renderer import Renderer
from graphics.camera import Camera2D
from input.input_manager import InputManager
from config.settings import SETTINGS, DEBUG_CONFIG, PERFORMANCE


class Game(arcade.Window):
    """
    Classe principale du jeu Steam Defense
    Hérite d'arcade.Window et gère la boucle de jeu principale
    """
    
    def __init__(self, resource_manager: ResourceManager):
        """
        Initialise le jeu
        
        Args:
            resource_manager: Gestionnaire de ressources pré-initialisé
        """
        # Initialisation de la fenêtre Arcade
        super().__init__(
            SETTINGS['SCREEN_WIDTH'],
            SETTINGS['SCREEN_HEIGHT'],
            SETTINGS['SCREEN_TITLE'],
            resizable=True,
            vsync=SETTINGS['VSYNC']
        )
        
        # Configuration du logger
        self.logger = logging.getLogger('Game')
        self.logger.info("Initialisation de la classe Game")
        
        # Systèmes principaux
        self.resource_manager = resource_manager
        self.state_manager = StateManager()
        self.event_system = EventSystem()
        self.timer = GameTimer()
        self.input_manager = InputManager(self.event_system)
        
        # Systèmes de rendu
        self.camera = Camera2D(SETTINGS['SCREEN_WIDTH'], SETTINGS['SCREEN_HEIGHT'])
        self.renderer = Renderer(self.camera)
        
        # État du jeu
        self.is_running = True
        self.is_paused = False
        self.debug_mode = False
        
        # Métriques de performance
        self.frame_count = 0
        self.fps_timer = 0.0
        self.current_fps = 0.0
        self.frame_time_history = []
        
        # Configuration initiale
        self._setup_window()
        self._setup_states()
        self._setup_event_handlers()
        
        self.logger.info("Game initialisé avec succès")
    
    def _setup_window(self):
        """Configure les paramètres de la fenêtre"""
        arcade.set_background_color(SETTINGS['BACKGROUND_COLOR'])
        
        # Configuration de l'antialiasing si supporté
        if SETTINGS['ANTIALIASING']:
            try:
                arcade.enable_smooth_textures()
            except Exception as e:
                self.logger.warning(f"Antialiasing non supporté: {e}")
    
    def _setup_states(self):
        """Initialise les états de jeu"""
        from gameplay.states.main_menu_state import MainMenuState
        from gameplay.states.gameplay_state import GameplayState
        from gameplay.states.pause_state import PauseState
        from gameplay.states.game_over_state import GameOverState
        
        # Enregistrement des états
        self.state_manager.register_state(
            GameStateType.MAIN_MENU, 
            MainMenuState(self)
        )
        self.state_manager.register_state(
            GameStateType.GAMEPLAY, 
            GameplayState(self)
        )
        self.state_manager.register_state(
            GameStateType.PAUSE, 
            PauseState(self)
        )
        self.state_manager.register_state(
            GameStateType.GAME_OVER, 
            GameOverState(self)
        )
        
        # État initial
        self.state_manager.change_state(GameStateType.MAIN_MENU)
    
    def _setup_event_handlers(self):
        """Configure les gestionnaires d'événements globaux"""
        
        # Événements de jeu
        self.event_system.subscribe('game_pause', self._on_game_pause)
        self.event_system.subscribe('game_resume', self._on_game_resume)
        self.event_system.subscribe('game_quit', self._on_game_quit)
        self.event_system.subscribe('toggle_debug', self._on_toggle_debug)
        
        # Événements de performance
        self.event_system.subscribe('performance_warning', self._on_performance_warning)
    
    def run(self):
        """Lance la boucle principale du jeu"""
        self.logger.info("Démarrage de la boucle principale")
        
        try:
            arcade.run()
        except KeyboardInterrupt:
            self.logger.info("Interruption clavier détectée")
        except Exception as e:
            self.logger.error(f"Erreur dans la boucle principale: {e}")
            raise
        finally:
            self._cleanup()
    
    def on_update(self, delta_time: float):
        """
        Mise à jour du jeu (appelée chaque frame)
        
        Args:
            delta_time: Temps écoulé depuis la dernière frame
        """
        if not self.is_running:
            return
        
        # Limitation du delta_time pour éviter les gros sauts
        delta_time = min(delta_time, 1.0 / 30.0)  # Max 30 FPS pour la physique
        
        # Mise à jour des métriques de performance
        self._update_performance_metrics(delta_time)
        
        # Pause du jeu
        if self.is_paused:
            delta_time = 0.0
        
        # Mise à jour des systèmes principaux
        self.timer.update(delta_time)
        self.input_manager.update(delta_time)
        self.event_system.process_events()
        
        # Mise à jour de l'état actuel
        current_state = self.state_manager.get_current_state()
        if current_state:
            current_state.update(delta_time)
        
        # Mise à jour de la caméra
        self.camera.update(delta_time)
        
        # Vérification des performances
        self._check_performance()
    
    def on_draw(self):
        """Rendu du jeu (appelée chaque frame)"""
        if not self.is_running:
            return
        
        # Début du rendu
        self.renderer.begin_frame()
        
        try:
            # Rendu de l'état actuel
            current_state = self.state_manager.get_current_state()
            if current_state:
                current_state.render(self.renderer)
            
            # Rendu des éléments de debug
            if self.debug_mode:
                self._render_debug_info()
                
        except Exception as e:
            self.logger.error(f"Erreur de rendu: {e}")
        
        finally:
            # Fin du rendu
            self.renderer.end_frame()
    
    def on_key_press(self, key, modifiers):
        """Gestion des touches pressées"""
        self.input_manager.on_key_press(key, modifiers)
        
        # Raccourcis globaux
        if key == arcade.key.F1:
            self.event_system.emit('toggle_debug')
        elif key == arcade.key.F11:
            self.set_fullscreen(not self.fullscreen)
        elif key == arcade.key.ESCAPE:
            current_state = self.state_manager.get_current_state_type()
            if current_state == GameStateType.GAMEPLAY:
                self.event_system.emit('game_pause')
            elif current_state == GameStateType.PAUSE:
                self.event_system.emit('game_resume')
    
    def on_key_release(self, key, modifiers):
        """Gestion des touches relâchées"""
        self.input_manager.on_key_release(key, modifiers)
    
    def on_mouse_press(self, x, y, button, modifiers):
        """Gestion des clics de souris"""
        # Conversion en coordonnées monde
        world_x, world_y = self.camera.screen_to_world(x, y)
        self.input_manager.on_mouse_press(world_x, world_y, button, modifiers)
    
    def on_mouse_release(self, x, y, button, modifiers):
        """Gestion du relâchement de la souris"""
        world_x, world_y = self.camera.screen_to_world(x, y)
        self.input_manager.on_mouse_release(world_x, world_y, button, modifiers)
    
    def on_mouse_motion(self, x, y, dx, dy):
        """Gestion du mouvement de la souris"""
        world_x, world_y = self.camera.screen_to_world(x, y)
        self.input_manager.on_mouse_motion(world_x, world_y, dx, dy)
    
    def on_resize(self, width, height):
        """Gestion du redimensionnement de la fenêtre"""
        super().on_resize(width, height)
        self.camera.resize(width, height)
        self.renderer.resize(width, height)
        
        self.logger.info(f"Fenêtre redimensionnée: {width}x{height}")
    
    def _update_performance_metrics(self, delta_time: float):
        """Met à jour les métriques de performance"""
        self.frame_count += 1
        self.fps_timer += delta_time
        
        # Calcul du FPS toutes les secondes
        if self.fps_timer >= 1.0:
            self.current_fps = self.frame_count / self.fps_timer
            self.frame_count = 0
            self.fps_timer = 0.0
        
        # Historique des temps de frame
        self.frame_time_history.append(delta_time)
        if len(self.frame_time_history) > 60:  # Garde 1 seconde d'historique
            self.frame_time_history.pop(0)
    
    def _check_performance(self):
        """Vérifie les performances et émet des avertissements si nécessaire"""
        if len(self.frame_time_history) < 30:
            return
        
        # Calcul du temps de frame moyen
        avg_frame_time = sum(self.frame_time_history[-30:]) / 30
        avg_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        # Avertissement si les performances sont dégradées
        if avg_fps < SETTINGS['TARGET_FPS'] * 0.75:  # Moins de 75% du FPS cible
            self.event_system.emit('performance_warning', {
                'fps': avg_fps,
                'target_fps': SETTINGS['TARGET_FPS'],
                'frame_time': avg_frame_time
            })
    
    def _render_debug_info(self):
        """Affiche les informations de debug"""
        if not DEBUG_CONFIG['SHOW_FPS']:
            return
        
        debug_text = [
            f"FPS: {self.current_fps:.1f}",
            f"Frame Time: {self.frame_time_history[-1]*1000:.1f}ms" if self.frame_time_history else "Frame Time: N/A",
            f"State: {self.state_manager.get_current_state_type().name}",
            f"Camera: ({self.camera.x:.1f}, {self.camera.y:.1f})",
        ]
        
        # Ajout d'informations spécifiques à l'état
        current_state = self.state_manager.get_current_state()
        if hasattr(current_state, 'get_debug_info'):
            debug_text.extend(current_state.get_debug_info())
        
        # Rendu du texte de debug
        y_offset = self.height - 30
        for text in debug_text:
            arcade.draw_text(
                text,
                10, y_offset,
                arcade.color.WHITE,
                font_size=14,
                font_name="Courier New"
            )
            y_offset -= 20
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONNAIRES D'ÉVÉNEMENTS
    # ═══════════════════════════════════════════════════════════
    
    def _on_game_pause(self, data=None):
        """Gestionnaire pour la pause du jeu"""
        self.is_paused = True
        self.logger.info("Jeu mis en pause")
    
    def _on_game_resume(self, data=None):
        """Gestionnaire pour la reprise du jeu"""
        self.is_paused = False
        self.logger.info("Jeu repris")
    
    def _on_game_quit(self, data=None):
        """Gestionnaire pour quitter le jeu"""
        self.logger.info("Demande de fermeture du jeu")
        self.is_running = False
        self.close()
    
    def _on_toggle_debug(self, data=None):
        """Gestionnaire pour basculer le mode debug"""
        self.debug_mode = not self.debug_mode
        self.logger.info(f"Mode debug: {'activé' if self.debug_mode else 'désactivé'}")
    
    def _on_performance_warning(self, data):
        """Gestionnaire pour les avertissements de performance"""
        self.logger.warning(
            f"Performance dégradée - FPS: {data['fps']:.1f} "
            f"(cible: {data['target_fps']})"
        )
    
    def _cleanup(self):
        """Nettoyage des ressources avant fermeture"""
        self.logger.info("Nettoyage des ressources...")
        
        try:
            # Nettoyage des systèmes
            if hasattr(self, 'state_manager'):
                self.state_manager.cleanup()
            
            if hasattr(self, 'resource_manager'):
                self.resource_manager.cleanup()
            
            if hasattr(self, 'renderer'):
                self.renderer.cleanup()
                
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage: {e}")
        
        self.logger.info("Nettoyage terminé")
    
    # ═══════════════════════════════════════════════════════════
    # PROPRIÉTÉS ET ACCESSEURS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def current_fps(self) -> float:
        """Retourne le FPS actuel"""
        return self.current_fps
    
    @property
    def game_time(self) -> float:
        """Retourne le temps de jeu total"""
        return self.timer.total_time
    
    def get_resource_manager(self) -> ResourceManager:
        """Retourne le gestionnaire de ressources"""
        return self.resource_manager
    
    def get_event_system(self) -> EventSystem:
        """Retourne le système d'événements"""
        return self.event_system
    
    def get_camera(self) -> Camera2D:
        """Retourne la caméra"""
        return self.camera
    
    def get_renderer(self) -> Renderer:
        """Retourne le renderer"""
        return self.renderer