# graphics/ui/steampunk_ui.py
"""
Steam Defense - Interface utilisateur steampunk
Composants UI thématiques avec esthétique steampunk
"""

import arcade
import math
import random
from typing import Tuple, List, Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass
import logging

from config.settings import SteampunkColors, SETTINGS
from graphics.sprite_factory import SteampunkSpriteFactory


class UIComponentState(Enum):
    """États des composants UI"""
    NORMAL = "normal"
    HOVER = "hover"
    PRESSED = "pressed"
    DISABLED = "disabled"
    FOCUSED = "focused"


@dataclass
class SteampunkTheme:
    """Thème visuel steampunk pour les composants UI"""
    # Couleurs principales
    primary_color: Tuple[int, int, int] = SteampunkColors.BRONZE
    secondary_color: Tuple[int, int, int] = SteampunkColors.BRASS
    accent_color: Tuple[int, int, int] = SteampunkColors.GOLD
    
    # Couleurs de texte
    text_color: Tuple[int, int, int] = SteampunkColors.TEXT_GOLD
    text_shadow_color: Tuple[int, int, int] = SteampunkColors.TEXT_DARK
    
    # Couleurs d'état
    hover_color: Tuple[int, int, int] = SteampunkColors.COPPER
    pressed_color: Tuple[int, int, int] = SteampunkColors.RUST
    disabled_color: Tuple[int, int, int] = SteampunkColors.STEEL
    
    # Effets
    glow_color: Tuple[int, int, int] = SteampunkColors.FIRE_ORANGE
    steam_color: Tuple[int, int, int] = SteampunkColors.STEAM_WHITE
    
    # Polices
    title_font: str = "Arial"
    body_font: str = "Arial"
    monospace_font: str = "Courier New"


class AnimationSystem:
    """Système d'animation pour les composants UI"""
    
    def __init__(self):
        self.animations: List[Dict] = []
    
    def animate_value(self, target_obj: Any, property_name: str, 
                     start_value: float, end_value: float, 
                     duration: float, easing: str = "ease_out"):
        """Anime une propriété d'un objet"""
        animation = {
            'target': target_obj,
            'property': property_name,
            'start_value': start_value,
            'end_value': end_value,
            'duration': duration,
            'elapsed': 0.0,
            'easing': easing
        }
        self.animations.append(animation)
    
    def update(self, delta_time: float):
        """Met à jour toutes les animations"""
        completed_animations = []
        
        for animation in self.animations:
            animation['elapsed'] += delta_time
            progress = min(1.0, animation['elapsed'] / animation['duration'])
            
            # Application de l'easing
            eased_progress = self._apply_easing(progress, animation['easing'])
            
            # Calcul de la valeur interpolée
            value_range = animation['end_value'] - animation['start_value']
            current_value = animation['start_value'] + value_range * eased_progress
            
            # Application de la valeur
            setattr(animation['target'], animation['property'], current_value)
            
            # Vérification de fin d'animation
            if progress >= 1.0:
                completed_animations.append(animation)
        
        # Suppression des animations terminées
        for animation in completed_animations:
            self.animations.remove(animation)
    
    def _apply_easing(self, t: float, easing_type: str) -> float:
        """Applique une fonction d'easing"""
        if easing_type == "linear":
            return t
        elif easing_type == "ease_in":
            return t * t
        elif easing_type == "ease_out":
            return 1 - (1 - t) * (1 - t)
        elif easing_type == "ease_in_out":
            if t < 0.5:
                return 2 * t * t
            return 1 - 2 * (1 - t) * (1 - t)
        elif easing_type == "bounce":
            if t < 0.5:
                return 2 * t * t
            return 1 - 2 * (1 - t) * (1 - t)
        return t


class SteampunkButton:
    """Bouton avec style steampunk authentique"""
    
    def __init__(self, x: float, y: float, width: float, height: float,
                 text: str = "", theme: Optional[SteampunkTheme] = None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.theme = theme or SteampunkTheme()
        
        # État
        self.state = UIComponentState.NORMAL
        self.is_enabled = True
        self.is_visible = True
        
        # Callbacks
        self.on_click: Optional[Callable] = None
        self.on_hover: Optional[Callable] = None
        
        # Animation
        self.hover_scale = 1.0
        self.press_offset = 0.0
        self.steam_particles: List[Dict] = []
        self.glow_intensity = 0.0
        
        # Effets visuels
        self.rivets_positions = self._generate_rivets()
        self.gear_rotation = 0.0
        self.steam_timer = 0.0
        
        self.logger = logging.getLogger('SteampunkButton')
    
    def _generate_rivets(self) -> List[Tuple[float, float]]:
        """Génère les positions des rivets décoratifs"""
        rivets = []
        rivet_spacing = 20
        
        # Rivets sur les bords
        num_horizontal = max(2, int(self.width // rivet_spacing))
        num_vertical = max(2, int(self.height // rivet_spacing))
        
        # Bord supérieur et inférieur
        for i in range(num_horizontal):
            x = self.x + (i + 1) * self.width / (num_horizontal + 1)
            rivets.append((x, self.y + 5))  # Bord supérieur
            rivets.append((x, self.y + self.height - 5))  # Bord inférieur
        
        # Bords gauche et droit
        for i in range(num_vertical):
            y = self.y + (i + 1) * self.height / (num_vertical + 1)
            rivets.append((self.x + 5, y))  # Bord gauche
            rivets.append((self.x + self.width - 5, y))  # Bord droit
        
        return rivets
    
    def update(self, delta_time: float):
        """Met à jour les animations et effets"""
        if not self.is_visible:
            return
        
        # Animation d'engrenage
        self.gear_rotation += delta_time * 45  # 45 degrés par seconde
        self.gear_rotation = self.gear_rotation % 360
        
        # Gestion des particules de vapeur
        self.steam_timer += delta_time
        
        if self.state == UIComponentState.HOVER and self.steam_timer >= 0.1:
            # Génération de vapeur au survol
            self._add_steam_particle()
            self.steam_timer = 0.0
        
        # Mise à jour des particules de vapeur
        for particle in self.steam_particles[:]:
            particle['y'] += particle['velocity_y'] * delta_time
            particle['x'] += particle['velocity_x'] * delta_time
            particle['life'] -= delta_time
            particle['alpha'] *= 0.98  # Fade progressif
            
            if particle['life'] <= 0 or particle['alpha'] < 10:
                self.steam_particles.remove(particle)
        
        # Animation de glow
        target_glow = 0.8 if self.state == UIComponentState.HOVER else 0.0
        glow_speed = 3.0
        if self.glow_intensity < target_glow:
            self.glow_intensity = min(target_glow, self.glow_intensity + glow_speed * delta_time)
        elif self.glow_intensity > target_glow:
            self.glow_intensity = max(target_glow, self.glow_intensity - glow_speed * delta_time)
    
    def _add_steam_particle(self):
        """Ajoute une particule de vapeur"""
        if len(self.steam_particles) > 20:  # Limite le nombre de particules
            return
        
        # Position aléatoire sur le bord du bouton
        edge = random.randint(0, 3)  # 0=haut, 1=droite, 2=bas, 3=gauche
        
        if edge == 0:  # Haut
            x = random.uniform(self.x + 10, self.x + self.width - 10)
            y = self.y + self.height
        elif edge == 1:  # Droite
            x = self.x + self.width
            y = random.uniform(self.y + 10, self.y + self.height - 10)
        elif edge == 2:  # Bas
            x = random.uniform(self.x + 10, self.x + self.width - 10)
            y = self.y
        else:  # Gauche
            x = self.x
            y = random.uniform(self.y + 10, self.y + self.height - 10)
        
        particle = {
            'x': x,
            'y': y,
            'velocity_x': random.uniform(-20, 20),
            'velocity_y': random.uniform(10, 30),
            'life': random.uniform(1.0, 2.0),
            'alpha': random.uniform(150, 255),
            'size': random.uniform(3, 8)
        }
        
        self.steam_particles.append(particle)
    
    def handle_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> bool:
        """Gère les clics de souris"""
        if not self.is_enabled or not self.is_visible:
            return False
        
        if self._point_in_bounds(x, y):
            self.state = UIComponentState.PRESSED
            self.press_offset = 2.0
            return True
        
        return False
    
    def handle_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> bool:
        """Gère le relâchement de la souris"""
        if not self.is_enabled or not self.is_visible:
            return False
        
        was_pressed = self.state == UIComponentState.PRESSED
        self.press_offset = 0.0
        
        if self._point_in_bounds(x, y):
            self.state = UIComponentState.HOVER
            if was_pressed and self.on_click:
                self.on_click()
                self._trigger_click_effects()
            return True
        else:
            self.state = UIComponentState.NORMAL
        
        return was_pressed
    
    def handle_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> bool:
        """Gère le mouvement de la souris"""
        if not self.is_enabled or not self.is_visible:
            return False
        
        if self._point_in_bounds(x, y):
            if self.state == UIComponentState.NORMAL:
                self.state = UIComponentState.HOVER
                if self.on_hover:
                    self.on_hover()
            return True
        else:
            if self.state == UIComponentState.HOVER:
                self.state = UIComponentState.NORMAL
        
        return False
    
    def _point_in_bounds(self, x: float, y: float) -> bool:
        """Vérifie si un point est dans les limites du bouton"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)
    
    def _trigger_click_effects(self):
        """Déclenche les effets visuels de clic"""
        # Explosion de vapeur
        for _ in range(8):
            particle = {
                'x': self.x + self.width / 2 + random.uniform(-20, 20),
                'y': self.y + self.height / 2 + random.uniform(-20, 20),
                'velocity_x': random.uniform(-50, 50),
                'velocity_y': random.uniform(-50, 50),
                'life': 0.8,
                'alpha': 255,
                'size': random.uniform(4, 10)
            }
            self.steam_particles.append(particle)
    
    def render(self):
        """Rendu du bouton steampunk"""
        if not self.is_visible:
            return
        
        # Position avec effet de pression
        render_y = self.y - self.press_offset
        
        # Couleur selon l'état
        if not self.is_enabled:
            main_color = self.theme.disabled_color
        elif self.state == UIComponentState.PRESSED:
            main_color = self.theme.pressed_color
        elif self.state == UIComponentState.HOVER:
            main_color = self.theme.hover_color
        else:
            main_color = self.theme.primary_color
        
        # Glow effect
        if self.glow_intensity > 0:
            glow_radius = max(self.width, self.height) * 0.6
            glow_alpha = int(100 * self.glow_intensity)
            glow_color = (*self.theme.glow_color, glow_alpha)
            
            for i in range(3):
                radius = glow_radius * (1.0 - i * 0.3)
                alpha = glow_alpha // (i + 1)
                
                arcade.draw_rectangle_filled(
                    self.x + self.width / 2,
                    render_y + self.height / 2,
                    self.width + radius,
                    self.height + radius / 2,
                    (*self.theme.glow_color, alpha)
                )
        
        # Corps principal du bouton
        arcade.draw_rectangle_filled(
            self.x + self.width / 2,
            render_y + self.height / 2,
            self.width,
            self.height,
            main_color
        )
        
        # Bordure métallique
        border_color = self.theme.secondary_color
        arcade.draw_rectangle_outline(
            self.x + self.width / 2,
            render_y + self.height / 2,
            self.width,
            self.height,
            border_color,
            3
        )
        
        # Biseautage (effet 3D)
        self._render_bevel_effect(render_y)
        
        # Rivets décoratifs
        self._render_rivets(render_y)
        
        # Engrenage décoratif
        self._render_gear(render_y)
        
        # Texte
        if self.text:
            self._render_text(render_y)
        
        # Particules de vapeur
        self._render_steam_particles()
    
    def _render_bevel_effect(self, render_y: float):
        """Rend l'effet de biseautage 3D"""
        # Highlight (haut et gauche)
        highlight_color = tuple(min(255, c + 40) for c in self.theme.primary_color)
        
        # Haut
        arcade.draw_line(
            self.x, render_y + self.height,
            self.x + self.width, render_y + self.height,
            highlight_color, 2
        )
        
        # Gauche
        arcade.draw_line(
            self.x, render_y,
            self.x, render_y + self.height,
            highlight_color, 2
        )
        
        # Shadow (bas et droite)
        shadow_color = tuple(max(0, c - 40) for c in self.theme.primary_color)
        
        # Bas
        arcade.draw_line(
            self.x, render_y,
            self.x + self.width, render_y,
            shadow_color, 2
        )
        
        # Droite
        arcade.draw_line(
            self.x + self.width, render_y,
            self.x + self.width, render_y + self.height,
            shadow_color, 2
        )
    
    def _render_rivets(self, render_y: float):
        """Rend les rivets décoratifs"""
        for rivet_x, rivet_y_offset in self.rivets_positions:
            rivet_y = render_y + rivet_y_offset - self.y
            
            # Rivet principal
            arcade.draw_circle_filled(
                rivet_x, rivet_y, 3,
                self.theme.secondary_color
            )
            
            # Highlight
            arcade.draw_circle_filled(
                rivet_x - 1, rivet_y + 1, 1,
                self.theme.accent_color
            )
            
            # Contour
            arcade.draw_circle_outline(
                rivet_x, rivet_y, 3,
                SteampunkColors.IRON, 1
            )
    
    def _render_gear(self, render_y: float):
        """Rend un engrenage décoratif"""
        gear_x = self.x + self.width - 20
        gear_y = render_y + 20
        gear_radius = 8
        teeth = 8
        
        # Dents de l'engrenage
        points = []
        for i in range(teeth * 2):
            angle = math.radians(i * 180 / teeth + self.gear_rotation)
            if i % 2 == 0:  # Pointe
                radius = gear_radius
            else:  # Creux
                radius = gear_radius * 0.7
            
            x = gear_x + radius * math.cos(angle)
            y = gear_y + radius * math.sin(angle)
            points.extend([x, y])
        
        # Dessin de l'engrenage
        arcade.draw_polygon_filled(points, self.theme.accent_color)
        arcade.draw_polygon_outline(points, SteampunkColors.IRON, 1)
        
        # Centre de l'engrenage
        arcade.draw_circle_filled(gear_x, gear_y, gear_radius * 0.3, SteampunkColors.IRON)
    
    def _render_text(self, render_y: float):
        """Rend le texte du bouton"""
        text_x = self.x + self.width / 2
        text_y = render_y + self.height / 2
        
        # Ombre du texte
        arcade.draw_text(
            self.text,
            text_x + 1, text_y - 1,
            self.theme.text_shadow_color,
            font_size=14,
            font_name=self.theme.body_font,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )
        
        # Texte principal
        arcade.draw_text(
            self.text,
            text_x, text_y,
            self.theme.text_color,
            font_size=14,
            font_name=self.theme.body_font,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )
    
    def _render_steam_particles(self):
        """Rend les particules de vapeur"""
        for particle in self.steam_particles:
            color = (*self.theme.steam_color, int(particle['alpha']))
            arcade.draw_circle_filled(
                particle['x'], particle['y'],
                particle['size'],
                color
            )


class SteampunkGauge:
    """Jauge steampunk (manomètre analogique)"""
    
    def __init__(self, x: float, y: float, radius: float, 
                 min_value: float = 0.0, max_value: float = 100.0,
                 theme: Optional[SteampunkTheme] = None):
        self.x = x
        self.y = y
        self.radius = radius
        self.min_value = min_value
        self.max_value = max_value
        self.current_value = min_value
        self.theme = theme or SteampunkTheme()
        
        # Configuration visuelle
        self.start_angle = 225  # Angle de départ (degrés)
        self.sweep_angle = 270  # Amplitude de la jauge (degrés)
        
        # Animation
        self.needle_angle = self.start_angle
        self.target_needle_angle = self.start_angle
        self.needle_smoothing = 5.0
        
        # Effets visuels
        self.pressure_steam_timer = 0.0
        self.danger_zone_threshold = 0.8  # 80% = zone dangereuse
        
        self.is_visible = True
    
    def set_value(self, value: float):
        """Met à jour la valeur de la jauge"""
        self.current_value = max(self.min_value, min(self.max_value, value))
        
        # Calcul de l'angle cible de l'aiguille
        value_ratio = (self.current_value - self.min_value) / (self.max_value - self.min_value)
        self.target_needle_angle = self.start_angle + value_ratio * self.sweep_angle
    
    def update(self, delta_time: float):
        """Met à jour l'animation de la jauge"""
        if not self.is_visible:
            return
        
        # Animation fluide de l'aiguille
        angle_diff = self.target_needle_angle - self.needle_angle
        self.needle_angle += angle_diff * self.needle_smoothing * delta_time
        
        # Effets de vapeur pour haute pression
        self.pressure_steam_timer += delta_time
        
        value_ratio = (self.current_value - self.min_value) / (self.max_value - self.min_value)
        if value_ratio > self.danger_zone_threshold and self.pressure_steam_timer >= 0.2:
            # Vapeur de surpression
            self.pressure_steam_timer = 0.0
    
    def render(self):
        """Rendu de la jauge steampunk"""
        if not self.is_visible:
            return
        
        # Fond de la jauge (plaque métallique)
        arcade.draw_circle_filled(
            self.x, self.y, self.radius + 5,
            self.theme.primary_color
        )
        
        # Bordure externe
        arcade.draw_circle_outline(
            self.x, self.y, self.radius + 5,
            self.theme.secondary_color, 3
        )
        
        # Cadran interne
        arcade.draw_circle_filled(
            self.x, self.y, self.radius,
            SteampunkColors.STEAM_WHITE
        )
        
        # Graduations
        self._render_graduations()
        
        # Zone dangereuse (rouge)
        self._render_danger_zone()
        
        # Aiguille
        self._render_needle()
        
        # Centre de l'aiguille
        arcade.draw_circle_filled(
            self.x, self.y, 6,
            self.theme.accent_color
        )
        
        arcade.draw_circle_outline(
            self.x, self.y, 6,
            SteampunkColors.IRON, 2
        )
        
        # Rivets décoratifs
        self._render_decorative_rivets()
    
    def _render_graduations(self):
        """Rend les graduations de la jauge"""
        num_major_marks = 6  # Graduations principales
        num_minor_marks = 24  # Graduations secondaires
        
        # Graduations principales
        for i in range(num_major_marks):
            angle = math.radians(self.start_angle + i * self.sweep_angle / (num_major_marks - 1))
            
            # Ligne externe
            outer_x = self.x + (self.radius - 10) * math.cos(angle)
            outer_y = self.y + (self.radius - 10) * math.sin(angle)
            
            # Ligne interne
            inner_x = self.x + (self.radius - 20) * math.cos(angle)
            inner_y = self.y + (self.radius - 20) * math.sin(angle)
            
            arcade.draw_line(
                outer_x, outer_y, inner_x, inner_y,
                SteampunkColors.IRON, 3
            )
            
            # Chiffres
            if i % 2 == 0:  # Chiffres sur une graduation sur deux
                value = self.min_value + i * (self.max_value - self.min_value) / (num_major_marks - 1)
                text_x = self.x + (self.radius - 35) * math.cos(angle)
                text_y = self.y + (self.radius - 35) * math.sin(angle)
                
                arcade.draw_text(
                    f"{int(value)}",
                    text_x, text_y,
                    SteampunkColors.TEXT_DARK,
                    font_size=10,
                    anchor_x="center",
                    anchor_y="center",
                    bold=True
                )
        
        # Graduations secondaires
        for i in range(num_minor_marks):
            if i % (num_minor_marks // (num_major_marks - 1)) != 0:  # Éviter les graduations principales
                angle = math.radians(self.start_angle + i * self.sweep_angle / (num_minor_marks - 1))
                
                outer_x = self.x + (self.radius - 10) * math.cos(angle)
                outer_y = self.y + (self.radius - 10) * math.sin(angle)
                
                inner_x = self.x + (self.radius - 15) * math.cos(angle)
                inner_y = self.y + (self.radius - 15) * math.sin(angle)
                
                arcade.draw_line(
                    outer_x, outer_y, inner_x, inner_y,
                    SteampunkColors.STEEL, 1
                )
    
    def _render_danger_zone(self):
        """Rend la zone dangereuse en rouge"""
        danger_start_angle = self.start_angle + self.danger_zone_threshold * self.sweep_angle
        danger_sweep = self.sweep_angle * (1.0 - self.danger_zone_threshold)
        
        # Arc rouge pour la zone dangereuse
        num_segments = 20
        for i in range(num_segments):
            angle1 = math.radians(danger_start_angle + i * danger_sweep / num_segments)
            angle2 = math.radians(danger_start_angle + (i + 1) * danger_sweep / num_segments)
            
            # Points externes
            outer_x1 = self.x + (self.radius - 5) * math.cos(angle1)
            outer_y1 = self.y + (self.radius - 5) * math.sin(angle1)
            outer_x2 = self.x + (self.radius - 5) * math.cos(angle2)
            outer_y2 = self.y + (self.radius - 5) * math.sin(angle2)
            
            # Points internes
            inner_x1 = self.x + (self.radius - 15) * math.cos(angle1)
            inner_y1 = self.y + (self.radius - 15) * math.sin(angle1)
            inner_x2 = self.x + (self.radius - 15) * math.cos(angle2)
            inner_y2 = self.y + (self.radius - 15) * math.sin(angle2)
            
            # Quadrilatère coloré
            points = [outer_x1, outer_y1, outer_x2, outer_y2, inner_x2, inner_y2, inner_x1, inner_y1]
            arcade.draw_polygon_filled(points, arcade.color.RED)
    
    def _render_needle(self):
        """Rend l'aiguille de la jauge"""
        angle = math.radians(self.needle_angle)
        
        # Aiguille principale
        needle_length = self.radius - 25
        needle_tip_x = self.x + needle_length * math.cos(angle)
        needle_tip_y = self.y + needle_length * math.sin(angle)
        
        # Corps de l'aiguille
        arcade.draw_line(
            self.x, self.y,
            needle_tip_x, needle_tip_y,
            self.theme.accent_color, 4
        )
        
        # Pointe de l'aiguille
        arcade.draw_circle_filled(
            needle_tip_x, needle_tip_y, 3,
            SteampunkColors.GOLD
        )
        
        # Contre-poids (opposé à l'aiguille)
        counter_angle = angle + math.pi
        counter_length = 15
        counter_x = self.x + counter_length * math.cos(counter_angle)
        counter_y = self.y + counter_length * math.sin(counter_angle)
        
        arcade.draw_line(
            self.x, self.y,
            counter_x, counter_y,
            self.theme.accent_color, 6
        )
    
    def _render_decorative_rivets(self):
        """Rend les rivets décoratifs"""
        for i in range(8):
            angle = math.radians(i * 45)
            rivet_x = self.x + (self.radius + 3) * math.cos(angle)
            rivet_y = self.y + (self.radius + 3) * math.sin(angle)
            
            arcade.draw_circle_filled(rivet_x, rivet_y, 2, self.theme.secondary_color)
            arcade.draw_circle_outline(rivet_x, rivet_y, 2, SteampunkColors.IRON, 1)


class SteampunkProgressBar:
    """Barre de progression avec tubes de vapeur"""
    
    def __init__(self, x: float, y: float, width: float, height: float,
                 theme: Optional[SteampunkTheme] = None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.theme = theme or SteampunkTheme()
        
        self.progress = 0.0  # 0.0 à 1.0
        self.is_visible = True
        
        # Animation
        self.animated_progress = 0.0
        self.animation_speed = 2.0
        
        # Effets visuels
        self.bubble_timer = 0.0
        self.bubbles: List[Dict] = []
    
    def set_progress(self, progress: float):
        """Met à jour le progrès (0.0 à 1.0)"""
        self.progress = max(0.0, min(1.0, progress))
    
    def update(self, delta_time: float):
        """Met à jour l'animation"""
        if not self.is_visible:
            return
        
        # Animation fluide du progrès
        progress_diff = self.progress - self.animated_progress
        self.animated_progress += progress_diff * self.animation_speed * delta_time
        
        # Bulles dans le liquide
        self.bubble_timer += delta_time
        if self.bubble_timer >= 0.3 and self.animated_progress > 0:
            self._add_bubble()
            self.bubble_timer = 0.0
        
        # Mise à jour des bulles
        for bubble in self.bubbles[:]:
            bubble['y'] += bubble['speed'] * delta_time
            bubble['life'] -= delta_time
            
            # Mouvement latéral léger
            bubble['x'] += math.sin(bubble['life'] * 5) * 10 * delta_time
            
            if (bubble['life'] <= 0 or 
                bubble['y'] > self.y + self.height or
                bubble['x'] < self.x or bubble['x'] > self.x + self.width):
                self.bubbles.remove(bubble)
    
    def _add_bubble(self):
        """Ajoute une bulle dans le liquide"""
        if len(self.bubbles) > 15:  # Limite le nombre de bulles
            return
        
        # Position dans la zone de liquide
        liquid_width = self.width * self.animated_progress
        
        if liquid_width > 10:  # Assez de liquide pour des bulles
            bubble = {
                'x': self.x + random.uniform(5, liquid_width - 5),
                'y': self.y + random.uniform(5, self.height * 0.3),
                'speed': random.uniform(20, 40),
                'size': random.uniform(2, 5),
                'life': random.uniform(2, 4)
            }
            self.bubbles.append(bubble)
    
    def render(self):
        """Rendu de la barre de progression"""
        if not self.is_visible:
            return
        
        # Tube externe (contenant)
        arcade.draw_rectangle_filled(
            self.x + self.width / 2,
            self.y + self.height / 2,
            self.width,
            self.height,
            SteampunkColors.STEEL
        )
        
        # Intérieur du tube (verre)
        inner_margin = 4
        arcade.draw_rectangle_filled(
            self.x + self.width / 2,
            self.y + self.height / 2,
            self.width - inner_margin * 2,
            self.height - inner_margin * 2,
            (200, 200, 200, 100)  # Verre transparent
        )
        
        # Liquide (progression)
        if self.animated_progress > 0:
            liquid_width = (self.width - inner_margin * 2) * self.animated_progress
            
            # Couleur du liquide selon le progrès
            if self.animated_progress < 0.3:
                liquid_color = SteampunkColors.ELECTRIC_BLUE  # Bleu pour faible
            elif self.animated_progress < 0.7:
                liquid_color = SteampunkColors.GOLD  # Or pour moyen
            else:
                liquid_color = SteampunkColors.FIRE_ORANGE  # Orange pour élevé
            
            arcade.draw_rectangle_filled(
                self.x + inner_margin + liquid_width / 2,
                self.y + self.height / 2,
                liquid_width,
                self.height - inner_margin * 2,
                liquid_color
            )
        
        # Graduations sur le tube
        self._render_graduations()
        
        # Bulles dans le liquide
        for bubble in self.bubbles:
            # Vérifier que la bulle est dans la zone de liquide
            liquid_width = (self.width - inner_margin * 2) * self.animated_progress
            if bubble['x'] <= self.x + inner_margin + liquid_width:
                arcade.draw_circle_filled(
                    bubble['x'], bubble['y'],
                    bubble['size'],
                    (255, 255, 255, 150)  # Bulles blanches transparentes
                )
        
        # Bordures et détails
        arcade.draw_rectangle_outline(
            self.x + self.width / 2,
            self.y + self.height / 2,
            self.width,
            self.height,
            self.theme.secondary_color,
            2
        )
        
        # Connecteurs de tuyau
        self._render_connectors()
    
    def _render_graduations(self):
        """Rend les graduations sur le tube"""
        num_marks = 5
        for i in range(num_marks + 1):
            x_pos = self.x + i * self.width / num_marks
            
            # Graduation courte
            arcade.draw_line(
                x_pos, self.y + self.height,
                x_pos, self.y + self.height + 5,
                self.theme.secondary_color, 2
            )
            
            # Pourcentage
            if i % 2 == 0:
                percentage = int(100 * i / num_marks)
                arcade.draw_text(
                    f"{percentage}%",
                    x_pos, self.y + self.height + 8,
                    self.theme.text_color,
                    font_size=8,
                    anchor_x="center",
                    bold=True
                )
    
    def _render_connectors(self):
        """Rend les connecteurs de tuyau"""
        # Connecteur gauche
        arcade.draw_circle_filled(
            self.x, self.y + self.height / 2,
            8, self.theme.primary_color
        )
        arcade.draw_circle_outline(
            self.x, self.y + self.height / 2,
            8, self.theme.secondary_color, 2
        )
        
        # Connecteur droit
        arcade.draw_circle_filled(
            self.x + self.width, self.y + self.height / 2,
            8, self.theme.primary_color
        )
        arcade.draw_circle_outline(
            self.x + self.width, self.y + self.height / 2,
            8, self.theme.secondary_color, 2
        )


# ═══════════════════════════════════════════════════════════
# GESTIONNAIRE D'INTERFACE PRINCIPALE
# ═══════════════════════════════════════════════════════════

class SteampunkUIManager:
    """Gestionnaire principal pour tous les composants UI steampunk"""
    
    def __init__(self):
        self.components: List[Any] = []
        self.theme = SteampunkTheme()
        self.animation_system = AnimationSystem()
        self.logger = logging.getLogger('SteampunkUIManager')
        
        # État global de l'UI
        self.is_visible = True
        self.mouse_x = 0.0
        self.mouse_y = 0.0
    
    def add_component(self, component):
        """Ajoute un composant à l'interface"""
        self.components.append(component)
        self.logger.debug(f"Composant ajouté: {type(component).__name__}")
    
    def remove_component(self, component):
        """Supprime un composant de l'interface"""
        if component in self.components:
            self.components.remove(component)
            self.logger.debug(f"Composant supprimé: {type(component).__name__}")
    
    def update(self, delta_time: float):
        """Met à jour tous les composants"""
        if not self.is_visible:
            return
        
        self.animation_system.update(delta_time)
        
        for component in self.components:
            if hasattr(component, 'update'):
                component.update(delta_time)
    
    def render(self):
        """Rendu de tous les composants"""
        if not self.is_visible:
            return
        
        for component in self.components:
            if hasattr(component, 'render'):
                component.render()
    
    def handle_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> bool:
        """Gère les clics de souris pour tous les composants"""
        self.mouse_x, self.mouse_y = x, y
        
        # Traitement en ordre inverse pour gérer la superposition
        for component in reversed(self.components):
            if hasattr(component, 'handle_mouse_press'):
                if component.handle_mouse_press(x, y, button, modifiers):
                    return True
        
        return False
    
    def handle_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> bool:
        """Gère le relâchement de la souris"""
        self.mouse_x, self.mouse_y = x, y
        
        for component in reversed(self.components):
            if hasattr(component, 'handle_mouse_release'):
                if component.handle_mouse_release(x, y, button, modifiers):
                    return True
        
        return False
    
    def handle_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> bool:
        """Gère le mouvement de la souris"""
        self.mouse_x, self.mouse_y = x, y
        
        handled = False
        for component in self.components:
            if hasattr(component, 'handle_mouse_motion'):
                if component.handle_mouse_motion(x, y, dx, dy):
                    handled = True
        
        return handled
    
    def clear_all_components(self):
        """Supprime tous les composants"""
        count = len(self.components)
        self.components.clear()
        self.logger.info(f"Tous les composants supprimés ({count})")
    
    def get_component_count(self) -> int:
        """Retourne le nombre de composants"""
        return len(self.components)
    
    def set_theme(self, theme: SteampunkTheme):
        """Change le thème global"""
        self.theme = theme
        
        # Applique le nouveau thème aux composants existants
        for component in self.components:
            if hasattr(component, 'theme'):
                component.theme = theme
        
        self.logger.info("Thème mis à jour pour tous les composants")