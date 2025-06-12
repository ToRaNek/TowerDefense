# world/grid.py
"""
Steam Defense - Système de grille pour la carte de jeu
Gère la grille de tuiles et les opérations spatiales
"""

import logging
from typing import List, Tuple, Set, Optional, Dict, Any, Iterator
from enum import Enum
import numpy as np
from dataclasses import dataclass

from config.settings import GRID_CONFIG


class TileType(Enum):
    """Types de tuiles disponibles"""
    EMPTY = 0          # Tuile vide (constructible par défaut)
    PATH = 1           # Chemin pour les ennemis
    WALL = 2           # Obstacle infranchissable
    SPAWN = 3          # Point d'apparition des ennemis
    BASE = 4           # Base à défendre
    DECORATION = 5     # Élément décoratif
    BUILDABLE = 6      # Zone de construction de tours
    WATER = 7          # Eau (infranchissable pour unités terrestres)
    BRIDGE = 8         # Pont (franchissable)


@dataclass
class TileProperties:
    """Propriétés étendues d'une tuile"""
    tile_type: TileType = TileType.EMPTY
    is_walkable: bool = True
    is_buildable: bool = True
    movement_cost: float = 1.0
    elevation: float = 0.0
    
    # Propriétés visuelles
    rotation: float = 0.0
    variant: int = 0
    
    # Données personnalisées
    custom_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_data is None:
            self.custom_data = {}
        
        # Configuration automatique selon le type
        if self.tile_type == TileType.WALL:
            self.is_walkable = False
            self.is_buildable = False
        elif self.tile_type == TileType.PATH:
            self.is_buildable = False
        elif self.tile_type == TileType.SPAWN or self.tile_type == TileType.BASE:
            self.is_buildable = False
        elif self.tile_type == TileType.DECORATION:
            self.is_buildable = False
        elif self.tile_type == TileType.WATER:
            self.is_walkable = False
            self.is_buildable = False
            self.movement_cost = float('inf')


class Grid:
    """
    Grille de jeu 2D pour Tower Defense
    Gère la représentation spatiale et les opérations sur les tuiles
    """
    
    def __init__(self, width: int, height: int, tile_size: int = None):
        """
        Initialise la grille
        
        Args:
            width: Largeur en nombre de tuiles
            height: Hauteur en nombre de tuiles
            tile_size: Taille d'une tuile en pixels
        """
        self.width = width
        self.height = height
        self.tile_size = tile_size or GRID_CONFIG['TILE_SIZE']
        
        # Grille des types de tuiles (pour compatibilité/performance)
        self.tiles = np.full((height, width), TileType.EMPTY.value, dtype=np.int8)
        
        # Grille des propriétés détaillées
        self.tile_properties: Dict[Tuple[int, int], TileProperties] = {}
        
        # Cache pour optimiser les requêtes fréquentes
        self._walkable_cache: Optional[np.ndarray] = None
        self._buildable_cache: Optional[np.ndarray] = None
        self._cache_dirty = True
        
        # Métadonnées de la grille
        self.metadata = {
            'created_at': 0.0,
            'last_modified': 0.0,
            'version': 1,
            'theme': 'industrial_factory'
        }
        
        self.logger = logging.getLogger('Grid')
        self.logger.debug(f"Grille créée: {width}x{height} (tuiles de {self.tile_size}px)")
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Vérifie si une position est valide dans la grille"""
        return 0 <= x < self.width and 0 <= y < self.height
    
    def get_tile(self, x: int, y: int) -> TileType:
        """Récupère le type d'une tuile"""
        if not self.is_valid_position(x, y):
            return TileType.WALL  # Les positions invalides sont considérées comme des murs
        
        return TileType(self.tiles[y, x])
    
    def set_tile(self, x: int, y: int, tile_type: TileType):
        """Définit le type d'une tuile"""
        if not self.is_valid_position(x, y):
            self.logger.warning(f"Tentative de définition de tuile hors limites: ({x}, {y})")
            return
        
        old_type = TileType(self.tiles[y, x])
        self.tiles[y, x] = tile_type.value
        
        # Mise à jour des propriétés détaillées
        if (x, y) not in self.tile_properties:
            self.tile_properties[(x, y)] = TileProperties()
        
        self.tile_properties[(x, y)].tile_type = tile_type
        
        # Invalidation du cache
        self._cache_dirty = True
        
        self.logger.debug(f"Tuile ({x}, {y}) changée: {old_type.name} -> {tile_type.name}")
    
    def get_tile_properties(self, x: int, y: int) -> TileProperties:
        """Récupère les propriétés détaillées d'une tuile"""
        if not self.is_valid_position(x, y):
            return TileProperties(tile_type=TileType.WALL, is_walkable=False, is_buildable=False)
        
        if (x, y) not in self.tile_properties:
            # Création des propriétés par défaut
            tile_type = self.get_tile(x, y)
            self.tile_properties[(x, y)] = TileProperties(tile_type=tile_type)
        
        return self.tile_properties[(x, y)]
    
    def set_tile_properties(self, x: int, y: int, properties: TileProperties):
        """Définit les propriétés détaillées d'une tuile"""
        if not self.is_valid_position(x, y):
            return
        
        self.tile_properties[(x, y)] = properties
        self.tiles[y, x] = properties.tile_type.value
        self._cache_dirty = True
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Vérifie si une tuile est franchissable"""
        properties = self.get_tile_properties(x, y)
        return properties.is_walkable
    
    def is_buildable(self, x: int, y: int) -> bool:
        """Vérifie si on peut construire sur une tuile"""
        properties = self.get_tile_properties(x, y)
        return properties.is_buildable
    
    def get_movement_cost(self, x: int, y: int) -> float:
        """Récupère le coût de mouvement d'une tuile"""
        properties = self.get_tile_properties(x, y)
        return properties.movement_cost
    
    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convertit des coordonnées monde en coordonnées grille"""
        grid_x = int(world_x // self.tile_size)
        grid_y = int(world_y // self.tile_size)
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convertit des coordonnées grille en coordonnées monde (centre de la tuile)"""
        world_x = grid_x * self.tile_size + self.tile_size // 2
        world_y = grid_y * self.tile_size + self.tile_size // 2
        return float(world_x), float(world_y)
    
    def grid_to_world_corner(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convertit des coordonnées grille en coordonnées monde (coin inférieur gauche)"""
        world_x = grid_x * self.tile_size
        world_y = grid_y * self.tile_size
        return float(world_x), float(world_y)
    
    def get_neighbors(self, x: int, y: int, include_diagonals: bool = False) -> List[Tuple[int, int]]:
        """
        Récupère les voisins d'une tuile
        
        Args:
            x, y: Position de la tuile
            include_diagonals: Inclure les voisins diagonaux
            
        Returns:
            Liste des positions voisines valides
        """
        neighbors = []
        
        # Voisins orthogonaux
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        if include_diagonals:
            directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_valid_position(nx, ny):
                neighbors.append((nx, ny))
        
        return neighbors
    
    def get_walkable_neighbors(self, x: int, y: int, include_diagonals: bool = False) -> List[Tuple[int, int]]:
        """Récupère les voisins franchissables d'une tuile"""
        neighbors = self.get_neighbors(x, y, include_diagonals)
        return [(nx, ny) for nx, ny in neighbors if self.is_walkable(nx, ny)]
    
    def get_tiles_in_radius(self, center_x: int, center_y: int, radius: float) -> List[Tuple[int, int]]:
        """
        Récupère toutes les tuiles dans un rayon donné
        
        Args:
            center_x, center_y: Centre du cercle
            radius: Rayon en tuiles
            
        Returns:
            Liste des positions dans le rayon
        """
        tiles = []
        
        # Boîte englobante pour optimiser
        min_x = max(0, int(center_x - radius))
        max_x = min(self.width, int(center_x + radius + 1))
        min_y = max(0, int(center_y - radius))
        max_y = min(self.height, int(center_y + radius + 1))
        
        radius_squared = radius * radius
        
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                # Distance au centre
                dx = x - center_x
                dy = y - center_y
                distance_squared = dx * dx + dy * dy
                
                if distance_squared <= radius_squared:
                    tiles.append((x, y))
        
        return tiles
    
    def get_tiles_of_type(self, tile_type: TileType) -> List[Tuple[int, int]]:
        """Récupère toutes les tuiles d'un type donné"""
        positions = []
        
        # Utilisation de NumPy pour une recherche efficace
        y_indices, x_indices = np.where(self.tiles == tile_type.value)
        
        for y, x in zip(y_indices, x_indices):
            positions.append((int(x), int(y)))
        
        return positions
    
    def flood_fill(self, start_x: int, start_y: int, target_type: TileType, 
                  replacement_type: TileType) -> int:
        """
        Remplissage par diffusion (flood fill)
        
        Args:
            start_x, start_y: Position de départ
            target_type: Type de tuile à remplacer
            replacement_type: Type de remplacement
            
        Returns:
            Nombre de tuiles modifiées
        """
        if not self.is_valid_position(start_x, start_y):
            return 0
        
        if self.get_tile(start_x, start_y) != target_type:
            return 0
        
        if target_type == replacement_type:
            return 0
        
        # Pile pour l'algorithme iteratif
        stack = [(start_x, start_y)]
        visited = set()
        modified_count = 0
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited:
                continue
            
            if not self.is_valid_position(x, y):
                continue
            
            if self.get_tile(x, y) != target_type:
                continue
            
            # Modification de la tuile
            self.set_tile(x, y, replacement_type)
            visited.add((x, y))
            modified_count += 1
            
            # Ajout des voisins
            for nx, ny in self.get_neighbors(x, y):
                if (nx, ny) not in visited:
                    stack.append((nx, ny))
        
        self.logger.debug(f"Flood fill: {modified_count} tuiles modifiées")
        return modified_count
    
    def find_path_between_types(self, start_type: TileType, end_type: TileType) -> List[Tuple[int, int]]:
        """
        Trouve un chemin simple entre deux types de tuiles
        Utilise une recherche en largeur (BFS)
        """
        start_positions = self.get_tiles_of_type(start_type)
        end_positions = self.get_tiles_of_type(end_type)
        
        if not start_positions or not end_positions:
            return []
        
        # Utilise la première position de chaque type
        start = start_positions[0]
        end = end_positions[0]
        
        return self._bfs_path(start, end)
    
    def _bfs_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Recherche de chemin en largeur (BFS)"""
        from collections import deque
        
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            (x, y), path = queue.popleft()
            
            if (x, y) == end:
                return path
            
            for nx, ny in self.get_walkable_neighbors(x, y):
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))
        
        return []  # Aucun chemin trouvé
    
    def get_walkable_mask(self) -> np.ndarray:
        """Retourne un masque NumPy des tuiles franchissables (pour optimisation)"""
        if self._cache_dirty or self._walkable_cache is None:
            self._rebuild_cache()
        
        return self._walkable_cache.copy()
    
    def get_buildable_mask(self) -> np.ndarray:
        """Retourne un masque NumPy des tuiles constructibles"""
        if self._cache_dirty or self._buildable_cache is None:
            self._rebuild_cache()
        
        return self._buildable_cache.copy()
    
    def _rebuild_cache(self):
        """Reconstruit les caches d'optimisation"""
        self._walkable_cache = np.zeros((self.height, self.width), dtype=bool)
        self._buildable_cache = np.zeros((self.height, self.width), dtype=bool)
        
        for y in range(self.height):
            for x in range(self.width):
                properties = self.get_tile_properties(x, y)
                self._walkable_cache[y, x] = properties.is_walkable
                self._buildable_cache[y, x] = properties.is_buildable
        
        self._cache_dirty = False
        self.logger.debug("Cache de grille reconstruit")
    
    def clear_area(self, x: int, y: int, width: int, height: int, 
                  tile_type: TileType = TileType.EMPTY):
        """Vide une zone rectangulaire"""
        for dy in range(height):
            for dx in range(width):
                tx, ty = x + dx, y + dy
                if self.is_valid_position(tx, ty):
                    self.set_tile(tx, ty, tile_type)
        
        self.logger.debug(f"Zone vidée: ({x}, {y}) {width}x{height}")
    
    def copy_area(self, src_x: int, src_y: int, dst_x: int, dst_y: int,
                 width: int, height: int):
        """Copie une zone rectangulaire"""
        # Extraction de la zone source
        temp_tiles = []
        temp_properties = []
        
        for dy in range(height):
            row_tiles = []
            row_properties = []
            for dx in range(width):
                sx, sy = src_x + dx, src_y + dy
                if self.is_valid_position(sx, sy):
                    row_tiles.append(self.get_tile(sx, sy))
                    row_properties.append(self.get_tile_properties(sx, sy))
                else:
                    row_tiles.append(TileType.WALL)
                    row_properties.append(TileProperties(tile_type=TileType.WALL))
            
            temp_tiles.append(row_tiles)
            temp_properties.append(row_properties)
        
        # Application à la zone de destination
        for dy in range(height):
            for dx in range(width):
                dx_pos, dy_pos = dst_x + dx, dst_y + dy
                if self.is_valid_position(dx_pos, dy_pos):
                    self.set_tile(dx_pos, dy_pos, temp_tiles[dy][dx])
                    self.set_tile_properties(dx_pos, dy_pos, temp_properties[dy][dx])
    
    def rotate_area(self, x: int, y: int, width: int, height: int, 
                   clockwise: bool = True):
        """Fait tourner une zone rectangulaire de 90 degrés"""
        # Extraction des données
        temp_tiles = []
        temp_properties = []
        
        for dy in range(height):
            row_tiles = []
            row_props = []
            for dx in range(width):
                tx, ty = x + dx, y + dy
                if self.is_valid_position(tx, ty):
                    row_tiles.append(self.get_tile(tx, ty))
                    row_props.append(self.get_tile_properties(tx, ty))
                else:
                    row_tiles.append(TileType.WALL)
                    row_props.append(TileProperties(tile_type=TileType.WALL))
            
            temp_tiles.append(row_tiles)
            temp_properties.append(row_props)
        
        # Rotation et application
        for dy in range(height):
            for dx in range(width):
                tx, ty = x + dx, y + dy
                
                if clockwise:
                    # Rotation horaire
                    src_dx = dy
                    src_dy = width - 1 - dx
                else:
                    # Rotation anti-horaire
                    src_dx = height - 1 - dy
                    src_dy = dx
                
                if (0 <= src_dy < height and 0 <= src_dx < width and
                    self.is_valid_position(tx, ty)):
                    
                    new_tile = temp_tiles[src_dy][src_dx]
                    new_props = temp_properties[src_dy][src_dx]
                    
                    self.set_tile(tx, ty, new_tile)
                    self.set_tile_properties(tx, ty, new_props)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la grille"""
        type_counts = {}
        
        # Comptage des types de tuiles
        for tile_type in TileType:
            positions = self.get_tiles_of_type(tile_type)
            type_counts[tile_type.name] = len(positions)
        
        # Calcul des pourcentages
        total_tiles = self.width * self.height
        type_percentages = {
            name: (count / total_tiles) * 100
            for name, count in type_counts.items()
        }
        
        return {
            'dimensions': (self.width, self.height),
            'total_tiles': total_tiles,
            'tile_size': self.tile_size,
            'type_counts': type_counts,
            'type_percentages': type_percentages,
            'has_spawn': type_counts.get('SPAWN', 0) > 0,
            'has_base': type_counts.get('BASE', 0) > 0,
            'path_length': type_counts.get('PATH', 0),
            'buildable_tiles': type_counts.get('EMPTY', 0) + type_counts.get('BUILDABLE', 0)
        }
    
    def validate_grid(self) -> List[str]:
        """Valide la cohérence de la grille et retourne les problèmes détectés"""
        issues = []
        
        stats = self.get_statistics()
        
        # Vérification de la présence d'éléments essentiels
        if not stats['has_spawn']:
            issues.append("Aucun point de spawn défini")
        
        if not stats['has_base']:
            issues.append("Aucune base définie")
        
        # Vérification du chemin
        if stats['path_length'] == 0:
            issues.append("Aucun chemin défini")
        elif stats['path_length'] < 10:
            issues.append("Chemin trop court (moins de 10 tuiles)")
        
        # Vérification des zones constructibles
        if stats['buildable_tiles'] < 5:
            issues.append("Pas assez de zones constructibles")
        
        # Vérification de la connectivité (simple)
        spawn_positions = self.get_tiles_of_type(TileType.SPAWN)
        base_positions = self.get_tiles_of_type(TileType.BASE)
        
        if spawn_positions and base_positions:
            path = self._bfs_path(spawn_positions[0], base_positions[0])
            if not path:
                issues.append("Aucun chemin entre spawn et base")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Exporte la grille vers un dictionnaire (sérialisation)"""
        return {
            'width': self.width,
            'height': self.height,
            'tile_size': self.tile_size,
            'tiles': self.tiles.tolist(),
            'properties': {
                f"{x},{y}": {
                    'tile_type': props.tile_type.value,
                    'is_walkable': props.is_walkable,
                    'is_buildable': props.is_buildable,
                    'movement_cost': props.movement_cost,
                    'elevation': props.elevation,
                    'rotation': props.rotation,
                    'variant': props.variant,
                    'custom_data': props.custom_data
                }
                for (x, y), props in self.tile_properties.items()
            },
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Grid':
        """Importe une grille depuis un dictionnaire"""
        grid = cls(data['width'], data['height'], data.get('tile_size'))
        
        # Import des tuiles
        tiles_array = np.array(data['tiles'], dtype=np.int8)
        grid.tiles = tiles_array
        
        # Import des propriétés
        if 'properties' in data:
            for pos_str, props_data in data['properties'].items():
                x, y = map(int, pos_str.split(','))
                
                properties = TileProperties(
                    tile_type=TileType(props_data['tile_type']),
                    is_walkable=props_data.get('is_walkable', True),
                    is_buildable=props_data.get('is_buildable', True),
                    movement_cost=props_data.get('movement_cost', 1.0),
                    elevation=props_data.get('elevation', 0.0),
                    rotation=props_data.get('rotation', 0.0),
                    variant=props_data.get('variant', 0),
                    custom_data=props_data.get('custom_data', {})
                )
                
                grid.tile_properties[(x, y)] = properties
        
        # Import des métadonnées
        if 'metadata' in data:
            grid.metadata.update(data['metadata'])
        
        grid._cache_dirty = True
        return grid
    
    def __iter__(self) -> Iterator[Tuple[int, int, TileType]]:
        """Itérateur sur toutes les tuiles de la grille"""
        for y in range(self.height):
            for x in range(self.width):
                yield x, y, self.get_tile(x, y)
    
    def __str__(self) -> str:
        """Représentation textuelle de la grille"""
        lines = []
        
        # En-tête
        lines.append(f"Grid {self.width}x{self.height} (tile_size: {self.tile_size})")
        
        # Représentation visuelle simplifiée
        char_map = {
            TileType.EMPTY: '.',
            TileType.PATH: '#',
            TileType.WALL: '█',
            TileType.SPAWN: 'S',
            TileType.BASE: 'B',
            TileType.DECORATION: '*',
            TileType.BUILDABLE: '+',
            TileType.WATER: '~',
            TileType.BRIDGE: '='
        }
        
        for y in range(min(20, self.height)):  # Limite à 20 lignes pour l'affichage
            line = ""
            for x in range(min(40, self.width)):  # Limite à 40 colonnes
                tile_type = self.get_tile(x, y)
                line += char_map.get(tile_type, '?')
            
            if self.width > 40:
                line += "..."
            
            lines.append(line)
        
        if self.height > 20:
            lines.append("...")
        
        return '\n'.join(lines)