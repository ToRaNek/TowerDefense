# world/map_generator.py
"""
Steam Defense - Générateur de cartes procédural
Crée des cartes uniques pour maximiser la rejouabilité
"""

import random
import numpy as np
from enum import Enum
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import logging

from config.settings import GRID_CONFIG
from world.grid import Grid, TileType


class EnvironmentTheme(Enum):
    """Thèmes d'environnement disponibles"""
    INDUSTRIAL_FACTORY = "industrial_factory"
    STEAMPUNK_PORT = "steampunk_port"
    GEOTHERMAL_MINE = "geothermal_mine"
    INVENTOR_LAB = "inventor_lab"


@dataclass
class DecorationElement:
    """Élément décoratif à placer sur la carte"""
    name: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    rotation: float = 0.0
    scale: float = 1.0
    theme_specific: bool = False


@dataclass
class GenerationParams:
    """Paramètres de génération de carte"""
    width: int = GRID_CONFIG['GRID_WIDTH']
    height: int = GRID_CONFIG['GRID_HEIGHT']
    theme: EnvironmentTheme = EnvironmentTheme.INDUSTRIAL_FACTORY
    difficulty: int = 1
    seed: Optional[int] = None
    
    # Paramètres de chemin
    path_complexity: float = 0.5  # 0.0 = direct, 1.0 = très sinueux
    path_branches: int = 0        # Nombre de chemins secondaires
    
    # Paramètres de zones de placement
    min_placement_areas: int = 8
    placement_area_size: int = 3  # Taille moyenne des zones
    
    # Paramètres décoratifs
    decoration_density: float = 0.3  # 0.0 = vide, 1.0 = très dense


class MapGenerator:
    """
    Générateur procédural de cartes pour Tower Defense
    Utilise plusieurs algorithmes pour créer des cartes équilibrées et variées
    """
    
    def __init__(self):
        self.logger = logging.getLogger('MapGenerator')
        self.current_grid: Optional[Grid] = None
        self.spawn_point: Optional[Tuple[int, int]] = None
        self.base_point: Optional[Tuple[int, int]] = None
        self.main_path: List[Tuple[int, int]] = []
        self.placement_zones: List[List[Tuple[int, int]]] = []
        self.decorations: List[DecorationElement] = []
    
    def generate_map(self, params: GenerationParams) -> Grid:
        """
        Génère une nouvelle carte selon les paramètres donnés
        
        Args:
            params: Paramètres de génération
            
        Returns:
            Grid: Grille générée avec tous les éléments placés
        """
        self.logger.info(f"Génération d'une carte {params.theme.value} (seed: {params.seed})")
        
        # Initialisation du générateur aléatoire
        if params.seed is not None:
            random.seed(params.seed)
            np.random.seed(params.seed)
        
        # Réinitialisation
        self._reset_generation_state()
        
        # Phase 1: Création de la grille de base
        self.current_grid = Grid(params.width, params.height)
        
        # Phase 2: Placement des points critiques
        self._place_spawn_and_base(params)
        
        # Phase 3: Génération du chemin principal
        self._generate_main_path(params)
        
        # Phase 4: Génération des chemins secondaires
        if params.path_branches > 0:
            self._generate_secondary_paths(params)
        
        # Phase 5: Création des zones de placement
        self._generate_placement_zones(params)
        
        # Phase 6: Ajout des éléments décoratifs
        self._add_decorative_elements(params)
        
        # Phase 7: Post-traitement thématique
        self._apply_theme_specific_elements(params)
        
        # Phase 8: Validation et corrections
        self._validate_and_fix_map(params)
        
        self.logger.info("Génération de carte terminée avec succès")
        return self.current_grid
    
    def _reset_generation_state(self):
        """Remet à zéro l'état de génération"""
        self.current_grid = None
        self.spawn_point = None
        self.base_point = None
        self.main_path = []
        self.placement_zones = []
        self.decorations = []
    
    def _place_spawn_and_base(self, params: GenerationParams):
        """Place les points d'apparition et la base"""
        width, height = params.width, params.height
        
        # Choix de l'orientation (horizontal ou vertical)
        if random.choice([True, False]):
            # Orientation horizontale
            self.spawn_point = (0, random.randint(height // 4, 3 * height // 4))
            self.base_point = (width - 1, random.randint(height // 4, 3 * height // 4))
        else:
            # Orientation verticale
            self.spawn_point = (random.randint(width // 4, 3 * width // 4), 0)
            self.base_point = (random.randint(width // 4, 3 * width // 4), height - 1)
        
        # Placement sur la grille
        self.current_grid.set_tile(*self.spawn_point, TileType.SPAWN)
        self.current_grid.set_tile(*self.base_point, TileType.BASE)
        
        self.logger.debug(f"Spawn: {self.spawn_point}, Base: {self.base_point}")
    
    def _generate_main_path(self, params: GenerationParams):
        """Génère le chemin principal entre spawn et base"""
        self.logger.debug("Génération du chemin principal")
        
        # Algorithme de Random Walk contraint
        current = self.spawn_point
        target = self.base_point
        path = [current]
        
        max_iterations = params.width * params.height
        iteration = 0
        
        while current != target and iteration < max_iterations:
            iteration += 1
            
            # Calcul de la direction générale vers la cible
            dx = 1 if target[0] > current[0] else -1 if target[0] < current[0] else 0
            dy = 1 if target[1] > current[1] else -1 if target[1] < current[1] else 0
            
            # Ajout de complexité selon le paramètre
            if random.random() < params.path_complexity:
                # Mouvement aléatoire (sinuosité)
                possible_moves = []
                for delta_x, delta_y in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    new_x = current[0] + delta_x
                    new_y = current[1] + delta_y
                    
                    if self._is_valid_position(new_x, new_y, params):
                        possible_moves.append((new_x, new_y))
                
                if possible_moves:
                    current = random.choice(possible_moves)
            else:
                # Mouvement vers la cible
                if dx != 0 and (dy == 0 or random.choice([True, False])):
                    new_x = current[0] + dx
                    if self._is_valid_position(new_x, current[1], params):
                        current = (new_x, current[1])
                elif dy != 0:
                    new_y = current[1] + dy
                    if self._is_valid_position(current[0], new_y, params):
                        current = (current[0], new_y)
            
            if current not in path:
                path.append(current)
        
        # Élargissement du chemin selon PATH_WIDTH
        self.main_path = self._widen_path(path, GRID_CONFIG['PATH_WIDTH'])
        
        # Application sur la grille
        for x, y in self.main_path:
            if (x, y) not in [self.spawn_point, self.base_point]:
                self.current_grid.set_tile(x, y, TileType.PATH)
        
        self.logger.debug(f"Chemin principal: {len(self.main_path)} tuiles")
    
    def _generate_secondary_paths(self, params: GenerationParams):
        """Génère des chemins secondaires pour plus de complexité"""
        for i in range(params.path_branches):
            # Choix d'un point de départ sur le chemin principal
            if len(self.main_path) < 10:
                continue
                
            branch_start_idx = random.randint(5, len(self.main_path) - 6)
            branch_start = self.main_path[branch_start_idx]
            
            # Génération d'un petit chemin secondaire
            branch_length = random.randint(3, 8)
            self._generate_branch_path(branch_start, branch_length, params)
    
    def _generate_branch_path(self, start: Tuple[int, int], length: int, params: GenerationParams):
        """Génère un chemin de branche à partir d'un point donné"""
        current = start
        branch_path = []
        
        for _ in range(length):
            # Direction aléatoire perpendiculaire au chemin principal
            possible_moves = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_x, new_y = current[0] + dx, current[1] + dy
                
                if (self._is_valid_position(new_x, new_y, params) and 
                    (new_x, new_y) not in self.main_path and
                    (new_x, new_y) not in branch_path):
                    possible_moves.append((new_x, new_y))
            
            if not possible_moves:
                break
                
            current = random.choice(possible_moves)
            branch_path.append(current)
        
        # Application sur la grille
        for x, y in branch_path:
            self.current_grid.set_tile(x, y, TileType.PATH)
        
        self.main_path.extend(branch_path)
    
    def _generate_placement_zones(self, params: GenerationParams):
        """Génère les zones de placement des tours"""
        self.logger.debug("Génération des zones de placement")
        
        zones_created = 0
        attempts = 0
        max_attempts = params.width * params.height
        
        while zones_created < params.min_placement_areas and attempts < max_attempts:
            attempts += 1
            
            # Position aléatoire
            center_x = random.randint(1, params.width - 2)
            center_y = random.randint(1, params.height - 2)
            
            # Vérification de la distance du chemin
            if self._distance_to_path(center_x, center_y) < 2:
                continue
            
            # Création d'une zone de placement
            zone = self._create_placement_zone(
                center_x, center_y, 
                params.placement_area_size, 
                params
            )
            
            if len(zone) >= 4:  # Zone minimum viable
                self.placement_zones.append(zone)
                zones_created += 1
                
                # Application sur la grille
                for x, y in zone:
                    self.current_grid.set_tile(x, y, TileType.BUILDABLE)
        
        self.logger.debug(f"Zones de placement créées: {zones_created}")
    
    def _create_placement_zone(self, center_x: int, center_y: int, 
                              size: int, params: GenerationParams) -> List[Tuple[int, int]]:
        """Crée une zone de placement autour d'un point central"""
        zone = []
        
        # Forme légèrement irrégulière
        for dx in range(-size//2, size//2 + 1):
            for dy in range(-size//2, size//2 + 1):
                x, y = center_x + dx, center_y + dy
                
                # Vérifications
                if (self._is_valid_position(x, y, params) and
                    self.current_grid.get_tile(x, y) == TileType.EMPTY and
                    self._distance_to_path(x, y) >= 1):
                    
                    # Forme organique (pas un carré parfait)
                    if (dx * dx + dy * dy) <= (size * size / 4) + random.randint(-1, 1):
                        zone.append((x, y))
        
        return zone
    
    def _add_decorative_elements(self, params: GenerationParams):
        """Ajoute des éléments décoratifs selon le thème"""
        self.logger.debug("Ajout d'éléments décoratifs")
        
        num_decorations = int(
            params.width * params.height * params.decoration_density * 0.1
        )
        
        decoration_types = self._get_decoration_types_for_theme(params.theme)
        
        for _ in range(num_decorations):
            # Position aléatoire
            x = random.randint(0, params.width - 1)
            y = random.randint(0, params.height - 1)
            
            # Vérification que la position est libre
            if (self.current_grid.get_tile(x, y) == TileType.EMPTY and
                self._distance_to_path(x, y) >= 1):
                
                decoration_type = random.choice(decoration_types)
                decoration = DecorationElement(
                    name=decoration_type['name'],
                    position=(x, y),
                    size=decoration_type['size'],
                    rotation=random.uniform(0, 360),
                    scale=random.uniform(0.8, 1.2)
                )
                
                self.decorations.append(decoration)
                self.current_grid.set_tile(x, y, TileType.DECORATION)
    
    def _apply_theme_specific_elements(self, params: GenerationParams):
        """Applique des éléments spécifiques au thème choisi"""
        theme_handlers = {
            EnvironmentTheme.INDUSTRIAL_FACTORY: self._apply_factory_theme,
            EnvironmentTheme.STEAMPUNK_PORT: self._apply_port_theme,
            EnvironmentTheme.GEOTHERMAL_MINE: self._apply_mine_theme,
            EnvironmentTheme.INVENTOR_LAB: self._apply_lab_theme,
        }
        
        handler = theme_handlers.get(params.theme)
        if handler:
            handler(params)
    
    def _apply_factory_theme(self, params: GenerationParams):
        """Applique le thème d'usine industrielle"""
        # Ajout de cheminées d'usine
        for _ in range(random.randint(2, 4)):
            self._place_large_decoration("industrial_chimney", (3, 3), params)
        
        # Conduites de vapeur le long des chemins
        self._add_steam_pipes_along_paths()
    
    def _apply_port_theme(self, params: GenerationParams):
        """Applique le thème de port steampunk"""
        # Grues à vapeur
        for _ in range(random.randint(1, 3)):
            self._place_large_decoration("steam_crane", (2, 4), params)
        
        # Entrepôts
        for _ in range(random.randint(2, 4)):
            self._place_large_decoration("warehouse", (4, 2), params)
    
    def _apply_mine_theme(self, params: GenerationParams):
        """Applique le thème de mine géothermique"""
        # Rails de wagonnets
        self._add_mine_rails()
        
        # Geysers de vapeur
        for _ in range(random.randint(3, 6)):
            self._place_decoration("steam_geyser", (1, 1), params)
    
    def _apply_lab_theme(self, params: GenerationParams):
        """Applique le thème de laboratoire d'inventeur"""
        # Machines expérimentales
        for _ in range(random.randint(2, 5)):
            self._place_decoration("experimental_machine", (2, 2), params)
        
        # Arcs électriques (décoratifs)
        self._add_electrical_effects()
    
    def _validate_and_fix_map(self, params: GenerationParams):
        """Valide la carte et corrige les problèmes éventuels"""
        self.logger.debug("Validation de la carte")
        
        # Vérification que le chemin est continu
        if not self._is_path_continuous():
            self.logger.warning("Chemin discontinu détecté, correction...")
            self._fix_path_continuity()
        
        # Vérification du nombre de zones de placement
        if len(self.placement_zones) < params.min_placement_areas // 2:
            self.logger.warning("Pas assez de zones de placement, ajout...")
            self._add_emergency_placement_zones(params)
        
        # Vérification que la base est accessible
        if not self._is_base_accessible():
            self.logger.error("Base inaccessible! Correction forcée...")
            self._force_path_to_base()
    
    # ═══════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES
    # ═══════════════════════════════════════════════════════════
    
    def _is_valid_position(self, x: int, y: int, params: GenerationParams) -> bool:
        """Vérifie si une position est valide dans la grille"""
        return 0 <= x < params.width and 0 <= y < params.height
    
    def _distance_to_path(self, x: int, y: int) -> float:
        """Calcule la distance minimale d'un point au chemin"""
        if not self.main_path:
            return float('inf')
        
        min_dist = float('inf')
        for path_x, path_y in self.main_path:
            dist = abs(x - path_x) + abs(y - path_y)  # Distance Manhattan
            min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _widen_path(self, path: List[Tuple[int, int]], width: int) -> List[Tuple[int, int]]:
        """Élargit un chemin pour obtenir la largeur désirée"""
        if width <= 1:
            return path
        
        widened = set(path)
        
        for x, y in path:
            for dx in range(-(width//2), width//2 + 1):
                for dy in range(-(width//2), width//2 + 1):
                    if abs(dx) + abs(dy) <= width//2:  # Forme de losange
                        new_x, new_y = x + dx, y + dy
                        if (0 <= new_x < GRID_CONFIG['GRID_WIDTH'] and
                            0 <= new_y < GRID_CONFIG['GRID_HEIGHT']):
                            widened.add((new_x, new_y))
        
        return list(widened)
    
    def _get_decoration_types_for_theme(self, theme: EnvironmentTheme) -> List[Dict]:
        """Retourne les types de décorations pour un thème donné"""
        base_decorations = [
            {'name': 'gear_small', 'size': (1, 1)},
            {'name': 'gear_medium', 'size': (2, 2)},
            {'name': 'steam_pipe', 'size': (1, 3)},
            {'name': 'lamp_post', 'size': (1, 1)},
        ]
        
        theme_specific = {
            EnvironmentTheme.INDUSTRIAL_FACTORY: [
                {'name': 'furnace', 'size': (2, 2)},
                {'name': 'conveyor_belt', 'size': (4, 1)},
                {'name': 'steam_tank', 'size': (2, 3)},
            ],
            EnvironmentTheme.STEAMPUNK_PORT: [
                {'name': 'anchor', 'size': (2, 2)},
                {'name': 'cargo_crate', 'size': (1, 1)},
                {'name': 'ship_wheel', 'size': (2, 2)},
            ],
            EnvironmentTheme.GEOTHERMAL_MINE: [
                {'name': 'mine_cart', 'size': (1, 2)},
                {'name': 'pickaxe', 'size': (1, 1)},
                {'name': 'crystal_formation', 'size': (2, 2)},
            ],
            EnvironmentTheme.INVENTOR_LAB: [
                {'name': 'tesla_coil', 'size': (2, 3)},
                {'name': 'workbench', 'size': (3, 2)},
                {'name': 'blueprint_table', 'size': (2, 2)},
            ]
        }
        
        return base_decorations + theme_specific.get(theme, [])
    
    def _place_decoration(self, name: str, size: Tuple[int, int], params: GenerationParams):
        """Place une décoration à une position libre"""
        for _ in range(10):  # 10 tentatives
            x = random.randint(0, params.width - size[0])
            y = random.randint(0, params.height - size[1])
            
            # Vérification que la zone est libre
            can_place = True
            for dx in range(size[0]):
                for dy in range(size[1]):
                    if self.current_grid.get_tile(x + dx, y + dy) != TileType.EMPTY:
                        can_place = False
                        break
                if not can_place:
                    break
            
            if can_place and self._distance_to_path(x, y) >= 1:
                decoration = DecorationElement(
                    name=name,
                    position=(x, y),
                    size=size,
                    rotation=random.uniform(0, 360)
                )
                self.decorations.append(decoration)
                
                # Marquage sur la grille
                for dx in range(size[0]):
                    for dy in range(size[1]):
                        self.current_grid.set_tile(x + dx, y + dy, TileType.DECORATION)
                break
    
    def _place_large_decoration(self, name: str, size: Tuple[int, int], params: GenerationParams):
        """Place une grande décoration en évitant les collisions"""
        self._place_decoration(name, size, params)
    
    def _add_steam_pipes_along_paths(self):
        """Ajoute des conduites de vapeur le long des chemins"""
        # Simplification: quelques conduites aléatoires
        for _ in range(random.randint(3, 6)):
            if self.main_path:
                path_point = random.choice(self.main_path)
                # Ajouter une conduite perpendiculaire au chemin
                pipe_decoration = DecorationElement(
                    name="steam_pipe_main",
                    position=path_point,
                    size=(1, 3),
                    rotation=random.choice([0, 90])
                )
                self.decorations.append(pipe_decoration)
    
    def _add_mine_rails(self):
        """Ajoute des rails de mine"""
        # Rails parallèles au chemin principal sur certaines sections
        if len(self.main_path) > 10:
            start_idx = random.randint(0, len(self.main_path) - 10)
            for i in range(start_idx, min(start_idx + 8, len(self.main_path))):
                rail_decoration = DecorationElement(
                    name="mine_rail",
                    position=self.main_path[i],
                    size=(1, 1),
                    rotation=0
                )
                self.decorations.append(rail_decoration)
    
    def _add_electrical_effects(self):
        """Ajoute des effets électriques décoratifs"""
        for _ in range(random.randint(2, 4)):
            if self.placement_zones:
                zone = random.choice(self.placement_zones)
                if zone:
                    position = random.choice(zone)
                    electrical_decoration = DecorationElement(
                        name="electrical_arc",
                        position=position,
                        size=(1, 1),
                        rotation=0
                    )
                    self.decorations.append(electrical_decoration)
    
    def _is_path_continuous(self) -> bool:
        """Vérifie que le chemin principal est continu"""
        # Implémentation simplifiée: vérification que spawn et base sont connectés
        return (self.spawn_point in self.main_path and 
                self.base_point in self.main_path)
    
    def _fix_path_continuity(self):
        """Corrige la continuité du chemin"""
        # Force une connexion directe entre spawn et base
        self._generate_main_path(GenerationParams(path_complexity=0.1))
    
    def _add_emergency_placement_zones(self, params: GenerationParams):
        """Ajoute des zones de placement d'urgence"""
        for _ in range(params.min_placement_areas - len(self.placement_zones)):
            # Placement forcé dans les coins
            corners = [
                (2, 2), (params.width - 3, 2),
                (2, params.height - 3), (params.width - 3, params.height - 3)
            ]
            
            for corner_x, corner_y in corners:
                if self._distance_to_path(corner_x, corner_y) >= 2:
                    emergency_zone = [(corner_x, corner_y), (corner_x + 1, corner_y),
                                    (corner_x, corner_y + 1), (corner_x + 1, corner_y + 1)]
                    self.placement_zones.append(emergency_zone)
                    
                    for x, y in emergency_zone:
                        if self._is_valid_position(x, y, params):
                            self.current_grid.set_tile(x, y, TileType.BUILDABLE)
                    break
    
    def _is_base_accessible(self) -> bool:
        """Vérifie que la base est accessible depuis le spawn"""
        # Implémentation simplifiée
        return self.base_point in self.main_path
    
    def _force_path_to_base(self):
        """Force un chemin vers la base"""
        if self.base_point not in self.main_path:
            self.main_path.append(self.base_point)
            self.current_grid.set_tile(*self.base_point, TileType.PATH)
    
    # ═══════════════════════════════════════════════════════════
    # ACCESSEURS
    # ═══════════════════════════════════════════════════════════
    
    def get_decorations(self) -> List[DecorationElement]:
        """Retourne la liste des décorations"""
        return self.decorations.copy()
    
    def get_placement_zones(self) -> List[List[Tuple[int, int]]]:
        """Retourne les zones de placement"""
        return self.placement_zones.copy()
    
    def get_main_path(self) -> List[Tuple[int, int]]:
        """Retourne le chemin principal"""
        return self.main_path.copy()
    
    def get_spawn_point(self) -> Tuple[int, int]:
        """Retourne le point de spawn"""
        return self.spawn_point
    
    def get_base_point(self) -> Tuple[int, int]:
        """Retourne le point de base"""
        return self.base_point