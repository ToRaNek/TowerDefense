# input/input_manager.py
"""
Steam Defense - Gestionnaire d'entrées utilisateur
Gère les entrées clavier, souris et les raccourcis
"""

import arcade
import logging
from typing import Dict, Set, List, Callable, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import time

from core.event_system import EventSystem


class InputType(Enum):
    """Types d'entrées"""
    KEYBOARD = "keyboard"
    MOUSE_BUTTON = "mouse_button"
    MOUSE_MOTION = "mouse_motion"
    MOUSE_WHEEL = "mouse_wheel"


class InputAction(Enum):
    """Actions d'entrée prédéfinies"""
    # Navigation
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    
    # Interaction
    SELECT = "select"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    
    # Jeu
    PAUSE = "pause"
    SPEED_UP = "speed_up"
    SPEED_DOWN = "speed_down"
    SPEED_NORMAL = "speed_normal"
    
    # Interface
    TOGGLE_MENU = "toggle_menu"
    SHOW_STATS = "show_stats"
    TOGGLE_DEBUG = "toggle_debug"
    
    # Construction
    BUILD_MODE = "build_mode"
    UPGRADE_TOWER = "upgrade_tower"
    SELL_TOWER = "sell_tower"
    
    # Caméra
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    CAMERA_RESET = "camera_reset"


@dataclass
class InputBinding:
    """Association entre une entrée physique et une action"""
    action: InputAction
    input_type: InputType
    key_or_button: int
    modifiers: int = 0
    description: str = ""
    
    def matches(self, input_type: InputType, key_or_button: int, modifiers: int = 0) -> bool:
        """Vérifie si cette liaison correspond à l'entrée donnée"""
        return (self.input_type == input_type and 
                self.key_or_button == key_or_button and 
                self.modifiers == modifiers)


@dataclass
class InputEvent:
    """Événement d'entrée"""
    action: InputAction
    input_type: InputType
    key_or_button: int
    modifiers: int
    pressed: bool  # True = pressé, False = relâché
    timestamp: float
    position: Optional[Tuple[float, float]] = None  # Pour la souris
    delta: Optional[Tuple[float, float]] = None     # Pour le mouvement de souris


class InputManager:
    """
    Gestionnaire principal des entrées utilisateur
    Gère les liaisons clavier/souris et les actions du jeu
    """
    
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.logger = logging.getLogger('InputManager')
        
        # État des entrées
        self.pressed_keys: Set[int] = set()
        self.pressed_mouse_buttons: Set[int] = set()
        self.mouse_position = (0.0, 0.0)
        self.last_mouse_position = (0.0, 0.0)
        
        # Liaisons d'entrées
        self.bindings: List[InputBinding] = []
        self.action_callbacks: Dict[InputAction, List[Callable]] = {}
        
        # Configuration
        self.mouse_sensitivity = 1.0
        self.key_repeat_delay = 0.5  # Délai avant répétition en secondes
        self.key_repeat_rate = 0.1   # Taux de répétition
        
        # État de répétition des touches
        self.key_repeat_timers: Dict[int, float] = {}
        self.key_repeat_active: Dict[int, bool] = {}
        
        # Double-clic
        self.double_click_time = 0.3  # Temps maximum entre deux clics
        self.last_click_time: Dict[int, float] = {}
        self.last_click_position: Dict[int, Tuple[float, float]] = {}
        
        # Glisser-déposer
        self.drag_threshold = 5.0  # Distance minimum pour démarrer un drag
        self.drag_state: Dict[int, Dict[str, Any]] = {}
        
        # Historique des entrées pour debug
        self.input_history: List[InputEvent] = []
        self.max_history_size = 100
        
        # Configuration par défaut
        self._setup_default_bindings()
        
        self.logger.info("InputManager initialisé")
    
    def _setup_default_bindings(self):
        """Configure les liaisons par défaut"""
        default_bindings = [
            # Clavier - Navigation
            InputBinding(InputAction.MOVE_LEFT, InputType.KEYBOARD, arcade.key.LEFT, description="Déplacer à gauche"),
            InputBinding(InputAction.MOVE_LEFT, InputType.KEYBOARD, arcade.key.A, description="Déplacer à gauche (WASD)"),
            InputBinding(InputAction.MOVE_RIGHT, InputType.KEYBOARD, arcade.key.RIGHT, description="Déplacer à droite"),
            InputBinding(InputAction.MOVE_RIGHT, InputType.KEYBOARD, arcade.key.D, description="Déplacer à droite (WASD)"),
            InputBinding(InputAction.MOVE_UP, InputType.KEYBOARD, arcade.key.UP, description="Déplacer vers le haut"),
            InputBinding(InputAction.MOVE_UP, InputType.KEYBOARD, arcade.key.W, description="Déplacer vers le haut (WASD)"),
            InputBinding(InputAction.MOVE_DOWN, InputType.KEYBOARD, arcade.key.DOWN, description="Déplacer vers le bas"),
            InputBinding(InputAction.MOVE_DOWN, InputType.KEYBOARD, arcade.key.S, description="Déplacer vers le bas (WASD)"),
            
            # Clavier - Interaction
            InputBinding(InputAction.SELECT, InputType.KEYBOARD, arcade.key.ENTER, description="Sélectionner"),
            InputBinding(InputAction.SELECT, InputType.KEYBOARD, arcade.key.SPACE, description="Sélectionner (espace)"),
            InputBinding(InputAction.CONFIRM, InputType.KEYBOARD, arcade.key.ENTER, description="Confirmer"),
            InputBinding(InputAction.CANCEL, InputType.KEYBOARD, arcade.key.ESCAPE, description="Annuler"),
            
            # Clavier - Jeu
            InputBinding(InputAction.PAUSE, InputType.KEYBOARD, arcade.key.P, description="Pause"),
            InputBinding(InputAction.PAUSE, InputType.KEYBOARD, arcade.key.SPACE, description="Pause (espace)"),
            InputBinding(InputAction.SPEED_UP, InputType.KEYBOARD, arcade.key.PLUS, description="Accélérer"),
            InputBinding(InputAction.SPEED_UP, InputType.KEYBOARD, arcade.key.NUM_PLUS, description="Accélérer (pavé num)"),
            InputBinding(InputAction.SPEED_DOWN, InputType.KEYBOARD, arcade.key.MINUS, description="Ralentir"),
            InputBinding(InputAction.SPEED_DOWN, InputType.KEYBOARD, arcade.key.NUM_MINUS, description="Ralentir (pavé num)"),
            InputBinding(InputAction.SPEED_NORMAL, InputType.KEYBOARD, arcade.key.NUM_1, description="Vitesse normale"),
            
            # Clavier - Interface
            InputBinding(InputAction.TOGGLE_MENU, InputType.KEYBOARD, arcade.key.TAB, description="Basculer menu"),
            InputBinding(InputAction.SHOW_STATS, InputType.KEYBOARD, arcade.key.F1, description="Afficher statistiques"),
            InputBinding(InputAction.TOGGLE_DEBUG, InputType.KEYBOARD, arcade.key.F3, description="Basculer debug"),
            
            # Clavier - Construction
            InputBinding(InputAction.BUILD_MODE, InputType.KEYBOARD, arcade.key.B, description="Mode construction"),
            InputBinding(InputAction.UPGRADE_TOWER, InputType.KEYBOARD, arcade.key.U, description="Améliorer tour"),
            InputBinding(InputAction.SELL_TOWER, InputType.KEYBOARD, arcade.key.X, description="Vendre tour"),
            
            # Clavier - Caméra
            InputBinding(InputAction.ZOOM_IN, InputType.KEYBOARD, arcade.key.PLUS, arcade.key.MOD_CTRL, "Zoom avant"),
            InputBinding(InputAction.ZOOM_OUT, InputType.KEYBOARD, arcade.key.MINUS, arcade.key.MOD_CTRL, "Zoom arrière"),
            InputBinding(InputAction.CAMERA_RESET, InputType.KEYBOARD, arcade.key.HOME, description="Reset caméra"),
            
            # Souris
            InputBinding(InputAction.SELECT, InputType.MOUSE_BUTTON, arcade.MOUSE_BUTTON_LEFT, description="Clic gauche"),
            InputBinding(InputAction.CANCEL, InputType.MOUSE_BUTTON, arcade.MOUSE_BUTTON_RIGHT, description="Clic droit"),
        ]
        
        for binding in default_bindings:
            self.add_binding(binding)
        
        self.logger.debug(f"Liaisons par défaut configurées: {len(default_bindings)} bindings")
    
    def add_binding(self, binding: InputBinding):
        """Ajoute une liaison d'entrée"""
        self.bindings.append(binding)
        self.logger.debug(f"Liaison ajoutée: {binding.action.value} -> {binding.description}")
    
    def remove_binding(self, action: InputAction, input_type: InputType, key_or_button: int, modifiers: int = 0):
        """Supprime une liaison d'entrée"""
        self.bindings = [
            b for b in self.bindings 
            if not (b.action == action and 
                   b.input_type == input_type and 
                   b.key_or_button == key_or_button and 
                   b.modifiers == modifiers)
        ]
        self.logger.debug(f"Liaison supprimée: {action.value}")
    
    def clear_bindings_for_action(self, action: InputAction):
        """Supprime toutes les liaisons pour une action"""
        original_count = len(self.bindings)
        self.bindings = [b for b in self.bindings if b.action != action]
        removed_count = original_count - len(self.bindings)
        self.logger.debug(f"Liaisons supprimées pour {action.value}: {removed_count}")
    
    def register_action_callback(self, action: InputAction, callback: Callable):
        """Enregistre un callback pour une action"""
        if action not in self.action_callbacks:
            self.action_callbacks[action] = []
        
        self.action_callbacks[action].append(callback)
        self.logger.debug(f"Callback enregistré pour {action.value}")
    
    def unregister_action_callback(self, action: InputAction, callback: Callable):
        """Désenregistre un callback pour une action"""
        if action in self.action_callbacks:
            if callback in self.action_callbacks[action]:
                self.action_callbacks[action].remove(callback)
                
                # Nettoyage si la liste est vide
                if not self.action_callbacks[action]:
                    del self.action_callbacks[action]
                
                self.logger.debug(f"Callback désenregistré pour {action.value}")
    
    def update(self, delta_time: float):
        """Met à jour le gestionnaire d'entrées"""
        # Gestion de la répétition des touches
        self._update_key_repeat(delta_time)
        
        # Mise à jour de l'état de glisser-déposer
        self._update_drag_state(delta_time)
        
        # Nettoyage de l'historique
        if len(self.input_history) > self.max_history_size:
            self.input_history = self.input_history[-self.max_history_size:]
    
    def on_key_press(self, key: int, modifiers: int):
        """Gère l'appui sur une touche"""
        self.pressed_keys.add(key)
        
        # Initialisation du timer de répétition
        self.key_repeat_timers[key] = 0.0
        self.key_repeat_active[key] = False
        
        # Traitement des actions
        self._process_input(InputType.KEYBOARD, key, modifiers, True)
        
        self.logger.debug(f"Touche pressée: {key} (modifiers: {modifiers})")
    
    def on_key_release(self, key: int, modifiers: int):
        """Gère le relâchement d'une touche"""
        self.pressed_keys.discard(key)
        
        # Nettoyage de la répétition
        if key in self.key_repeat_timers:
            del self.key_repeat_timers[key]
        if key in self.key_repeat_active:
            del self.key_repeat_active[key]
        
        # Traitement des actions
        self._process_input(InputType.KEYBOARD, key, modifiers, False)
        
        self.logger.debug(f"Touche relâchée: {key}")
    
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        """Gère l'appui sur un bouton de souris"""
        self.pressed_mouse_buttons.add(button)
        self.mouse_position = (x, y)
        
        # Gestion du double-clic
        current_time = time.time()
        is_double_click = False
        
        if button in self.last_click_time:
            time_diff = current_time - self.last_click_time[button]
            if time_diff <= self.double_click_time:
                # Vérification de la position
                if button in self.last_click_position:
                    last_x, last_y = self.last_click_position[button]
                    distance = ((x - last_x) ** 2 + (y - last_y) ** 2) ** 0.5
                    if distance <= self.drag_threshold:
                        is_double_click = True
        
        self.last_click_time[button] = current_time
        self.last_click_position[button] = (x, y)
        
        # Initialisation du glisser-déposer
        self.drag_state[button] = {
            'start_position': (x, y),
            'current_position': (x, y),
            'is_dragging': False,
            'start_time': current_time
        }
        
        # Traitement des actions
        self._process_input(InputType.MOUSE_BUTTON, button, modifiers, True, (x, y))
        
        # Événement de double-clic
        if is_double_click:
            self._emit_input_event('double_click', {
                'button': button,
                'position': (x, y),
                'modifiers': modifiers
            })
        
        self.logger.debug(f"Bouton souris pressé: {button} à ({x}, {y})")
    
    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int):
        """Gère le relâchement d'un bouton de souris"""
        self.pressed_mouse_buttons.discard(button)
        self.mouse_position = (x, y)
        
        # Finalisation du glisser-déposer
        if button in self.drag_state:
            drag_info = self.drag_state[button]
            if drag_info['is_dragging']:
                self._emit_input_event('drag_end', {
                    'button': button,
                    'start_position': drag_info['start_position'],
                    'end_position': (x, y),
                    'modifiers': modifiers
                })
            
            del self.drag_state[button]
        
        # Traitement des actions
        self._process_input(InputType.MOUSE_BUTTON, button, modifiers, False, (x, y))
        
        self.logger.debug(f"Bouton souris relâché: {button} à ({x}, {y})")
    
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        """Gère le mouvement de la souris"""
        self.last_mouse_position = self.mouse_position
        self.mouse_position = (x, y)
        
        # Mise à jour du glisser-déposer
        for button, drag_info in self.drag_state.items():
            drag_info['current_position'] = (x, y)
            
            # Vérification si le drag commence
            if not drag_info['is_dragging']:
                start_x, start_y = drag_info['start_position']
                distance = ((x - start_x) ** 2 + (y - start_y) ** 2) ** 0.5
                
                if distance >= self.drag_threshold:
                    drag_info['is_dragging'] = True
                    self._emit_input_event('drag_start', {
                        'button': button,
                        'start_position': drag_info['start_position'],
                        'current_position': (x, y)
                    })
            
            # Événement de drag en cours
            if drag_info['is_dragging']:
                self._emit_input_event('drag_move', {
                    'button': button,
                    'start_position': drag_info['start_position'],
                    'current_position': (x, y),
                    'delta': (dx, dy)
                })
        
        # Événement de mouvement de souris
        self._emit_input_event('mouse_motion', {
            'position': (x, y),
            'delta': (dx, dy),
            'buttons': list(self.pressed_mouse_buttons)
        })
    
    def on_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float):
        """Gère le défilement de la molette"""
        self.mouse_position = (x, y)
        
        # Émission d'événement de scroll
        self._emit_input_event('mouse_scroll', {
            'position': (x, y),
            'scroll_x': scroll_x,
            'scroll_y': scroll_y
        })
        
        self.logger.debug(f"Molette: ({scroll_x}, {scroll_y}) à ({x}, {y})")
    
    def _process_input(self, input_type: InputType, key_or_button: int, modifiers: int, 
                      pressed: bool, position: Optional[Tuple[float, float]] = None):
        """Traite une entrée et déclenche les actions correspondantes"""
        # Recherche des liaisons correspondantes
        matching_bindings = [
            binding for binding in self.bindings
            if binding.matches(input_type, key_or_button, modifiers)
        ]
        
        for binding in matching_bindings:
            # Création de l'événement d'entrée
            input_event = InputEvent(
                action=binding.action,
                input_type=input_type,
                key_or_button=key_or_button,
                modifiers=modifiers,
                pressed=pressed,
                timestamp=time.time(),
                position=position
            )
            
            # Ajout à l'historique
            self.input_history.append(input_event)
            
            # Appel des callbacks
            self._trigger_action(binding.action, input_event)
            
            # Émission d'événement global
            self._emit_input_event('action_triggered', {
                'action': binding.action.value,
                'pressed': pressed,
                'input_event': input_event
            })
    
    def _trigger_action(self, action: InputAction, input_event: InputEvent):
        """Déclenche les callbacks pour une action"""
        if action in self.action_callbacks:
            for callback in self.action_callbacks[action]:
                try:
                    callback(input_event)
                except Exception as e:
                    self.logger.error(f"Erreur dans callback pour {action.value}: {e}")
    
    def _emit_input_event(self, event_type: str, data: Dict[str, Any]):
        """Émet un événement d'entrée via le système d'événements"""
        self.event_system.emit(f'input_{event_type}', data, source='InputManager')
    
    def _update_key_repeat(self, delta_time: float):
        """Met à jour la répétition des touches"""
        for key in list(self.key_repeat_timers.keys()):
            if key in self.pressed_keys:
                self.key_repeat_timers[key] += delta_time
                
                # Démarrage de la répétition
                if not self.key_repeat_active[key] and self.key_repeat_timers[key] >= self.key_repeat_delay:
                    self.key_repeat_active[key] = True
                    self.key_repeat_timers[key] = 0.0
                
                # Répétition active
                elif self.key_repeat_active[key] and self.key_repeat_timers[key] >= self.key_repeat_rate:
                    self.key_repeat_timers[key] = 0.0
                    # Déclencher à nouveau l'action
                    modifiers = 0  # Simplification: pas de gestion des modifiers en répétition
                    self._process_input(InputType.KEYBOARD, key, modifiers, True)
    
    def _update_drag_state(self, delta_time: float):
        """Met à jour l'état du glisser-déposer"""
        # Nettoyage des états de drag obsolètes
        current_time = time.time()
        for button in list(self.drag_state.keys()):
            if button not in self.pressed_mouse_buttons:
                # Le bouton a été relâché mais l'état n'a pas été nettoyé
                if current_time - self.drag_state[button]['start_time'] > 1.0:  # Timeout de 1 seconde
                    del self.drag_state[button]
    
    def is_key_pressed(self, key: int) -> bool:
        """Vérifie si une touche est pressée"""
        return key in self.pressed_keys
    
    def is_mouse_button_pressed(self, button: int) -> bool:
        """Vérifie si un bouton de souris est pressé"""
        return button in self.pressed_mouse_buttons
    
    def get_mouse_position(self) -> Tuple[float, float]:
        """Retourne la position actuelle de la souris"""
        return self.mouse_position
    
    def get_mouse_delta(self) -> Tuple[float, float]:
        """Retourne le déplacement de souris depuis la dernière frame"""
        current_x, current_y = self.mouse_position
        last_x, last_y = self.last_mouse_position
        return (current_x - last_x, current_y - last_y)
    
    def is_action_active(self, action: InputAction) -> bool:
        """Vérifie si une action est actuellement active"""
        for binding in self.bindings:
            if binding.action == action:
                if binding.input_type == InputType.KEYBOARD:
                    if self.is_key_pressed(binding.key_or_button):
                        return True
                elif binding.input_type == InputType.MOUSE_BUTTON:
                    if self.is_mouse_button_pressed(binding.key_or_button):
                        return True
        return False
    
    def get_bindings_for_action(self, action: InputAction) -> List[InputBinding]:
        """Retourne toutes les liaisons pour une action"""
        return [binding for binding in self.bindings if binding.action == action]
    
    def get_action_description(self, action: InputAction) -> str:
        """Retourne une description des touches pour une action"""
        bindings = self.get_bindings_for_action(action)
        if not bindings:
            return "Non assigné"
        
        descriptions = []
        for binding in bindings:
            key_name = self._get_key_name(binding.key_or_button, binding.input_type)
            if binding.modifiers:
                modifier_name = self._get_modifier_name(binding.modifiers)
                descriptions.append(f"{modifier_name}+{key_name}")
            else:
                descriptions.append(key_name)
        
        return " ou ".join(descriptions)
    
    def _get_key_name(self, key: int, input_type: InputType) -> str:
        """Retourne le nom lisible d'une touche"""
        if input_type == InputType.MOUSE_BUTTON:
            mouse_names = {
                arcade.MOUSE_BUTTON_LEFT: "Clic gauche",
                arcade.MOUSE_BUTTON_RIGHT: "Clic droit",
                arcade.MOUSE_BUTTON_MIDDLE: "Clic milieu"
            }
            return mouse_names.get(key, f"Bouton {key}")
        
        # Mapping des touches spéciales
        key_names = {
            arcade.key.SPACE: "Espace",
            arcade.key.ENTER: "Entrée",
            arcade.key.ESCAPE: "Échap",
            arcade.key.TAB: "Tab",
            arcade.key.BACKSPACE: "Retour",
            arcade.key.DELETE: "Suppr",
            arcade.key.LEFT: "←",
            arcade.key.RIGHT: "→",
            arcade.key.UP: "↑",
            arcade.key.DOWN: "↓",
            arcade.key.HOME: "Début",
            arcade.key.END: "Fin",
            arcade.key.PAGE_UP: "Page↑",
            arcade.key.PAGE_DOWN: "Page↓",
            arcade.key.F1: "F1",
            arcade.key.F2: "F2",
            arcade.key.F3: "F3",
            arcade.key.F4: "F4",
            arcade.key.F5: "F5",
            arcade.key.F6: "F6",
            arcade.key.F7: "F7",
            arcade.key.F8: "F8",
            arcade.key.F9: "F9",
            arcade.key.F10: "F10",
            arcade.key.F11: "F11",
            arcade.key.F12: "F12",
        }
        
        if key in key_names:
            return key_names[key]
        
        # Caractères alphabétiques
        if 65 <= key <= 90:  # A-Z
            return chr(key)
        
        # Chiffres
        if 48 <= key <= 57:  # 0-9
            return chr(key)
        
        return f"Touche {key}"
    
    def _get_modifier_name(self, modifiers: int) -> str:
        """Retourne le nom des modificateurs"""
        modifier_names = []
        
        if modifiers & arcade.key.MOD_CTRL:
            modifier_names.append("Ctrl")
        if modifiers & arcade.key.MOD_ALT:
            modifier_names.append("Alt")
        if modifiers & arcade.key.MOD_SHIFT:
            modifier_names.append("Maj")
        if modifiers & arcade.key.MOD_ACCEL:
            modifier_names.append("Cmd")
        
        return "+".join(modifier_names)
    
    def save_bindings(self, filename: str):
        """Sauvegarde les liaisons dans un fichier"""
        import json
        
        bindings_data = []
        for binding in self.bindings:
            bindings_data.append({
                'action': binding.action.value,
                'input_type': binding.input_type.value,
                'key_or_button': binding.key_or_button,
                'modifiers': binding.modifiers,
                'description': binding.description
            })
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'bindings': bindings_data,
                    'settings': {
                        'mouse_sensitivity': self.mouse_sensitivity,
                        'key_repeat_delay': self.key_repeat_delay,
                        'key_repeat_rate': self.key_repeat_rate,
                        'double_click_time': self.double_click_time,
                        'drag_threshold': self.drag_threshold
                    }
                }, f, indent=2)
            
            self.logger.info(f"Liaisons sauvegardées: {filename}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des liaisons: {e}")
    
    def load_bindings(self, filename: str):
        """Charge les liaisons depuis un fichier"""
        import json
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Chargement des liaisons
            self.bindings.clear()
            for binding_data in data.get('bindings', []):
                binding = InputBinding(
                    action=InputAction(binding_data['action']),
                    input_type=InputType(binding_data['input_type']),
                    key_or_button=binding_data['key_or_button'],
                    modifiers=binding_data.get('modifiers', 0),
                    description=binding_data.get('description', '')
                )
                self.bindings.append(binding)
            
            # Chargement des paramètres
            settings = data.get('settings', {})
            self.mouse_sensitivity = settings.get('mouse_sensitivity', 1.0)
            self.key_repeat_delay = settings.get('key_repeat_delay', 0.5)
            self.key_repeat_rate = settings.get('key_repeat_rate', 0.1)
            self.double_click_time = settings.get('double_click_time', 0.3)
            self.drag_threshold = settings.get('drag_threshold', 5.0)
            
            self.logger.info(f"Liaisons chargées: {filename} ({len(self.bindings)} bindings)")
            
        except FileNotFoundError:
            self.logger.warning(f"Fichier de liaisons non trouvé: {filename}")
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des liaisons: {e}")
    
    def reset_to_defaults(self):
        """Remet les liaisons par défaut"""
        self.bindings.clear()
        self._setup_default_bindings()
        self.logger.info("Liaisons remises par défaut")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire d'entrées"""
        return {
            'total_bindings': len(self.bindings),
            'pressed_keys': len(self.pressed_keys),
            'pressed_mouse_buttons': len(self.pressed_mouse_buttons),
            'mouse_position': self.mouse_position,
            'active_drags': len(self.drag_state),
            'input_history_size': len(self.input_history),
            'registered_callbacks': sum(len(callbacks) for callbacks in self.action_callbacks.values()),
            'settings': {
                'mouse_sensitivity': self.mouse_sensitivity,
                'key_repeat_delay': self.key_repeat_delay,
                'key_repeat_rate': self.key_repeat_rate,
                'double_click_time': self.double_click_time,
                'drag_threshold': self.drag_threshold
            }
        }
    
    def clear_history(self):
        """Efface l'historique des entrées"""
        self.input_history.clear()
        self.logger.debug("Historique des entrées effacé")
    
    def get_recent_inputs(self, count: int = 10) -> List[InputEvent]:
        """Retourne les dernières entrées"""
        return self.input_history[-count:] if self.input_history else []
    
    def cleanup(self):
        """Nettoyage du gestionnaire d'entrées"""
        self.pressed_keys.clear()
        self.pressed_mouse_buttons.clear()
        self.key_repeat_timers.clear()
        self.key_repeat_active.clear()
        self.drag_state.clear()
        self.action_callbacks.clear()
        self.input_history.clear()
        
        self.logger.info("InputManager nettoyé")
