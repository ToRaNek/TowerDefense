# gameplay/entities/enemy.py
"""
Steam Defense - Système d'ennemis
Définit tous les types d'ennemis et leurs comportements
"""

import arcade
import math
import random
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
import logging

from gameplay.entities.entity import Entity, EntityComponent
from graphics.sprite_factory import SteampunkSpriteFactory, SpriteType
from config.settings import SteampunkColors, GAMEPLAY_BALANCE
from world.pathfinding import PathfindingResult


class EnemyType(Enum):
    """Types d'ennemis disponibles"""
    STEAM_SOLDIER = "steam_soldier"
    SKY_ZEPPELIN = "sky_zeppelin"
    STEAM_TANK = "steam_tank"
    LIGHTNING_DRONE = "lightning_drone"
    STEEL_SPIDER = "steel_spider"
    IRON_GOLEM = "iron_golem"
    CYBER_SURVIVOR = "cyber_survivor"


class EnemyState(Enum):
    """États possibles d'un ennemi"""
    SPAWNING = "spawning"
    MOVING = "moving"
    ATTACKING = "attacking"
    STUNNED = "stunned"
    SLOWED = "slowed"
    DYING = "dying"
    DEAD = "dead"


@dataclass
class EnemyStats:
    """Statistiques de base d'un ennemi"""
    max_health: int
    speed: float              # Pixels par seconde
    armor: int               # Réduction de dégâts
    reward: int              # Or donné à la mort
    
    # Résistances (0.0 = pas de résistance, 1.0 = immunité totale)
    physical_resistance: float = 0.0
    fire_resistance: float = 0.0
    electric_resistance: float = 0.0
    ice_resistance: float = 0.0
    
    # Propriétés spéciales
    is_flying: bool = False
    can_regenerate: bool = False
    explosion_damage: int = 0
    explosion_radius: float = 0.0


class HealthComponent(EntityComponent):
    """Composant de santé pour les ennemis"""
    
    def __init__(self, max_health: int):
        super().__init__()
        self.max_health = max_health
        self.current_health = max_health
        self.armor = 0
        self.is_alive = True
        
        # Effets temporaires
        self.damage_over_time_effects: List[Dict] = []
        self.heal_over_time_effects: List[Dict] = []
    
    def take_damage(self, damage: int, damage_type: str = "physical") -> bool:
        """
        Inflige des dégâts à l'ennemi
        
        Args:
            damage: Montant des dégâts
            damage_type: Type de dégâts
            
        Returns:
            bool: True si l'ennemi est mort
        """
        if not self.is_alive:
            return True
        
        # Application de l'armure
        effective_damage = max(1, damage - self.armor)
        
        self.current_health -= effective_damage
        
        if self.current_health <= 0:
            self.current_health = 0
            self.is_alive = False
            return True
        
        return False
    
    def heal(self, amount: int):
        """Soigne l'ennemi"""
        if self.is_alive:
            self.current_health = min(self.max_health, self.current_health + amount)
    
    def add_damage_over_time(self, damage_per_second: int, duration: float, damage_type: str = "fire"):
        """Ajoute un effet de dégâts sur la durée"""
        effect = {
            'damage_per_second': damage_per_second,
            'remaining_time': duration,
            'damage_type': damage_type,
            'next_tick': 1.0
        }
        self.damage_over_time_effects.append(effect)
    
    def update(self, delta_time: float):
        """Met à jour les effets temporaires"""
        # Mise à jour des DoT
        for effect in self.damage_over_time_effects[:]:
            effect['remaining_time'] -= delta_time
            effect['next_tick'] -= delta_time
            
            if effect['next_tick'] <= 0:
                self.take_damage(effect['damage_per_second'], effect['damage_type'])
                effect['next_tick'] = 1.0
            
            if effect['remaining_time'] <= 0:
                self.damage_over_time_effects.remove(effect)
        
        # Mise à jour des HoT
        for effect in self.heal_over_time_effects[:]:
            effect['remaining_time'] -= delta_time
            effect['next_tick'] -= delta_time
            
            if effect['next_tick'] <= 0:
                self.heal(effect['heal_per_second'])
                effect['next_tick'] = 1.0
            
            if effect['remaining_time'] <= 0:
                self.heal_over_time_effects.remove(effect)
    
    def get_health_percentage(self) -> float:
        """Retourne le pourcentage de vie restant"""
        return self.current_health / self.max_health if self.max_health > 0 else 0.0


class MovementComponent(EntityComponent):
    """Composant de mouvement pour les ennemis"""
    
    def __init__(self, base_speed: float):
        super().__init__()
        self.base_speed = base_speed
        self.current_speed = base_speed
        self.position = (0.0, 0.0)
        self.target_position: Optional[Tuple[float, float]] = None
        self.path: List[Tuple[int, int]] = []
        self.path_index = 0
        self.reached_end = False
        
        # Effets de mouvement
        self.speed_modifiers: List[Dict] = []
        self.is_stunned = False
        self.stun_duration = 0.0
    
    def set_path(self, path: List[Tuple[int, int]]):
        """Définit le chemin à suivre"""
        self.path = path.copy()
        self.path_index = 0
        self.reached_end = False
        
        if self.path:
            self.position = (float(self.path[0][0] * 32 + 16), 
                           float(self.path[0][1] * 32 + 16))
            self._update_target()
    
    def _update_target(self):
        """Met à jour la position cible suivante"""
        if self.path_index + 1 < len(self.path):
            next_tile = self.path[self.path_index + 1]
            self.target_position = (next_tile[0] * 32 + 16, next_tile[1] * 32 + 16)
        else:
            self.target_position = None
            self.reached_end = True
    
    def add_speed_modifier(self, multiplier: float, duration: float, source: str):
        """Ajoute un modificateur de vitesse temporaire"""
        modifier = {
            'multiplier': multiplier,
            'remaining_time': duration,
            'source': source
        }
        self.speed_modifiers.append(modifier)
    
    def stun(self, duration: float):
        """Étourdit l'ennemi"""
        self.is_stunned = True
        self.stun_duration = max(self.stun_duration, duration)
    
    def update(self, delta_time: float):
        """Met à jour le mouvement"""
        # Mise à jour de l'étourdissement
        if self.is_stunned:
            self.stun_duration -= delta_time
            if self.stun_duration <= 0:
                self.is_stunned = False
                self.stun_duration = 0.0
            return  # Pas de mouvement si étourdi
        
        # Mise à jour des modificateurs de vitesse
        for modifier in self.speed_modifiers[:]:
            modifier['remaining_time'] -= delta_time
            if modifier['remaining_time'] <= 0:
                self.speed_modifiers.remove(modifier)
        
        # Calcul de la vitesse effective
        speed_multiplier = 1.0
        for modifier in self.speed_modifiers:
            speed_multiplier *= modifier['multiplier']
        
        self.current_speed = self.base_speed * speed_multiplier
        
        # Mouvement vers la cible
        if self.target_position and not self.reached_end:
            self._move_towards_target(delta_time)
    
    def _move_towards_target(self, delta_time: float):
        """Déplace l'ennemi vers sa cible"""
        current_x, current_y = self.position
        target_x, target_y = self.target_position
        
        # Calcul de la direction
        dx = target_x - current_x
        dy = target_y - current_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < 2.0:  # Assez proche de la cible
            self.position = self.target_position
            self.path_index += 1
            self._update_target()
        else:
            # Mouvement vers la cible
            move_distance = self.current_speed * delta_time
            if move_distance > distance:
                move_distance = distance
            
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance
            
            self.position = (current_x + move_x, current_y + move_y)


class StatusEffectComponent(EntityComponent):
    """Composant pour gérer les effets de statut"""
    
    def __init__(self):
        super().__init__()
        self.active_effects: Dict[str, Dict] = {}
    
    def add_effect(self, effect_type: str, duration: float, **params):
        """Ajoute un effet de statut"""
        self.active_effects[effect_type] = {
            'duration': duration,
            'remaining_time': duration,
            **params
        }
    
    def remove_effect(self, effect_type: str):
        """Supprime un effet de statut"""
        if effect_type in self.active_effects:
            del self.active_effects[effect_type]
    
    def has_effect(self, effect_type: str) -> bool:
        """Vérifie si un effet est actif"""
        return effect_type in self.active_effects
    
    def get_effect(self, effect_type: str) -> Optional[Dict]:
        """Récupère les données d'un effet"""
        return self.active_effects.get(effect_type)
    
    def update(self, delta_time: float):
        """Met à jour les effets"""
        expired_effects = []
        
        for effect_type, effect_data in self.active_effects.items():
            effect_data['remaining_time'] -= delta_time
            if effect_data['remaining_time'] <= 0:
                expired_effects.append(effect_type)
        
        for effect_type in expired_effects:
            self.remove_effect(effect_type)


class Enemy(Entity):
    """
    Classe de base pour tous les ennemis
    Utilise un système de composants pour la modularité
    """
    
    def __init__(self, enemy_type: EnemyType, position: Tuple[float, float], 
                 sprite_factory: SteampunkSpriteFactory):
        super().__init__()
        
        self.logger = logging.getLogger(f'Enemy.{enemy_type.value}')
        self.enemy_type = enemy_type
        self.sprite_factory = sprite_factory
        
        # Chargement des statistiques
        self.stats = self._load_enemy_stats(enemy_type)
        
        # Ajout des composants
        self.health = HealthComponent(self.stats.max_health)
        self.movement = MovementComponent(self.stats.speed)
        self.status_effects = StatusEffectComponent()
        
        self.add_component(self.health)
        self.add_component(self.movement)
        self.add_component(self.status_effects)
        
        # Sprite et visuel
        self.sprite = self._create_sprite()
        self.sprite.center_x, self.sprite.center_y = position
        self.movement.position = position
        
        # État et comportement
        self.state = EnemyState.SPAWNING
        self.behavior_timer = 0.0
        
        # Effets visuels
        self.damage_flash_timer = 0.0
        self.spawn_animation_timer = 1.0
        
        self.logger.debug(f"Ennemi {enemy_type.value} créé à {position}")
    
    def _load_enemy_stats(self, enemy_type: EnemyType) -> EnemyStats:
        """Charge les statistiques selon le type d'ennemi"""
        stats_database = {
            EnemyType.STEAM_SOLDIER: EnemyStats(
                max_health=100,
                speed=60.0,
                armor=5,
                reward=10,
                physical_resistance=0.0,
                fire_resistance=0.2,
                electric_resistance=0.0,
                ice_resistance=0.0
            ),
            
            EnemyType.SKY_ZEPPELIN: EnemyStats(
                max_health=150,
                speed=40.0,
                armor=10,
                reward=25,
                physical_resistance=0.3,
                fire_resistance=0.0,
                electric_resistance=0.1,
                ice_resistance=0.0,
                is_flying=True
            ),
            
            EnemyType.STEAM_TANK: EnemyStats(
                max_health=400,
                speed=25.0,
                armor=20,
                reward=40,
                physical_resistance=0.4,
                fire_resistance=0.1,
                electric_resistance=0.8,
                ice_resistance=0.2,
                explosion_damage=80,
                explosion_radius=64.0
            ),
            
            EnemyType.LIGHTNING_DRONE: EnemyStats(
                max_health=75,
                speed=80.0,
                armor=0,
                reward=15,
                physical_resistance=0.0,
                fire_resistance=0.0,
                electric_resistance=0.9,
                ice_resistance=0.0,
                is_flying=True
            ),
            
            EnemyType.STEEL_SPIDER: EnemyStats(
                max_health=120,
                speed=90.0,
                armor=8,
                reward=12,
                physical_resistance=0.2,
                fire_resistance=0.8,
                electric_resistance=0.0,
                ice_resistance=0.4
            ),
            
            EnemyType.IRON_GOLEM: EnemyStats(
                max_health=800,
                speed=30.0,
                armor=25,
                reward=80,
                physical_resistance=0.5,
                fire_resistance=0.3,
                electric_resistance=0.2,
                ice_resistance=0.0,
                can_regenerate=True
            ),
            
            EnemyType.CYBER_SURVIVOR: EnemyStats(
                max_health=200,
                speed=55.0,
                armor=12,
                reward=30,
                physical_resistance=0.2,
                fire_resistance=0.2,
                electric_resistance=0.2,
                ice_resistance=0.2
            )
        }
        
        return stats_database[enemy_type]
    
    def _create_sprite(self) -> arcade.Sprite:
        """Crée le sprite de l'ennemi"""
        sprite_type_map = {
            EnemyType.STEAM_SOLDIER: SpriteType.STEAM_SOLDIER,
            EnemyType.SKY_ZEPPELIN: SpriteType.SKY_ZEPPELIN,
            EnemyType.STEAM_TANK: SpriteType.STEAM_TANK,
            EnemyType.LIGHTNING_DRONE: SpriteType.LIGHTNING_DRONE,
            EnemyType.STEEL_SPIDER: SpriteType.STEEL_SPIDER,
            EnemyType.IRON_GOLEM: SpriteType.IRON_GOLEM,
            EnemyType.CYBER_SURVIVOR: SpriteType.CYBER_SURVIVOR
        }
        
        sprite_type = sprite_type_map[self.enemy_type]
        texture = self.sprite_factory.create_sprite(sprite_type)
        
        sprite = arcade.Sprite()
        sprite.texture = texture
        sprite.scale = 1.0
        
        return sprite
    
    def set_path(self, path: List[Tuple[int, int]]):
        """Définit le chemin que l'ennemi doit suivre"""
        self.movement.set_path(path)
        if self.state == EnemyState.SPAWNING:
            self.state = EnemyState.MOVING
    
    def take_damage(self, damage: int, damage_type: str = "physical", 
                   source_position: Optional[Tuple[float, float]] = None) -> bool:
        """
        Fait subir des dégâts à l'ennemi
        
        Args:
            damage: Montant des dégâts
            damage_type: Type de dégâts
            source_position: Position de la source des dégâts
            
        Returns:
            bool: True si l'ennemi est mort
        """
        if not self.health.is_alive:
            return True
        
        # Application des résistances
        resistance = getattr(self.stats, f"{damage_type}_resistance", 0.0)
        effective_damage = int(damage * (1.0 - resistance))
        
        # Effet visuel de dégâts
        self.damage_flash_timer = 0.2
        
        # Application des dégâts
        is_dead = self.health.take_damage(effective_damage, damage_type)
        
        if is_dead:
            self._on_death()
            return True
        
        return False
    
    def apply_effect(self, effect_type: str, duration: float, **params):
        """Applique un effet de statut à l'ennemi"""
        self.status_effects.add_effect(effect_type, duration, **params)
        
        # Gestion des effets spéciaux
        if effect_type == "slow":
            multiplier = params.get('speed_multiplier', 0.5)
            self.movement.add_speed_modifier(multiplier, duration, "slow_effect")
        
        elif effect_type == "stun":
            self.movement.stun(duration)
        
        elif effect_type == "burn":
            damage_per_second = params.get('damage_per_second', 10)
            self.health.add_damage_over_time(damage_per_second, duration, "fire")
        
        elif effect_type == "freeze":
            self.movement.add_speed_modifier(0.1, duration, "freeze_effect")
    
    def update(self, delta_time: float):
        """Met à jour l'ennemi"""
        if not self.health.is_alive:
            return
        
        # Mise à jour des timers
        self.behavior_timer += delta_time
        
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= delta_time
        
        if self.spawn_animation_timer > 0:
            self.spawn_animation_timer -= delta_time
        
        # Mise à jour des composants
        self.health.update(delta_time)
        self.movement.update(delta_time)
        self.status_effects.update(delta_time)
        
        # Mise à jour de la position du sprite
        self.sprite.center_x, self.sprite.center_y = self.movement.position
        
        # Comportements spéciaux selon le type
        self._update_special_behavior(delta_time)
        
        # Mise à jour de l'état
        self._update_state(delta_time)
    
    def _update_special_behavior(self, delta_time: float):
        """Met à jour les comportements spéciaux selon le type d'ennemi"""
        if self.enemy_type == EnemyType.IRON_GOLEM and self.stats.can_regenerate:
            # Régénération lente
            if self.behavior_timer >= 2.0:  # Toutes les 2 secondes
                if self.health.current_health < self.stats.max_health:
                    self.health.heal(5)
                self.behavior_timer = 0.0
        
        elif self.enemy_type == EnemyType.CYBER_SURVIVOR:
            # Changement aléatoire de résistances
            if self.behavior_timer >= 5.0:
                self._randomize_cyber_resistances()
                self.behavior_timer = 0.0
        
        elif self.enemy_type == EnemyType.LIGHTNING_DRONE:
            # Comportement d'attaque en chaîne (pour plus tard)
            pass
    
    def _randomize_cyber_resistances(self):
        """Change les résistances du Cyber Survivor aléatoirement"""
        resistance_types = ['physical', 'fire', 'electric', 'ice']
        chosen_type = random.choice(resistance_types)
        
        # Reset toutes les résistances
        for res_type in resistance_types:
            setattr(self.stats, f"{res_type}_resistance", 0.1)
        
        # Boost une résistance aléatoire
        setattr(self.stats, f"{chosen_type}_resistance", 0.8)
        
        self.logger.debug(f"Cyber Survivor résistance changée vers {chosen_type}")
    
    def _update_state(self, delta_time: float):
        """Met à jour l'état de l'ennemi"""
        if self.state == EnemyState.SPAWNING:
            if self.spawn_animation_timer <= 0:
                self.state = EnemyState.MOVING
        
        elif self.state == EnemyState.MOVING:
            if self.movement.reached_end:
                self.state = EnemyState.ATTACKING
        
        elif self.state == EnemyState.ATTACKING:
            # L'ennemi a atteint la base
            pass
    
    def _on_death(self):
        """Appelé quand l'ennemi meurt"""
        self.state = EnemyState.DYING
        
        # Explosion pour le Steam Tank
        if (self.enemy_type == EnemyType.STEAM_TANK and 
            self.stats.explosion_damage > 0):
            self._trigger_explosion()
        
        self.logger.debug(f"Ennemi {self.enemy_type.value} mort")
    
    def _trigger_explosion(self):
        """Déclenche l'explosion du Steam Tank"""
        # Cette méthode sera appelée par le système de combat
        # pour infliger des dégâts de zone
        explosion_data = {
            'position': self.movement.position,
            'damage': self.stats.explosion_damage,
            'radius': self.stats.explosion_radius,
            'damage_type': 'fire'
        }
        
        # Émission d'un événement pour l'explosion
        self.emit_event('enemy_explosion', explosion_data)
    
    def render(self, renderer):
        """Rendu personnalisé de l'ennemi"""
        # Effet de flash quand l'ennemi prend des dégâts
        if self.damage_flash_timer > 0:
            # Teinte rouge temporaire
            self.sprite.color = (255, 200, 200)
        else:
            self.sprite.color = (255, 255, 255)
        
        # Animation de spawn
        if self.spawn_animation_timer > 0:
            scale_factor = 1.0 - (self.spawn_animation_timer * 0.5)
            self.sprite.scale = max(0.5, scale_factor)
        else:
            self.sprite.scale = 1.0
        
        # Rendu du sprite principal
        self.sprite.draw()
        
        # Barre de vie si l'ennemi est blessé
        if self.health.current_health < self.stats.max_health:
            self._render_health_bar(renderer)
        
        # Indicateurs d'effets de statut
        self._render_status_indicators(renderer)
    
    def _render_health_bar(self, renderer):
        """Affiche la barre de vie de l'ennemi"""
        bar_width = 24
        bar_height = 4
        x = self.sprite.center_x - bar_width // 2
        y = self.sprite.center_y + self.sprite.height // 2 + 8
        
        # Fond de la barre (rouge)
        arcade.draw_rectangle_filled(x + bar_width//2, y + bar_height//2, 
                                   bar_width, bar_height, arcade.color.RED)
        
        # Barre de vie (verte)
        health_percentage = self.health.get_health_percentage()
        health_width = int(bar_width * health_percentage)
        
        if health_width > 0:
            arcade.draw_rectangle_filled(x + health_width//2, y + bar_height//2,
                                       health_width, bar_height, arcade.color.GREEN)
        
        # Contour
        arcade.draw_rectangle_outline(x + bar_width//2, y + bar_height//2,
                                    bar_width, bar_height, arcade.color.BLACK, 1)
    
    def _render_status_indicators(self, renderer):
        """Affiche les indicateurs d'effets de statut"""
        indicator_size = 8
        indicator_y = self.sprite.center_y - self.sprite.height // 2 - 12
        indicator_x_start = self.sprite.center_x - 16
        
        indicator_index = 0
        colors = SteampunkColors()
        
        # Indicateurs des effets actifs
        if self.status_effects.has_effect('slow'):
            arcade.draw_circle_filled(
                indicator_x_start + indicator_index * (indicator_size + 2),
                indicator_y, indicator_size // 2, colors.ELECTRIC_BLUE
            )
            indicator_index += 1
        
        if self.status_effects.has_effect('burn'):
            arcade.draw_circle_filled(
                indicator_x_start + indicator_index * (indicator_size + 2),
                indicator_y, indicator_size // 2, colors.FIRE_ORANGE
            )
            indicator_index += 1
        
        if self.movement.is_stunned:
            arcade.draw_circle_filled(
                indicator_x_start + indicator_index * (indicator_size + 2),
                indicator_y, indicator_size // 2, colors.GOLD
            )
            indicator_index += 1
    
    # ═══════════════════════════════════════════════════════════
    # PROPRIÉTÉS ET ACCESSEURS
    # ═══════════════════════════════════════════════════════════
    
    def is_alive(self) -> bool:
        """Retourne si l'ennemi est vivant"""
        return self.health.is_alive
    
    def is_flying(self) -> bool:
        """Retourne si l'ennemi vole"""
        return self.stats.is_flying
    
    def has_reached_end(self) -> bool:
        """Retourne si l'ennemi a atteint la fin du chemin"""
        return self.movement.reached_end
    
    def get_position(self) -> Tuple[float, float]:
        """Retourne la position actuelle"""
        return self.movement.position
    
    def get_reward(self) -> int:
        """Retourne la récompense pour tuer cet ennemi"""
        return self.stats.reward
    
    def get_distance_traveled(self) -> float:
        """Retourne la distance parcourue sur le chemin"""
        if not self.movement.path:
            return 0.0
        
        total_distance = 0.0
        for i in range(self.movement.path_index):
            if i + 1 < len(self.movement.path):
                x1, y1 = self.movement.path[i]
                x2, y2 = self.movement.path[i + 1]
                total_distance += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        
        # Distance partielle vers la cible actuelle
        if self.movement.target_position and self.movement.path_index < len(self.movement.path):
            current_x, current_y = self.movement.position
            start_tile = self.movement.path[self.movement.path_index]
            start_x, start_y = start_tile[0] * 32 + 16, start_tile[1] * 32 + 16
            
            partial_distance = math.sqrt((current_x - start_x) ** 2 + (current_y - start_y) ** 2)
            total_distance += partial_distance
        
        return total_distance
    
    def get_debug_info(self) -> List[str]:
        """Retourne des informations de debug"""
        return [
            f"Type: {self.enemy_type.value}",
            f"HP: {self.health.current_health}/{self.stats.max_health}",
            f"Speed: {self.movement.current_speed:.1f}",
            f"Position: ({self.movement.position[0]:.1f}, {self.movement.position[1]:.1f})",
            f"State: {self.state.value}",
            f"Path: {self.movement.path_index}/{len(self.movement.path)}",
            f"Effects: {list(self.status_effects.active_effects.keys())}"
        ]


# ═══════════════════════════════════════════════════════════
# FACTORY POUR CRÉER LES ENNEMIS
# ═══════════════════════════════════════════════════════════

class EnemyFactory:
    """Factory pour créer des ennemis selon leur type"""
    
    def __init__(self, sprite_factory: SteampunkSpriteFactory):
        self.sprite_factory = sprite_factory
        self.logger = logging.getLogger('EnemyFactory')
    
    def create_enemy(self, enemy_type: EnemyType, position: Tuple[float, float], 
                    level_multiplier: float = 1.0) -> Enemy:
        """
        Crée un ennemi du type spécifié
        
        Args:
            enemy_type: Type d'ennemi à créer
            position: Position de spawn
            level_multiplier: Multiplicateur de niveau pour la difficulté
            
        Returns:
            Enemy: Instance de l'ennemi créé
        """
        enemy = Enemy(enemy_type, position, self.sprite_factory)
        
        # Application du multiplicateur de niveau
        if level_multiplier != 1.0:
            enemy.stats.max_health = int(enemy.stats.max_health * level_multiplier)
            enemy.health.max_health = enemy.stats.max_health
            enemy.health.current_health = enemy.stats.max_health
            enemy.stats.speed *= min(1.5, 1.0 + (level_multiplier - 1.0) * 0.3)  # Vitesse limitée
            enemy.stats.reward = int(enemy.stats.reward * level_multiplier)
        
        self.logger.debug(f"Ennemi créé: {enemy_type.value} (niveau {level_multiplier:.1f})")
        
        return enemy
    
    def create_wave_enemies(self, wave_config: Dict[str, Any], 
                          spawn_position: Tuple[float, float]) -> List[Enemy]:
        """
        Crée une liste d'ennemis pour une vague
        
        Args:
            wave_config: Configuration de la vague
            spawn_position: Position de spawn
            
        Returns:
            List[Enemy]: Liste des ennemis créés
        """
        enemies = []
        level_multiplier = wave_config.get('level_multiplier', 1.0)
        
        for enemy_config in wave_config.get('enemies', []):
            enemy_type = EnemyType(enemy_config['type'])
            count = enemy_config.get('count', 1)
            
            for _ in range(count):
                enemy = self.create_enemy(enemy_type, spawn_position, level_multiplier)
                enemies.append(enemy)
        
        self.logger.info(f"Vague créée: {len(enemies)} ennemis")
        
        return enemies