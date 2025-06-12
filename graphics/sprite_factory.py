# graphics/sprite_factory.py
"""
Steam Defense - Factory de génération de sprites procéduraux
Génère tous les sprites du jeu en utilisant des formes géométriques
"""

import arcade
import math
import random
from typing import Tuple, List, Dict, Optional
from enum import Enum
import numpy as np

from config.settings import SteampunkColors, GRID_CONFIG


class SpriteType(Enum):
    """Types de sprites disponibles"""
    # Ennemis
    STEAM_SOLDIER = "steam_soldier"
    SKY_ZEPPELIN = "sky_zeppelin"
    STEAM_TANK = "steam_tank"
    LIGHTNING_DRONE = "lightning_drone"
    STEEL_SPIDER = "steel_spider"
    IRON_GOLEM = "iron_golem"
    CYBER_SURVIVOR = "cyber_survivor"
    
    # Tours
    STEAM_CANNON = "steam_cannon"
    LIGHTNING_TOWER = "lightning_tower"
    FLAME_THROWER = "flame_thrower"
    ANTI_AIR_GUN = "anti_air_gun"
    BRONZE_MORTAR = "bronze_mortar"
    CRYO_STEAM = "cryo_steam"
    MINE_LAYER = "mine_layer"
    SNIPER_MECHA = "sniper_mecha"
    SHIELD_GENERATOR = "shield_generator"
    
    # Projectiles
    CANNONBALL = "cannonball"
    LIGHTNING_BOLT = "lightning_bolt"
    FLAME_BURST = "flame_burst"
    BULLET = "bullet"
    MORTAR_SHELL = "mortar_shell"
    ICE_CRYSTAL = "ice_crystal"
    SNIPER_BULLET = "sniper_bullet"
    
    # Décorations
    GEAR_SMALL = "gear_small"
    GEAR_MEDIUM = "gear_medium"
    STEAM_PIPE = "steam_pipe"
    LAMP_POST = "lamp_post"
    INDUSTRIAL_CHIMNEY = "industrial_chimney"


class SteampunkSpriteFactory:
    """
    Factory pour générer des sprites steampunk procéduralement
    Utilise des formes géométriques simples pour créer des sprites cohérents
    """
    
    def __init__(self):
        self.tile_size = GRID_CONFIG['TILE_SIZE']
        self.colors = SteampunkColors()
        self.sprite_cache: Dict[str, arcade.Texture] = {}
        
    def create_sprite(self, sprite_type: SpriteType, size: Optional[Tuple[int, int]] = None,
                     scale: float = 1.0, rotation: float = 0.0, **kwargs) -> arcade.Texture:
        """
        Crée un sprite du type demandé
        
        Args:
            sprite_type: Type de sprite à créer
            size: Taille personnalisée (largeur, hauteur)
            scale: Facteur d'échelle
            rotation: Rotation en degrés
            **kwargs: Paramètres spécifiques au sprite
            
        Returns:
            arcade.Texture: Texture générée
        """
        # Génération d'une clé de cache
        cache_key = f"{sprite_type.value}_{size}_{scale}_{rotation}_{hash(str(kwargs))}"
        
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]
        
        # Taille par défaut
        if size is None:
            size = (self.tile_size, self.tile_size)
        
        # Génération du sprite
        texture = self._generate_sprite_texture(sprite_type, size, scale, rotation, **kwargs)
        
        # Mise en cache
        self.sprite_cache[cache_key] = texture
        
        return texture
    
    def _generate_sprite_texture(self, sprite_type: SpriteType, size: Tuple[int, int],
                                scale: float, rotation: float, **kwargs) -> arcade.Texture:
        """Génère la texture pour un type de sprite donné"""
        
        # Création d'une surface de rendu
        width, height = int(size[0] * scale), int(size[1] * scale)
        
        # Sélection de la méthode de génération
        generators = {
            # Ennemis
            SpriteType.STEAM_SOLDIER: self._create_steam_soldier,
            SpriteType.SKY_ZEPPELIN: self._create_sky_zeppelin,
            SpriteType.STEAM_TANK: self._create_steam_tank,
            SpriteType.LIGHTNING_DRONE: self._create_lightning_drone,
            SpriteType.STEEL_SPIDER: self._create_steel_spider,
            SpriteType.IRON_GOLEM: self._create_iron_golem,
            SpriteType.CYBER_SURVIVOR: self._create_cyber_survivor,
            
            # Tours
            SpriteType.STEAM_CANNON: self._create_steam_cannon,
            SpriteType.LIGHTNING_TOWER: self._create_lightning_tower,
            SpriteType.FLAME_THROWER: self._create_flame_thrower,
            SpriteType.ANTI_AIR_GUN: self._create_anti_air_gun,
            SpriteType.BRONZE_MORTAR: self._create_bronze_mortar,
            SpriteType.CRYO_STEAM: self._create_cryo_steam,
            SpriteType.MINE_LAYER: self._create_mine_layer,
            SpriteType.SNIPER_MECHA: self._create_sniper_mecha,
            SpriteType.SHIELD_GENERATOR: self._create_shield_generator,
            
            # Projectiles
            SpriteType.CANNONBALL: self._create_cannonball,
            SpriteType.LIGHTNING_BOLT: self._create_lightning_bolt,
            SpriteType.FLAME_BURST: self._create_flame_burst,
            SpriteType.BULLET: self._create_bullet,
            SpriteType.MORTAR_SHELL: self._create_mortar_shell,
            SpriteType.ICE_CRYSTAL: self._create_ice_crystal,
            SpriteType.SNIPER_BULLET: self._create_sniper_bullet,
            
            # Décorations
            SpriteType.GEAR_SMALL: self._create_gear_small,
            SpriteType.GEAR_MEDIUM: self._create_gear_medium,
            SpriteType.STEAM_PIPE: self._create_steam_pipe,
            SpriteType.LAMP_POST: self._create_lamp_post,
            SpriteType.INDUSTRIAL_CHIMNEY: self._create_industrial_chimney,
        }
        
        generator = generators.get(sprite_type)
        if not generator:
            raise ValueError(f"Générateur non trouvé pour {sprite_type}")
        
        return generator(width, height, rotation, **kwargs)
    
    # ═══════════════════════════════════════════════════════════
    # GÉNÉRATEURS D'ENNEMIS
    # ═══════════════════════════════════════════════════════════
    
    def _create_steam_soldier(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un soldat à vapeur"""
        texture = arcade.Texture.create_empty("steam_soldier", (width, height))
        texture = texture.create_filled("steam_soldier", (width, height), (0, 0, 0, 0))
        
        # Utilisation du système de rendu direct d'Arcade
        with texture.create_draw_context() as ctx:
            # Corps principal (rectangle bronze)
            body_width = width * 0.6
            body_height = height * 0.7
            body_x = (width - body_width) / 2
            body_y = height * 0.1
            
            arcade.draw_rectangle_filled(
                body_x + body_width/2, body_y + body_height/2,
                body_width, body_height,
                self.colors.BRONZE
            )
            
            # Casque (arc supérieur)
            helmet_radius = width * 0.3
            arcade.draw_circle_filled(
                width/2, height * 0.8,
                helmet_radius,
                self.colors.COPPER
            )
            
            # Tuyaux de vapeur (petits cylindres)
            pipe_positions = [(width * 0.3, height * 0.6), (width * 0.7, height * 0.6)]
            for px, py in pipe_positions:
                arcade.draw_circle_filled(px, py, width * 0.05, self.colors.STEEL)
            
            # Détails mécaniques (rivets)
            for i in range(3):
                for j in range(2):
                    rivet_x = body_x + (i + 1) * body_width / 4
                    rivet_y = body_y + (j + 1) * body_height / 3
                    arcade.draw_circle_filled(rivet_x, rivet_y, 2, self.colors.IRON)
        
        return texture
    
    def _create_sky_zeppelin(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un dirigeable"""
        texture = arcade.Texture.create_filled("sky_zeppelin", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Enveloppe principale (ellipse)
            envelope_width = width * 0.8
            envelope_height = height * 0.4
            arcade.draw_ellipse_filled(
                width/2, height * 0.7,
                envelope_width, envelope_height,
                self.colors.BRASS
            )
            
            # Nacelle (rectangle)
            nacelle_width = width * 0.3
            nacelle_height = height * 0.2
            arcade.draw_rectangle_filled(
                width/2, height * 0.2,
                nacelle_width, nacelle_height,
                self.colors.BRONZE
            )
            
            # Hélices (cercles avec pales)
            propeller_positions = [(width * 0.2, height * 0.5), (width * 0.8, height * 0.5)]
            for px, py in propeller_positions:
                # Hub de l'hélice
                arcade.draw_circle_filled(px, py, width * 0.05, self.colors.IRON)
                # Pales
                for angle in [0, 90, 180, 270]:
                    blade_x = px + math.cos(math.radians(angle)) * width * 0.1
                    blade_y = py + math.sin(math.radians(angle)) * width * 0.1
                    arcade.draw_line(px, py, blade_x, blade_y, self.colors.STEEL, 2)
        
        return texture
    
    def _create_steam_tank(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un char à vapeur"""
        texture = arcade.Texture.create_filled("steam_tank", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Châssis principal
            chassis_width = width * 0.8
            chassis_height = height * 0.5
            arcade.draw_rectangle_filled(
                width/2, height * 0.3,
                chassis_width, chassis_height,
                self.colors.IRON
            )
            
            # Tourelle
            turret_radius = width * 0.25
            arcade.draw_circle_filled(
                width/2, height * 0.6,
                turret_radius,
                self.colors.STEEL
            )
            
            # Canon
            barrel_length = width * 0.4
            barrel_width = height * 0.08
            arcade.draw_rectangle_filled(
                width/2 + barrel_length/2, height * 0.6,
                barrel_length, barrel_width,
                self.colors.BRONZE
            )
            
            # Chenilles (rectangles dentelés)
            track_positions = [(width * 0.2, height * 0.15), (width * 0.8, height * 0.15)]
            for tx, ty in track_positions:
                arcade.draw_rectangle_filled(tx, ty, width * 0.15, height * 0.2, self.colors.IRON)
                # Détails des chenilles
                for i in range(3):
                    detail_y = ty + (i - 1) * height * 0.06
                    arcade.draw_rectangle_filled(tx, detail_y, width * 0.12, height * 0.03, self.colors.RUST)
        
        return texture
    
    def _create_lightning_drone(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un drone électrique"""
        texture = arcade.Texture.create_filled("lightning_drone", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Corps central (hexagone)
            center_x, center_y = width/2, height/2
            radius = min(width, height) * 0.3
            
            # Hexagone approximé par un octogone
            points = []
            for i in range(6):
                angle = math.radians(i * 60)
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                points.extend([x, y])
            
            arcade.draw_polygon_filled(points, self.colors.ELECTRIC_BLUE)
            
            # Bobines électriques (petits cercles)
            coil_positions = [
                (width * 0.3, height * 0.3), (width * 0.7, height * 0.3),
                (width * 0.3, height * 0.7), (width * 0.7, height * 0.7)
            ]
            for cx, cy in coil_positions:
                arcade.draw_circle_filled(cx, cy, width * 0.08, self.colors.COPPER)
                arcade.draw_circle_outline(cx, cy, width * 0.1, self.colors.GOLD, 2)
            
            # Arcs électriques (lignes en zigzag)
            for i in range(2):
                start_x = width * (0.2 + i * 0.6)
                start_y = height * 0.5
                end_x = width * (0.8 - i * 0.6)
                end_y = height * 0.5
                
                # Zigzag simplifié
                mid_x = (start_x + end_x) / 2
                mid_y = start_y + random.uniform(-height*0.1, height*0.1)
                
                arcade.draw_line(start_x, start_y, mid_x, mid_y, self.colors.ELECTRIC_BLUE, 3)
                arcade.draw_line(mid_x, mid_y, end_x, end_y, self.colors.ELECTRIC_BLUE, 3)
        
        return texture
    
    def _create_steel_spider(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère une araignée mécanique"""
        texture = arcade.Texture.create_filled("steel_spider", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            center_x, center_y = width/2, height/2
            
            # Corps central (ellipse)
            body_width = width * 0.4
            body_height = height * 0.6
            arcade.draw_ellipse_filled(center_x, center_y, body_width, body_height, self.colors.STEEL)
            
            # Pattes (8 pattes d'araignée)
            leg_length = width * 0.4
            for i in range(8):
                angle = math.radians(i * 45)
                
                # Articulation 1
                joint1_x = center_x + math.cos(angle) * body_width * 0.3
                joint1_y = center_y + math.sin(angle) * body_height * 0.3
                
                # Articulation 2
                joint2_x = joint1_x + math.cos(angle + 0.5) * leg_length * 0.5
                joint2_y = joint1_y + math.sin(angle + 0.5) * leg_length * 0.5
                
                # Extrémité
                end_x = joint2_x + math.cos(angle - 0.5) * leg_length * 0.5
                end_y = joint2_y + math.sin(angle - 0.5) * leg_length * 0.5
                
                # Dessin des segments
                arcade.draw_line(center_x, center_y, joint1_x, joint1_y, self.colors.IRON, 3)
                arcade.draw_line(joint1_x, joint1_y, joint2_x, joint2_y, self.colors.IRON, 2)
                arcade.draw_line(joint2_x, joint2_y, end_x, end_y, self.colors.IRON, 2)
                
                # Articulations
                arcade.draw_circle_filled(joint1_x, joint1_y, 3, self.colors.BRASS)
                arcade.draw_circle_filled(joint2_x, joint2_y, 2, self.colors.BRASS)
            
            # Détails du corps
            arcade.draw_circle_filled(center_x, center_y + height*0.1, width*0.08, self.colors.GOLD)  # "Œil"
            arcade.draw_circle_outline(center_x, center_y, body_width*0.6, self.colors.BRONZE, 2)
        
        return texture
    
    def _create_iron_golem(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un golem de fer massif"""
        texture = arcade.Texture.create_filled("iron_golem", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Corps massif (rectangle principal)
            body_width = width * 0.7
            body_height = height * 0.8
            body_x = (width - body_width) / 2
            body_y = height * 0.1
            
            arcade.draw_rectangle_filled(
                body_x + body_width/2, body_y + body_height/2,
                body_width, body_height,
                self.colors.IRON
            )
            
            # Tête (carré plus petit)
            head_size = width * 0.3
            arcade.draw_rectangle_filled(
                width/2, height * 0.85,
                head_size, head_size,
                self.colors.STEEL
            )
            
            # Bras (rectangles latéraux)
            arm_width = width * 0.15
            arm_height = height * 0.5
            
            # Bras gauche
            arcade.draw_rectangle_filled(
                body_x - arm_width/2, body_y + body_height * 0.7,
                arm_width, arm_height,
                self.colors.IRON
            )
            
            # Bras droit
            arcade.draw_rectangle_filled(
                body_x + body_width + arm_width/2, body_y + body_height * 0.7,
                arm_width, arm_height,
                self.colors.IRON
            )
            
            # Jambes
            leg_width = width * 0.2
            leg_height = height * 0.3
            
            arcade.draw_rectangle_filled(
                width * 0.4, leg_height/2,
                leg_width, leg_height,
                self.colors.IRON
            )
            
            arcade.draw_rectangle_filled(
                width * 0.6, leg_height/2,
                leg_width, leg_height,
                self.colors.IRON
            )
            
            # Détails (plaques rivetées)
            rivet_size = 3
            for i in range(4):
                for j in range(6):
                    rivet_x = body_x + (i + 1) * body_width / 5
                    rivet_y = body_y + (j + 1) * body_height / 7
                    arcade.draw_circle_filled(rivet_x, rivet_y, rivet_size, self.colors.BRASS)
            
            # Yeux lumineux
            eye_y = height * 0.85
            arcade.draw_circle_filled(width * 0.45, eye_y, 4, self.colors.FIRE_ORANGE)
            arcade.draw_circle_filled(width * 0.55, eye_y, 4, self.colors.FIRE_ORANGE)
        
        return texture
    
    def _create_cyber_survivor(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un survivant cybernétique"""
        texture = arcade.Texture.create_filled("cyber_survivor", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Corps humanoïde de base
            body_width = width * 0.5
            body_height = height * 0.6
            arcade.draw_rectangle_filled(
                width/2, height * 0.4,
                body_width, body_height,
                self.colors.BRONZE
            )
            
            # Tête
            head_radius = width * 0.15
            arcade.draw_circle_filled(width/2, height * 0.8, head_radius, self.colors.COPPER)
            
            # Implants cybernétiques (rectangles métalliques)
            implant_positions = [
                (width * 0.3, height * 0.7), (width * 0.7, height * 0.7),  # Tempes
                (width * 0.4, height * 0.5), (width * 0.6, height * 0.5)   # Torse
            ]
            
            for ix, iy in implant_positions:
                arcade.draw_rectangle_filled(ix, iy, width * 0.08, height * 0.06, self.colors.STEEL)
                # LED d'état
                arcade.draw_circle_filled(ix, iy, 2, self.colors.ELECTRIC_BLUE)
            
            # Bras mécaniques
            arm_segments = [
                # Bras gauche
                [(width * 0.3, height * 0.6), (width * 0.15, height * 0.4)],
                [(width * 0.15, height * 0.4), (width * 0.1, height * 0.2)],
                # Bras droit  
                [(width * 0.7, height * 0.6), (width * 0.85, height * 0.4)],
                [(width * 0.85, height * 0.4), (width * 0.9, height * 0.2)]
            ]
            
            for start, end in arm_segments:
                arcade.draw_line(start[0], start[1], end[0], end[1], self.colors.IRON, 4)
                # Articulations
                arcade.draw_circle_filled(start[0], start[1], 3, self.colors.BRASS)
                arcade.draw_circle_filled(end[0], end[1], 3, self.colors.BRASS)
            
            # Jambes
            leg_width = width * 0.12
            leg_height = height * 0.3
            
            arcade.draw_rectangle_filled(width * 0.4, leg_height/2, leg_width, leg_height, self.colors.IRON)
            arcade.draw_rectangle_filled(width * 0.6, leg_height/2, leg_width, leg_height, self.colors.IRON)
            
            # Effets énergétiques (aura)
            for radius in [width * 0.6, width * 0.65, width * 0.7]:
                arcade.draw_circle_outline(width/2, height/2, radius, 
                                         (*self.colors.ELECTRIC_BLUE, 50), 2)
        
        return texture
    
    # ═══════════════════════════════════════════════════════════
    # GÉNÉRATEURS DE TOURS
    # ═══════════════════════════════════════════════════════════
    
    def _create_steam_cannon(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un canon à vapeur"""
        texture = arcade.Texture.create_filled("steam_cannon", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Base de la tour (hexagone)
            base_radius = width * 0.4
            center_x, center_y = width/2, height/2
            
            # Hexagone pour la base
            points = []
            for i in range(6):
                angle = math.radians(i * 60)
                x = center_x + base_radius * math.cos(angle)
                y = center_y + base_radius * math.sin(angle)
                points.extend([x, y])
            
            arcade.draw_polygon_filled(points, self.colors.BRONZE)
            arcade.draw_polygon_outline(points, self.colors.BRASS, 3)
            
            # Canon principal
            barrel_length = width * 0.6
            barrel_width = height * 0.12
            
            # Rotation du canon
            barrel_angle = math.radians(rotation)
            barrel_end_x = center_x + math.cos(barrel_angle) * barrel_length
            barrel_end_y = center_y + math.sin(barrel_angle) * barrel_length
            
            # Tube du canon
            arcade.draw_line(center_x, center_y, barrel_end_x, barrel_end_y, 
                           self.colors.STEEL, int(barrel_width))
            
            # Embout du canon
            arcade.draw_circle_filled(barrel_end_x, barrel_end_y, barrel_width/2, self.colors.IRON)
            
            # Réservoir de vapeur (cylindre)
            tank_width = width * 0.2
            tank_height = height * 0.3
            arcade.draw_rectangle_filled(
                center_x - width * 0.2, center_y,
                tank_width, tank_height,
                self.colors.COPPER
            )
            
            # Détails (rivets et jauges)
            for i in range(3):
                rivet_angle = math.radians(i * 120)
                rivet_x = center_x + base_radius * 0.7 * math.cos(rivet_angle)
                rivet_y = center_y + base_radius * 0.7 * math.sin(rivet_angle)
                arcade.draw_circle_filled(rivet_x, rivet_y, 3, self.colors.BRASS)
            
            # Jauge de pression (petit cercle avec aiguille)
            gauge_x = center_x + width * 0.15
            gauge_y = center_y + height * 0.15
            arcade.draw_circle_filled(gauge_x, gauge_y, width * 0.06, self.colors.STEAM_WHITE)
            arcade.draw_circle_outline(gauge_x, gauge_y, width * 0.06, self.colors.IRON, 2)
            
            # Aiguille de jauge
            needle_angle = math.radians(45)  # Position aléatoire
            needle_end_x = gauge_x + math.cos(needle_angle) * width * 0.04
            needle_end_y = gauge_y + math.sin(needle_angle) * width * 0.04
            arcade.draw_line(gauge_x, gauge_y, needle_end_x, needle_end_y, self.colors.GOLD, 2)
        
        return texture
    
    def _create_lightning_tower(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère une tour à éclairs"""
        texture = arcade.Texture.create_filled("lightning_tower", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            center_x, center_y = width/2, height/2
            
            # Base carrée
            base_size = width * 0.6
            arcade.draw_rectangle_filled(center_x, center_y * 0.6, base_size, base_size * 0.8, 
                                       self.colors.IRON)
            
            # Bobine Tesla (cylindre vertical)
            coil_width = width * 0.3
            coil_height = height * 0.5
            arcade.draw_rectangle_filled(center_x, center_y + height * 0.2, 
                                       coil_width, coil_height, self.colors.COPPER)
            
            # Spires de la bobine (lignes horizontales)
            for i in range(5):
                y_pos = center_y + height * 0.05 + i * height * 0.08
                arcade.draw_line(center_x - coil_width/2, y_pos,
                               center_x + coil_width/2, y_pos,
                               self.colors.BRASS, 2)
            
            # Électrodes supérieures (sphères)
            electrode_y = center_y + height * 0.4
            electrode_radius = width * 0.08
            
            arcade.draw_circle_filled(center_x - width * 0.15, electrode_y, 
                                    electrode_radius, self.colors.STEEL)
            arcade.draw_circle_filled(center_x + width * 0.15, electrode_y, 
                                    electrode_radius, self.colors.STEEL)
            
            # Arc électrique entre les électrodes
            num_segments = 4
            for i in range(num_segments):
                start_x = center_x - width * 0.15 + i * width * 0.075
                start_y = electrode_y + random.uniform(-height*0.02, height*0.02)
                end_x = start_x + width * 0.075
                end_y = electrode_y + random.uniform(-height*0.02, height*0.02)
                
                arcade.draw_line(start_x, start_y, end_x, end_y, 
                               self.colors.ELECTRIC_BLUE, 3)
            
            # Condensateurs (cylindres latéraux)
            capacitor_positions = [(center_x - width * 0.25, center_y),
                                 (center_x + width * 0.25, center_y)]
            
            for cap_x, cap_y in capacitor_positions:
                arcade.draw_rectangle_filled(cap_x, cap_y, width * 0.08, height * 0.3,
                                           self.colors.BRONZE)
                # Bornes
                arcade.draw_circle_filled(cap_x, cap_y + height * 0.12, 3, self.colors.GOLD)
                arcade.draw_circle_filled(cap_x, cap_y - height * 0.12, 3, self.colors.GOLD)
        
        return texture
    
    # ═══════════════════════════════════════════════════════════
    # GÉNÉRATEURS DE PROJECTILES
    # ═══════════════════════════════════════════════════════════
    
    def _create_cannonball(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un boulet de canon"""
        texture = arcade.Texture.create_filled("cannonball", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            center_x, center_y = width/2, height/2
            radius = min(width, height) * 0.4
            
            # Sphère principale
            arcade.draw_circle_filled(center_x, center_y, radius, self.colors.IRON)
            
            # Reflets métalliques
            highlight_x = center_x - radius * 0.3
            highlight_y = center_y + radius * 0.3
            arcade.draw_circle_filled(highlight_x, highlight_y, radius * 0.2, self.colors.STEEL)
            
            # Traînée de vapeur (optionnelle)
            trail_length = kwargs.get('trail_length', 0)
            if trail_length > 0:
                for i in range(trail_length):
                    trail_x = center_x - (i + 1) * width * 0.1
                    trail_radius = radius * (1 - i * 0.2)
                    trail_alpha = max(0, 255 - i * 50)
                    trail_color = (*self.colors.STEAM_WHITE, trail_alpha)
                    arcade.draw_circle_filled(trail_x, center_y, trail_radius, trail_color)
        
        return texture
    
    def _create_lightning_bolt(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un éclair"""
        texture = arcade.Texture.create_filled("lightning_bolt", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Éclair en zigzag
            segments = kwargs.get('segments', 6)
            
            points = [(0, height/2)]
            
            for i in range(1, segments):
                x = (i / segments) * width
                y = height/2 + random.uniform(-height*0.3, height*0.3)
                points.append((x, y))
            
            points.append((width, height/2))
            
            # Dessin de l'éclair principal
            for i in range(len(points) - 1):
                start_x, start_y = points[i]
                end_x, end_y = points[i + 1]
                
                # Éclair principal
                arcade.draw_line(start_x, start_y, end_x, end_y, 
                               self.colors.ELECTRIC_BLUE, 4)
                
                # Éclair secondaire (plus fin)
                arcade.draw_line(start_x, start_y, end_x, end_y, 
                               self.colors.STEAM_WHITE, 2)
            
            # Éclat au centre
            center_x, center_y = width/2, height/2
            for radius in [8, 6, 4]:
                color_intensity = 255 - (8 - radius) * 30
                glow_color = (*self.colors.ELECTRIC_BLUE[:3], color_intensity)
                arcade.draw_circle_filled(center_x, center_y, radius, glow_color)
        
        return texture
    
    # ═══════════════════════════════════════════════════════════
    # GÉNÉRATEURS DE DÉCORATIONS
    # ═══════════════════════════════════════════════════════════
    
    def _create_gear_small(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un petit engrenage"""
        return self._create_gear(width, height, rotation, teeth=8, **kwargs)
    
    def _create_gear_medium(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un engrenage moyen"""
        return self._create_gear(width, height, rotation, teeth=12, **kwargs)
    
    def _create_gear(self, width: int, height: int, rotation: float, teeth: int = 8, **kwargs) -> arcade.Texture:
        """Génère un engrenage avec le nombre de dents spécifié"""
        texture = arcade.Texture.create_filled(f"gear_{teeth}", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            center_x, center_y = width/2, height/2
            outer_radius = min(width, height) * 0.45
            inner_radius = outer_radius * 0.7
            hub_radius = outer_radius * 0.3
            
            # Dents de l'engrenage
            tooth_points = []
            
            for i in range(teeth * 2):  # Deux points par dent
                angle = math.radians(i * 180 / teeth + rotation)
                
                if i % 2 == 0:  # Sommet de dent
                    radius = outer_radius
                else:  # Creux entre dents
                    radius = inner_radius
                
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                tooth_points.extend([x, y])
            
            # Dessin de l'engrenage
            arcade.draw_polygon_filled(tooth_points, self.colors.BRONZE)
            arcade.draw_polygon_outline(tooth_points, self.colors.BRASS, 2)
            
            # Moyeu central
            arcade.draw_circle_filled(center_x, center_y, hub_radius, self.colors.IRON)
            arcade.draw_circle_outline(center_x, center_y, hub_radius, self.colors.STEEL, 2)
            
            # Trou central
            arcade.draw_circle_filled(center_x, center_y, hub_radius * 0.4, self.colors.STEAM_WHITE)
            
            # Rivets sur le moyeu
            for i in range(4):
                rivet_angle = math.radians(i * 90)
                rivet_x = center_x + hub_radius * 0.7 * math.cos(rivet_angle)
                rivet_y = center_y + hub_radius * 0.7 * math.sin(rivet_angle)
                arcade.draw_circle_filled(rivet_x, rivet_y, 2, self.colors.BRASS)
        
        return texture
    
    def _create_steam_pipe(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un tuyau de vapeur"""
        texture = arcade.Texture.create_filled("steam_pipe", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            # Orientation du tuyau selon la rotation
            if abs(rotation) < 45 or abs(rotation) > 135:  # Horizontal
                pipe_width = width * 0.8
                pipe_height = height * 0.3
                pipe_x, pipe_y = width/2, height/2
            else:  # Vertical
                pipe_width = width * 0.3
                pipe_height = height * 0.8
                pipe_x, pipe_y = width/2, height/2
            
            # Tube principal
            arcade.draw_rectangle_filled(pipe_x, pipe_y, pipe_width, pipe_height, 
                                       self.colors.COPPER)
            
            # Joints (anneaux de renforcement)
            num_joints = 3
            if pipe_width > pipe_height:  # Horizontal
                for i in range(num_joints):
                    joint_x = pipe_x - pipe_width/2 + (i + 1) * pipe_width / (num_joints + 1)
                    arcade.draw_rectangle_filled(joint_x, pipe_y, width * 0.05, pipe_height * 1.2,
                                               self.colors.BRASS)
            else:  # Vertical
                for i in range(num_joints):
                    joint_y = pipe_y - pipe_height/2 + (i + 1) * pipe_height / (num_joints + 1)
                    arcade.draw_rectangle_filled(pipe_x, joint_y, pipe_width * 1.2, height * 0.05,
                                               self.colors.BRASS)
            
            # Vannes (petits carrés)
            valve_size = min(width, height) * 0.15
            valve_x = pipe_x + (pipe_width/2 if pipe_width > pipe_height else 0)
            valve_y = pipe_y + (pipe_height/2 if pipe_height > pipe_width else 0)
            
            arcade.draw_rectangle_filled(valve_x, valve_y, valve_size, valve_size, 
                                       self.colors.BRONZE)
            
            # Levier de vanne
            lever_length = valve_size * 0.8
            lever_angle = math.radians(45)
            lever_end_x = valve_x + lever_length * math.cos(lever_angle)
            lever_end_y = valve_y + lever_length * math.sin(lever_angle)
            
            arcade.draw_line(valve_x, valve_y, lever_end_x, lever_end_y, 
                           self.colors.IRON, 3)
            arcade.draw_circle_filled(lever_end_x, lever_end_y, 3, self.colors.GOLD)
        
        return texture
    
    def _create_lamp_post(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère un lampadaire à gaz"""
        texture = arcade.Texture.create_filled("lamp_post", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            center_x = width/2
            
            # Poteau principal
            post_width = width * 0.1
            post_height = height * 0.8
            arcade.draw_rectangle_filled(center_x, post_height/2, post_width, post_height,
                                       self.colors.IRON)
            
            # Base du poteau
            base_width = width * 0.3
            base_height = height * 0.1
            arcade.draw_rectangle_filled(center_x, base_height/2, base_width, base_height,
                                       self.colors.BRONZE)
            
            # Lanterne
            lantern_width = width * 0.4
            lantern_height = height * 0.25
            lantern_y = height * 0.85
            
            # Corps de la lanterne
            arcade.draw_rectangle_filled(center_x, lantern_y, lantern_width, lantern_height,
                                       self.colors.BRASS)
            
            # Panneaux de verre
            glass_width = lantern_width * 0.8
            glass_height = lantern_height * 0.6
            arcade.draw_rectangle_filled(center_x, lantern_y, glass_width, glass_height,
                                       self.colors.STEAM_WHITE)
            
            # Toit de la lanterne
            roof_points = [
                center_x - lantern_width/2, lantern_y + lantern_height/2,
                center_x + lantern_width/2, lantern_y + lantern_height/2,
                center_x, lantern_y + lantern_height/2 + width * 0.15
            ]
            arcade.draw_polygon_filled(roof_points, self.colors.COPPER)
            
            # Flamme à l'intérieur
            flame_x = center_x
            flame_y = lantern_y
            
            # Flamme (forme de goutte inversée)
            flame_points = [
                flame_x, flame_y - height * 0.05,
                flame_x - width * 0.05, flame_y,
                flame_x, flame_y + height * 0.08,
                flame_x + width * 0.05, flame_y
            ]
            arcade.draw_polygon_filled(flame_points, self.colors.FIRE_ORANGE)
            
            # Détails décoratifs
            for i in range(3):
                detail_y = post_height * 0.2 + i * post_height * 0.2
                arcade.draw_circle_filled(center_x, detail_y, post_width * 0.8, self.colors.BRASS)
        
        return texture
    
    def _create_industrial_chimney(self, width: int, height: int, rotation: float, **kwargs) -> arcade.Texture:
        """Génère une cheminée industrielle"""
        texture = arcade.Texture.create_filled("industrial_chimney", (width, height), (0, 0, 0, 0))
        
        with texture.create_draw_context() as ctx:
            center_x = width/2
            
            # Base de la cheminée (légèrement plus large)
            base_width = width * 0.7
            base_height = height * 0.2
            arcade.draw_rectangle_filled(center_x, base_height/2, base_width, base_height,
                                       self.colors.BRONZE)
            
            # Fût principal de la cheminée
            stack_width = width * 0.5
            stack_height = height * 0.7
            stack_y = base_height + stack_height/2
            
            arcade.draw_rectangle_filled(center_x, stack_y, stack_width, stack_height,
                                       self.colors.IRON)
            
            # Anneaux de renforcement
            for i in range(4):
                ring_y = base_height + (i + 1) * stack_height / 5
                arcade.draw_rectangle_filled(center_x, ring_y, stack_width * 1.1, height * 0.03,
                                           self.colors.BRASS)
            
            # Couronne au sommet
            crown_width = stack_width * 1.2
            crown_height = height * 0.08
            crown_y = base_height + stack_height + crown_height/2
            
            arcade.draw_rectangle_filled(center_x, crown_y, crown_width, crown_height,
                                       self.colors.COPPER)
            
            # Vapeur sortant du sommet
            steam_y = crown_y + crown_height/2
            
            for i in range(3):
                steam_offset_x = center_x + (i - 1) * width * 0.1
                steam_offset_y = steam_y + i * height * 0.05
                
                # Nuages de vapeur de taille décroissante
                steam_radius = width * 0.08 * (1 - i * 0.2)
                steam_alpha = max(50, 200 - i * 50)
                steam_color = (*self.colors.STEAM_WHITE, steam_alpha)
                
                arcade.draw_circle_filled(steam_offset_x, steam_offset_y, steam_radius, steam_color)
            
            # Échelle sur le côté
            ladder_x = center_x + stack_width/2 + width * 0.05
            ladder_width = width * 0.03
            
            # Montants de l'échelle
            arcade.draw_rectangle_filled(ladder_x, stack_y, ladder_width, stack_height,
                                       self.colors.STEEL)
            
            # Barreaux de l'échelle
            for i in range(8):
                rung_y = base_height + (i + 1) * stack_height / 9
                arcade.draw_line(ladder_x - ladder_width, rung_y,
                               ladder_x + ladder_width, rung_y,
                               self.colors.STEEL, 2)
        
        return texture
    
    # ═══════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES
    # ═══════════════════════════════════════════════════════════
    
    def clear_cache(self):
        """Vide le cache des sprites"""
        self.sprite_cache.clear()
    
    def get_cache_size(self) -> int:
        """Retourne la taille actuelle du cache"""
        return len(self.sprite_cache)
    
    def preload_common_sprites(self):
        """Précharge les sprites les plus utilisés"""
        common_sprites = [
            SpriteType.STEAM_SOLDIER,
            SpriteType.STEAM_CANNON,
            SpriteType.CANNONBALL,
            SpriteType.GEAR_SMALL,
            SpriteType.STEAM_PIPE
        ]
        
        for sprite_type in common_sprites:
            self.create_sprite(sprite_type)