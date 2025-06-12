# core/event_system.py
"""
Steam Defense - Système d'événements global
Gère la communication entre les différents systèmes du jeu
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass
import time
import weakref


class EventPriority(Enum):
    """Priorités des événements"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Représente un événement dans le système"""
    event_type: str
    data: Any = None
    timestamp: float = 0.0
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    target: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class EventListener:
    """Encapsule un écouteur d'événement avec ses métadonnées"""
    
    def __init__(self, callback: Callable, priority: EventPriority = EventPriority.NORMAL,
                 once: bool = False, filter_func: Optional[Callable] = None):
        self.callback = callback
        self.priority = priority
        self.once = once  # True si l'écouteur ne doit être appelé qu'une fois
        self.filter_func = filter_func  # Fonction de filtrage optionnelle
        self.call_count = 0
        self.last_called = 0.0
        
        # Utilisation de weak reference si possible pour éviter les fuites mémoire
        try:
            if hasattr(callback, '__self__'):
                self.weak_callback = weakref.WeakMethod(callback)
            else:
                self.weak_callback = weakref.ref(callback)
            self.use_weak_ref = True
        except TypeError:
            # Si on ne peut pas créer une weak reference, on garde la référence normale
            self.weak_callback = None
            self.use_weak_ref = False
    
    def get_callback(self):
        """Retourne le callback, en gérant les weak references"""
        if self.use_weak_ref and self.weak_callback:
            callback = self.weak_callback()
            if callback is None:
                # L'objet a été garbage collecté
                return None
            return callback
        return self.callback
    
    def should_call(self, event: Event) -> bool:
        """Vérifie si l'écouteur doit être appelé pour cet événement"""
        if self.filter_func:
            try:
                return self.filter_func(event)
            except Exception as e:
                logging.getLogger('EventListener').error(f"Erreur dans le filtre: {e}")
                return False
        return True
    
    def call(self, event: Event) -> bool:
        """
        Appelle l'écouteur avec l'événement
        
        Returns:
            bool: True si l'appel a réussi, False sinon
        """
        callback = self.get_callback()
        if callback is None:
            return False
        
        try:
            callback(event.data if event.data is not None else event)
            self.call_count += 1
            self.last_called = time.time()
            return True
        except Exception as e:
            logging.getLogger('EventListener').error(f"Erreur lors de l'appel du callback: {e}")
            return False


class EventSystem:
    """
    Système d'événements centralisé pour la communication inter-composants
    Implémente le pattern Observer avec support des priorités et du filtrage
    """
    
    def __init__(self, max_event_queue_size: int = 1000):
        self.logger = logging.getLogger('EventSystem')
        
        # Écouteurs organisés par type d'événement et priorité
        self.listeners: Dict[str, Dict[EventPriority, List[EventListener]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # File d'attente des événements
        self.event_queue: deque = deque(maxlen=max_event_queue_size)
        self.immediate_events: List[Event] = []  # Événements à traiter immédiatement
        
        # Statistiques
        self.stats = {
            'events_sent': 0,
            'events_processed': 0,
            'listeners_called': 0,
            'failed_calls': 0
        }
        
        # Configuration
        self.max_recursion_depth = 10
        self.current_recursion_depth = 0
        self.processing_events = False
        
        # Cache pour optimiser les recherches d'écouteurs
        self.listener_cache: Dict[str, List[EventListener]] = {}
        self.cache_dirty = True
        
        self.logger.info("EventSystem initialisé")
    
    def subscribe(self, event_type: str, callback: Callable, 
                 priority: EventPriority = EventPriority.NORMAL,
                 once: bool = False, filter_func: Optional[Callable] = None) -> EventListener:
        """
        S'abonne à un type d'événement
        
        Args:
            event_type: Type d'événement à écouter
            callback: Fonction à appeler quand l'événement se produit
            priority: Priorité de l'écouteur
            once: Si True, l'écouteur ne sera appelé qu'une fois
            filter_func: Fonction de filtrage optionnelle
            
        Returns:
            EventListener: L'écouteur créé
        """
        listener = EventListener(callback, priority, once, filter_func)
        self.listeners[event_type][priority].append(listener)
        self.cache_dirty = True
        
        self.logger.debug(f"Abonnement à '{event_type}' avec priorité {priority.name}")
        return listener
    
    def unsubscribe(self, event_type: str, callback: Callable = None, 
                   listener: EventListener = None):
        """
        Se désabonne d'un type d'événement
        
        Args:
            event_type: Type d'événement
            callback: Fonction à désabonner (optionnel si listener fourni)
            listener: Écouteur spécifique à désabonner
        """
        if event_type not in self.listeners:
            return
        
        removed_count = 0
        
        for priority_listeners in self.listeners[event_type].values():
            if listener:
                # Suppression d'un écouteur spécifique
                if listener in priority_listeners:
                    priority_listeners.remove(listener)
                    removed_count += 1
            elif callback:
                # Suppression par callback
                to_remove = []
                for l in priority_listeners:
                    if l.get_callback() == callback:
                        to_remove.append(l)
                
                for l in to_remove:
                    priority_listeners.remove(l)
                    removed_count += 1
        
        if removed_count > 0:
            self.cache_dirty = True
            self.logger.debug(f"Désabonnement de '{event_type}': {removed_count} écouteurs supprimés")
    
    def emit(self, event_type: str, data: Any = None, 
            priority: EventPriority = EventPriority.NORMAL,
            immediate: bool = False, source: str = None, target: str = None):
        """
        Émet un événement
        
        Args:
            event_type: Type d'événement
            data: Données de l'événement
            priority: Priorité de l'événement
            immediate: Si True, traite l'événement immédiatement
            source: Source de l'événement
            target: Cible de l'événement
        """
        event = Event(event_type, data, priority=priority, source=source, target=target)
        
        self.stats['events_sent'] += 1
        
        if immediate or self.current_recursion_depth < self.max_recursion_depth:
            if immediate:
                self.immediate_events.append(event)
            else:
                self._process_event(event)
        else:
            # Ajout à la file d'attente si on dépasse la profondeur de récursion
            self.event_queue.append(event)
        
        self.logger.debug(f"Événement émis: '{event_type}' (immediate: {immediate})")
    
    def emit_immediate(self, event_type: str, data: Any = None, source: str = None):
        """Raccourci pour émettre un événement immédiat"""
        self.emit(event_type, data, immediate=True, source=source)
    
    def process_events(self):
        """Traite tous les événements en attente"""
        if self.processing_events:
            return  # Évite la récursion
        
        self.processing_events = True
        
        try:
            # Traitement des événements immédiats en premier
            while self.immediate_events:
                event = self.immediate_events.pop(0)
                self._process_event(event)
            
            # Traitement de la file d'attente principale
            while self.event_queue:
                event = self.event_queue.popleft()
                self._process_event(event)
                
        finally:
            self.processing_events = False
    
    def _process_event(self, event: Event):
        """Traite un événement individuel"""
        self.current_recursion_depth += 1
        
        try:
            listeners = self._get_listeners_for_event(event.event_type)
            
            if not listeners:
                return
            
            # Tri des écouteurs par priorité (CRITICAL > HIGH > NORMAL > LOW)
            sorted_listeners = sorted(listeners, 
                                    key=lambda l: l.priority.value, 
                                    reverse=True)
            
            listeners_to_remove = []
            
            for listener in sorted_listeners:
                if not listener.should_call(event):
                    continue
                
                success = listener.call(event)
                
                if success:
                    self.stats['listeners_called'] += 1
                    
                    # Suppression des écouteurs "once"
                    if listener.once:
                        listeners_to_remove.append((event.event_type, listener))
                else:
                    self.stats['failed_calls'] += 1
                    # Suppression des écouteurs avec callback invalide
                    if listener.get_callback() is None:
                        listeners_to_remove.append((event.event_type, listener))
            
            # Nettoyage des écouteurs à supprimer
            for event_type, listener in listeners_to_remove:
                self.unsubscribe(event_type, listener=listener)
            
            self.stats['events_processed'] += 1
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de l'événement '{event.event_type}': {e}")
        
        finally:
            self.current_recursion_depth -= 1
    
    def _get_listeners_for_event(self, event_type: str) -> List[EventListener]:
        """Récupère tous les écouteurs pour un type d'événement (avec cache)"""
        if self.cache_dirty:
            self._rebuild_cache()
        
        return self.listener_cache.get(event_type, [])
    
    def _rebuild_cache(self):
        """Reconstruit le cache des écouteurs"""
        self.listener_cache.clear()
        
        for event_type, priority_dict in self.listeners.items():
            all_listeners = []
            for priority_listeners in priority_dict.values():
                all_listeners.extend(priority_listeners)
            
            # Filtrage des écouteurs invalides
            valid_listeners = [l for l in all_listeners if l.get_callback() is not None]
            self.listener_cache[event_type] = valid_listeners
        
        self.cache_dirty = False
        self.logger.debug("Cache des écouteurs reconstruit")
    
    def clear_listeners(self, event_type: str = None):
        """
        Supprime tous les écouteurs
        
        Args:
            event_type: Type d'événement spécifique, ou None pour tous
        """
        if event_type:
            if event_type in self.listeners:
                del self.listeners[event_type]
                self.logger.debug(f"Écouteurs supprimés pour '{event_type}'")
        else:
            self.listeners.clear()
            self.logger.info("Tous les écouteurs supprimés")
        
        self.cache_dirty = True
    
    def clear_event_queue(self):
        """Vide la file d'attente des événements"""
        queue_size = len(self.event_queue)
        immediate_size = len(self.immediate_events)
        
        self.event_queue.clear()
        self.immediate_events.clear()
        
        self.logger.info(f"File d'attente vidée: {queue_size + immediate_size} événements supprimés")
    
    def has_listeners(self, event_type: str) -> bool:
        """Vérifie si un type d'événement a des écouteurs"""
        return len(self._get_listeners_for_event(event_type)) > 0
    
    def get_listener_count(self, event_type: str = None) -> int:
        """
        Retourne le nombre d'écouteurs
        
        Args:
            event_type: Type spécifique, ou None pour le total
            
        Returns:
            int: Nombre d'écouteurs
        """
        if event_type:
            return len(self._get_listeners_for_event(event_type))
        else:
            total = 0
            for listeners_list in self.listener_cache.values():
                total += len(listeners_list)
            return total
    
    def get_event_types(self) -> List[str]:
        """Retourne la liste de tous les types d'événements écoutés"""
        return list(self.listeners.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du système d'événements"""
        return {
            **self.stats,
            'queue_size': len(self.event_queue),
            'immediate_queue_size': len(self.immediate_events),
            'total_listeners': self.get_listener_count(),
            'event_types_count': len(self.listeners),
            'recursion_depth': self.current_recursion_depth
        }
    
    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            'events_sent': 0,
            'events_processed': 0,
            'listeners_called': 0,
            'failed_calls': 0
        }
        self.logger.debug("Statistiques remises à zéro")
    
    def cleanup_dead_listeners(self):
        """Supprime les écouteurs avec des weak references mortes"""
        removed_count = 0
        
        for event_type, priority_dict in list(self.listeners.items()):
            for priority, listeners_list in list(priority_dict.items()):
                valid_listeners = []
                
                for listener in listeners_list:
                    if listener.get_callback() is not None:
                        valid_listeners.append(listener)
                    else:
                        removed_count += 1
                
                if valid_listeners:
                    priority_dict[priority] = valid_listeners
                else:
                    del priority_dict[priority]
            
            if not priority_dict:
                del self.listeners[event_type]
        
        if removed_count > 0:
            self.cache_dirty = True
            self.logger.debug(f"Nettoyage: {removed_count} écouteurs morts supprimés")
    
    def set_max_queue_size(self, size: int):
        """Modifie la taille maximale de la file d'attente"""
        old_queue = list(self.event_queue)
        self.event_queue = deque(old_queue, maxlen=size)
        self.logger.debug(f"Taille de file d'attente changée: {size}")
    
    def debug_listeners(self, event_type: str = None):
        """Affiche des informations de debug sur les écouteurs"""
        if event_type:
            listeners = self._get_listeners_for_event(event_type)
            self.logger.info(f"Écouteurs pour '{event_type}': {len(listeners)}")
            
            for i, listener in enumerate(listeners):
                callback_info = str(listener.get_callback())
                self.logger.info(f"  {i+1}. {callback_info} (priorité: {listener.priority.name}, "
                               f"appels: {listener.call_count})")
        else:
            self.logger.info(f"Types d'événements écoutés: {len(self.listeners)}")
            for event_type in sorted(self.listeners.keys()):
                count = len(self._get_listeners_for_event(event_type))
                self.logger.info(f"  '{event_type}': {count} écouteurs")
    
    def create_event_group(self) -> 'EventGroup':
        """Crée un groupe d'événements pour gérer plusieurs abonnements"""
        return EventGroup(self)


class EventGroup:
    """
    Groupe d'écouteurs d'événements pour faciliter la gestion
    Permet de s'abonner/désabonner en lot
    """
    
    def __init__(self, event_system: EventSystem):
        self.event_system = event_system
        self.listeners: List[tuple] = []  # (event_type, listener)
        self.logger = logging.getLogger('EventGroup')
    
    def subscribe(self, event_type: str, callback: Callable, 
                 priority: EventPriority = EventPriority.NORMAL,
                 once: bool = False, filter_func: Optional[Callable] = None) -> EventListener:
        """S'abonne à un événement et ajoute l'écouteur au groupe"""
        listener = self.event_system.subscribe(event_type, callback, priority, once, filter_func)
        self.listeners.append((event_type, listener))
        return listener
    
    def unsubscribe_all(self):
        """Désabonne tous les écouteurs du groupe"""
        for event_type, listener in self.listeners:
            self.event_system.unsubscribe(event_type, listener=listener)
        
        count = len(self.listeners)
        self.listeners.clear()
        self.logger.debug(f"Groupe désabonné: {count} écouteurs supprimés")
    
    def get_listener_count(self) -> int:
        """Retourne le nombre d'écouteurs dans le groupe"""
        return len(self.listeners)


# ═══════════════════════════════════════════════════════════
# ÉVÉNEMENTS PRÉDÉFINIS POUR STEAM DEFENSE
# ═══════════════════════════════════════════════════════════

class SteamDefenseEvents:
    """Constantes pour les types d'événements du jeu"""
    
    # Événements de jeu
    GAME_START = "game_start"
    GAME_PAUSE = "game_pause"
    GAME_RESUME = "game_resume"
    GAME_OVER = "game_over"
    GAME_VICTORY = "game_victory"
    GAME_QUIT = "game_quit"
    
    # Événements de niveau
    LEVEL_START = "level_start"
    LEVEL_COMPLETE = "level_complete"
    WAVE_START = "wave_start"
    WAVE_COMPLETE = "wave_complete"
    
    # Événements d'ennemis
    ENEMY_SPAWN = "enemy_spawn"
    ENEMY_DEATH = "enemy_death"
    ENEMY_REACH_BASE = "enemy_reach_base"
    ENEMY_TAKE_DAMAGE = "enemy_take_damage"
    
    # Événements de tours
    TOWER_BUILD = "tower_build"
    TOWER_UPGRADE = "tower_upgrade"
    TOWER_SELL = "tower_sell"
    TOWER_ATTACK = "tower_attack"
    
    # Événements de projectiles
    PROJECTILE_FIRE = "projectile_fire"
    PROJECTILE_HIT = "projectile_hit"
    PROJECTILE_MISS = "projectile_miss"
    
    # Événements d'interface
    UI_BUTTON_CLICK = "ui_button_click"
    UI_MENU_OPEN = "ui_menu_open"
    UI_MENU_CLOSE = "ui_menu_close"
    
    # Événements d'économie
    MONEY_GAINED = "money_gained"
    MONEY_SPENT = "money_spent"
    
    # Événements d'effets
    EXPLOSION = "explosion"
    STEAM_EFFECT = "steam_effect"
    LIGHTNING_EFFECT = "lightning_effect"
    
    # Événements de système
    PERFORMANCE_WARNING = "performance_warning"
    ERROR_OCCURRED = "error_occurred"
    DEBUG_TOGGLE = "debug_toggle"


# ═══════════════════════════════════════════════════════════
# DÉCORATEURS UTILITAIRES
# ═══════════════════════════════════════════════════════════

def event_handler(event_type: str, priority: EventPriority = EventPriority.NORMAL):
    """
    Décorateur pour marquer une méthode comme gestionnaire d'événement
    
    Args:
        event_type: Type d'événement à gérer
        priority: Priorité du gestionnaire
    """
    def decorator(func):
        func._event_type = event_type
        func._event_priority = priority
        func._is_event_handler = True
        return func
    return decorator


class EventMixin:
    """
    Mixin pour ajouter facilement la gestion d'événements à une classe
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_group: Optional[EventGroup] = None
    
    def setup_events(self, event_system: EventSystem):
        """Configure automatiquement les gestionnaires d'événements"""
        self._event_group = event_system.create_event_group()
        
        # Auto-découverte des méthodes marquées comme gestionnaires
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if (hasattr(attr, '_is_event_handler') and 
                hasattr(attr, '_event_type')):
                
                event_type = attr._event_type
                priority = attr._event_priority
                
                self._event_group.subscribe(event_type, attr, priority)
    
    def cleanup_events(self):
        """Nettoie tous les gestionnaires d'événements"""
        if self._event_group:
            self._event_group.unsubscribe_all()
            self._event_group = None


# ═══════════════════════════════════════════════════════════
# EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════

class ExampleGameComponent(EventMixin):
    """Exemple d'utilisation du système d'événements"""
    
    def __init__(self, event_system: EventSystem):
        super().__init__()
        self.setup_events(event_system)
    
    @event_handler(SteamDefenseEvents.ENEMY_DEATH, EventPriority.HIGH)
    def on_enemy_death(self, data):
        """Gestionnaire pour la mort d'un ennemi"""
        enemy = data.get('enemy')
        reward = data.get('reward', 0)
        print(f"Ennemi {enemy} tué, récompense: {reward}")
    
    @event_handler(SteamDefenseEvents.TOWER_BUILD)
    def on_tower_build(self, data):
        """Gestionnaire pour la construction d'une tour"""
        tower_type = data.get('tower_type')
        position = data.get('position')
        print(f"Tour {tower_type} construite en {position}")
    
    def __del__(self):
        self.cleanup_events()