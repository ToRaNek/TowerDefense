# graphics/renderer.py
"""
Steam Defense - Système de rendu principal
Gère le rendu optimisé pour le jeu 2D avec effets steampunk
"""

import arcade
import math
import logging
from typing import List, Dict, Tuple, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass
import time

from config.settings import SteampunkColors, SETTINGS, VISUAL_EFFECTS, PERFORMANCE
from graphics.camera import Camera2D


class RenderLayer(Enum):
    """Couches de rendu pour l'organisation Z-order"""
    BACKGROUND = 0
    TERRAIN = 100
    DECORATIONS = 200
    PATHS = 300
    TOWERS = 400
    ENEMIES = 500
    PROJECTILES = 600
    EFFECTS = 700
    UI_BACKGROUND = 800
    UI_ELEMENTS = 900
    UI_OVERLAY = 1000
    DEBUG = 1100


class BlendMode(Enum):
    """Modes de mélange pour les effets visuels"""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"


@dataclass
class RenderBatch:
    """Lot de rendu pour optimiser les appels de dessin"""
    layer: RenderLayer
    blend_mode: BlendMode
    textures: List[arcade.Texture]
    positions: List[Tuple[float, float]]
    scales: List[float]
    rotations: List[float]
    colors: List[Tuple[int, int, int, int]]
    
    def add_sprite(self, texture: arcade.Texture, position: Tuple[float, float], 
                  scale: float = 1.0, rotation: float = 0.0, 
                  color: Tuple[int, int, int, int] = (255, 255, 255, 255)):
        """Ajoute un sprite au lot"""
        self.textures.append(texture)
        self.positions.append(position)
        self.scales.append(scale)
        self.rotations.append(rotation)
        self.colors.append(color)
    
    def is_empty(self) -> bool:
        """Vérifie si le lot est vide"""
        return len(self.textures) == 0
    
    def clear(self):
        """Vide le lot"""
        self.textures.clear()
        self.positions.clear()
        self.scales.clear()
        self.rotations.clear()
        self.colors.clear()


@dataclass
class ParticleEffect:
    """Effet de particules"""
    name: str
    position: Tuple[float, float]
    particles: List[Dict[str, Any]]
    lifetime: float
    max_lifetime: float
    auto_cleanup: bool = True
    
    def update(self, delta_time: float):
        """Met à jour l'effet"""
        self.lifetime -= delta_time
        
        # Mise à jour des particules
        for particle in self.particles[:]:
            particle['life'] -= delta_time
            particle['x'] += particle['vel_x'] * delta_time
            particle['y'] += particle['vel_y'] * delta_time
            particle['vel_y'] += particle.get('gravity', 0) * delta_time
            particle['alpha'] *= particle.get('fade_rate', 0.98)
            
            if particle['life'] <= 0 or particle['alpha'] < 10:
                self.particles.remove(particle)
    
    def is_expired(self) -> bool:
        """Vérifie si l'effet est expiré"""
        return self.lifetime <= 0 and (not self.particles or self.auto_cleanup)


class Renderer:
    """
    Système de rendu principal pour Steam Defense
    Gère le rendu optimisé avec batching et effets visuels
    """
    
    def __init__(self, camera: Camera2D):
        self.camera = camera
        self.logger = logging.getLogger('Renderer')
        
        # Configuration de rendu
        self.background_color = SETTINGS['BACKGROUND_COLOR']
        self.enable_batching = True
        self.enable_culling = True
        self.enable_effects = True
        
        # Lots de rendu par couche
        self.render_batches: Dict[RenderLayer, List[RenderBatch]] = {}
        self.current_batch: Optional[RenderBatch] = None
        
        # Effets visuels
        self.particle_effects: List[ParticleEffect] = []
        self.lighting_enabled = True
        self.ambient_light = (50, 50, 50)  # Lumière ambiante sombre pour steampunk
        
        # Cache de textures pour optimisation
        self.texture_cache: Dict[str, arcade.Texture] = {}
        
        # Statistiques de rendu
        self.stats = {
            'frames_rendered': 0,
            'draw_calls': 0,
            'sprites_rendered': 0,
            'particles_rendered': 0,
            'culled_objects': 0,
            'batches_created': 0,
            'last_frame_time': 0.0
        }
        
        # Zone de rendu (culling)
        self.render_bounds = (0, 0, SETTINGS['SCREEN_WIDTH'], SETTINGS['SCREEN_HEIGHT'])
        self.culling_margin = PERFORMANCE['CULLING_MARGIN']
        
        # Initialisation d'OpenGL
        self._setup_opengl()
        
        self.logger.info("Renderer initialisé")
    
    def _setup_opengl(self):
        """Configure les paramètres OpenGL"""
        # Activation de l'alpha blending
        arcade.enable_blending()
        
        # Configuration de l'antialiasing si supporté
        if SETTINGS.get('ANTIALIASING', False):
            try:
                arcade.enable_smooth_textures()
                self.logger.debug("Antialiasing activé")
            except:
                self.logger.warning("Antialiasing non supporté")
    
    def begin_frame(self):
        """Démarre un nouveau frame de rendu"""
        frame_start_time = time.time()
        
        # Effacement de l'écran
        arcade.start_render()
        
        # Mise à jour de la caméra
        self.camera.use()
        
        # Mise à jour des limites de rendu pour le culling
        self._update_render_bounds()
        
        # Nettoyage des lots de rendu précédents
        self._clear_render_batches()
        
        # Réinitialisation des statistiques de frame
        self.stats['draw_calls'] = 0
        self.stats['sprites_rendered'] = 0
        self.stats['particles_rendered'] = 0
        self.stats['culled_objects'] = 0
        self.stats['batches_created'] = 0
        
        self.stats['last_frame_time'] = frame_start_time
    
    def end_frame(self):
        """Finalise le rendu du frame"""
        # Rendu de tous les lots par ordre de couche
        self._render_all_batches()
        
        # Rendu des effets de particules
        self._render_particle_effects()
        
        # Finalisation
        arcade.finish_render()
        
        # Mise à jour des statistiques
        self.stats['frames_rendered'] += 1
        frame_time = time.time() - self.stats['last_frame_time']
        self.stats['last_frame_time'] = frame_time
    
    def _update_render_bounds(self):
        """Met à jour les limites de rendu pour le culling"""
        camera_bounds = self.camera.get_viewport_bounds()
        
        self.render_bounds = (
            camera_bounds[0] - self.culling_margin,
            camera_bounds[1] - self.culling_margin,
            camera_bounds[2] + self.culling_margin,
            camera_bounds[3] + self.culling_margin
        )
    
    def _clear_render_batches(self):
        """Vide tous les lots de rendu"""
        for layer in RenderLayer:
            if layer not in self.render_batches:
                self.render_batches[layer] = []
            
            for batch in self.render_batches[layer]:
                batch.clear()
            
            self.render_batches[layer].clear()
    
    def _is_in_render_bounds(self, x: float, y: float, width: float = 0, height: float = 0) -> bool:
        """Vérifie si un objet est dans les limites de rendu"""
        if not self.enable_culling:
            return True
        
        left, bottom, right, top = self.render_bounds
        
        return not (x + width < left or x - width > right or 
                   y + height < bottom or y - height > top)
    
    def draw_sprite(self, texture: arcade.Texture, position: Tuple[float, float],
                   layer: RenderLayer = RenderLayer.ENEMIES, scale: float = 1.0,
                   rotation: float = 0.0, color: Tuple[int, int, int, int] = (255, 255, 255, 255),
                   blend_mode: BlendMode = BlendMode.NORMAL):
        """
        Dessine un sprite sur une couche donnée
        
        Args:
            texture: Texture à dessiner
            position: Position (x, y)
            layer: Couche de rendu
            scale: Échelle
            rotation: Rotation en degrés
            color: Couleur (R, G, B, A)
            blend_mode: Mode de mélange
        """
        x, y = position
        
        # Culling
        sprite_size = max(texture.width, texture.height) * scale
        if not self._is_in_render_bounds(x, y, sprite_size, sprite_size):
            self.stats['culled_objects'] += 1
            return
        
        # Recherche ou création d'un lot compatible
        batch = self._get_or_create_batch(layer, blend_mode)
        
        # Ajout du sprite au lot
        batch.add_sprite(texture, position, scale, rotation, color)
        
        self.stats['sprites_rendered'] += 1
    
    def _get_or_create_batch(self, layer: RenderLayer, blend_mode: BlendMode) -> RenderBatch:
        """Récupère ou crée un lot de rendu compatible"""
        if layer not in self.render_batches:
            self.render_batches[layer] = []
        
        # Recherche d'un lot existant compatible
        for batch in self.render_batches[layer]:
            if batch.blend_mode == blend_mode and len(batch.textures) < 1000:  # Limite de lot
                return batch
        
        # Création d'un nouveau lot
        new_batch = RenderBatch(
            layer=layer,
            blend_mode=blend_mode,
            textures=[],
            positions=[],
            scales=[],
            rotations=[],
            colors=[]
        )
        
        self.render_batches[layer].append(new_batch)
        self.stats['batches_created'] += 1
        
        return new_batch
    
    def _render_all_batches(self):
        """Rend tous les lots par ordre de couche"""
        # Tri des couches par valeur Z
        sorted_layers = sorted(RenderLayer, key=lambda layer: layer.value)
        
        for layer in sorted_layers:
            if layer in self.render_batches:
                for batch in self.render_batches[layer]:
                    if not batch.is_empty():
                        self._render_batch(batch)
    
    def _render_batch(self, batch: RenderBatch):
        """Rend un lot de sprites"""
        if batch.is_empty():
            return
        
        # Configuration du mode de mélange
        self._set_blend_mode(batch.blend_mode)
        
        # Rendu optimisé par texture groupée
        if self.enable_batching and len(batch.textures) > 1:
            self._render_batch_optimized(batch)
        else:
            self._render_batch_individual(batch)
        
        self.stats['draw_calls'] += 1
    
    def _render_batch_optimized(self, batch: RenderBatch):
        """Rendu optimisé d'un lot (groupage par texture)"""
        # Groupage par texture pour minimiser les changements d'état
        texture_groups: Dict[arcade.Texture, List[int]] = {}
        
        for i, texture in enumerate(batch.textures):
            if texture not in texture_groups:
                texture_groups[texture] = []
            texture_groups[texture].append(i)
        
        # Rendu par groupe de texture
        for texture, indices in texture_groups.items():
            sprite_list = arcade.SpriteList()
            
            for i in indices:
                sprite = arcade.Sprite()
                sprite.texture = texture
                sprite.center_x, sprite.center_y = batch.positions[i]
                sprite.scale = batch.scales[i]
                sprite.angle = batch.rotations[i]
                sprite.color = batch.colors[i][:3]  # RGB seulement
                sprite.alpha = batch.colors[i][3]
                
                sprite_list.append(sprite)
            
            sprite_list.draw()
    
    def _render_batch_individual(self, batch: RenderBatch):
        """Rendu individuel d'un lot"""
        for i in range(len(batch.textures)):
            texture = batch.textures[i]
            x, y = batch.positions[i]
            scale = batch.scales[i]
            rotation = batch.rotations[i]
            color = batch.colors[i]
            
            # Application de la couleur si différente de blanc
            if color != (255, 255, 255, 255):
                arcade.draw_scaled_texture_rectangle(
                    x, y, texture.width * scale, texture.height * scale,
                    texture, rotation, alpha=color[3]
                )
            else:
                arcade.draw_scaled_texture_rectangle(
                    x, y, texture.width * scale, texture.height * scale,
                    texture, rotation
                )
    
    def _set_blend_mode(self, blend_mode: BlendMode):
        """Configure le mode de mélange OpenGL"""
        # Implémentation simplifiée - Arcade gère déjà le blending de base
        # Dans une vraie implémentation, on utiliserait glBlendFunc directement
        pass
    
    def draw_rectangle_filled(self, center_x: float, center_y: float, width: float, height: float,
                             color: Tuple[int, int, int, int], layer: RenderLayer = RenderLayer.UI_ELEMENTS):
        """Dessine un rectangle rempli"""
        if not self._is_in_render_bounds(center_x, center_y, width, height):
            self.stats['culled_objects'] += 1
            return
        
        # Pour les formes simples, on dessine directement
        arcade.draw_rectangle_filled(center_x, center_y, width, height, color)
        self.stats['draw_calls'] += 1
    
    def draw_circle_filled(self, center_x: float, center_y: float, radius: float,
                          color: Tuple[int, int, int, int], layer: RenderLayer = RenderLayer.UI_ELEMENTS):
        """Dessine un cercle rempli"""
        if not self._is_in_render_bounds(center_x, center_y, radius * 2, radius * 2):
            self.stats['culled_objects'] += 1
            return
        
        arcade.draw_circle_filled(center_x, center_y, radius, color)
        self.stats['draw_calls'] += 1
    
    def draw_line(self, start_x: float, start_y: float, end_x: float, end_y: float,
                 color: Tuple[int, int, int, int], line_width: float = 1.0,
                 layer: RenderLayer = RenderLayer.UI_ELEMENTS):
        """Dessine une ligne"""
        # Culling simple pour les lignes
        bounds_x = [start_x, end_x]
        bounds_y = [start_y, end_y]
        if not self._is_in_render_bounds(
            (min(bounds_x) + max(bounds_x)) / 2,
            (min(bounds_y) + max(bounds_y)) / 2,
            abs(max(bounds_x) - min(bounds_x)),
            abs(max(bounds_y) - min(bounds_y))
        ):
            self.stats['culled_objects'] += 1
            return
        
        arcade.draw_line(start_x, start_y, end_x, end_y, color, line_width)
        self.stats['draw_calls'] += 1
    
    def draw_text(self, text: str, x: float, y: float, color: Tuple[int, int, int, int],
                 font_size: int = 12, font_name: str = "Arial", bold: bool = False,
                 layer: RenderLayer = RenderLayer.UI_ELEMENTS):
        """Dessine du texte"""
        # Le texte est généralement toujours visible (UI)
        arcade.draw_text(text, x, y, color, font_size, font_name=font_name, bold=bold)
        self.stats['draw_calls'] += 1
    
    # ═══════════════════════════════════════════════════════════
    # EFFETS VISUELS STEAMPUNK
    # ═══════════════════════════════════════════════════════════
    
    def create_steam_effect(self, position: Tuple[float, float], intensity: float = 1.0,
                           duration: float = 3.0) -> ParticleEffect:
        """Crée un effet de vapeur steampunk"""
        particles = []
        num_particles = int(20 * intensity)
        
        for _ in range(num_particles):
            particle = {
                'x': position[0] + random.uniform(-10, 10),
                'y': position[1] + random.uniform(-10, 10),
                'vel_x': random.uniform(-20, 20),
                'vel_y': random.uniform(30, 60),
                'size': random.uniform(3, 8) * intensity,
                'life': random.uniform(1.0, 2.5),
                'alpha': random.uniform(150, 255),
                'fade_rate': 0.96,
                'gravity': 0
            }
            particles.append(particle)
        
        effect = ParticleEffect(
            name="steam",
            position=position,
            particles=particles,
            lifetime=duration,
            max_lifetime=duration
        )
        
        self.particle_effects.append(effect)
        return effect
    
    def create_explosion_effect(self, position: Tuple[float, float], size: float = 1.0,
                               color: Tuple[int, int, int] = SteampunkColors.FIRE_ORANGE) -> ParticleEffect:
        """Crée un effet d'explosion"""
        particles = []
        num_particles = int(30 * size)
        
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150) * size
            
            particle = {
                'x': position[0],
                'y': position[1],
                'vel_x': math.cos(angle) * speed,
                'vel_y': math.sin(angle) * speed,
                'size': random.uniform(2, 6) * size,
                'life': random.uniform(0.5, 1.5),
                'alpha': 255,
                'fade_rate': 0.92,
                'gravity': -100,
                'color': color
            }
            particles.append(particle)
        
        effect = ParticleEffect(
            name="explosion",
            position=position,
            particles=particles,
            lifetime=2.0,
            max_lifetime=2.0
        )
        
        self.particle_effects.append(effect)
        return effect
    
    def create_electric_arc_effect(self, start: Tuple[float, float], end: Tuple[float, float],
                                  intensity: float = 1.0) -> ParticleEffect:
        """Crée un effet d'arc électrique"""
        particles = []
        
        # Points de l'arc principal
        num_segments = 8
        for i in range(num_segments + 1):
            t = i / num_segments
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            
            # Zigzag aléatoire
            offset_x = random.uniform(-10, 10) * intensity
            offset_y = random.uniform(-10, 10) * intensity
            
            particle = {
                'x': x + offset_x,
                'y': y + offset_y,
                'vel_x': 0,
                'vel_y': 0,
                'size': random.uniform(2, 4),
                'life': 0.3,
                'alpha': 255,
                'fade_rate': 0.85,
                'gravity': 0,
                'color': SteampunkColors.ELECTRIC_BLUE
            }
            particles.append(particle)
        
        # Étincelles secondaires
        for _ in range(int(10 * intensity)):
            mid_x = (start[0] + end[0]) / 2 + random.uniform(-20, 20)
            mid_y = (start[1] + end[1]) / 2 + random.uniform(-20, 20)
            
            particle = {
                'x': mid_x,
                'y': mid_y,
                'vel_x': random.uniform(-50, 50),
                'vel_y': random.uniform(-50, 50),
                'size': random.uniform(1, 3),
                'life': random.uniform(0.2, 0.6),
                'alpha': 200,
                'fade_rate': 0.9,
                'gravity': 0,
                'color': SteampunkColors.ELECTRIC_BLUE
            }
            particles.append(particle)
        
        effect = ParticleEffect(
            name="electric_arc",
            position=((start[0] + end[0]) / 2, (start[1] + end[1]) / 2),
            particles=particles,
            lifetime=0.5,
            max_lifetime=0.5
        )
        
        self.particle_effects.append(effect)
        return effect
    
    def create_gear_rotation_effect(self, position: Tuple[float, float], radius: float = 20.0):
        """Crée un effet d'engrenage qui tourne avec des particules métalliques"""
        particles = []
        num_particles = 8
        
        for i in range(num_particles):
            angle = (i / num_particles) * 2 * math.pi
            x = position[0] + math.cos(angle) * radius
            y = position[1] + math.sin(angle) * radius
            
            particle = {
                'x': x,
                'y': y,
                'vel_x': math.cos(angle + math.pi/2) * 20,  # Rotation
                'vel_y': math.sin(angle + math.pi/2) * 20,
                'size': 2,
                'life': 2.0,
                'alpha': 180,
                'fade_rate': 0.995,
                'gravity': 0,
                'color': SteampunkColors.BRASS
            }
            particles.append(particle)
        
        effect = ParticleEffect(
            name="gear_sparks",
            position=position,
            particles=particles,
            lifetime=2.0,
            max_lifetime=2.0
        )
        
        self.particle_effects.append(effect)
        return effect
    
    def update_particle_effects(self, delta_time: float):
        """Met à jour tous les effets de particules"""
        for effect in self.particle_effects[:]:
            effect.update(delta_time)
            
            if effect.is_expired():
                self.particle_effects.remove(effect)
    
    def _render_particle_effects(self):
        """Rend tous les effets de particules"""
        if not self.enable_effects:
            return
        
        for effect in self.particle_effects:
            self._render_particle_effect(effect)
    
    def _render_particle_effect(self, effect: ParticleEffect):
        """Rend un effet de particules spécifique"""
        particles_rendered = 0
        
        for particle in effect.particles:
            x, y = particle['x'], particle['y']
            
            # Culling des particules
            if not self._is_in_render_bounds(x, y, particle['size'], particle['size']):
                continue
            
            # Couleur avec alpha
            color = particle.get('color', SteampunkColors.STEAM_WHITE)
            alpha = max(0, min(255, int(particle['alpha'])))
            render_color = (*color, alpha)
            
            # Rendu de la particule
            arcade.draw_circle_filled(x, y, particle['size'], render_color)
            particles_rendered += 1
        
        self.stats['particles_rendered'] += particles_rendered
    
    # ═══════════════════════════════════════════════════════════
    # DEBUG ET OUTILS
    # ═══════════════════════════════════════════════════════════
    
    def draw_debug_grid(self, tile_size: int = 32, color: Tuple[int, int, int, int] = (255, 255, 255, 50)):
        """Dessine une grille de debug"""
        bounds = self.camera.get_viewport_bounds()
        
        # Lignes verticales
        start_x = int(bounds[0] / tile_size) * tile_size
        end_x = int(bounds[2] / tile_size + 1) * tile_size
        
        for x in range(start_x, end_x + 1, tile_size):
            self.draw_line(x, bounds[1], x, bounds[3], color, layer=RenderLayer.DEBUG)
        
        # Lignes horizontales
        start_y = int(bounds[1] / tile_size) * tile_size
        end_y = int(bounds[3] / tile_size + 1) * tile_size
        
        for y in range(start_y, end_y + 1, tile_size):
            self.draw_line(bounds[0], y, bounds[2], y, color, layer=RenderLayer.DEBUG)
    
    def draw_debug_bounds(self, x: float, y: float, width: float, height: float,
                         color: Tuple[int, int, int, int] = (255, 0, 0, 128)):
        """Dessine les limites de debug d'un objet"""
        self.draw_rectangle_filled(x, y, width, height, color, RenderLayer.DEBUG)
    
    def get_render_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de rendu"""
        return {
            **self.stats,
            'active_particle_effects': len(self.particle_effects),
            'active_batches': sum(len(batches) for batches in self.render_batches.values()),
            'camera_position': self.camera.get_position(),
            'render_bounds': self.render_bounds,
            'settings': {
                'enable_batching': self.enable_batching,
                'enable_culling': self.enable_culling,
                'enable_effects': self.enable_effects,
                'culling_margin': self.culling_margin
            }
        }
    
    def toggle_batching(self):
        """Active/désactive le batching"""
        self.enable_batching = not self.enable_batching
        self.logger.info(f"Batching: {'activé' if self.enable_batching else 'désactivé'}")
    
    def toggle_culling(self):
        """Active/désactive le culling"""
        self.enable_culling = not self.enable_culling
        self.logger.info(f"Culling: {'activé' if self.enable_culling else 'désactivé'}")
    
    def toggle_effects(self):
        """Active/désactive les effets visuels"""
        self.enable_effects = not self.enable_effects
        self.logger.info(f"Effets visuels: {'activés' if self.enable_effects else 'désactivés'}")
    
    def clear_particle_effects(self):
        """Supprime tous les effets de particules"""
        count = len(self.particle_effects)
        self.particle_effects.clear()
        self.logger.debug(f"Effets de particules supprimés: {count}")
    
    def resize(self, width: int, height: int):
        """Redimensionne le renderer"""
        # Mise à jour des limites de base
        self.render_bounds = (0, 0, width, height)
        self.logger.info(f"Renderer redimensionné: {width}x{height}")
    
    def set_background_color(self, color: Tuple[int, int, int]):
        """Définit la couleur de fond"""
        self.background_color = color
        arcade.set_background_color(color)
    
    def cleanup(self):
        """Nettoyage du renderer"""
        self.logger.info("Nettoyage du Renderer")
        
        # Nettoyage des effets
        self.particle_effects.clear()
        
        # Nettoyage des lots
        self._clear_render_batches()
        
        # Nettoyage du cache
        self.texture_cache.clear()
        
        self.logger.info("Renderer nettoyé")


# ═══════════════════════════════════════════════════════════
# UTILITAIRES DE RENDU
# ═══════════════════════════════════════════════════════════

def create_gradient_texture(width: int, height: int, 
                           start_color: Tuple[int, int, int], 
                           end_color: Tuple[int, int, int],
                           direction: str = "vertical") -> arcade.Texture:
    """
    Crée une texture de dégradé
    
    Args:
        width, height: Dimensions de la texture
        start_color, end_color: Couleurs de début et fin
        direction: "vertical", "horizontal", "radial"
    """
    import numpy as np
    
    # Création du tableau de pixels
    pixels = np.zeros((height, width, 4), dtype=np.uint8)
    
    if direction == "vertical":
        for y in range(height):
            t = y / (height - 1) if height > 1 else 0
            color = [
                int(start_color[i] + (end_color[i] - start_color[i]) * t)
                for i in range(3)
            ]
            pixels[y, :, :3] = color
            pixels[y, :, 3] = 255  # Alpha
    
    elif direction == "horizontal":
        for x in range(width):
            t = x / (width - 1) if width > 1 else 0
            color = [
                int(start_color[i] + (end_color[i] - start_color[i]) * t)
                for i in range(3)
            ]
            pixels[:, x, :3] = color
            pixels[:, x, 3] = 255  # Alpha
    
    elif direction == "radial":
        center_x, center_y = width // 2, height // 2
        max_distance = math.sqrt(center_x**2 + center_y**2)
        
        for y in range(height):
            for x in range(width):
                distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                t = min(1.0, distance / max_distance)
                
                color = [
                    int(start_color[i] + (end_color[i] - start_color[i]) * t)
                    for i in range(3)
                ]
                pixels[y, x, :3] = color
                pixels[y, x, 3] = 255  # Alpha
    
    # Conversion en texture Arcade
    # Note: Arcade peut nécessiter une conversion différente selon la version
    texture_name = f"gradient_{direction}_{width}x{height}"
    
    try:
        # Tentative de création directe
        return arcade.Texture.create_from_array(texture_name, pixels)
    except:
        # Méthode alternative si la précédente échoue
        return arcade.Texture.create_filled(texture_name, (width, height), end_color)


import random  # Import manquant pour les effets de particules

def lerp_color(color1: Tuple[int, int, int], color2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Interpolation linéaire entre deux couleurs"""
    return tuple(
        int(color1[i] + (color2[i] - color1[i]) * t)
        for i in range(3)
    )
