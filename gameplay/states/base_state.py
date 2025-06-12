# gameplay/states/base_state.py
"""
Steam Defense - Classe de base pour tous les états de jeu
Compatible avec le système de StateManager existant
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from core.state_manager import GameState


class BaseState(GameState):
    """
    Classe de base pour tous les états de jeu
    Hérite de GameState du StateManager et ajoute des fonctionnalités spécifiques au jeu
    """
    
    def __init__(self, game_instance):
        """
        Initialise l'état de base
        
        Args:
            game_instance: Instance du jeu principal
        """
        super().__init__(game_instance)
        self.game = game_instance
    
    def enter(self, previous_state: Optional['GameState'] = None, **kwargs):
        """
        Appelé quand on entre dans cet état
        
        Args:
            previous_state: État précédent
            **kwargs: Données de transition
        """
        super().enter(previous_state, **kwargs)
    
    def exit(self, next_state: Optional['GameState'] = None):
        """
        Appelé quand on sort de cet état
        
        Args:
            next_state: Prochain état
        """
        super().exit(next_state)
    
    @abstractmethod
    def update(self, delta_time: float):
        """
        Met à jour l'état (appelé chaque frame)
        
        Args:
            delta_time: Temps écoulé depuis la dernière frame
        """
        pass
    
    @abstractmethod
    def render(self, renderer):
        """
        Rendu de l'état
        
        Args:
            renderer: Moteur de rendu
        """
        pass
    
    def handle_event(self, event_type: str, event_data: Any = None):
        """
        Gère les événements spécifiques à cet état
        
        Args:
            event_type: Type d'événement
            event_data: Données de l'événement
        """
        super().handle_event(event_type, event_data)
    
    # ═══════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES COMMUNES
    # ═══════════════════════════════════════════════════════════
    
    def start_game(self):
        """Démarre une nouvelle partie"""
        from core.state_manager import GameStateType
        self.game.state_manager.change_state(GameStateType.GAMEPLAY)
    
    def pause_game(self):
        """Met le jeu en pause"""
        from core.state_manager import GameStateType
        self.game.state_manager.change_state(GameStateType.PAUSE)
    
    def resume_game(self):
        """Reprend le jeu"""
        from core.state_manager import GameStateType
        self.game.state_manager.change_state(GameStateType.GAMEPLAY)
    
    def return_to_menu(self):
        """Retourne au menu principal"""
        from core.state_manager import GameStateType
        self.game.state_manager.change_state(GameStateType.MAIN_MENU)
    
    def restart_game(self):
        """Redémarre la partie"""
        from core.state_manager import GameStateType
        # Retour au menu puis nouvelle partie
        self.game.state_manager.change_state(GameStateType.MAIN_MENU)
        # Ou directement vers gameplay selon la logique voulue
        # self.game.state_manager.change_state(GameStateType.GAMEPLAY)
    
    def game_over(self, score: int = 0, is_victory: bool = False):
        """Termine la partie et va vers l'état Game Over"""
        from core.state_manager import GameStateType
        self.game.state_manager.change_state(
            GameStateType.GAME_OVER, 
            score=score, 
            is_victory=is_victory
        )
    
    def quit_game(self):
        """Quitte le jeu"""
        self.game.event_system.emit('game_quit')
    
    def open_options(self):
        """Ouvre le menu des options"""
        from core.state_manager import GameStateType
        # Si l'état SETTINGS existe, l'utiliser
        if hasattr(GameStateType, 'SETTINGS'):
            self.game.state_manager.change_state(GameStateType.SETTINGS)
        else:
            # Sinon, rester sur l'état actuel ou afficher un message
            self.logger.info("Menu d'options non implémenté")
    
    def show_scores(self):
        """Affiche les meilleurs scores"""
        # Pour l'instant, juste un log
        # Dans une vraie implémentation, on créerait un état SCORES
        self.logger.info("Tableau des scores non implémenté")
    
    def toggle_game_speed(self):
        """Bascule la vitesse du jeu"""
        if hasattr(self, 'game_speed'):
            speeds = [0.5, 1.0, 1.5, 2.0]
            current_index = speeds.index(self.game_speed) if self.game_speed in speeds else 1
            next_index = (current_index + 1) % len(speeds)
            self.game_speed = speeds[next_index]
            self.logger.info(f"Vitesse de jeu: {self.game_speed}x")
    
    def select_tower_type(self, tower_type: str):
        """Sélectionne un type de tour à placer"""
        if hasattr(self, 'tower_type_to_place'):
            self.tower_type_to_place = tower_type
            self.placing_tower = True
            self.logger.debug(f"Tour sélectionnée: {tower_type}")
    
    def get_debug_info(self) -> list:
        """Retourne des informations de debug spécifiques à l'état"""
        debug_info = []
        
        # Informations de base
        debug_info.append(f"État: {self.__class__.__name__}")
        debug_info.append(f"Actif: {self.is_active}")
        
        # Données spécifiques selon l'état
        if hasattr(self, 'game_speed'):
            debug_info.append(f"Vitesse: {self.game_speed}x")
        
        if hasattr(self, 'placing_tower') and self.placing_tower:
            debug_info.append(f"Placement: {self.tower_type_to_place}")
        
        if hasattr(self, 'player'):
            debug_info.append(f"Vie: {self.player.health}")
            debug_info.append(f"Argent: {self.player.money}")
        
        return debug_info
    
    def cleanup(self):
        """Nettoyage de l'état"""
        # Nettoyage spécifique à chaque état
        # À surcharger dans les classes filles si nécessaire
        pass