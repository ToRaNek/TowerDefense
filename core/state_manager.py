# core/state_manager.py
"""
Steam Defense - Gestionnaire d'états de jeu
Gère les différents états du jeu (menu, gameplay, pause, etc.)
"""

import logging
from typing import Dict, Optional, Any, Type
from enum import Enum
from abc import ABC, abstractmethod


class GameStateType(Enum):
    """Types d'états de jeu disponibles"""
    MAIN_MENU = "main_menu"
    GAMEPLAY = "gameplay"
    PAUSE = "pause"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    SETTINGS = "settings"
    LEVEL_SELECT = "level_select"
    LOADING = "loading"


class GameState(ABC):
    """
    Classe de base pour tous les états de jeu
    Utilise le pattern State pour gérer les transitions
    """
    
    def __init__(self, game_instance):
        self.game = game_instance
        self.logger = logging.getLogger(f'GameState.{self.__class__.__name__}')
        self.state_data: Dict[str, Any] = {}
        self.is_active = False
        
    @abstractmethod
    def enter(self, previous_state: Optional['GameState'] = None, **kwargs):
        """
        Appelé quand on entre dans cet état
        
        Args:
            previous_state: État précédent
            **kwargs: Données de transition
        """
        self.is_active = True
        self.logger.info(f"Entrée dans l'état {self.__class__.__name__}")
    
    @abstractmethod
    def exit(self, next_state: Optional['GameState'] = None):
        """
        Appelé quand on sort de cet état
        
        Args:
            next_state: Prochain état
        """
        self.is_active = False
        self.logger.info(f"Sortie de l'état {self.__class__.__name__}")
    
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
        pass
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """Récupère une donnée de l'état"""
        return self.state_data.get(key, default)
    
    def set_state_data(self, key: str, value: Any):
        """Définit une donnée de l'état"""
        self.state_data[key] = value
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Retourne des informations de debug"""
        return {
            'state_name': self.__class__.__name__,
            'is_active': self.is_active,
            'state_data_keys': list(self.state_data.keys())
        }


class StateTransition:
    """Représente une transition entre états"""
    
    def __init__(self, from_state: GameStateType, to_state: GameStateType,
                 condition: Optional[callable] = None, **transition_data):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition  # Fonction qui doit retourner True pour permettre la transition
        self.transition_data = transition_data
        
    def can_transition(self, current_data: Dict[str, Any] = None) -> bool:
        """Vérifie si la transition est possible"""
        if self.condition is None:
            return True
        
        try:
            return self.condition(current_data or {})
        except Exception as e:
            logging.getLogger('StateTransition').error(f"Erreur dans la condition de transition: {e}")
            return False


class StateManager:
    """
    Gestionnaire principal des états de jeu
    Implémente le pattern State Machine
    """
    
    def __init__(self):
        self.logger = logging.getLogger('StateManager')
        
        # États enregistrés
        self.states: Dict[GameStateType, GameState] = {}
        
        # État actuel
        self.current_state: Optional[GameState] = None
        self.current_state_type: Optional[GameStateType] = None
        
        # État précédent (pour retours)
        self.previous_state: Optional[GameState] = None
        self.previous_state_type: Optional[GameStateType] = None
        
        # Transitions définies
        self.transitions: Dict[GameStateType, List[StateTransition]] = {}
        
        # File d'attente de changements d'état (pour éviter les changements en cours d'update)
        self.pending_state_change: Optional[tuple] = None
        
        # Données partagées entre états
        self.shared_data: Dict[str, Any] = {}
        
        # Historique des états (pour debugging)
        self.state_history: List[GameStateType] = []
        self.max_history_size = 10
        
        self.logger.info("StateManager initialisé")
    
    def register_state(self, state_type: GameStateType, state_instance: GameState):
        """
        Enregistre un état dans le gestionnaire
        
        Args:
            state_type: Type de l'état
            state_instance: Instance de l'état
        """
        self.states[state_type] = state_instance
        self.logger.debug(f"État enregistré: {state_type.value}")
    
    def register_transition(self, transition: StateTransition):
        """
        Enregistre une transition possible
        
        Args:
            transition: Transition à enregistrer
        """
        if transition.from_state not in self.transitions:
            self.transitions[transition.from_state] = []
        
        self.transitions[transition.from_state].append(transition)
        self.logger.debug(f"Transition enregistrée: {transition.from_state.value} -> {transition.to_state.value}")
    
    def setup_default_transitions(self):
        """Configure les transitions par défaut du jeu"""
        # Menu principal vers gameplay
        self.register_transition(StateTransition(
            GameStateType.MAIN_MENU, GameStateType.GAMEPLAY
        ))
        
        # Gameplay vers pause
        self.register_transition(StateTransition(
            GameStateType.GAMEPLAY, GameStateType.PAUSE
        ))
        
        # Pause vers gameplay
        self.register_transition(StateTransition(
            GameStateType.PAUSE, GameStateType.GAMEPLAY
        ))
        
        # Gameplay vers game over
        self.register_transition(StateTransition(
            GameStateType.GAMEPLAY, GameStateType.GAME_OVER
        ))
        
        # Gameplay vers victoire
        self.register_transition(StateTransition(
            GameStateType.GAMEPLAY, GameStateType.VICTORY
        ))
        
        # Game over vers menu principal
        self.register_transition(StateTransition(
            GameStateType.GAME_OVER, GameStateType.MAIN_MENU
        ))
        
        # Victoire vers menu principal
        self.register_transition(StateTransition(
            GameStateType.VICTORY, GameStateType.MAIN_MENU
        ))
        
        # Retours vers menu depuis pause
        self.register_transition(StateTransition(
            GameStateType.PAUSE, GameStateType.MAIN_MENU
        ))
        
        # Accès aux paramètres depuis le menu principal
        self.register_transition(StateTransition(
            GameStateType.MAIN_MENU, GameStateType.SETTINGS
        ))
        
        # Retour des paramètres vers menu
        self.register_transition(StateTransition(
            GameStateType.SETTINGS, GameStateType.MAIN_MENU
        ))
        
        # Sélection de niveau
        self.register_transition(StateTransition(
            GameStateType.MAIN_MENU, GameStateType.LEVEL_SELECT
        ))
        
        self.register_transition(StateTransition(
            GameStateType.LEVEL_SELECT, GameStateType.MAIN_MENU
        ))
        
        self.register_transition(StateTransition(
            GameStateType.LEVEL_SELECT, GameStateType.LOADING
        ))
        
        self.register_transition(StateTransition(
            GameStateType.LOADING, GameStateType.GAMEPLAY
        ))
        
        self.logger.info("Transitions par défaut configurées")
    
    def change_state(self, new_state_type: GameStateType, **kwargs) -> bool:
        """
        Demande un changement d'état
        
        Args:
            new_state_type: Nouveau type d'état
            **kwargs: Données à passer au nouvel état
            
        Returns:
            bool: True si le changement est possible
        """
        # Vérification que l'état existe
        if new_state_type not in self.states:
            self.logger.error(f"État non enregistré: {new_state_type.value}")
            return False
        
        # Vérification des transitions autorisées
        if self.current_state_type is not None:
            if not self._is_transition_allowed(self.current_state_type, new_state_type):
                self.logger.warning(f"Transition non autorisée: {self.current_state_type.value} -> {new_state_type.value}")
                return False
        
        # Programmation du changement pour le prochain update
        self.pending_state_change = (new_state_type, kwargs)
        self.logger.info(f"Changement d'état programmé: {new_state_type.value}")
        
        return True
    
    def _is_transition_allowed(self, from_state: GameStateType, to_state: GameStateType) -> bool:
        """Vérifie si une transition est autorisée"""
        if from_state not in self.transitions:
            return False
        
        for transition in self.transitions[from_state]:
            if transition.to_state == to_state:
                return transition.can_transition(self.shared_data)
        
        return False
    
    def _execute_state_change(self, new_state_type: GameStateType, **kwargs):
        """Exécute effectivement le changement d'état"""
        new_state = self.states[new_state_type]
        
        # Sauvegarde de l'état actuel
        self.previous_state = self.current_state
        self.previous_state_type = self.current_state_type
        
        # Sortie de l'état actuel
        if self.current_state:
            self.current_state.exit(new_state)
        
        # Mise à jour de l'historique
        if self.current_state_type:
            self.state_history.append(self.current_state_type)
            if len(self.state_history) > self.max_history_size:
                self.state_history.pop(0)
        
        # Changement d'état
        self.current_state = new_state
        self.current_state_type = new_state_type
        
        # Entrée dans le nouvel état
        self.current_state.enter(self.previous_state, **kwargs)
        
        self.logger.info(f"Changement d'état exécuté: {new_state_type.value}")
    
    def return_to_previous_state(self, **kwargs) -> bool:
        """
        Retourne à l'état précédent
        
        Args:
            **kwargs: Données à passer à l'état précédent
            
        Returns:
            bool: True si le retour est possible
        """
        if self.previous_state_type is None:
            self.logger.warning("Aucun état précédent disponible")
            return False
        
        return self.change_state(self.previous_state_type, **kwargs)
    
    def update(self, delta_time: float):
        """
        Met à jour le gestionnaire d'états
        
        Args:
            delta_time: Temps écoulé depuis la dernière frame
        """
        # Exécution des changements d'état en attente
        if self.pending_state_change:
            new_state_type, kwargs = self.pending_state_change
            self.pending_state_change = None
            self._execute_state_change(new_state_type, **kwargs)
        
        # Mise à jour de l'état actuel
        if self.current_state:
            self.current_state.update(delta_time)
    
    def render(self, renderer):
        """
        Rendu de l'état actuel
        
        Args:
            renderer: Moteur de rendu
        """
        if self.current_state:
            self.current_state.render(renderer)
    
    def handle_event(self, event_type: str, event_data: Any = None):
        """
        Transmet un événement à l'état actuel
        
        Args:
            event_type: Type d'événement
            event_data: Données de l'événement
        """
        if self.current_state:
            self.current_state.handle_event(event_type, event_data)
    
    def get_current_state(self) -> Optional[GameState]:
        """Retourne l'état actuel"""
        return self.current_state
    
    def get_current_state_type(self) -> Optional[GameStateType]:
        """Retourne le type de l'état actuel"""
        return self.current_state_type
    
    def get_previous_state_type(self) -> Optional[GameStateType]:
        """Retourne le type de l'état précédent"""
        return self.previous_state_type
    
    def set_shared_data(self, key: str, value: Any):
        """Définit une donnée partagée entre états"""
        self.shared_data[key] = value
    
    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """Récupère une donnée partagée"""
        return self.shared_data.get(key, default)
    
    def clear_shared_data(self):
        """Efface toutes les données partagées"""
        self.shared_data.clear()
        self.logger.debug("Données partagées effacées")
    
    def get_state_history(self) -> List[GameStateType]:
        """Retourne l'historique des états"""
        return self.state_history.copy()
    
    def is_in_state(self, state_type: GameStateType) -> bool:
        """Vérifie si on est dans un état donné"""
        return self.current_state_type == state_type
    
    def can_go_to_state(self, state_type: GameStateType) -> bool:
        """Vérifie si on peut aller vers un état donné"""
        if self.current_state_type is None:
            return state_type in self.states
        
        return self._is_transition_allowed(self.current_state_type, state_type)
    
    def force_state_change(self, new_state_type: GameStateType, **kwargs):
        """
        Force un changement d'état sans vérifier les transitions
        À utiliser avec précaution (debug, états d'urgence)
        
        Args:
            new_state_type: Nouveau type d'état
            **kwargs: Données à passer au nouvel état
        """
        if new_state_type not in self.states:
            self.logger.error(f"État non enregistré pour changement forcé: {new_state_type.value}")
            return
        
        self.logger.warning(f"Changement d'état forcé: {new_state_type.value}")
        self._execute_state_change(new_state_type, **kwargs)
    
    def cleanup(self):
        """Nettoyage du gestionnaire d'états"""
        self.logger.info("Nettoyage du StateManager")
        
        # Sortie de l'état actuel
        if self.current_state:
            self.current_state.exit()
        
        # Nettoyage des références
        self.current_state = None
        self.current_state_type = None
        self.previous_state = None
        self.previous_state_type = None
        
        # Nettoyage des données
        self.shared_data.clear()
        self.state_history.clear()
        self.pending_state_change = None
        
        # Nettoyage des états
        for state in self.states.values():
            if hasattr(state, 'cleanup'):
                try:
                    state.cleanup()
                except Exception as e:
                    self.logger.error(f"Erreur lors du nettoyage d'un état: {e}")
        
        self.states.clear()
        self.transitions.clear()
        
        self.logger.info("StateManager nettoyé")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Retourne des informations de debug"""
        info = {
            'current_state': self.current_state_type.value if self.current_state_type else None,
            'previous_state': self.previous_state_type.value if self.previous_state_type else None,
            'registered_states': [state_type.value for state_type in self.states.keys()],
            'shared_data_keys': list(self.shared_data.keys()),
            'state_history': [state_type.value for state_type in self.state_history],
            'pending_change': self.pending_state_change[0].value if self.pending_state_change else None
        }
        
        # Informations de l'état actuel
        if self.current_state:
            try:
                current_state_info = self.current_state.get_debug_info()
                info['current_state_info'] = current_state_info
            except Exception as e:
                info['current_state_info'] = f"Erreur: {e}"
        
        # Transitions possibles depuis l'état actuel
        if self.current_state_type and self.current_state_type in self.transitions:
            possible_transitions = []
            for transition in self.transitions[self.current_state_type]:
                possible_transitions.append({
                    'to_state': transition.to_state.value,
                    'can_transition': transition.can_transition(self.shared_data)
                })
            info['possible_transitions'] = possible_transitions
        
        return info
    
    def log_current_state(self):
        """Log les informations de l'état actuel"""
        if self.current_state:
            self.logger.info(f"État actuel: {self.current_state_type.value}")
            
            # Log des données de l'état
            state_data = self.current_state.state_data
            if state_data:
                self.logger.debug(f"Données de l'état: {state_data}")
        else:
            self.logger.info("Aucun état actuel")
    
    def validate_state_machine(self) -> List[str]:
        """
        Valide la cohérence de la machine à états
        
        Returns:
            List[str]: Liste des problèmes détectés
        """
        issues = []
        
        # Vérification que tous les états référencés dans les transitions existent
        for from_state, transitions in self.transitions.items():
            if from_state not in self.states:
                issues.append(f"État source de transition non enregistré: {from_state.value}")
            
            for transition in transitions:
                if transition.to_state not in self.states:
                    issues.append(f"État cible de transition non enregistré: {transition.to_state.value}")
        
        # Vérification qu'il y a au moins un chemin vers le menu principal
        main_menu_reachable = False
        for transitions in self.transitions.values():
            for transition in transitions:
                if transition.to_state == GameStateType.MAIN_MENU:
                    main_menu_reachable = True
                    break
        
        if not main_menu_reachable and GameStateType.MAIN_MENU in self.states:
            issues.append("Aucun chemin vers le menu principal trouvé")
        
        # Vérification des états orphelins (pas de transition vers eux)
        reachable_states = set()
        for transitions in self.transitions.values():
            for transition in transitions:
                reachable_states.add(transition.to_state)
        
        for state_type in self.states.keys():
            if state_type not in reachable_states and state_type != GameStateType.MAIN_MENU:
                issues.append(f"État orphelin (non atteignable): {state_type.value}")
        
        return issues


# ═══════════════════════════════════════════════════════════
# ÉTATS DE BASE ABSTRAITS
# ═══════════════════════════════════════════════════════════

class MenuState(GameState):
    """État de base pour tous les menus"""
    
    def __init__(self, game_instance):
        super().__init__(game_instance)
        self.ui_manager = None
        self.menu_music_playing = False
    
    def enter(self, previous_state: Optional[GameState] = None, **kwargs):
        super().enter(previous_state, **kwargs)
        
        # Initialisation de l'UI si nécessaire
        if self.ui_manager is None:
            self._setup_ui()
        
        # Musique de menu
        if hasattr(self.game, 'audio_manager') and not self.menu_music_playing:
            # self.game.audio_manager.play_music('menu_theme')
            self.menu_music_playing = True
    
    def exit(self, next_state: Optional[GameState] = None):
        super().exit(next_state)
        
        # Arrêt de la musique de menu si on va en gameplay
        if (next_state and hasattr(next_state, '__class__') and 
            'Gameplay' in next_state.__class__.__name__):
            if hasattr(self.game, 'audio_manager'):
                # self.game.audio_manager.stop_music()
                self.menu_music_playing = False
    
    @abstractmethod
    def _setup_ui(self):
        """Configure l'interface utilisateur du menu"""
        pass


class GameplayState(GameState):
    """État de base pour le gameplay"""
    
    def __init__(self, game_instance):
        super().__init__(game_instance)
        self.is_paused = False
        self.game_speed = 1.0
    
    def pause_game(self):
        """Met le jeu en pause"""
        self.is_paused = True
        self.logger.info("Jeu mis en pause")
    
    def resume_game(self):
        """Reprend le jeu"""
        self.is_paused = False
        self.logger.info("Jeu repris")
    
    def set_game_speed(self, speed: float):
        """Définit la vitesse du jeu"""
        self.game_speed = max(0.0, min(3.0, speed))  # Entre 0x et 3x
        self.logger.info(f"Vitesse de jeu: {self.game_speed}x")
    
    def update(self, delta_time: float):
        if self.is_paused:
            delta_time = 0.0
        else:
            delta_time *= self.game_speed
        
        super().update(delta_time)