# gameplay/entities/entity.py
"""
Steam Defense - Système d'entités et de composants
Architecture Entity-Component-System (ECS) pour la modularité
"""

import logging
import uuid
from typing import Dict, List, Optional, Type, Any, Callable, Set
from abc import ABC, abstractmethod
from enum import Enum
import weakref
import time


class ComponentType(Enum):
    """Types de composants disponibles"""
    HEALTH = "health"
    MOVEMENT = "movement"
    ATTACK = "attack"
    TARGETING = "targeting"
    UPGRADE = "upgrade"
    STATUS_EFFECTS = "status_effects"
    RENDER = "render"
    COLLISION = "collision"
    AI = "ai"
    INVENTORY = "inventory"
    ECONOMY = "economy"


class EntityComponent(ABC):
    """
    Classe de base pour tous les composants d'entité
    Un composant représente un aspect spécifique d'une entité (santé, mouvement, etc.)
    """
    
    def __init__(self):
        self.entity: Optional['Entity'] = None
        self.enabled = True
        self.component_type = self._get_component_type()
        
        # Métadonnées
        self.created_at = time.time()
        self.last_updated = time.time()
        
        # Événements
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    def _get_component_type(self) -> str:
        """Retourne le type de composant (basé sur le nom de classe par défaut)"""
        return self.__class__.__name__.lower().replace('component', '')
    
    def set_entity(self, entity: 'Entity'):
        """Définit l'entité parente de ce composant"""
        self.entity = entity
    
    def update(self, delta_time: float):
        """
        Met à jour le composant
        
        Args:
            delta_time: Temps écoulé depuis la dernière mise à jour
        """
        if self.enabled:
            self.last_updated = time.time()
    
    def on_attached(self):
        """Appelé quand le composant est attaché à une entité"""
        pass
    
    def on_detached(self):
        """Appelé quand le composant est détaché d'une entité"""
        pass
    
    def on_enabled(self):
        """Appelé quand le composant est activé"""
        pass
    
    def on_disabled(self):
        """Appelé quand le composant est désactivé"""
        pass
    
    def set_enabled(self, enabled: bool):
        """Active ou désactive le composant"""
        if self.enabled != enabled:
            self.enabled = enabled
            if enabled:
                self.on_enabled()
            else:
                self.on_disabled()
    
    def subscribe_to_event(self, event_type: str, handler: Callable):
        """S'abonne à un événement de l'entité"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def handle_event(self, event_type: str, data: Any = None):
        """Gère un événement"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    logging.getLogger('EntityComponent').error(f"Erreur dans le gestionnaire d'événement: {e}")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Retourne des informations de debug"""
        return {
            'type': self.component_type,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'entity_id': self.entity.entity_id if self.entity else None
        }
    
    def cleanup(self):
        """Nettoyage du composant"""
        self._event_handlers.clear()
        self.entity = None


class Entity:
    """
    Classe de base pour toutes les entités du jeu
    Une entité est un conteneur pour des composants
    """
    
    def __init__(self, entity_id: Optional[str] = None):
        """
        Initialise une entité
        
        Args:
            entity_id: Identifiant unique (généré automatiquement si None)
        """
        self.entity_id = entity_id or str(uuid.uuid4())
        self.components: Dict[Type[EntityComponent], EntityComponent] = {}
        self.tags: Set[str] = set()
        
        # Métadonnées
        self.created_at = time.time()
        self.last_updated = time.time()
        self.is_active = True
        self.is_destroyed = False
        
        # Hiérarchie d'entités
        self.parent: Optional['Entity'] = None
        self.children: List['Entity'] = []
        
        # Événements
        self._event_system: Optional[Any] = None  # Référence au système d'événements global
        self._local_event_handlers: Dict[str, List[Callable]] = {}
        
        # Logger
        self.logger = logging.getLogger(f'Entity.{self.__class__.__name__}')
        
        self.logger.debug(f"Entité créée: {self.entity_id}")
    
    def add_component(self, component: EntityComponent) -> EntityComponent:
        """
        Ajoute un composant à l'entité
        
        Args:
            component: Composant à ajouter
            
        Returns:
            Le composant ajouté
        """
        component_type = type(component)
        
        if component_type in self.components:
            self.logger.warning(f"Remplacement du composant {component_type.__name__}")
            self.remove_component(component_type)
        
        self.components[component_type] = component
        component.set_entity(self)
        component.on_attached()
        
        self.logger.debug(f"Composant ajouté: {component_type.__name__}")
        
        return component
    
    def remove_component(self, component_type: Type[EntityComponent]) -> bool:
        """
        Supprime un composant de l'entité
        
        Args:
            component_type: Type de composant à supprimer
            
        Returns:
            True si le composant a été supprimé
        """
        if component_type in self.components:
            component = self.components[component_type]
            component.on_detached()
            component.cleanup()
            del self.components[component_type]
            
            self.logger.debug(f"Composant supprimé: {component_type.__name__}")
            return True
        
        return False
    
    def get_component(self, component_type: Type[EntityComponent]) -> Optional[EntityComponent]:
        """
        Récupère un composant de l'entité
        
        Args:
            component_type: Type de composant à récupérer
            
        Returns:
            Le composant ou None s'il n'existe pas
        """
        return self.components.get(component_type)
    
    def has_component(self, component_type: Type[EntityComponent]) -> bool:
        """
        Vérifie si l'entité possède un composant
        
        Args:
            component_type: Type de composant à vérifier
            
        Returns:
            True si le composant existe
        """
        return component_type in self.components
    
    def get_components_of_type(self, base_type: Type[EntityComponent]) -> List[EntityComponent]:
        """
        Récupère tous les composants d'un type de base donné
        
        Args:
            base_type: Type de base des composants
            
        Returns:
            Liste des composants correspondants
        """
        matching_components = []
        
        for component in self.components.values():
            if isinstance(component, base_type):
                matching_components.append(component)
        
        return matching_components
    
    def add_tag(self, tag: str):
        """Ajoute un tag à l'entité"""
        self.tags.add(tag)
        self.logger.debug(f"Tag ajouté: {tag}")
    
    def remove_tag(self, tag: str) -> bool:
        """
        Supprime un tag de l'entité
        
        Returns:
            True si le tag a été supprimé
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.logger.debug(f"Tag supprimé: {tag}")
            return True
        return False
    
    def has_tag(self, tag: str) -> bool:
        """Vérifie si l'entité possède un tag"""
        return tag in self.tags
    
    def add_child(self, child: 'Entity'):
        """Ajoute une entité enfant"""
        if child.parent:
            child.parent.remove_child(child)
        
        child.parent = self
        self.children.append(child)
        
        self.logger.debug(f"Enfant ajouté: {child.entity_id}")
    
    def remove_child(self, child: 'Entity') -> bool:
        """
        Supprime une entité enfant
        
        Returns:
            True si l'enfant a été supprimé
        """
        if child in self.children:
            child.parent = None
            self.children.remove(child)
            self.logger.debug(f"Enfant supprimé: {child.entity_id}")
            return True
        return False
    
    def get_children_with_tag(self, tag: str) -> List['Entity']:
        """Récupère tous les enfants avec un tag donné"""
        return [child for child in self.children if child.has_tag(tag)]
    
    def update(self, delta_time: float):
        """
        Met à jour l'entité et tous ses composants
        
        Args:
            delta_time: Temps écoulé depuis la dernière mise à jour
        """
        if not self.is_active or self.is_destroyed:
            return
        
        self.last_updated = time.time()
        
        # Mise à jour des composants
        for component in self.components.values():
            if component.enabled:
                try:
                    component.update(delta_time)
                except Exception as e:
                    self.logger.error(f"Erreur lors de la mise à jour du composant {type(component).__name__}: {e}")
        
        # Mise à jour des enfants
        for child in self.children:
            child.update(delta_time)
    
    def set_active(self, active: bool):
        """Active ou désactive l'entité"""
        if self.is_active != active:
            self.is_active = active
            
            # Propagation aux enfants
            for child in self.children:
                child.set_active(active)
            
            if active:
                self.on_activated()
            else:
                self.on_deactivated()
    
    def destroy(self):
        """Marque l'entité pour destruction"""
        if self.is_destroyed:
            return
        
        self.is_destroyed = True
        self.is_active = False
        
        # Destruction des enfants
        for child in self.children[:]:  # Copie pour éviter les modifications pendant l'itération
            child.destroy()
        
        # Détachement du parent
        if self.parent:
            self.parent.remove_child(self)
        
        self.on_destroyed()
        self.logger.debug(f"Entité détruite: {self.entity_id}")
    
    def set_event_system(self, event_system):
        """Définit le système d'événements global"""
        self._event_system = event_system
    
    def emit_event(self, event_type: str, data: Any = None):
        """
        Émet un événement
        
        Args:
            event_type: Type d'événement
            data: Données de l'événement
        """
        # Événement local
        self.handle_local_event(event_type, data)
        
        # Événement global si système disponible
        if self._event_system:
            self._event_system.emit(event_type, data, source=self.entity_id)
    
    def subscribe_to_event(self, event_type: str, handler: Callable):
        """S'abonne à un événement local"""
        if event_type not in self._local_event_handlers:
            self._local_event_handlers[event_type] = []
        self._local_event_handlers[event_type].append(handler)
    
    def handle_local_event(self, event_type: str, data: Any = None):
        """Gère un événement local"""
        # Gestionnaires locaux
        if event_type in self._local_event_handlers:
            for handler in self._local_event_handlers[event_type]:
                try:
                    handler(data)
                except Exception as e:
                    self.logger.error(f"Erreur dans le gestionnaire d'événement local: {e}")
        
        # Propagation aux composants
        for component in self.components.values():
            component.handle_event(event_type, data)
    
    def on_activated(self):
        """Appelé quand l'entité est activée"""
        pass
    
    def on_deactivated(self):
        """Appelé quand l'entité est désactivée"""
        pass
    
    def on_destroyed(self):
        """Appelé quand l'entité est détruite"""
        pass
    
    def cleanup(self):
        """Nettoyage complet de l'entité"""
        # Nettoyage des composants
        for component in list(self.components.values()):
            component.cleanup()
        
        self.components.clear()
        
        # Nettoyage des références
        self._local_event_handlers.clear()
        self.tags.clear()
        self.children.clear()
        self.parent = None
        self._event_system = None
        
        self.logger.debug(f"Entité nettoyée: {self.entity_id}")
    
    def clone(self, new_id: Optional[str] = None) -> 'Entity':
        """
        Crée une copie de l'entité
        
        Args:
            new_id: Nouvel identifiant (généré automatiquement si None)
            
        Returns:
            Nouvelle entité clonée
        """
        # Création de la nouvelle entité
        cloned_entity = self.__class__(new_id)
        
        # Copie des tags
        cloned_entity.tags = self.tags.copy()
        
        # Copie des composants (attention: copie superficielle)
        for component_type, component in self.components.items():
            # Création d'un nouveau composant du même type
            new_component = component_type()
            
            # Copie des attributs publics
            for attr_name in dir(component):
                if not attr_name.startswith('_') and hasattr(new_component, attr_name):
                    attr_value = getattr(component, attr_name)
                    if not callable(attr_value):
                        try:
                            setattr(new_component, attr_name, attr_value)
                        except AttributeError:
                            pass  # Attribut en lecture seule
            
            cloned_entity.add_component(new_component)
        
        self.logger.debug(f"Entité clonée: {self.entity_id} -> {cloned_entity.entity_id}")
        return cloned_entity
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Retourne des informations de debug complètes"""
        component_info = {}
        for component_type, component in self.components.items():
            try:
                component_info[component_type.__name__] = component.get_debug_info()
            except Exception as e:
                component_info[component_type.__name__] = f"Erreur: {e}"
        
        return {
            'entity_id': self.entity_id,
            'entity_type': self.__class__.__name__,
            'is_active': self.is_active,
            'is_destroyed': self.is_destroyed,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'tags': list(self.tags),
            'components': component_info,
            'children_count': len(self.children),
            'parent_id': self.parent.entity_id if self.parent else None
        }
    
    def __str__(self) -> str:
        """Représentation textuelle de l'entité"""
        components_str = ', '.join([comp.__class__.__name__ for comp in self.components.values()])
        tags_str = ', '.join(self.tags) if self.tags else 'aucun'
        
        return (f"Entity({self.__class__.__name__}, id={self.entity_id[:8]}..., "
                f"components=[{components_str}], tags=[{tags_str}], "
                f"active={self.is_active})")
    
    def __repr__(self) -> str:
        return self.__str__()


# ═══════════════════════════════════════════════════════════
# SYSTÈME DE GESTION DES ENTITÉS
# ═══════════════════════════════════════════════════════════

class EntityManager:
    """
    Gestionnaire centralisé pour toutes les entités du jeu
    Implémente le pattern Entity Manager pour optimiser les opérations
    """
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.entities_by_tag: Dict[str, Set[Entity]] = {}
        self.entities_by_type: Dict[Type[Entity], Set[Entity]] = {}
        
        # Files d'attente pour les opérations différées
        self.entities_to_add: List[Entity] = []
        self.entities_to_remove: List[str] = []
        
        # Statistiques
        self.stats = {
            'total_created': 0,
            'total_destroyed': 0,
            'active_entities': 0
        }
        
        self.logger = logging.getLogger('EntityManager')
        self.logger.info("EntityManager initialisé")
    
    def add_entity(self, entity: Entity, immediate: bool = False):
        """
        Ajoute une entité au gestionnaire
        
        Args:
            entity: Entité à ajouter
            immediate: Si True, ajoute immédiatement (sinon différé)
        """
        if immediate:
            self._add_entity_immediate(entity)
        else:
            self.entities_to_add.append(entity)
    
    def _add_entity_immediate(self, entity: Entity):
        """Ajoute immédiatement une entité"""
        if entity.entity_id in self.entities:
            self.logger.warning(f"Entité avec ID existant: {entity.entity_id}")
            return
        
        self.entities[entity.entity_id] = entity
        
        # Indexation par tag
        for tag in entity.tags:
            if tag not in self.entities_by_tag:
                self.entities_by_tag[tag] = set()
            self.entities_by_tag[tag].add(entity)
        
        # Indexation par type
        entity_type = type(entity)
        if entity_type not in self.entities_by_type:
            self.entities_by_type[entity_type] = set()
        self.entities_by_type[entity_type].add(entity)
        
        self.stats['total_created'] += 1
        self.stats['active_entities'] += 1
        
        self.logger.debug(f"Entité ajoutée: {entity.entity_id}")
    
    def remove_entity(self, entity_id: str, immediate: bool = False) -> bool:
        """
        Supprime une entité du gestionnaire
        
        Args:
            entity_id: ID de l'entité à supprimer
            immediate: Si True, supprime immédiatement
            
        Returns:
            True si l'entité a été trouvée pour suppression
        """
        if entity_id not in self.entities:
            return False
        
        if immediate:
            return self._remove_entity_immediate(entity_id)
        else:
            self.entities_to_remove.append(entity_id)
            return True
    
    def _remove_entity_immediate(self, entity_id: str) -> bool:
        """Supprime immédiatement une entité"""
        if entity_id not in self.entities:
            return False
        
        entity = self.entities[entity_id]
        
        # Suppression des index
        for tag in entity.tags:
            if tag in self.entities_by_tag:
                self.entities_by_tag[tag].discard(entity)
                if not self.entities_by_tag[tag]:
                    del self.entities_by_tag[tag]
        
        entity_type = type(entity)
        if entity_type in self.entities_by_type:
            self.entities_by_type[entity_type].discard(entity)
            if not self.entities_by_type[entity_type]:
                del self.entities_by_type[entity_type]
        
        # Nettoyage de l'entité
        entity.cleanup()
        
        # Suppression de la collection principale
        del self.entities[entity_id]
        
        self.stats['total_destroyed'] += 1
        self.stats['active_entities'] -= 1
        
        self.logger.debug(f"Entité supprimée: {entity_id}")
        return True
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Récupère une entité par son ID"""
        return self.entities.get(entity_id)
    
    def get_entities_by_tag(self, tag: str) -> List[Entity]:
        """Récupère toutes les entités avec un tag donné"""
        entities_set = self.entities_by_tag.get(tag, set())
        return list(entities_set)
    
    def get_entities_by_type(self, entity_type: Type[Entity]) -> List[Entity]:
        """Récupère toutes les entités d'un type donné"""
        entities_set = self.entities_by_type.get(entity_type, set())
        return list(entities_set)
    
    def get_entities_with_component(self, component_type: Type[EntityComponent]) -> List[Entity]:
        """Récupère toutes les entités possédant un composant donné"""
        matching_entities = []
        
        for entity in self.entities.values():
            if entity.has_component(component_type):
                matching_entities.append(entity)
        
        return matching_entities
    
    def update_all(self, delta_time: float):
        """Met à jour toutes les entités actives"""
        # Traitement des ajouts et suppressions différés
        self._process_pending_operations()
        
        # Mise à jour des entités actives
        for entity in self.entities.values():
            if entity.is_active and not entity.is_destroyed:
                entity.update(delta_time)
        
        # Nettoyage des entités détruites
        self._cleanup_destroyed_entities()
    
    def _process_pending_operations(self):
        """Traite les opérations en attente"""
        # Ajouts
        for entity in self.entities_to_add:
            self._add_entity_immediate(entity)
        self.entities_to_add.clear()
        
        # Suppressions
        for entity_id in self.entities_to_remove:
            self._remove_entity_immediate(entity_id)
        self.entities_to_remove.clear()
    
    def _cleanup_destroyed_entities(self):
        """Nettoie les entités marquées comme détruites"""
        destroyed_ids = []
        
        for entity_id, entity in self.entities.items():
            if entity.is_destroyed:
                destroyed_ids.append(entity_id)
        
        for entity_id in destroyed_ids:
            self._remove_entity_immediate(entity_id)
    
    def clear_all(self):
        """Supprime toutes les entités"""
        entity_ids = list(self.entities.keys())
        for entity_id in entity_ids:
            self._remove_entity_immediate(entity_id)
        
        self.entities_to_add.clear()
        self.entities_to_remove.clear()
        
        self.logger.info("Toutes les entités supprimées")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire"""
        type_counts = {}
        for entity_type, entities_set in self.entities_by_type.items():
            type_counts[entity_type.__name__] = len(entities_set)
        
        tag_counts = {}
        for tag, entities_set in self.entities_by_tag.items():
            tag_counts[tag] = len(entities_set)
        
        return {
            **self.stats,
            'pending_additions': len(self.entities_to_add),
            'pending_removals': len(self.entities_to_remove),
            'entity_types': type_counts,
            'entity_tags': tag_counts
        }
    
    def find_entities_in_radius(self, center_x: float, center_y: float, 
                               radius: float, entity_type: Optional[Type[Entity]] = None) -> List[Entity]:
        """
        Trouve les entités dans un rayon donné
        
        Args:
            center_x, center_y: Centre de recherche
            radius: Rayon de recherche
            entity_type: Type d'entité à filtrer (optionnel)
            
        Returns:
            Liste des entités dans le rayon
        """
        matching_entities = []
        radius_squared = radius * radius
        
        entities_to_check = (self.get_entities_by_type(entity_type) 
                           if entity_type else self.entities.values())
        
        for entity in entities_to_check:
            # Supposons que l'entité a une position (composant de mouvement ou autre)
            if hasattr(entity, 'get_position'):
                entity_x, entity_y = entity.get_position()
                distance_squared = (center_x - entity_x) ** 2 + (center_y - entity_y) ** 2
                
                if distance_squared <= radius_squared:
                    matching_entities.append(entity)
        
        return matching_entities
    
    def cleanup(self):
        """Nettoyage complet du gestionnaire"""
        self.logger.info("Nettoyage de l'EntityManager")
        self.clear_all()
        
        # Nettoyage des structures de données
        self.entities_by_tag.clear()
        self.entities_by_type.clear()
        
        self.stats = {
            'total_created': 0,
            'total_destroyed': 0,
            'active_entities': 0
        }