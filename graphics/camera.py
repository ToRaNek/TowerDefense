# graphics/camera.py
"""
Steam Defense - Système de caméra 2D
Gère la vue, le zoom, le suivi et les effets de caméra pour le jeu
"""

import arcade
import math
import logging
from typing import Tuple, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from config.settings import SETTINGS, GRID_CONFIG


class CameraMode(Enum):
    """Modes de fonctionnement de la caméra"""
    FREE = "free"           # Caméra libre
    FOLLOW = "follow"       # Suit une cible
    FIXED = "fixed"         # Position fixe
    CINEMATIC = "cinematic" # Mode cinématique


@dataclass
class CameraBounds:
    """Limites de la caméra"""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    def clamp_position(self, x: float, y: float) -> Tuple[float, float]:
        """Contraint une position dans les limites"""
        clamped_x = max(self.min_x, min(self.max_x, x))
        clamped_y = max(self.min_y, min(self.max_y, y))
        return clamped_x, clamped_y


class Camera2D:
    """
    Caméra 2D avancée pour Steam Defense
    Gère le zoom, le suivi, les effets et les transitions
    """
    
    def __init__(self, viewport_width: int, viewport_height: int):
        """
        Initialise la caméra
        
        Args:
            viewport_width: Largeur de la zone d'affichage
            viewport_height: Hauteur de la zone d'affichage
        """
        self.logger = logging.getLogger('Camera2D')
        
        # Dimensions de base
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        
        # Position et transformation
        self.x = 0.0
        self.y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        
        # Zoom
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 3.0
        
        # Rotation
        self.angle = 0.0
        self.target_angle = 0.0
        
        # Mode et comportement
        self.mode = CameraMode.FREE
        self.follow_target: Optional[Any] = None
        self.follow_speed = 5.0
        self.follow_offset_x = 0.0
        self.follow_offset_y = 0.0
        
        # Limites de mouvement
        self.bounds: Optional[CameraBounds] = None
        self.enable_bounds = False
        
        # Effets visuels
        self.shake_intensity = 0.0
        self.shake_duration = 0.0
        self.shake_timer = 0.0
        self.shake_frequency = 60.0
        
        # Animation et transitions
        self.transition_speed = 3.0
        self.zoom_speed = 2.0
        self.rotation_speed = 180.0  # degrés par seconde
        
        # Caméra Arcade native (utilisation de SimpleCamera)
        try:
            # Essaie d'utiliser la nouvelle API Camera2D si disponible
            if hasattr(arcade, 'camera') and hasattr(arcade.camera, 'Camera2D'):
                self.arcade_camera = arcade.camera.Camera2D()
            elif hasattr(arcade, 'Camera2D'):
                self.arcade_camera = arcade.Camera2D()
            else:
                # Fallback: pas de caméra Arcade native
                self.arcade_camera = None
                self.logger.warning("Caméra Arcade native non disponible, utilisation du système manuel")
        except Exception as e:
            self.logger.warning(f"Impossible d'initialiser la caméra Arcade: {e}")
            self.arcade_camera = None
        
        # Historique pour effets
        self.position_history = []
        self.max_history_length = 10
        
        # Configuration pour le tower defense
        self.edge_scroll_enabled = True
        self.edge_scroll_margin = 50  # pixels
        self.edge_scroll_speed = 200.0  # pixels/sec
        
        self.logger.info(f"Caméra 2D initialisée: {viewport_width}x{viewport_height}")
    
    def update(self, delta_time: float):
        """Met à jour la caméra"""
        # Mise à jour du suivi de cible
        if self.mode == CameraMode.FOLLOW and self.follow_target:
            self._update_follow_mode(delta_time)
        
        # Animation vers la position cible
        self._animate_position(delta_time)
        
        # Animation du zoom
        self._animate_zoom(delta_time)
        
        # Animation de la rotation
        self._animate_rotation(delta_time)
        
        # Effets de secousse
        self._update_shake(delta_time)
        
        # Application des limites
        if self.enable_bounds and self.bounds:
            self.x, self.y = self.bounds.clamp_position(self.x, self.y)
        
        # Mise à jour de l'historique
        self._update_position_history()
        
        # Synchronisation avec la caméra Arcade
        self._sync_arcade_camera()
    
    def _update_follow_mode(self, delta_time: float):
        """Met à jour le mode de suivi"""
        if not self.follow_target:
            return
        
        # Récupération de la position de la cible
        if hasattr(self.follow_target, 'get_position'):
            target_x, target_y = self.follow_target.get_position()
        elif hasattr(self.follow_target, 'center_x') and hasattr(self.follow_target, 'center_y'):
            target_x, target_y = self.follow_target.center_x, self.follow_target.center_y
        elif hasattr(self.follow_target, 'x') and hasattr(self.follow_target, 'y'):
            target_x, target_y = self.follow_target.x, self.follow_target.y
        else:
            self.logger.warning("Cible de suivi sans position valide")
            return
        
        # Application de l'offset
        target_x += self.follow_offset_x
        target_y += self.follow_offset_y
        
        # Mise à jour de la position cible avec interpolation
        self.target_x = target_x
        self.target_y = target_y
    
    def _animate_position(self, delta_time: float):
        """Anime la position vers la cible"""
        if self.mode == CameraMode.FIXED:
            return
        
        # Interpolation exponentielle pour un mouvement fluide
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        
        self.x += dx * self.transition_speed * delta_time
        self.y += dy * self.transition_speed * delta_time
    
    def _animate_zoom(self, delta_time: float):
        """Anime le zoom vers la cible"""
        zoom_diff = self.target_zoom - self.zoom
        self.zoom += zoom_diff * self.zoom_speed * delta_time
        
        # Contrainte du zoom
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom))
    
    def _animate_rotation(self, delta_time: float):
        """Anime la rotation vers la cible"""
        angle_diff = self.target_angle - self.angle
        
        # Normalisation de l'angle (-180° à 180°)
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360
        
        rotation_step = self.rotation_speed * delta_time
        if abs(angle_diff) < rotation_step:
            self.angle = self.target_angle
        else:
            self.angle += math.copysign(rotation_step, angle_diff)
    
    def _update_shake(self, delta_time: float):
        """Met à jour l'effet de secousse"""
        if self.shake_duration <= 0:
            self.shake_intensity = 0.0
            return
        
        self.shake_timer += delta_time
        self.shake_duration -= delta_time
        
        if self.shake_duration <= 0:
            self.shake_intensity = 0.0
            self.shake_timer = 0.0
    
    def _update_position_history(self):
        """Met à jour l'historique des positions"""
        self.position_history.append((self.x, self.y))
        
        if len(self.position_history) > self.max_history_length:
            self.position_history.pop(0)
    
    def _sync_arcade_camera(self):
        """Synchronise avec la caméra Arcade native"""
        if not self.arcade_camera:
            return
            
        # Position avec effet de secousse
        final_x = self.x
        final_y = self.y
        
        if self.shake_intensity > 0 and self.shake_duration > 0:
            shake_x = math.sin(self.shake_timer * self.shake_frequency) * self.shake_intensity
            shake_y = math.cos(self.shake_timer * self.shake_frequency * 1.3) * self.shake_intensity
            final_x += shake_x
            final_y += shake_y
        
        # Application à la caméra Arcade selon l'API disponible
        try:
            if hasattr(self.arcade_camera, 'position'):
                self.arcade_camera.position = (final_x, final_y)
            elif hasattr(self.arcade_camera, 'move_to'):
                self.arcade_camera.move_to((final_x, final_y))
        except Exception as e:
            self.logger.debug(f"Erreur lors de la synchronisation de la caméra: {e}")
    
    def use(self):
        """Active cette caméra pour le rendu"""
        if self.arcade_camera and hasattr(self.arcade_camera, 'use'):
            self.arcade_camera.use()
        else:
            # Transformation manuelle si pas de caméra Arcade
            self.apply_manual_transform()
    
    def apply_manual_transform(self):
        """Applique une transformation manuelle pour simuler la caméra"""
        # Position avec effet de secousse
        final_x = self.x
        final_y = self.y
        
        if self.shake_intensity > 0 and self.shake_duration > 0:
            shake_x = math.sin(self.shake_timer * self.shake_frequency) * self.shake_intensity
            shake_y = math.cos(self.shake_timer * self.shake_frequency * 1.3) * self.shake_intensity
            final_x += shake_x
            final_y += shake_y
        
        # Application de la transformation
        arcade.set_viewport(
            final_x - self.viewport_width / (2 * self.zoom),
            final_x + self.viewport_width / (2 * self.zoom),
            final_y - self.viewport_height / (2 * self.zoom),
            final_y + self.viewport_height / (2 * self.zoom)
        )
    
    def set_position(self, x: float, y: float, immediate: bool = False):
        """
        Définit la position de la caméra
        
        Args:
            x, y: Nouvelle position
            immediate: Si True, déplace immédiatement sans animation
        """
        if immediate:
            self.x = x
            self.y = y
        
        self.target_x = x
        self.target_y = y
        
        self.logger.debug(f"Position caméra: ({x}, {y}) immediate={immediate}")
    
    def get_position(self) -> Tuple[float, float]:
        """Retourne la position actuelle de la caméra"""
        return self.x, self.y
    
    def move(self, dx: float, dy: float):
        """Déplace la caméra relativement"""
        self.set_position(self.target_x + dx, self.target_y + dy)
    
    def set_zoom(self, zoom: float, immediate: bool = False):
        """
        Définit le niveau de zoom
        
        Args:
            zoom: Niveau de zoom (1.0 = normal)
            immediate: Si True, applique immédiatement
        """
        zoom = max(self.min_zoom, min(self.max_zoom, zoom))
        
        if immediate:
            self.zoom = zoom
        
        self.target_zoom = zoom
        self.logger.debug(f"Zoom caméra: {zoom} immediate={immediate}")
    
    def zoom_in(self, factor: float = 1.2):
        """Zoom avant"""
        self.set_zoom(self.target_zoom * factor)
    
    def zoom_out(self, factor: float = 1.2):
        """Zoom arrière"""
        self.set_zoom(self.target_zoom / factor)
    
    def set_rotation(self, angle: float, immediate: bool = False):
        """
        Définit la rotation de la caméra
        
        Args:
            angle: Angle en degrés
            immediate: Si True, applique immédiatement
        """
        if immediate:
            self.angle = angle
        
        self.target_angle = angle
        self.logger.debug(f"Rotation caméra: {angle}° immediate={immediate}")
    
    def rotate(self, delta_angle: float):
        """Fait tourner la caméra relativement"""
        self.set_rotation(self.target_angle + delta_angle)
    
    def set_mode(self, mode: CameraMode):
        """Change le mode de la caméra"""
        old_mode = self.mode
        self.mode = mode
        
        if mode != CameraMode.FOLLOW:
            self.follow_target = None
        
        self.logger.debug(f"Mode caméra: {old_mode.value} -> {mode.value}")
    
    def follow_target(self, target: Any, offset_x: float = 0.0, offset_y: float = 0.0):
        """
        Configure le suivi d'une cible
        
        Args:
            target: Objet à suivre (doit avoir une position)
            offset_x, offset_y: Décalage par rapport à la cible
        """
        self.mode = CameraMode.FOLLOW
        self.follow_target = target
        self.follow_offset_x = offset_x
        self.follow_offset_y = offset_y
        
        self.logger.debug(f"Suivi de cible configuré avec offset ({offset_x}, {offset_y})")
    
    def stop_following(self):
        """Arrête le suivi de cible"""
        self.mode = CameraMode.FREE
        self.follow_target = None
    
    def set_bounds(self, min_x: float, min_y: float, max_x: float, max_y: float, enable: bool = True):
        """
        Définit les limites de mouvement de la caméra
        
        Args:
            min_x, min_y: Limites minimales
            max_x, max_y: Limites maximales
            enable: Active ou désactive les limites
        """
        self.bounds = CameraBounds(min_x, min_y, max_x, max_y)
        self.enable_bounds = enable
        
        self.logger.debug(f"Limites caméra: ({min_x}, {min_y}) - ({max_x}, {max_y}) enabled={enable}")
    
    def shake(self, intensity: float, duration: float, frequency: float = 60.0):
        """
        Déclenche un effet de secousse
        
        Args:
            intensity: Intensité de la secousse en pixels
            duration: Durée en secondes
            frequency: Fréquence des oscillations
        """
        self.shake_intensity = intensity
        self.shake_duration = duration
        self.shake_frequency = frequency
        self.shake_timer = 0.0
        
        self.logger.debug(f"Secousse caméra: intensité={intensity}, durée={duration}s")
    
    def resize(self, new_width: int, new_height: int):
        """
        Redimensionne la caméra
        
        Args:
            new_width, new_height: Nouvelles dimensions
        """
        self.viewport_width = new_width
        self.viewport_height = new_height
        
        if self.arcade_camera and hasattr(self.arcade_camera, 'resize'):
            try:
                self.arcade_camera.resize(new_width, new_height)
            except Exception as e:
                self.logger.debug(f"Erreur lors du redimensionnement de la caméra Arcade: {e}")
        
        self.logger.info(f"Caméra redimensionnée: {new_width}x{new_height}")
    
    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """
        Convertit des coordonnées écran en coordonnées monde
        
        Args:
            screen_x, screen_y: Position écran
            
        Returns:
            Position dans le monde
        """
        # Calcul avec la transformation de la caméra
        world_x = (screen_x - self.viewport_width / 2) / self.zoom + self.x
        world_y = (screen_y - self.viewport_height / 2) / self.zoom + self.y
        
        return world_x, world_y
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Convertit des coordonnées monde en coordonnées écran
        
        Args:
            world_x, world_y: Position monde
            
        Returns:
            Position écran
        """
        screen_x = (world_x - self.x) * self.zoom + self.viewport_width / 2
        screen_y = (world_y - self.y) * self.zoom + self.viewport_height / 2
        
        return screen_x, screen_y
    
    def get_viewport_bounds(self) -> Tuple[float, float, float, float]:
        """
        Retourne les limites de la vue actuelle
        
        Returns:
            (left, bottom, right, top) en coordonnées monde
        """
        half_width = (self.viewport_width / 2) / self.zoom
        half_height = (self.viewport_height / 2) / self.zoom
        
        left = self.x - half_width
        right = self.x + half_width
        bottom = self.y - half_height
        top = self.y + half_height
        
        return left, bottom, right, top
    
    def is_point_visible(self, x: float, y: float, margin: float = 0.0) -> bool:
        """
        Vérifie si un point est visible par la caméra
        
        Args:
            x, y: Position à tester
            margin: Marge supplémentaire
            
        Returns:
            True si le point est visible
        """
        left, bottom, right, top = self.get_viewport_bounds()
        
        return (left - margin <= x <= right + margin and
                bottom - margin <= y <= top + margin)
    
    def center_on_grid(self):
        """Centre la caméra sur le centre de la grille de jeu"""
        grid_center_x = (GRID_CONFIG['GRID_WIDTH'] * GRID_CONFIG['TILE_SIZE']) / 2
        grid_center_y = (GRID_CONFIG['GRID_HEIGHT'] * GRID_CONFIG['TILE_SIZE']) / 2
        
        self.set_position(grid_center_x, grid_center_y, immediate=True)
        self.logger.debug(f"Caméra centrée sur la grille: ({grid_center_x}, {grid_center_y})")
    
    def fit_to_grid(self, margin: float = 1.1):
        """
        Ajuste le zoom pour afficher toute la grille
        
        Args:
            margin: Marge supplémentaire (1.1 = 10% de marge)
        """
        grid_width = GRID_CONFIG['GRID_WIDTH'] * GRID_CONFIG['TILE_SIZE']
        grid_height = GRID_CONFIG['GRID_HEIGHT'] * GRID_CONFIG['TILE_SIZE']
        
        # Calcul du zoom nécessaire pour afficher toute la grille
        zoom_x = self.viewport_width / (grid_width * margin)
        zoom_y = self.viewport_height / (grid_height * margin)
        
        # Utilisation du plus petit zoom pour tout afficher
        optimal_zoom = min(zoom_x, zoom_y)
        optimal_zoom = max(self.min_zoom, min(self.max_zoom, optimal_zoom))
        
        self.set_zoom(optimal_zoom, immediate=True)
        self.center_on_grid()
        
        self.logger.debug(f"Caméra ajustée à la grille: zoom={optimal_zoom}")
    
    def handle_edge_scrolling(self, mouse_x: float, mouse_y: float, delta_time: float):
        """
        Gère le défilement par les bords de l'écran
        
        Args:
            mouse_x, mouse_y: Position de la souris
            delta_time: Temps écoulé
        """
        if not self.edge_scroll_enabled or self.mode == CameraMode.FOLLOW:
            return
        
        # Vérification des bords
        scroll_x = 0.0
        scroll_y = 0.0
        
        if mouse_x < self.edge_scroll_margin:
            scroll_x = -self.edge_scroll_speed * delta_time
        elif mouse_x > self.viewport_width - self.edge_scroll_margin:
            scroll_x = self.edge_scroll_speed * delta_time
        
        if mouse_y < self.edge_scroll_margin:
            scroll_y = -self.edge_scroll_speed * delta_time
        elif mouse_y > self.viewport_height - self.edge_scroll_margin:
            scroll_y = self.edge_scroll_speed * delta_time
        
        if scroll_x != 0.0 or scroll_y != 0.0:
            self.move(scroll_x, scroll_y)
    
    def smooth_transition_to(self, target_x: float, target_y: float, target_zoom: float = None,
                           duration: float = 1.0):
        """
        Transition fluide vers une position et zoom
        
        Args:
            target_x, target_y: Position cible
            target_zoom: Zoom cible (optionnel)
            duration: Durée de la transition
        """
        # Ajustement de la vitesse selon la durée
        self.transition_speed = 1.0 / duration if duration > 0 else 3.0
        
        self.set_position(target_x, target_y)
        
        if target_zoom is not None:
            self.zoom_speed = 1.0 / duration if duration > 0 else 2.0
            self.set_zoom(target_zoom)
        
        self.logger.debug(f"Transition vers ({target_x}, {target_y}), zoom={target_zoom}, durée={duration}s")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la caméra"""
        return {
            'position': (self.x, self.y),
            'target_position': (self.target_x, self.target_y),
            'zoom': self.zoom,
            'target_zoom': self.target_zoom,
            'angle': self.angle,
            'mode': self.mode.value,
            'has_follow_target': self.follow_target is not None,
            'bounds_enabled': self.enable_bounds,
            'shake_active': self.shake_duration > 0,
            'viewport_size': (self.viewport_width, self.viewport_height),
            'viewport_bounds': self.get_viewport_bounds()
        }
    
    def reset(self):
        """Remet la caméra à l'état initial"""
        self.set_position(0, 0, immediate=True)
        self.set_zoom(1.0, immediate=True)
        self.set_rotation(0.0, immediate=True)
        self.set_mode(CameraMode.FREE)
        self.shake_intensity = 0.0
        self.shake_duration = 0.0
        
        self.logger.debug("Caméra remise à zéro")