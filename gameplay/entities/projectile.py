# gameplay/entities/projectile.py
"""
Steam Defense - Système de projectiles
Gère tous les types de projectiles tirés par les tours
"""

import arcade
import math
import random
from typing import Tuple, List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
import logging

from gameplay.entities.entity import Entity, EntityComponent
from graphics.sprite_factory import SteampunkSpriteFactory, SpriteType
from config.settings import SteampunkColors
from gameplay.entities.tower import TowerStats


class ProjectileType(Enum):
    """Types de projectiles disponibles"""
    CANNONBALL = "cannonball"
    LIGHTNING_BOLT = "lightning_bolt"
    FLAME_BURST = "flame_burst"
    BULLET = "bullet"
    MORTAR_SHELL = "mortar_shell"
    ICE_CRYSTAL = "ice_crystal"
    SNIPER_BULLET = "sniper_bullet"
    MINE = "mine"


class ProjectileMovementType(Enum):
    """Types de mouvement des projectiles"""
    LINEAR = "linear"           # Mouvement linéaire direct
    BALLISTIC = "ballistic"     # Trajectoire parabolique
    HOMING = "homing"          # Poursuite de cible
    INSTANT = "instant"        # Impact immédiat
    STATIC = "static"          # Immobile (mines)


@dataclass
class ProjectileTrail:
    """Configuration de traînée visuelle"""
    enabled: bool = False
    length: int = 5
    fade_rate: float = 0.8
    color: Tuple[int, int, int] = (255, 255, 255)
    particles: bool = False


class MovementComponent(EntityComponent):
    """Composant de mouvement pour projectiles"""
    
    def __init__(self, movement_type: ProjectileMovementType, speed: float):
        super().__init__()
        self.movement_type = movement_type
        self.speed = speed
        self.position = (0.0, 0.0)
        self.velocity = (0.0, 0.0)
        self.target_position: Optional[Tuple[float, float]] = None
        self.start_position = (0.0, 0.0)
        
        # Paramètres spécifiques au mouvement
        self.gravity = 500.0  # Pour les projectiles balistiques
        self.homing_strength = 3.0  # Force de poursuite
        self.max_turn_rate = math.radians(180)  # Vitesse de rotation max
        
        # État du mouvement
        self.has_hit = False
        self.travel_time = 0.0
        self.max_travel_time = 10.0  # Durée de vie maximale
        
        # Historique des positions pour la traînée
        self.position_history: List[Tuple[float, float]] = []
        self.max_history_length = 10
    
    def set_target(self, start_pos: Tuple[float, float], target_pos: Tuple[float, float]):
        """Configure la trajectoire du projectile"""
        self.start_position = start_pos
        self.position = start_pos
        self.target_position = target_pos
        
        if self.movement_type == ProjectileMovementType.LINEAR:
            self._setup_linear_movement()
        elif self.movement_type == ProjectileMovementType.BALLISTIC:
            self._setup_ballistic_movement()
        elif self.movement_type == ProjectileMovementType.HOMING:
            self._setup_homing_movement()
        elif self.movement_type == ProjectileMovementType.INSTANT:
            self._setup_instant_movement()
    
    def _setup_linear_movement(self):
        """Configure le mouvement linéaire"""
        if not self.target_position:
            return
        
        dx = self.target_position[0] - self.start_position[0]
        dy = self.target_position[1] - self.start_position[1]
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            self.velocity = (
                (dx / distance) * self.speed,
                (dy / distance) * self.speed
            )
    
    def _setup_ballistic_movement(self):
        """Configure le mouvement balistique (parabolique)"""
        if not self.target_position:
            return
        
        dx = self.target_position[0] - self.start_position[0]
        dy = self.target_position[1] - self.start_position[1]
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            # Calcul de l'angle optimal pour atteindre la cible
            travel_time = distance / self.speed
            
            # Vitesse horizontale constante
            vx = dx / travel_time
            
            # Vitesse verticale initiale pour compenser la gravité
            vy = dy / travel_time + 0.5 * self.gravity * travel_time
            
            self.velocity = (vx, vy)
    
    def _setup_homing_movement(self):
        """Configure le mouvement de poursuite"""
        # Démarrage avec une direction générale vers la cible
        self._setup_linear_movement()
    
    def _setup_instant_movement(self):
        """Configure l'impact instantané"""
        self.has_hit = True
        if self.target_position:
            self.position = self.target_position
    
    def update(self, delta_time: float):
        """Met à jour le mouvement du projectile"""
        if self.has_hit:
            return
        
        self.travel_time += delta_time
        
        # Vérification de la durée de vie
        if self.travel_time >= self.max_travel_time:
            self.has_hit = True
            return
        
        # Sauvegarde de la position pour la traînée
        self.position_history.append(self.position)
        if len(self.position_history) > self.max_history_length:
            self.position_history.pop(0)
        
        # Mise à jour selon le type de mouvement
        if self.movement_type == ProjectileMovementType.LINEAR:
            self._update_linear_movement(delta_time)
        elif self.movement_type == ProjectileMovementType.BALLISTIC:
            self._update_ballistic_movement(delta_time)
        elif self.movement_type == ProjectileMovementType.HOMING:
            self._update_homing_movement(delta_time)
        elif self.movement_type == ProjectileMovementType.STATIC:
            pass  # Pas de mouvement pour les mines
    
    def _update_linear_movement(self, delta_time: float):
        """Met à jour le mouvement linéaire"""
        new_x = self.position[0] + self.velocity[0] * delta_time
        new_y = self.position[1] + self.velocity[1] * delta_time
        self.position = (new_x, new_y)
        
        # Vérification de l'atteinte de la cible
        if self.target_position:
            distance_to_target = math.sqrt(
                (self.position[0] - self.target_position[0]) ** 2 +
                (self.position[1] - self.target_position[1]) ** 2
            )
            
            if distance_to_target < 5.0:  # Proche de la cible
                self.position = self.target_position
                self.has_hit = True
    
    def _update_ballistic_movement(self, delta_time: float):
        """Met à jour le mouvement balistique"""
        # Mouvement horizontal constant
        new_x = self.position[0] + self.velocity[0] * delta_time
        
        # Mouvement vertical avec gravité
        new_y = self.position[1] + self.velocity[1] * delta_time
        self.velocity = (self.velocity[0], self.velocity[1] - self.gravity * delta_time)
        
        self.position = (new_x, new_y)
        
        # Vérification si le projectile est passé sous la cible
        if (self.target_position and 
            self.position[1] <= self.target_position[1] and
            abs(self.position[0] - self.target_position[0]) < 20.0):
            self.position = self.target_position
            self.has_hit = True
    
    def _update_homing_movement(self, delta_time: float):
        """Met à jour le mouvement de poursuite"""
        if not self.target_position:
            self._update_linear_movement(delta_time)
            return
        
        # Direction actuelle
        current_angle = math.atan2(self.velocity[1], self.velocity[0])
        
        # Direction vers la cible
        dx = self.target_position[0] - self.position[0]
        dy = self.target_position[1] - self.position[1]
        target_angle = math.atan2(dy, dx)
        
        # Calcul de l'angle de rotation nécessaire
        angle_diff = target_angle - current_angle
        
        # Normalisation de l'angle entre -π et π
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        # Limitation de la vitesse de rotation
        max_rotation = self.max_turn_rate * delta_time
        if abs(angle_diff) > max_rotation:
            angle_diff = math.copysign(max_rotation, angle_diff)
        
        # Nouvelle direction
        new_angle = current_angle + angle_diff * self.homing_strength * delta_time
        
        # Mise à jour de la vélocité
        self.velocity = (
            self.speed * math.cos(new_angle),
            self.speed * math.sin(new_angle)
        )
        
        # Mouvement
        new_x = self.position[0] + self.velocity[0] * delta_time
        new_y = self.position[1] + self.velocity[1] * delta_time
        self.position = (new_x, new_y)
        
        # Vérification de l'atteinte de la cible
        distance_to_target = math.sqrt(dx * dx + dy * dy)
        if distance_to_target < 8.0:
            self.position = self.target_position
            self.has_hit = True


class EffectsComponent(EntityComponent):
    """Composant pour les effets visuels des projectiles"""
    
    def __init__(self, projectile_type: ProjectileType):
        super().__init__()
        self.projectile_type = projectile_type
        self.trail = self._setup_trail()
        self.rotation = 0.0
        self.rotation_speed = 0.0
        self.scale = 1.0
        self.alpha = 255
        
        # Effets spéciaux
        self.glow_enabled = False
        self.glow_radius = 0.0
        self.glow_color = (255, 255, 255)
        
        # Animation
        self.animation_timer = 0.0
        self.animation_speed = 1.0
    
    def _setup_trail(self) -> ProjectileTrail:
        """Configure la traînée selon le type de projectile"""
        trail_configs = {
            ProjectileType.CANNONBALL: ProjectileTrail(
                enabled=True, length=3, fade_rate=0.9,
                color=SteampunkColors.STEAM_WHITE, particles=True
            ),
            ProjectileType.LIGHTNING_BOLT: ProjectileTrail(
                enabled=True, length=8, fade_rate=0.7,
                color=SteampunkColors.ELECTRIC_BLUE, particles=True
            ),
            ProjectileType.FLAME_BURST: ProjectileTrail(
                enabled=True, length=5, fade_rate=0.8,
                color=SteampunkColors.FIRE_ORANGE, particles=True
            ),
            ProjectileType.BULLET: ProjectileTrail(
                enabled=True, length=2, fade_rate=0.95,
                color=SteampunkColors.STEEL
            ),
            ProjectileType.MORTAR_SHELL: ProjectileTrail(
                enabled=True, length=4, fade_rate=0.85,
                color=SteampunkColors.STEAM_WHITE, particles=True
            ),
            ProjectileType.ICE_CRYSTAL: ProjectileTrail(
                enabled=True, length=6, fade_rate=0.75,
                color=(173, 216, 230), particles=True  # Bleu glace
            ),
            ProjectileType.SNIPER_BULLET: ProjectileTrail(
                enabled=True, length=8, fade_rate=0.6,
                color=SteampunkColors.GOLD
            ),
        }
        
        return trail_configs.get(projectile_type, ProjectileTrail())
    
    def update(self, delta_time: float):
        """Met à jour les effets visuels"""
        self.animation_timer += delta_time * self.animation_speed
        
        # Rotation automatique pour certains projectiles
        if self.rotation_speed != 0:
            self.rotation += self.rotation_speed * delta_time
            self.rotation = self.rotation % (2 * math.pi)
        
        # Effets spéciaux selon le type
        if self.projectile_type == ProjectileType.LIGHTNING_BOLT:
            # Scintillement électrique
            self.alpha = int(255 * (0.8 + 0.2 * math.sin(self.animation_timer * 10)))
            self.glow_enabled = True
            self.glow_radius = 8 + 4 * math.sin(self.animation_timer * 8)
            self.glow_color = SteampunkColors.ELECTRIC_BLUE
        
        elif self.projectile_type == ProjectileType.FLAME_BURST:
            # Fluctuation de flamme
            self.scale = 1.0 + 0.2 * math.sin(self.animation_timer * 6)
            self.glow_enabled = True
            self.glow_radius = 6
            self.glow_color = SteampunkColors.FIRE_ORANGE
        
        elif self.projectile_type == ProjectileType.ICE_CRYSTAL:
            # Rotation cristalline
            self.rotation_speed = math.radians(180)
            self.glow_enabled = True
            self.glow_radius = 4
            self.glow_color = (173, 216, 230)


class Projectile(Entity):
    """
    Classe principale pour tous les projectiles
    """
    
    def __init__(self, projectile_type: ProjectileType, start_position: Tuple[float, float],
                 target_position: Tuple[float, float], damage: int, speed: float,
                 tower_stats: TowerStats, sprite_factory: SteampunkSpriteFactory):
        super().__init__()
        
        self.logger = logging.getLogger(f'Projectile.{projectile_type.value}')
        self.projectile_type = projectile_type
        self.damage = damage
        self.tower_stats = tower_stats
        self.sprite_factory = sprite_factory
        
        # Configuration du mouvement selon le type
        movement_type = self._get_movement_type(projectile_type)
        
        # Ajout des composants
        self.movement = MovementComponent(movement_type, speed)
        self.effects = EffectsComponent(projectile_type)
        
        self.add_component(self.movement)
        self.add_component(self.effects)
        
        # Configuration de la trajectoire
        self.movement.set_target(start_position, target_position)
        
        # Sprite et visuel
        self.sprite = self._create_sprite()
        self.sprite.center_x, self.sprite.center_y = start_position
        
        # État
        self.is_active = True
        self.has_exploded = False
        
        # Effets spéciaux selon le type
        self._setup_special_properties()
        
        self.logger.debug(f"Projectile {projectile_type.value} créé: {start_position} -> {target_position}")
    
    def _get_movement_type(self, projectile_type: ProjectileType) -> ProjectileMovementType:
        """Détermine le type de mouvement selon le projectile"""
        movement_map = {
            ProjectileType.CANNONBALL: ProjectileMovementType.LINEAR,
            ProjectileType.LIGHTNING_BOLT: ProjectileMovementType.INSTANT,
            ProjectileType.FLAME_BURST: ProjectileMovementType.LINEAR,
            ProjectileType.BULLET: ProjectileMovementType.LINEAR,
            ProjectileType.MORTAR_SHELL: ProjectileMovementType.BALLISTIC,
            ProjectileType.ICE_CRYSTAL: ProjectileMovementType.HOMING,
            ProjectileType.SNIPER_BULLET: ProjectileMovementType.LINEAR,
            ProjectileType.MINE: ProjectileMovementType.STATIC,
        }
        
        return movement_map.get(projectile_type, ProjectileMovementType.LINEAR)
    
    def _create_sprite(self) -> arcade.Sprite:
        """Crée le sprite du projectile"""
        sprite_type_map = {
            ProjectileType.CANNONBALL: SpriteType.CANNONBALL,
            ProjectileType.LIGHTNING_BOLT: SpriteType.LIGHTNING_BOLT,
            ProjectileType.FLAME_BURST: SpriteType.FLAME_BURST,
            ProjectileType.BULLET: SpriteType.BULLET,
            ProjectileType.MORTAR_SHELL: SpriteType.MORTAR_SHELL,
            ProjectileType.ICE_CRYSTAL: SpriteType.ICE_CRYSTAL,
            ProjectileType.SNIPER_BULLET: SpriteType.SNIPER_BULLET,
        }
        
        sprite_type = sprite_type_map.get(self.projectile_type, SpriteType.BULLET)
        
        # Taille personnalisée selon le type
        size_map = {
            ProjectileType.CANNONBALL: (16, 16),
            ProjectileType.LIGHTNING_BOLT: (32, 8),
            ProjectileType.FLAME_BURST: (12, 12),
            ProjectileType.BULLET: (8, 4),
            ProjectileType.MORTAR_SHELL: (20, 20),
            ProjectileType.ICE_CRYSTAL: (14, 14),
            ProjectileType.SNIPER_BULLET: (12, 3),
        }
        
        size = size_map.get(self.projectile_type, (8, 8))
        texture = self.sprite_factory.create_sprite(sprite_type, size)
        
        sprite = arcade.Sprite()
        sprite.texture = texture
        sprite.scale = 1.0
        
        return sprite
    
    def _setup_special_properties(self):
        """Configure les propriétés spéciales selon le type"""
        if self.projectile_type == ProjectileType.CANNONBALL:
            # Traînée de vapeur
            self.effects.trail.particles = True
            self.effects.rotation_speed = math.radians(90)
        
        elif self.projectile_type == ProjectileType.LIGHTNING_BOLT:
            # Effet électrique instantané
            self.effects.glow_enabled = True
            self.effects.glow_radius = 12
        
        elif self.projectile_type == ProjectileType.FLAME_BURST:
            # Flamme ondulante
            self.effects.animation_speed = 3.0
        
        elif self.projectile_type == ProjectileType.MORTAR_SHELL:
            # Projectile lourd avec gravité
            self.movement.gravity = 800.0
        
        elif self.projectile_type == ProjectileType.ICE_CRYSTAL:
            # Cristal qui cherche sa cible
            self.movement.homing_strength = 5.0
            self.effects.rotation_speed = math.radians(360)
        
        elif self.projectile_type == ProjectileType.SNIPER_BULLET:
            # Balle perforante ultra-rapide
            self.effects.trail.length = 12
            self.effects.trail.fade_rate = 0.5
    
    def update(self, delta_time: float):
        """Met à jour le projectile"""
        if not self.is_active:
            return
        
        # Mise à jour des composants
        self.movement.update(delta_time)
        self.effects.update(delta_time)
        
        # Mise à jour de la position du sprite
        self.sprite.center_x, self.sprite.center_y = self.movement.position
        
        # Mise à jour de la rotation du sprite
        if self.movement.velocity[0] != 0 or self.movement.velocity[1] != 0:
            # Orientation selon la vélocité
            angle = math.atan2(self.movement.velocity[1], self.movement.velocity[0])
            self.sprite.angle = math.degrees(angle)
        
        # Application des effets visuels
        self.sprite.alpha = self.effects.alpha
        self.sprite.scale = self.effects.scale
        
        # Vérification de l'état
        if self.movement.has_hit and not self.has_exploded:
            self._trigger_impact()
    
    def _trigger_impact(self):
        """Déclenche l'impact du projectile"""
        self.has_exploded = True
        
        # Effet visuel d'impact selon le type
        impact_effects = {
            ProjectileType.CANNONBALL: 'cannon_explosion',
            ProjectileType.LIGHTNING_BOLT: 'lightning_strike',
            ProjectileType.FLAME_BURST: 'flame_explosion',
            ProjectileType.BULLET: 'bullet_impact',
            ProjectileType.MORTAR_SHELL: 'mortar_explosion',
            ProjectileType.ICE_CRYSTAL: 'ice_shatter',
            ProjectileType.SNIPER_BULLET: 'sniper_impact',
        }
        
        effect_type = impact_effects.get(self.projectile_type, 'generic_impact')
        
        # Émission de l'événement d'impact
        self.emit_event('projectile_impact', {
            'projectile': self,
            'position': self.movement.position,
            'effect_type': effect_type,
            'damage': self.damage,
            'area_radius': self.tower_stats.area_radius if self.tower_stats.area_damage else 0
        })
        
        self.logger.debug(f"Projectile {self.projectile_type.value} impact à {self.movement.position}")
    
    def render(self, renderer):
        """Rendu personnalisé du projectile"""
        if not self.is_active:
            return
        
        # Rendu de la traînée
        if self.effects.trail.enabled and len(self.movement.position_history) > 1:
            self._render_trail(renderer)
        
        # Rendu de l'aura/glow
        if self.effects.glow_enabled:
            self._render_glow(renderer)
        
        # Rendu du sprite principal
        self.sprite.draw()
        
        # Effets spéciaux selon le type
        self._render_special_effects(renderer)
    
    def _render_trail(self, renderer):
        """Affiche la traînée du projectile"""
        if len(self.movement.position_history) < 2:
            return
        
        trail = self.effects.trail
        
        for i, pos in enumerate(self.movement.position_history):
            # Calcul de l'opacité selon la position dans la traînée
            alpha_factor = (i + 1) / len(self.movement.position_history)
            alpha_factor *= trail.fade_rate ** (len(self.movement.position_history) - i - 1)
            
            alpha = int(255 * alpha_factor)
            if alpha < 10:
                continue
            
            # Taille décroissante
            size = 4 * alpha_factor
            
            # Couleur avec transparence
            color = (*trail.color, alpha)
            
            arcade.draw_circle_filled(pos[0], pos[1], size, color)
            
            # Particules additionnelles
            if trail.particles and random.random() < 0.3:
                particle_offset_x = random.uniform(-3, 3)
                particle_offset_y = random.uniform(-3, 3)
                particle_size = random.uniform(1, 3) * alpha_factor
                
                arcade.draw_circle_filled(
                    pos[0] + particle_offset_x,
                    pos[1] + particle_offset_y,
                    particle_size,
                    (*trail.color, alpha // 2)
                )
    
    def _render_glow(self, renderer):
        """Affiche l'aura lumineuse"""
        if self.effects.glow_radius <= 0:
            return
        
        # Plusieurs cercles concentriques pour un effet de dégradé
        for i in range(3):
            radius = self.effects.glow_radius * (1.0 - i * 0.3)
            alpha = int(50 * (1.0 - i * 0.4))
            
            color = (*self.effects.glow_color, alpha)
            
            arcade.draw_circle_filled(
                self.movement.position[0],
                self.movement.position[1],
                radius,
                color
            )
    
    def _render_special_effects(self, renderer):
        """Affiche les effets spéciaux selon le type"""
        if self.projectile_type == ProjectileType.LIGHTNING_BOLT:
            self._render_lightning_effects()
        elif self.projectile_type == ProjectileType.FLAME_BURST:
            self._render_flame_effects()
        elif self.projectile_type == ProjectileType.ICE_CRYSTAL:
            self._render_ice_effects()
    
    def _render_lightning_effects(self):
        """Effets spéciaux pour les éclairs"""
        # Arcs électriques aléatoires autour du projectile
        center_x, center_y = self.movement.position
        
        for _ in range(2):
            # Points aléatoires autour du projectile
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(5, 15)
            
            end_x = center_x + math.cos(angle) * distance
            end_y = center_y + math.sin(angle) * distance
            
            # Arc électrique en zigzag
            segments = 3
            points = [(center_x, center_y)]
            
            for i in range(1, segments):
                t = i / segments
                mid_x = center_x + (end_x - center_x) * t
                mid_y = center_y + (end_y - center_y) * t
                
                # Zigzag aléatoire
                offset_x = random.uniform(-3, 3)
                offset_y = random.uniform(-3, 3)
                
                points.append((mid_x + offset_x, mid_y + offset_y))
            
            points.append((end_x, end_y))
            
            # Dessin des segments
            for i in range(len(points) - 1):
                arcade.draw_line(
                    points[i][0], points[i][1],
                    points[i + 1][0], points[i + 1][1],
                    SteampunkColors.ELECTRIC_BLUE, 2
                )
    
    def _render_flame_effects(self):
        """Effets spéciaux pour les flammes"""
        # Particules de feu autour du projectile
        center_x, center_y = self.movement.position
        
        for _ in range(4):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(2, 8)
            size = random.uniform(2, 5)
            
            particle_x = center_x + math.cos(angle) * distance
            particle_y = center_y + math.sin(angle) * distance
            
            # Dégradé de couleur du feu
            colors = [
                SteampunkColors.FIRE_ORANGE,
                (255, 69, 0),  # Rouge orangé
                (255, 255, 0)  # Jaune
            ]
            
            color = random.choice(colors)
            alpha = random.randint(100, 200)
            
            arcade.draw_circle_filled(
                particle_x, particle_y, size,
                (*color, alpha)
            )
    
    def _render_ice_effects(self):
        """Effets spéciaux pour la glace"""
        # Cristaux de glace qui scintillent
        center_x, center_y = self.movement.position
        
        # Effet de scintillement
        if random.random() < 0.4:
            sparkle_angle = random.uniform(0, 2 * math.pi)
            sparkle_distance = random.uniform(8, 16)
            
            sparkle_x = center_x + math.cos(sparkle_angle) * sparkle_distance
            sparkle_y = center_y + math.sin(sparkle_angle) * sparkle_distance
            
            arcade.draw_circle_filled(
                sparkle_x, sparkle_y, 2,
                (255, 255, 255, 180)
            )
        
        # Traînée cristalline
        if len(self.movement.position_history) > 2:
            last_pos = self.movement.position_history[-2]
            
            # Ligne de cristaux
            num_crystals = 3
            for i in range(num_crystals):
                t = (i + 1) / (num_crystals + 1)
                
                crystal_x = last_pos[0] + (center_x - last_pos[0]) * t
                crystal_y = last_pos[1] + (center_y - last_pos[1]) * t
                
                crystal_size = 3 * (1 - t)
                alpha = int(150 * (1 - t))
                
                arcade.draw_circle_filled(
                    crystal_x, crystal_y, crystal_size,
                    (173, 216, 230, alpha)
                )
    
    # ═══════════════════════════════════════════════════════════
    # PROPRIÉTÉS ET ACCESSEURS
    # ═══════════════════════════════════════════════════════════
    
    def has_hit_target(self) -> bool:
        """Retourne si le projectile a atteint sa cible"""
        return self.movement.has_hit
    
    def is_expired(self) -> bool:
        """Retourne si le projectile doit être supprimé"""
        return (self.movement.travel_time >= self.movement.max_travel_time or
                (self.has_exploded and self.projectile_type != ProjectileType.MINE))
    
    def get_position(self) -> Tuple[float, float]:
        """Retourne la position actuelle"""
        return self.movement.position
    
    def get_damage(self) -> int:
        """Retourne les dégâts du projectile"""
        return self.damage
    
    def get_travel_distance(self) -> float:
        """Retourne la distance parcourue"""
        start_pos = self.movement.start_position
        current_pos = self.movement.position
        
        return math.sqrt(
            (current_pos[0] - start_pos[0]) ** 2 +
            (current_pos[1] - start_pos[1]) ** 2
        )
    
    def set_target_position(self, new_target: Tuple[float, float]):
        """Met à jour la position cible (pour les projectiles à poursuite)"""
        if self.movement.movement_type == ProjectileMovementType.HOMING:
            self.movement.target_position = new_target
    
    def destroy(self):
        """Détruit le projectile immédiatement"""
        self.is_active = False
        self.movement.has_hit = True
        self.has_exploded = True
    
    def get_debug_info(self) -> List[str]:
        """Retourne des informations de debug"""
        return [
            f"Type: {self.projectile_type.value}",
            f"Damage: {self.damage}",
            f"Position: ({self.movement.position[0]:.1f}, {self.movement.position[1]:.1f})",
            f"Velocity: ({self.movement.velocity[0]:.1f}, {self.movement.velocity[1]:.1f})",
            f"Travel Time: {self.movement.travel_time:.1f}s",
            f"Hit Target: {self.movement.has_hit}",
            f"Exploded: {self.has_exploded}",
            f"Movement Type: {self.movement.movement_type.value}",
            f"Speed: {self.movement.speed:.1f}"
        ]


# ═══════════════════════════════════════════════════════════
# SYSTÈME DE GESTION DES PROJECTILES
# ═══════════════════════════════════════════════════════════

class ProjectileManager:
    """Gestionnaire centralisé pour tous les projectiles"""
    
    def __init__(self, sprite_factory: SteampunkSpriteFactory):
        self.sprite_factory = sprite_factory
        self.active_projectiles: List[Projectile] = []
        self.projectile_pool: Dict[ProjectileType, List[Projectile]] = {}
        self.logger = logging.getLogger('ProjectileManager')
        
        # Limitations de performance
        self.max_projectiles = 200
        self.cleanup_interval = 1.0
        self.cleanup_timer = 0.0
    
    def create_projectile(self, projectile_type: ProjectileType, start_position: Tuple[float, float],
                         target_position: Tuple[float, float], damage: int, speed: float,
                         tower_stats: TowerStats) -> Optional[Projectile]:
        """Crée un nouveau projectile"""
        
        # Vérification de la limite
        if len(self.active_projectiles) >= self.max_projectiles:
            self.logger.warning("Limite de projectiles atteinte")
            return None
        
        projectile = Projectile(
            projectile_type, start_position, target_position,
            damage, speed, tower_stats, self.sprite_factory
        )
        
        self.active_projectiles.append(projectile)
        
        self.logger.debug(f"Projectile créé: {projectile_type.value}")
        return projectile
    
    def update(self, delta_time: float):
        """Met à jour tous les projectiles"""
        self.cleanup_timer += delta_time
        
        # Mise à jour des projectiles actifs
        for projectile in self.active_projectiles:
            projectile.update(delta_time)
        
        # Nettoyage périodique
        if self.cleanup_timer >= self.cleanup_interval:
            self._cleanup_expired_projectiles()
            self.cleanup_timer = 0.0
    
    def _cleanup_expired_projectiles(self):
        """Supprime les projectiles expirés"""
        initial_count = len(self.active_projectiles)
        
        self.active_projectiles = [
            p for p in self.active_projectiles 
            if not p.is_expired()
        ]
        
        removed_count = initial_count - len(self.active_projectiles)
        if removed_count > 0:
            self.logger.debug(f"Nettoyage: {removed_count} projectiles supprimés")
    
    def render_all(self, renderer):
        """Rendu de tous les projectiles actifs"""
        for projectile in self.active_projectiles:
            projectile.render(renderer)
    
    def get_projectiles_in_radius(self, center: Tuple[float, float], 
                                 radius: float) -> List[Projectile]:
        """Retourne les projectiles dans un rayon donné"""
        result = []
        
        for projectile in self.active_projectiles:
            pos = projectile.get_position()
            distance = math.sqrt(
                (pos[0] - center[0]) ** 2 + 
                (pos[1] - center[1]) ** 2
            )
            
            if distance <= radius:
                result.append(projectile)
        
        return result
    
    def clear_all(self):
        """Supprime tous les projectiles"""
        count = len(self.active_projectiles)
        self.active_projectiles.clear()
        self.logger.info(f"Tous les projectiles supprimés ({count})")
    
    def get_projectile_count(self) -> int:
        """Retourne le nombre de projectiles actifs"""
        return len(self.active_projectiles)
    
    def get_debug_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques de debug"""
        projectile_types = {}
        for projectile in self.active_projectiles:
            ptype = projectile.projectile_type.value
            projectile_types[ptype] = projectile_types.get(ptype, 0) + 1
        
        return {
            'total_projectiles': len(self.active_projectiles),
            'max_projectiles': self.max_projectiles,
            'projectile_types': projectile_types,
            'memory_usage': len(self.active_projectiles) * 1024  # Estimation approximative
        }