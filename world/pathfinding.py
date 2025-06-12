# world/pathfinding.py
"""
Steam Defense - Algorithmes de recherche de chemin
Implémente A*, Dijkstra et autres algorithmes pour la navigation
"""

import heapq
import math
import logging
from typing import List, Tuple, Optional, Dict, Set, Callable
from enum import Enum
from dataclasses import dataclass, field
import numpy as np

from world.grid import Grid, TileType


class PathfindingAlgorithm(Enum):
    """Algorithmes de pathfinding disponibles"""
    A_STAR = "a_star"
    DIJKSTRA = "dijkstra"
    BREADTH_FIRST = "breadth_first"
    JUMP_POINT_SEARCH = "jump_point_search"


class HeuristicType(Enum):
    """Types d'heuristiques pour A*"""
    MANHATTAN = "manhattan"
    EUCLIDEAN = "euclidean"
    DIAGONAL = "diagonal"
    ZERO = "zero"  # Équivalent à Dijkstra


@dataclass
class PathfindingResult:
    """Résultat d'une recherche de chemin"""
    path: List[Tuple[int, int]] = field(default_factory=list)
    cost: float = float('inf')
    nodes_explored: int = 0
    computation_time: float = 0.0
    algorithm_used: PathfindingAlgorithm = PathfindingAlgorithm.A_STAR
    success: bool = False
    
    def get_path_length(self) -> int:
        """Retourne la longueur du chemin en nombre de nœuds"""
        return len(self.path)
    
    def get_world_positions(self, grid: Grid) -> List[Tuple[float, float]]:
        """Convertit le chemin en coordonnées monde"""
        world_path = []
        for grid_x, grid_y in self.path:
            world_x, world_y = grid.grid_to_world(grid_x, grid_y)
            world_path.append((world_x, world_y))
        return world_path


@dataclass
class PathNode:
    """Nœud pour les algorithmes de pathfinding"""
    x: int
    y: int
    g_cost: float = float('inf')  # Coût depuis le début
    h_cost: float = 0.0           # Heuristique vers la fin
    f_cost: float = float('inf')  # Coût total (g + h)
    parent: Optional['PathNode'] = None
    
    def __lt__(self, other: 'PathNode') -> bool:
        """Pour la comparaison dans la priority queue"""
        if self.f_cost == other.f_cost:
            return self.h_cost < other.h_cost
        return self.f_cost < other.f_cost
    
    def __eq__(self, other: 'PathNode') -> bool:
        return self.x == other.x and self.y == other.y
    
    def __hash__(self) -> int:
        return hash((self.x, self.y))


class PathfindingConstraints:
    """Contraintes pour la recherche de chemin"""
    
    def __init__(self):
        # Contraintes de mouvement
        self.allow_diagonal: bool = False
        self.diagonal_cost_multiplier: float = math.sqrt(2)
        
        # Contraintes de terrain
        self.max_slope: float = float('inf')
        self.can_cross_water: bool = False
        self.min_clearance: int = 1  # Espace minimum autour du chemin
        
        # Contraintes dynamiques
        self.avoid_enemies: bool = False
        self.avoid_projectiles: bool = False
        self.enemy_avoidance_radius: float = 2.0
        
        # Contraintes de performance
        self.max_search_nodes: int = 10000
        self.max_computation_time: float = 0.1  # secondes
        
        # Filtres personnalisés
        self.custom_walkable_filter: Optional[Callable[[int, int], bool]] = None
        self.custom_cost_modifier: Optional[Callable[[int, int], float]] = None


class Pathfinder:
    """
    Classe principale pour la recherche de chemin
    Supporte plusieurs algorithmes et contraintes avancées
    """
    
    def __init__(self, grid: Grid):
        self.grid = grid
        self.logger = logging.getLogger('Pathfinder')
        
        # Cache pour optimiser les recherches répétées
        self.path_cache: Dict[str, PathfindingResult] = {}
        self.cache_enabled = True
        self.cache_max_size = 1000
        
        # Statistiques
        self.stats = {
            'total_searches': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_nodes_explored': 0.0,
            'average_computation_time': 0.0
        }
        
        # Heuristiques pré-calculées
        self.heuristic_functions = {
            HeuristicType.MANHATTAN: self._manhattan_distance,
            HeuristicType.EUCLIDEAN: self._euclidean_distance,
            HeuristicType.DIAGONAL: self._diagonal_distance,
            HeuristicType.ZERO: lambda x1, y1, x2, y2: 0.0
        }
    
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int],
                 algorithm: PathfindingAlgorithm = PathfindingAlgorithm.A_STAR,
                 heuristic: HeuristicType = HeuristicType.MANHATTAN,
                 constraints: Optional[PathfindingConstraints] = None) -> PathfindingResult:
        """
        Trouve un chemin entre deux points
        
        Args:
            start: Position de départ (x, y)
            goal: Position d'arrivée (x, y)
            algorithm: Algorithme à utiliser
            heuristic: Type d'heuristique
            constraints: Contraintes de pathfinding
            
        Returns:
            Résultat du pathfinding
        """
        import time
        start_time = time.time()
        
        # Validation des entrées
        if not self._validate_positions(start, goal):
            return PathfindingResult(
                success=False,
                computation_time=time.time() - start_time
            )
        
        # Contraintes par défaut
        if constraints is None:
            constraints = PathfindingConstraints()
        
        # Vérification du cache
        cache_key = self._generate_cache_key(start, goal, algorithm, heuristic, constraints)
        if self.cache_enabled and cache_key in self.path_cache:
            self.stats['cache_hits'] += 1
            cached_result = self.path_cache[cache_key]
            cached_result.computation_time = time.time() - start_time
            return cached_result
        
        self.stats['cache_misses'] += 1
        
        # Sélection de l'algorithme
        algorithm_functions = {
            PathfindingAlgorithm.A_STAR: self._a_star,
            PathfindingAlgorithm.DIJKSTRA: self._dijkstra,
            PathfindingAlgorithm.BREADTH_FIRST: self._breadth_first_search,
            PathfindingAlgorithm.JUMP_POINT_SEARCH: self._jump_point_search
        }
        
        algorithm_func = algorithm_functions.get(algorithm, self._a_star)
        
        # Exécution de l'algorithme
        result = algorithm_func(start, goal, heuristic, constraints)
        result.algorithm_used = algorithm
        result.computation_time = time.time() - start_time
        
        # Mise à jour des statistiques
        self._update_stats(result)
        
        # Mise en cache
        if self.cache_enabled and result.success:
            self._cache_result(cache_key, result)
        
        return result
    
    def _validate_positions(self, start: Tuple[int, int], goal: Tuple[int, int]) -> bool:
        """Valide que les positions sont valides"""
        start_x, start_y = start
        goal_x, goal_y = goal
        
        if not self.grid.is_valid_position(start_x, start_y):
            self.logger.warning(f"Position de départ invalide: {start}")
            return False
        
        if not self.grid.is_valid_position(goal_x, goal_y):
            self.logger.warning(f"Position d'arrivée invalide: {goal}")
            return False
        
        if not self.grid.is_walkable(goal_x, goal_y):
            self.logger.warning(f"Position d'arrivée non franchissable: {goal}")
            return False
        
        return True
    
    def _a_star(self, start: Tuple[int, int], goal: Tuple[int, int],
               heuristic: HeuristicType, constraints: PathfindingConstraints) -> PathfindingResult:
        """Implémentation de l'algorithme A*"""
        
        start_node = PathNode(start[0], start[1], g_cost=0.0)
        start_node.h_cost = self.heuristic_functions[heuristic](start[0], start[1], goal[0], goal[1])
        start_node.f_cost = start_node.g_cost + start_node.h_cost
        
        open_set = [start_node]
        closed_set: Set[Tuple[int, int]] = set()
        g_scores: Dict[Tuple[int, int], float] = {start: 0.0}
        
        nodes_explored = 0
        max_nodes = constraints.max_search_nodes
        
        while open_set and nodes_explored < max_nodes:
            # Récupération du nœud avec le plus petit f_cost
            current_node = heapq.heappop(open_set)
            current_pos = (current_node.x, current_node.y)
            
            # Objectif atteint
            if current_pos == goal:
                path = self._reconstruct_path(current_node)
                return PathfindingResult(
                    path=path,
                    cost=current_node.g_cost,
                    nodes_explored=nodes_explored,
                    success=True
                )
            
            closed_set.add(current_pos)
            nodes_explored += 1
            
            # Exploration des voisins
            neighbors = self._get_neighbors(current_node.x, current_node.y, constraints)
            
            for neighbor_x, neighbor_y, move_cost in neighbors:
                neighbor_pos = (neighbor_x, neighbor_y)
                
                if neighbor_pos in closed_set:
                    continue
                
                # Calcul du nouveau g_cost
                tentative_g_cost = current_node.g_cost + move_cost
                
                # Amélioration trouvée ?
                if neighbor_pos not in g_scores or tentative_g_cost < g_scores[neighbor_pos]:
                    # Création du nœud voisin
                    neighbor_node = PathNode(neighbor_x, neighbor_y)
                    neighbor_node.g_cost = tentative_g_cost
                    neighbor_node.h_cost = self.heuristic_functions[heuristic](
                        neighbor_x, neighbor_y, goal[0], goal[1]
                    )
                    neighbor_node.f_cost = neighbor_node.g_cost + neighbor_node.h_cost
                    neighbor_node.parent = current_node
                    
                    g_scores[neighbor_pos] = tentative_g_cost
                    
                    # Ajout à l'open set (en évitant les doublons)
                    if not any(node.x == neighbor_x and node.y == neighbor_y for node in open_set):
                        heapq.heappush(open_set, neighbor_node)
        
        # Aucun chemin trouvé
        return PathfindingResult(
            nodes_explored=nodes_explored,
            success=False
        )
    
    def _dijkstra(self, start: Tuple[int, int], goal: Tuple[int, int],
                 heuristic: HeuristicType, constraints: PathfindingConstraints) -> PathfindingResult:
        """Implémentation de l'algorithme de Dijkstra"""
        # Dijkstra est A* avec heuristique nulle
        return self._a_star(start, goal, HeuristicType.ZERO, constraints)
    
    def _breadth_first_search(self, start: Tuple[int, int], goal: Tuple[int, int],
                             heuristic: HeuristicType, constraints: PathfindingConstraints) -> PathfindingResult:
        """Implémentation de la recherche en largeur (BFS)"""
        from collections import deque
        
        queue = deque([PathNode(start[0], start[1], g_cost=0.0)])
        visited: Set[Tuple[int, int]] = {start}
        parent_map: Dict[Tuple[int, int], PathNode] = {}
        
        nodes_explored = 0
        max_nodes = constraints.max_search_nodes
        
        while queue and nodes_explored < max_nodes:
            current_node = queue.popleft()
            current_pos = (current_node.x, current_node.y)
            nodes_explored += 1
            
            # Objectif atteint
            if current_pos == goal:
                path = self._reconstruct_path_from_map(goal, parent_map, start)
                return PathfindingResult(
                    path=path,
                    cost=len(path) - 1,  # BFS donne le chemin le plus court en nombre de nœuds
                    nodes_explored=nodes_explored,
                    success=True
                )
            
            # Exploration des voisins
            neighbors = self._get_neighbors(current_node.x, current_node.y, constraints)
            
            for neighbor_x, neighbor_y, _ in neighbors:
                neighbor_pos = (neighbor_x, neighbor_y)
                
                if neighbor_pos not in visited:
                    visited.add(neighbor_pos)
                    neighbor_node = PathNode(neighbor_x, neighbor_y)
                    neighbor_node.parent = current_node
                    parent_map[neighbor_pos] = current_node
                    queue.append(neighbor_node)
        
        return PathfindingResult(
            nodes_explored=nodes_explored,
            success=False
        )
    
    def _jump_point_search(self, start: Tuple[int, int], goal: Tuple[int, int],
                          heuristic: HeuristicType, constraints: PathfindingConstraints) -> PathfindingResult:
        """
        Implémentation simplifiée de Jump Point Search
        Optimisation d'A* pour les grilles uniformes
        """
        # Pour cette implémentation simplifiée, on utilise A* standard
        # Une vraie implémentation JPS nécessiterait une logique plus complexe
        return self._a_star(start, goal, heuristic, constraints)
    
    def _get_neighbors(self, x: int, y: int, constraints: PathfindingConstraints) -> List[Tuple[int, int, float]]:
        """
        Récupère les voisins valides d'une position
        
        Returns:
            Liste de tuples (x, y, cost)
        """
        neighbors = []
        
        # Directions orthogonales
        orthogonal_dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        # Directions diagonales
        diagonal_dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        # Vérification des voisins orthogonaux
        for dx, dy in orthogonal_dirs:
            nx, ny = x + dx, y + dy
            cost = self._get_movement_cost(x, y, nx, ny, constraints)
            
            if cost is not None:
                neighbors.append((nx, ny, cost))
        
        # Vérification des voisins diagonaux si autorisés
        if constraints.allow_diagonal:
            for dx, dy in diagonal_dirs:
                nx, ny = x + dx, y + dy
                cost = self._get_movement_cost(x, y, nx, ny, constraints)
                
                if cost is not None:
                    # Coût diagonal plus élevé
                    diagonal_cost = cost * constraints.diagonal_cost_multiplier
                    neighbors.append((nx, ny, diagonal_cost))
        
        return neighbors
    
    def _get_movement_cost(self, from_x: int, from_y: int, to_x: int, to_y: int,
                          constraints: PathfindingConstraints) -> Optional[float]:
        """
        Calcule le coût de mouvement entre deux tuiles adjacentes
        
        Returns:
            Coût du mouvement ou None si le mouvement est impossible
        """
        # Vérification des limites
        if not self.grid.is_valid_position(to_x, to_y):
            return None
        
        # Vérification de la franchissabilité de base
        if not self.grid.is_walkable(to_x, to_y):
            # Exception pour l'eau si autorisée
            if not constraints.can_cross_water or self.grid.get_tile(to_x, to_y) != TileType.WATER:
                return None
        
        # Filtre personnalisé
        if constraints.custom_walkable_filter:
            if not constraints.custom_walkable_filter(to_x, to_y):
                return None
        
        # Coût de base du terrain
        base_cost = self.grid.get_movement_cost(to_x, to_y)
        
        # Modificateur de coût personnalisé
        if constraints.custom_cost_modifier:
            cost_modifier = constraints.custom_cost_modifier(to_x, to_y)
            base_cost *= cost_modifier
        
        # Vérification de la pente (si des données d'élévation sont disponibles)
        if constraints.max_slope < float('inf'):
            elevation_diff = abs(
                self.grid.get_tile_properties(to_x, to_y).elevation -
                self.grid.get_tile_properties(from_x, from_y).elevation
            )
            
            if elevation_diff > constraints.max_slope:
                return None
        
        return base_cost
    
    def _reconstruct_path(self, end_node: PathNode) -> List[Tuple[int, int]]:
        """Reconstruit le chemin à partir du nœud final"""
        path = []
        current = end_node
        
        while current is not None:
            path.append((current.x, current.y))
            current = current.parent
        
        path.reverse()
        return path
    
    def _reconstruct_path_from_map(self, goal: Tuple[int, int], 
                                  parent_map: Dict[Tuple[int, int], PathNode],
                                  start: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Reconstruit le chemin à partir d'une map de parents"""
        path = [goal]
        current = goal
        
        while current != start and current in parent_map:
            parent = parent_map[current]
            current = (parent.x, parent.y)
            path.append(current)
        
        path.reverse()
        return path
    
    # ═══════════════════════════════════════════════════════════
    # HEURISTIQUES
    # ═══════════════════════════════════════════════════════════
    
    def _manhattan_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Distance de Manhattan"""
        return abs(x1 - x2) + abs(y1 - y2)
    
    def _euclidean_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Distance euclidienne"""
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
    
    def _diagonal_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Distance diagonale (Chebyshev)"""
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)
    
    # ═══════════════════════════════════════════════════════════
    # CACHE ET OPTIMISATIONS
    # ═══════════════════════════════════════════════════════════
    
    def _generate_cache_key(self, start: Tuple[int, int], goal: Tuple[int, int],
                           algorithm: PathfindingAlgorithm, heuristic: HeuristicType,
                           constraints: PathfindingConstraints) -> str:
        """Génère une clé de cache pour la recherche"""
        # Simplification: on inclut seulement les paramètres principaux
        # Une vraie implémentation devrait hasher tous les paramètres de contraintes
        return f"{start}_{goal}_{algorithm.value}_{heuristic.value}_{constraints.allow_diagonal}"
    
    def _cache_result(self, cache_key: str, result: PathfindingResult):
        """Met en cache un résultat"""
        if len(self.path_cache) >= self.cache_max_size:
            # Suppression LRU simple (premie entré, premier sorti)
            oldest_key = next(iter(self.path_cache))
            del self.path_cache[oldest_key]
        
        self.path_cache[cache_key] = result
    
    def clear_cache(self):
        """Vide le cache de pathfinding"""
        self.path_cache.clear()
        self.logger.debug("Cache de pathfinding vidé")
    
    def _update_stats(self, result: PathfindingResult):
        """Met à jour les statistiques"""
        self.stats['total_searches'] += 1
        
        # Moyenne mobile des nœuds explorés
        current_avg = self.stats['average_nodes_explored']
        new_avg = (current_avg * (self.stats['total_searches'] - 1) + result.nodes_explored) / self.stats['total_searches']
        self.stats['average_nodes_explored'] = new_avg
        
        # Moyenne mobile du temps de calcul
        current_avg_time = self.stats['average_computation_time']
        new_avg_time = (current_avg_time * (self.stats['total_searches'] - 1) + result.computation_time) / self.stats['total_searches']
        self.stats['average_computation_time'] = new_avg_time
    
    # ═══════════════════════════════════════════════════════════
    # FONCTIONS UTILITAIRES AVANCÉES
    # ═══════════════════════════════════════════════════════════
    
    def find_multiple_paths(self, start: Tuple[int, int], goals: List[Tuple[int, int]],
                           algorithm: PathfindingAlgorithm = PathfindingAlgorithm.A_STAR) -> List[PathfindingResult]:
        """Trouve des chemins vers plusieurs objectifs"""
        results = []
        
        for goal in goals:
            result = self.find_path(start, goal, algorithm)
            results.append(result)
        
        return results
    
    def find_nearest_accessible_goal(self, start: Tuple[int, int], goals: List[Tuple[int, int]],
                                   algorithm: PathfindingAlgorithm = PathfindingAlgorithm.A_STAR) -> Optional[PathfindingResult]:
        """Trouve le chemin le plus court vers l'un des objectifs"""
        results = self.find_multiple_paths(start, goals, algorithm)
        
        # Filtrage des chemins réussis
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return None
        
        # Retour du chemin le plus court
        return min(successful_results, key=lambda r: r.cost)
    
    def smooth_path(self, path: List[Tuple[int, int]], constraints: Optional[PathfindingConstraints] = None) -> List[Tuple[int, int]]:
        """
        Lisse un chemin en supprimant les points redondants
        Utilise l'algorithme de simplification de ligne de visée
        """
        if len(path) <= 2:
            return path
        
        if constraints is None:
            constraints = PathfindingConstraints()
        
        smoothed_path = [path[0]]  # Commence par le point de départ
        current_index = 0
        
        while current_index < len(path) - 1:
            # Trouve le point le plus éloigné visible depuis la position actuelle
            farthest_visible = current_index + 1
            
            for i in range(current_index + 2, len(path)):
                if self._has_line_of_sight(path[current_index], path[i], constraints):
                    farthest_visible = i
                else:
                    break
            
            smoothed_path.append(path[farthest_visible])
            current_index = farthest_visible
        
        return smoothed_path
    
    def _has_line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int],
                          constraints: PathfindingConstraints) -> bool:
        """
        Vérifie s'il y a une ligne de visée directe entre deux points
        Utilise l'algorithme de Bresenham
        """
        x0, y0 = start
        x1, y1 = end
        
        # Algorithme de Bresenham
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        step_x = 1 if x0 < x1 else -1
        step_y = 1 if y0 < y1 else -1
        
        error = dx - dy
        
        x, y = x0, y0
        
        while True:
            # Vérification que la tuile actuelle est franchissable
            if self._get_movement_cost(x, y, x, y, constraints) is None:
                return False
            
            if x == x1 and y == y1:
                break
            
            error2 = 2 * error
            
            if error2 > -dy:
                error -= dy
                x += step_x
            
            if error2 < dx:
                error += dx
                y += step_y
        
        return True
    
    def generate_flow_field(self, goal: Tuple[int, int], 
                           constraints: Optional[PathfindingConstraints] = None) -> Dict[Tuple[int, int], Tuple[int, int]]:
        """
        Génère un champ de flux (flow field) vers un objectif
        Utile pour faire se diriger plusieurs unités vers le même point
        """
        if constraints is None:
            constraints = PathfindingConstraints()
        
        # Utilisation de Dijkstra depuis l'objectif (recherche inverse)
        goal_node = PathNode(goal[0], goal[1], g_cost=0.0)
        open_set = [goal_node]
        distances: Dict[Tuple[int, int], float] = {goal: 0.0}
        flow_field: Dict[Tuple[int, int], Tuple[int, int]] = {}
        
        while open_set:
            current_node = heapq.heappop(open_set)
            current_pos = (current_node.x, current_node.y)
            
            neighbors = self._get_neighbors(current_node.x, current_node.y, constraints)
            
            for neighbor_x, neighbor_y, move_cost in neighbors:
                neighbor_pos = (neighbor_x, neighbor_y)
                new_distance = distances[current_pos] + move_cost
                
                if neighbor_pos not in distances or new_distance < distances[neighbor_pos]:
                    distances[neighbor_pos] = new_distance
                    
                    neighbor_node = PathNode(neighbor_x, neighbor_y, g_cost=new_distance)
                    heapq.heappush(open_set, neighbor_node)
                    
                    # La direction du flux pointe vers la tuile qui mène à l'objectif
                    direction_x = current_node.x - neighbor_x
                    direction_y = current_node.y - neighbor_y
                    flow_field[neighbor_pos] = (direction_x, direction_y)
        
        return flow_field
    
    def get_stats(self) -> Dict[str, any]:
        """Retourne les statistiques du pathfinder"""
        cache_hit_rate = 0.0
        if self.stats['total_searches'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / self.stats['total_searches']
        
        return {
            **self.stats,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self.path_cache),
            'cache_max_size': self.cache_max_size,
            'cache_enabled': self.cache_enabled
        }
    
    def set_cache_enabled(self, enabled: bool):
        """Active ou désactive le cache"""
        self.cache_enabled = enabled
        if not enabled:
            self.clear_cache()
    
    def set_cache_max_size(self, max_size: int):
        """Définit la taille maximale du cache"""
        self.cache_max_size = max_size
        
        # Ajustement si nécessaire
        while len(self.path_cache) > max_size:
            oldest_key = next(iter(self.path_cache))
            del self.path_cache[oldest_key]


# ═══════════════════════════════════════════════════════════
# CLASSES UTILITAIRES
# ═══════════════════════════════════════════════════════════

class PathOptimizer:
    """Utilitaires pour optimiser les chemins"""
    
    @staticmethod
    def remove_redundant_points(path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Supprime les points redondants d'un chemin"""
        if len(path) <= 2:
            return path
        
        optimized = [path[0]]
        
        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            current_point = path[i]
            next_point = path[i + 1]
            
            # Vérification si le point actuel est sur la ligne droite
            if not PathOptimizer._is_collinear(prev_point, current_point, next_point):
                optimized.append(current_point)
        
        optimized.append(path[-1])
        return optimized
    
    @staticmethod
    def _is_collinear(p1: Tuple[int, int], p2: Tuple[int, int], p3: Tuple[int, int]) -> bool:
        """Vérifie si trois points sont colinéaires"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        
        # Utilise le produit vectoriel pour vérifier la colinéarité
        cross_product = (y2 - y1) * (x3 - x2) - (y3 - y2) * (x2 - x1)
        return abs(cross_product) < 0.001  # Tolérance pour les erreurs de précision
    
    @staticmethod
    def interpolate_path(path: List[Tuple[int, int]], resolution: float = 0.5) -> List[Tuple[float, float]]:
        """Interpole un chemin pour obtenir une trajectoire plus fluide"""
        if len(path) <= 1:
            return [(float(p[0]), float(p[1])) for p in path]
        
        interpolated = []
        
        for i in range(len(path) - 1):
            start_x, start_y = path[i]
            end_x, end_y = path[i + 1]
            
            # Distance entre les points
            distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
            num_steps = max(1, int(distance / resolution))
            
            # Interpolation linéaire
            for step in range(num_steps):
                t = step / num_steps
                interp_x = start_x + t * (end_x - start_x)
                interp_y = start_y + t * (end_y - start_y)
                interpolated.append((interp_x, interp_y))
        
        # Ajout du dernier point
        interpolated.append((float(path[-1][0]), float(path[-1][1])))
        
        return interpolated