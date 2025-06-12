# gameplay/entities/tower.py
"""
Steam Defense - Système de tours défensives
Définit tous les types de tours et leurs mécaniques d'attaque
"""

import arcade
import math
import random
from typing import List, Tuple, Optional, Dict, Any, Set
from enum import Enum
from dataclasses import dataclass
import logging

from gameplay.entities.entity import Entity, EntityComponent
from gameplay.entities.enemy import Enemy, EnemyType
from gameplay.entities.projectile import Projectile, ProjectileType
from graphics.sprite_factory import SteampunkSpriteFactory, SpriteType
from config.settings import SteampunkColors, GAMEPLAY_BALANCE


class TowerType(Enum):
    """Types de tours disponibles"""
    STEAM_CANNON = "steam_cannon"
    LIGHTNING_TOWER = "lightning_tower"
    FLAME_THROWER = "flame_thrower"
    ANTI_AIR_GUN = "anti_air_gun"
    BRONZE_MORTAR = "bronze_mortar"
    CRYO_STEAM = "cryo_steam"
    MINE_LAYER = "mine_layer"
    SNIPER_MECHA = "sniper_mecha"
    SHIELD_GENERATOR = "shield_generator"


class TargetingMode(Enum):
    """Modes de ciblage disponibles"""
    FIRST = "first"           # Premier ennemi
    LAST = "last"            # Dernier ennemi
    CLOSEST = "closest"      # Plus proche
    STRONGEST = "strongest"  # Plus de PV
    WEAKEST = "weakest"     # Moins de PV
    FLYING = "flying"       # Priorité aux volants


@dataclass
class TowerStats:
    """Statistiques de base d'une tour"""
    cost: int                # Coût de construction
    damage: int              # Dégâts de base
    range: float             # Portée en pixels
    attack_speed: float      # Attaques par seconde
    projectile_speed: float  # Vitesse des projectiles
    
    # Propriétés spéciales
    area_damage: bool = False
    area_radius: float = 0.0
    pierce_count: int = 0     # Nombre d'ennemis traversés
    chain_count: int = 0      # Nombre de chaînes
    
    # Restrictions de ciblage
    can_target_ground: bool = True
    can_target_air: bool = True
    
    # Effets spéciaux
    slow_effect: float = 0.0      # Multiplicateur de ralentissement
    slow_duration: float = 0.0    # Durée du ralentissement
    stun_duration: float = 0.0    # Durée d'étourdissement
    burn_damage: int = 0          # Dégâts de brûlure par seconde
    burn_duration: float = 0.0    # Durée de brûlure


class AttackComponent(EntityComponent):
    """Composant d'attaque pour les tours"""
    
    def __init__(self, stats: TowerStats):
        super().__init__()
        self.stats = stats
        self.attack_timer = 0.0
        self.target: Optional[Enemy] = None
        self.targeting_mode = TargetingMode.FIRST
        
        # Historique des cibles pour éviter les répétitions
        self.recent_targets: Set[int] = set()
        self.target_history_duration = 2.0
        self.target_history_timer = 0.0
    
    def can_attack(self) -> bool:
        """Vérifie si la tour peut attaquer"""
        return self.attack_timer <= 0.0
    
    def set_target(self, target: Optional[Enemy]):
        """Définit la cible actuelle"""
        self.target = target
        if target:
            self.recent_targets.add(id(target))
    
    def get_target(self) -> Optional[Enemy]:
        """Retourne la cible actuelle"""
        return self.target
    
    def start_attack(self):
        """Démarre une attaque"""
        if self.can_attack():
            self.attack_timer = 1.0 / self.stats.attack_speed
    
    def update(self, delta_time: float):
        """Met à jour le composant d'attaque"""
        if self.attack_timer > 0:
            self.attack_timer -= delta_time
        
        # Nettoyage de l'historique des cibles
        self.target_history_timer += delta_time
        if self.target_history_timer >= self.target_history_duration:
            self.recent_targets.clear()
            self.target_history_timer = 0.0
        
        # Vérification de la validité de la cible
        if self.target and (not self.target.is_alive() or not self._is_target_in_range()):
            self.target = None


class TargetingComponent(EntityComponent):
    """Composant de ciblage pour les tours"""
    
    def __init__(self, range_radius: float):
        super().__init__()
        self.range = range_radius
        self.targeting_mode = TargetingMode.FIRST
        self.enemy_priorities: Dict[EnemyType, float] = {}
        
        # Historique pour éviter le spam de ciblage
        self.last_scan_time = 0.0
        self.scan_interval = 0.1  # Scan toutes les 100ms
    
    def find_target(self, tower_position: Tuple[float, float], 
                   enemies: List[Enemy], delta_time: float) -> Optional[Enemy]:
        """
        Trouve la meilleure cible selon le mode de ciblage
        
        Args:
            tower_position: Position de la tour
            enemies: Liste des ennemis disponibles
            delta_time: Temps écoulé
            
        Returns:
            Enemy ou None: Meilleure cible trouvée
        """
        self.last_scan_time += delta_time
        
        # Limite la fréquence de scan pour les performances
        if self.last_scan_time < self.scan_interval:
            return None
        
        self.last_scan_time = 0.0
        
        # Filtrage des ennemis dans la portée
        targets_in_range = []
        for enemy in enemies:
            if enemy.is_alive() and self._is_enemy_in_range(tower_position, enemy):
                targets_in_range.append(enemy)
        
        if not targets_in_range:
            return None
        
        # Sélection selon le mode de ciblage
        return self._select_best_target(tower_position, targets_in_range)
    
    def _is_enemy_in_range(self, tower_position: Tuple[float, float], enemy: Enemy) -> bool:
        """Vérifie si un ennemi est dans la portée"""
        enemy_pos = enemy.get_position()
        distance = math.sqrt(
            (tower_position[0] - enemy_pos[0]) ** 2 + 
            (tower_position[1] - enemy_pos[1]) ** 2
        )
        return distance <= self.range
    
    def _select_best_target(self, tower_position: Tuple[float, float], 
                          candidates: List[Enemy]) -> Optional[Enemy]:
        """Sélectionne la meilleure cible selon le mode de ciblage"""
        if not candidates:
            return None
        
        if self.targeting_mode == TargetingMode.FIRST:
            # Ennemi le plus avancé sur le chemin
            return max(candidates, key=lambda e: e.get_distance_traveled())
        
        elif self.targeting_mode == TargetingMode.LAST:
            # Ennemi le moins avancé
            return min(candidates, key=lambda e: e.get_distance_traveled())
        
        elif self.targeting_mode == TargetingMode.CLOSEST:
            # Ennemi le plus proche
            def distance_to_tower(enemy):
                pos = enemy.get_position()
                return math.sqrt(
                    (tower_position[0] - pos[0]) ** 2 + 
                    (tower_position[1] - pos[1]) ** 2
                )
            return min(candidates, key=distance_to_tower)
        
        elif self.targeting_mode == TargetingMode.STRONGEST:
            # Ennemi avec le plus de PV
            return max(candidates, key=lambda e: e.health.current_health)
        
        elif self.targeting_mode == TargetingMode.WEAKEST:
            # Ennemi avec le moins de PV
            return min(candidates, key=lambda e: e.health.current_health)
        
        elif self.targeting_mode == TargetingMode.FLYING:
            # Priorité aux ennemis volants
            flying_enemies = [e for e in candidates if e.is_flying()]
            if flying_enemies:
                return max(flying_enemies, key=lambda e: e.get_distance_traveled())
            else:
                return max(candidates, key=lambda e: e.get_distance_traveled())
        
        return candidates[0]


class UpgradeComponent(EntityComponent):
    """Composant d'amélioration pour les tours"""
    
    def __init__(self, base_stats: TowerStats):
        super().__init__()
        self.level = 1
        self.max_level = 5
        self.base_stats = base_stats
        self.current_stats = self._calculate_stats()
        
        # Coûts d'amélioration
        self.upgrade_costs = [
            int(base_stats.cost * 0.5),   # Niveau 2
            int(base_stats.cost * 0.75),  # Niveau 3
            int(base_stats.cost * 1.0),   # Niveau 4
            int(base_stats.cost * 1.5),   # Niveau 5
        ]
    
    def can_upgrade(self) -> bool:
        """Vérifie si la tour peut être améliorée"""
        return self.level < self.max_level
    
    def get_upgrade_cost(self) -> int:
        """Retourne le coût de la prochaine amélioration"""
        if not self.can_upgrade():
            return 0
        return self.upgrade_costs[self.level - 1]
    
    def upgrade(self) -> bool:
        """Améliore la tour d'un niveau"""
        if not self.can_upgrade():
            return False
        
        self.level += 1
        self.current_stats = self._calculate_stats()
        return True
    
    def _calculate_stats(self) -> TowerStats:
        """Calcule les statistiques selon le niveau actuel"""
        # Facteurs d'amélioration par niveau
        damage_multiplier = 1.0 + (self.level - 1) * 0.25  # +25% par niveau
        range_multiplier = 1.0 + (self.level - 1) * 0.10   # +10% par niveau
        speed_multiplier = 1.0 + (self.level - 1) * 0.15   # +15% par niveau
        
        # Création des nouvelles stats
        new_stats = TowerStats(
            cost=self.base_stats.cost,
            damage=int(self.base_stats.damage * damage_multiplier),
            range=self.base_stats.range * range_multiplier,
            attack_speed=self.base_stats.attack_speed * speed_multiplier,
            projectile_speed=self.base_stats.projectile_speed,
            
            area_damage=self.base_stats.area_damage,
            area_radius=self.base_stats.area_radius * range_multiplier,
            pierce_count=self.base_stats.pierce_count,
            chain_count=self.base_stats.chain_count,
            
            can_target_ground=self.base_stats.can_target_ground,
            can_target_air=self.base_stats.can_target_air,
            
            slow_effect=self.base_stats.slow_effect,
            slow_duration=self.base_stats.slow_duration * 1.2,  # +20% durée
            stun_duration=self.base_stats.stun_duration * 1.2,
            burn_damage=int(self.base_stats.burn_damage * damage_multiplier),
            burn_duration=self.base_stats.burn_duration * 1.2
        )
        
        # Améliorations spéciales aux niveaux élevés
        if self.level >= 3:
            new_stats.pierce_count = max(new_stats.pierce_count, 1)
            
        if self.level >= 5:
            # Forme ultime avec bonus spéciaux
            new_stats.chain_count = max(new_stats.chain_count, 2)
            new_stats.area_radius *= 1.5
        
        return new_stats


class Tower(Entity):
    """
    Classe de base pour toutes les tours défensives
    """
    
    def __init__(self, tower_type: TowerType, position: Tuple[float, float],
                 sprite_factory: SteampunkSpriteFactory):
        super().__init__()
        
        self.logger = logging.getLogger(f'Tower.{tower_type.value}')
        self.tower_type = tower_type
        self.sprite_factory = sprite_factory
        self.position = position
        
        # Chargement des statistiques
        self.base_stats = self._load_tower_stats(tower_type)
        
        # Ajout des composants
        self.attack = AttackComponent(self.base_stats)
        self.targeting = TargetingComponent(self.base_stats.range)
        self.upgrade = UpgradeComponent(self.base_stats)
        
        self.add_component(self.attack)
        self.add_component(self.targeting)
        self.add_component(self.upgrade)
        
        # Sprite et visuel
        self.sprite = self._create_sprite()
        self.sprite.center_x, self.sprite.center_y = position
        
        # État et comportement
        self.construction_time = 2.0  # Temps de construction
        self.construction_timer = self.construction_time
        self.is_constructed = False
        
        # Effets visuels
        self.muzzle_flash_timer = 0.0
        self.range_indicator_visible = False
        
        # Projectiles créés
        self.active_projectiles: List[Projectile] = []
        
        self.logger.debug(f"Tour {tower_type.value} créée à {position}")
    
    def _load_tower_stats(self, tower_type: TowerType) -> TowerStats:
        """Charge les statistiques selon le type de tour"""
        stats_database = {
            TowerType.STEAM_CANNON: TowerStats(
                cost=50, damage=120, range=96.0, attack_speed=0.8, projectile_speed=300.0,
                area_damage=True, area_radius=32.0
            ),
            
            TowerType.LIGHTNING_TOWER: TowerStats(
                cost=80, damage=80, range=80.0, attack_speed=1.2, projectile_speed=1000.0,
                chain_count=3, stun_duration=2.0
            ),
            
            TowerType.FLAME_THROWER: TowerStats(
                cost=60, damage=60, range=64.0, attack_speed=3.0, projectile_speed=0.0,
                area_damage=True, area_radius=48.0, burn_damage=10, burn_duration=5.0,
                can_target_air=False
            ),
            
            TowerType.ANTI_AIR_GUN: TowerStats(
                cost=90, damage=100, range=128.0, attack_speed=2.0, projectile_speed=500.0,
                can_target_ground=False, can_target_air=True
            ),
            
            TowerType.BRONZE_MORTAR: TowerStats(
                cost=120, damage=250, range=160.0, attack_speed=0.4, projectile_speed=200.0,
                area_damage=True, area_radius=48.0
            ),
            
            TowerType.CRYO_STEAM: TowerStats(
                cost=70, damage=40, range=80.0, attack_speed=1.0, projectile_speed=0.0,
                area_damage=True, area_radius=64.0, slow_effect=0.5, slow_duration=4.0
            ),
            
            TowerType.MINE_LAYER: TowerStats(
                cost=40, damage=300, range=0.0, attack_speed=0.0, projectile_speed=0.0,
                area_damage=True, area_radius=32.0, can_target_air=False
            ),
            
            TowerType.SNIPER_MECHA: TowerStats(
                cost=150, damage=400, range=200.0, attack_speed=0.6, projectile_speed=800.0,
                pierce_count=2
            ),
            
            TowerType.SHIELD_GENERATOR: TowerStats(
                cost=100, damage=0, range=96.0, attack_speed=0.0, projectile_speed=0.0
            )
        }
        
        return stats_database[tower_type]
    
    def _create_sprite(self) -> arcade.Sprite:
        """Crée le sprite de la tour"""
        sprite_type_map = {
            TowerType.STEAM_CANNON: SpriteType.STEAM_CANNON,
            TowerType.LIGHTNING_TOWER: SpriteType.LIGHTNING_TOWER,
            TowerType.FLAME_THROWER: SpriteType.FLAME_THROWER,
            TowerType.ANTI_AIR_GUN: SpriteType.ANTI_AIR_GUN,
            TowerType.BRONZE_MORTAR: SpriteType.BRONZE_MORTAR,
            TowerType.CRYO_STEAM: SpriteType.CRYO_STEAM,
            TowerType.MINE_LAYER: SpriteType.MINE_LAYER,
            TowerType.SNIPER_MECHA: SpriteType.SNIPER_MECHA,
            TowerType.SHIELD_GENERATOR: SpriteType.SHIELD_GENERATOR
        }
        
        sprite_type = sprite_type_map[self.tower_type]
        texture = self.sprite_factory.create_sprite(sprite_type)
        
        sprite = arcade.Sprite()
        sprite.texture = texture
        sprite.scale = 1.0
        
        return sprite
    
    def update(self, delta_time: float, enemies: List[Enemy]):
        """Met à jour la tour"""
        # Construction
        if not self.is_constructed:
            self.construction_timer -= delta_time
            if self.construction_timer <= 0:
                self.is_constructed = True
                self.logger.debug(f"Tour {self.tower_type.value} construction terminée")
            return
        
        # Mise à jour des timers visuels
        if self.muzzle_flash_timer > 0:
            self.muzzle_flash_timer -= delta_time
        
        # Mise à jour des composants
        self.attack.update(delta_time)
        
        # Ciblage et attaque
        current_stats = self.upgrade.current_stats
        
        # Recherche de cible si nécessaire
        if not self.attack.target:
            new_target = self.targeting.find_target(self.position, enemies, delta_time)
            if new_target:
                self.attack.set_target(new_target)
        
        # Attaque si possible
        if self.attack.target and self.attack.can_attack():
            self._perform_attack()
        
        # Mise à jour des projectiles
        self._update_projectiles(delta_time, enemies)
        
        # Comportements spéciaux selon le type
        self._update_special_behavior(delta_time, enemies)
    
    def _perform_attack(self):
        """Exécute une attaque"""
        if not self.attack.target or not self.is_constructed:
            return
        
        current_stats = self.upgrade.current_stats
        target = self.attack.target
        
        # Démarrage de l'attaque
        self.attack.start_attack()
        self.muzzle_flash_timer = 0.2
        
        # Création du projectile ou application directe des dégâts
        if self.tower_type == TowerType.FLAME_THROWER:
            self._flame_thrower_attack(target)
        elif self.tower_type == TowerType.CRYO_STEAM:
            self._cryo_steam_attack(target)
        elif self.tower_type == TowerType.LIGHTNING_TOWER:
            self._lightning_attack(target)
        elif self.tower_type == TowerType.SHIELD_GENERATOR:
            self._shield_generator_effect()
        else:
            self._create_projectile(target)
        
        self.logger.debug(f"Tour {self.tower_type.value} attaque {target.enemy_type.value}")
    
    def _create_projectile(self, target: Enemy):
        """Crée un projectile vers la cible"""
        projectile_type_map = {
            TowerType.STEAM_CANNON: ProjectileType.CANNONBALL,
            TowerType.ANTI_AIR_GUN: ProjectileType.BULLET,
            TowerType.BRONZE_MORTAR: ProjectileType.MORTAR_SHELL,
            TowerType.SNIPER_MECHA: ProjectileType.SNIPER_BULLET,
        }
        
        projectile_type = projectile_type_map.get(self.tower_type, ProjectileType.BULLET)
        current_stats = self.upgrade.current_stats
        
        # Création du projectile
        projectile = Projectile(
            projectile_type=projectile_type,
            start_position=self.position,
            target_position=target.get_position(),
            damage=current_stats.damage,
            speed=current_stats.projectile_speed,
            tower_stats=current_stats,
            sprite_factory=self.sprite_factory
        )
        
        self.active_projectiles.append(projectile)
        
        # Émission d'un événement pour le système de jeu
        self.emit_event('projectile_created', {
            'projectile': projectile,
            'tower': self,
            'target': target
        })
    
    def _flame_thrower_attack(self, target: Enemy):
        """Attaque lance-flammes (effet immédiat en cône)"""
        current_stats = self.upgrade.current_stats
        
        # Calcul des ennemis dans le cône
        affected_enemies = self._get_enemies_in_cone(target.get_position(), 
                                                   current_stats.area_radius,
                                                   60)  # Cône de 60 degrés
        
        for enemy in affected_enemies:
            if enemy.is_alive():
                enemy.take_damage(current_stats.damage, "fire", self.position)
                if current_stats.burn_damage > 0:
                    enemy.apply_effect("burn", current_stats.burn_duration,
                                     damage_per_second=current_stats.burn_damage)
        
        # Effet visuel de flammes
        self.emit_event('flame_effect', {
            'position': self.position,
            'target_position': target.get_position(),
            'radius': current_stats.area_radius
        })
    
    def _cryo_steam_attack(self, target: Enemy):
        """Attaque vapeur glacée (effet de zone)"""
        current_stats = self.upgrade.current_stats
        
        # Tous les ennemis dans la zone
        affected_enemies = self._get_enemies_in_radius(target.get_position(),
                                                     current_stats.area_radius)
        
        for enemy in affected_enemies:
            if enemy.is_alive():
                enemy.take_damage(current_stats.damage, "ice", self.position)
                if current_stats.slow_effect > 0:
                    enemy.apply_effect("slow", current_stats.slow_duration,
                                     speed_multiplier=current_stats.slow_effect)
        
        # Effet visuel de glace
        self.emit_event('frost_effect', {
            'position': target.get_position(),
            'radius': current_stats.area_radius
        })
    
    def _lightning_attack(self, target: Enemy):
        """Attaque éclair (saut entre ennemis)"""
        current_stats = self.upgrade.current_stats
        targets_hit = [target]
        current_target = target
        
        # Application des dégâts à la cible principale
        current_target.take_damage(current_stats.damage, "electric", self.position)
        if current_stats.stun_duration > 0:
            current_target.apply_effect("stun", current_stats.stun_duration)
        
        # Chaînes d'éclairs
        for i in range(current_stats.chain_count):
            next_target = self._find_nearest_enemy_for_chain(current_target, targets_hit)
            if not next_target:
                break
            
            # Dégâts réduits pour les chaînes
            chain_damage = int(current_stats.damage * (0.8 ** (i + 1)))
            next_target.take_damage(chain_damage, "electric", self.position)
            
            targets_hit.append(next_target)
            current_target = next_target
        
        # Effet visuel d'éclair
        self.emit_event('lightning_effect', {
            'targets': [t.get_position() for t in targets_hit]
        })
    
    def _shield_generator_effect(self):
        """Effet du générateur de bouclier"""
        # Trouve les tours alliées dans la portée et leur donne un bouclier
        # Cette fonctionnalité sera implémentée avec le système de tours alliées
        pass
    
    def _update_special_behavior(self, delta_time: float, enemies: List[Enemy]):
        """Met à jour les comportements spéciaux selon le type de tour"""
        if self.tower_type == TowerType.MINE_LAYER:
            self._update_mine_layer(delta_time, enemies)
    
    def _update_mine_layer(self, delta_time: float, enemies: List[Enemy]):
        """Comportement spécial du poseur de mines"""
        # Place automatiquement des mines autour de la tour
        # Les mines explosent quand un ennemi terrestre s'approche
        
        mine_range = 48.0  # Portée de détection des mines
        
        for enemy in enemies:
            if (enemy.is_alive() and not enemy.is_flying() and
                self._distance_to_enemy(enemy) <= mine_range):
                
                # Explosion de mine
                current_stats = self.upgrade.current_stats
                affected_enemies = self._get_enemies_in_radius(
                    enemy.get_position(), current_stats.area_radius)
                
                for affected in affected_enemies:
                    if affected.is_alive() and not affected.is_flying():
                        affected.take_damage(current_stats.damage, "physical", self.position)
                
                # Effet visuel d'explosion
                self.emit_event('mine_explosion', {
                    'position': enemy.get_position(),
                    'radius': current_stats.area_radius
                })
                
                # Rechargement de la mine
                self.attack.attack_timer = 3.0  # 3 secondes pour recharger
                break
    
    def _update_projectiles(self, delta_time: float, enemies: List[Enemy]):
        """Met à jour les projectiles actifs"""
        for projectile in self.active_projectiles[:]:
            projectile.update(delta_time)
            
            # Vérification des collisions
            if projectile.has_hit_target():
                self._handle_projectile_hit(projectile, enemies)
                self.active_projectiles.remove(projectile)
            elif projectile.is_expired():
                self.active_projectiles.remove(projectile)
    
    def _handle_projectile_hit(self, projectile: Projectile, enemies: List[Enemy]):
        """Gère l'impact d'un projectile"""
        hit_position = projectile.get_position()
        stats = projectile.tower_stats
        
        if stats.area_damage:
            # Dégâts de zone
            affected_enemies = self._get_enemies_in_radius(hit_position, stats.area_radius)
            for enemy in affected_enemies:
                if enemy.is_alive():
                    enemy.take_damage(projectile.damage, "physical", self.position)
        else:
            # Recherche de l'ennemi le plus proche du point d'impact
            closest_enemy = self._find_closest_enemy_to_point(hit_position, enemies, 16.0)
            if closest_enemy and closest_enemy.is_alive():
                closest_enemy.take_damage(projectile.damage, "physical", self.position)
                
                # Effets spéciaux
                if stats.slow_effect > 0:
                    closest_enemy.apply_effect("slow", stats.slow_duration,
                                             speed_multiplier=stats.slow_effect)
                if stats.stun_duration > 0:
                    closest_enemy.apply_effect("stun", stats.stun_duration)
        
        # Effet visuel d'impact
        self.emit_event('projectile_impact', {
            'position': hit_position,
            'projectile_type': projectile.projectile_type,
            'area_radius': stats.area_radius if stats.area_damage else 0
        })
    
    def upgrade_tower(self) -> bool:
        """Améliore la tour d'un niveau"""
        if self.upgrade.upgrade():
            # Mise à jour des composants avec les nouvelles stats
            self.attack.stats = self.upgrade.current_stats
            self.targeting.range = self.upgrade.current_stats.range
            
            # Régénération du sprite pour refléter l'amélioration
            self.sprite = self._create_sprite()
            self.sprite.center_x, self.sprite.center_y = self.position
            
            # Effet visuel d'amélioration
            self.emit_event('tower_upgraded', {
                'tower': self,
                'new_level': self.upgrade.level
            })
            
            self.logger.info(f"Tour {self.tower_type.value} améliorée au niveau {self.upgrade.level}")
            return True
        
        return False
    
    def sell_tower(self) -> int:
        """Vend la tour et retourne l'argent récupéré"""
        sell_value = int(self.get_total_cost() * GAMEPLAY_BALANCE['ECONOMY']['TOWER_SELL_RATIO'])
        
        self.emit_event('tower_sold', {
            'tower': self,
            'sell_value': sell_value
        })
        
        self.logger.info(f"Tour {self.tower_type.value} vendue pour {sell_value} or")
        return sell_value
    
    def set_targeting_mode(self, mode: TargetingMode):
        """Change le mode de ciblage"""
        self.targeting.targeting_mode = mode
        self.attack.targeting_mode = mode
        self.logger.debug(f"Mode de ciblage changé vers {mode.value}")
    
    def toggle_range_indicator(self):
        """Active/désactive l'indicateur de portée"""
        self.range_indicator_visible = not self.range_indicator_visible
    
    def render(self, renderer):
        """Rendu personnalisé de la tour"""
        # Animation de construction
        if not self.is_constructed:
            # Effet de construction progressif
            construction_progress = 1.0 - (self.construction_timer / self.construction_time)
            self.sprite.alpha = int(255 * construction_progress)
            
            # Effet de particules de construction
            self.emit_event('construction_particles', {
                'position': self.position,
                'progress': construction_progress
            })
        else:
            self.sprite.alpha = 255
        
        # Rendu du sprite principal
        self.sprite.draw()
        
        # Indicateur de portée
        if self.range_indicator_visible:
            self._render_range_indicator(renderer)
        
        # Flash d'attaque
        if self.muzzle_flash_timer > 0:
            self._render_muzzle_flash(renderer)
        
        # Rendu des projectiles
        for projectile in self.active_projectiles:
            projectile.render(renderer)
        
        # Indicateur de niveau
        if self.upgrade.level > 1:
            self._render_level_indicator(renderer)
    
    def _render_range_indicator(self, renderer):
        """Affiche l'indicateur de portée"""
        range_radius = self.upgrade.current_stats.range
        arcade.draw_circle_outline(
            self.position[0], self.position[1], range_radius,
            SteampunkColors.GOLD, 2
        )
    
    def _render_muzzle_flash(self, renderer):
        """Affiche l'effet de flash d'attaque"""
        flash_size = 16 * (self.muzzle_flash_timer / 0.2)
        flash_alpha = int(255 * (self.muzzle_flash_timer / 0.2))
        
        arcade.draw_circle_filled(
            self.position[0], self.position[1], flash_size,
            (*SteampunkColors.FIRE_ORANGE, flash_alpha)
        )
    
    def _render_level_indicator(self, renderer):
        """Affiche l'indicateur de niveau"""
        indicator_x = self.position[0] + 20
        indicator_y = self.position[1] + 20
        
        # Fond
        arcade.draw_circle_filled(indicator_x, indicator_y, 8, SteampunkColors.BRONZE)
        arcade.draw_circle_outline(indicator_x, indicator_y, 8, SteampunkColors.BRASS, 2)
        
        # Texte du niveau
        arcade.draw_text(
            str(self.upgrade.level),
            indicator_x - 4, indicator_y - 6,
            SteampunkColors.TEXT_GOLD,
            font_size=12,
            font_name="Arial",
            bold=True
        )
    
    # ═══════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES
    # ═══════════════════════════════════════════════════════════
    
    def _distance_to_enemy(self, enemy: Enemy) -> float:
        """Calcule la distance à un ennemi"""
        enemy_pos = enemy.get_position()
        return math.sqrt(
            (self.position[0] - enemy_pos[0]) ** 2 + 
            (self.position[1] - enemy_pos[1]) ** 2
        )
    
    def _get_enemies_in_radius(self, center: Tuple[float, float], 
                              radius: float) -> List[Enemy]:
        """Retourne les ennemis dans un rayon donné"""
        # Cette méthode sera appelée avec une liste d'ennemis du système de jeu
        return []  # Placeholder
    
    def _get_enemies_in_cone(self, target_pos: Tuple[float, float], 
                           range_radius: float, angle_degrees: float) -> List[Enemy]:
        """Retourne les ennemis dans un cône"""
        # Calcul du cône depuis la tour vers la cible
        return []  # Placeholder
    
    def _find_nearest_enemy_for_chain(self, current_target: Enemy, 
                                    already_hit: List[Enemy]) -> Optional[Enemy]:
        """Trouve le prochain ennemi pour une chaîne d'éclair"""
        # Recherche dans un rayon de 64 pixels
        return None  # Placeholder
    
    def _find_closest_enemy_to_point(self, point: Tuple[float, float], 
                                   enemies: List[Enemy], max_distance: float) -> Optional[Enemy]:
        """Trouve l'ennemi le plus proche d'un point"""
        closest = None
        min_distance = max_distance
        
        for enemy in enemies:
            if enemy.is_alive():
                enemy_pos = enemy.get_position()
                distance = math.sqrt(
                    (point[0] - enemy_pos[0]) ** 2 + 
                    (point[1] - enemy_pos[1]) ** 2
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest = enemy
        
        return closest
    
    # ═══════════════════════════════════════════════════════════
    # PROPRIÉTÉS ET ACCESSEURS
    # ═══════════════════════════════════════════════════════════
    
    def is_ready(self) -> bool:
        """Retourne si la tour est opérationnelle"""
        return self.is_constructed
    
    def get_cost(self) -> int:
        """Retourne le coût de construction de base"""
        return self.base_stats.cost
    
    def get_total_cost(self) -> int:
        """Retourne le coût total investi (construction + améliorations)"""
        total = self.base_stats.cost
        for i in range(self.upgrade.level - 1):
            total += self.upgrade.upgrade_costs[i]
        return total
    
    def get_level(self) -> int:
        """Retourne le niveau actuel"""
        return self.upgrade.level
    
    def get_range(self) -> float:
        """Retourne la portée actuelle"""
        return self.upgrade.current_stats.range
    
    def get_damage(self) -> int:
        """Retourne les dégâts actuels"""
        return self.upgrade.current_stats.damage
    
    def get_position(self) -> Tuple[float, float]:
        """Retourne la position de la tour"""
        return self.position
    
    def can_target_enemy_type(self, enemy: Enemy) -> bool:
        """Vérifie si la tour peut cibler ce type d'ennemi"""
        stats = self.upgrade.current_stats
        
        if enemy.is_flying():
            return stats.can_target_air
        else:
            return stats.can_target_ground
    
    def get_debug_info(self) -> List[str]:
        """Retourne des informations de debug"""
        stats = self.upgrade.current_stats
        return [
            f"Type: {self.tower_type.value}",
            f"Level: {self.upgrade.level}/{self.upgrade.max_level}",
            f"Damage: {stats.damage}",
            f"Range: {stats.range:.1f}",
            f"Attack Speed: {stats.attack_speed:.1f}",
            f"Target: {self.attack.target.enemy_type.value if self.attack.target else 'None'}",
            f"Attack Timer: {self.attack.attack_timer:.1f}",
            f"Constructed: {self.is_constructed}",
            f"Active Projectiles: {len(self.active_projectiles)}"
        ]


# ═══════════════════════════════════════════════════════════
# FACTORY POUR CRÉER LES TOURS
# ═══════════════════════════════════════════════════════════

class TowerFactory:
    """Factory pour créer des tours selon leur type"""
    
    def __init__(self, sprite_factory: SteampunkSpriteFactory):
        self.sprite_factory = sprite_factory
        self.logger = logging.getLogger('TowerFactory')
    
    def create_tower(self, tower_type: TowerType, 
                    position: Tuple[float, float]) -> Tower:
        """
        Crée une tour du type spécifié
        
        Args:
            tower_type: Type de tour à créer
            position: Position de placement
            
        Returns:
            Tower: Instance de la tour créée
        """
        tower = Tower(tower_type, position, self.sprite_factory)
        
        self.logger.debug(f"Tour créée: {tower_type.value} à {position}")
        
        return tower
    
    def get_tower_cost(self, tower_type: TowerType) -> int:
        """Retourne le coût de construction d'une tour"""
        # Création temporaire pour récupérer le coût
        temp_tower = Tower(tower_type, (0, 0), self.sprite_factory)
        return temp_tower.get_cost()
    
    def get_available_towers(self, unlocked_towers: Set[TowerType] = None) -> List[TowerType]:
        """
        Retourne la liste des tours disponibles
        
        Args:
            unlocked_towers: Tours débloquées (None = toutes disponibles)
            
        Returns:
            List[TowerType]: Tours disponibles
        """
        all_towers = list(TowerType)
        
        if unlocked_towers is None:
            return all_towers
        
        return [tower for tower in all_towers if tower in unlocked_towers]