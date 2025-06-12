# core/resource_manager.py
"""
Steam Defense - Gestionnaire de ressources
Gère le chargement, le cache et la libération des ressources du jeu
"""

import arcade
import logging
import json
import hashlib
from typing import Dict, Any, Optional, List, Union, Callable
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
import threading
import time
import weakref


class ResourceType(Enum):
    """Types de ressources gérées"""
    TEXTURE = "texture"
    SOUND = "sound"
    MUSIC = "music"
    FONT = "font"
    DATA = "data"
    CONFIG = "config"
    GENERATED_SPRITE = "generated_sprite"


class CachePolicy(Enum):
    """Politiques de cache pour les ressources"""
    NEVER = "never"           # Ne jamais mettre en cache
    TEMPORARY = "temporary"   # Cache temporaire (libéré automatiquement)
    PERSISTENT = "persistent" # Cache persistant (manuel seulement)
    PRELOAD = "preload"      # Préchargé au démarrage


@dataclass
class ResourceMetadata:
    """Métadonnées d'une ressource"""
    resource_type: ResourceType
    file_path: Optional[Path] = None
    cache_policy: CachePolicy = CachePolicy.TEMPORARY
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    memory_size: int = 0  # Estimation en bytes
    dependencies: List[str] = field(default_factory=list)
    loader_func: Optional[Callable] = None
    
    def update_access(self):
        """Met à jour les statistiques d'accès"""
        self.last_accessed = time.time()
        self.access_count += 1


class ResourceCache:
    """Cache intelligent pour les ressources"""
    
    def __init__(self, max_memory_mb: int = 100):
        self.resources: Dict[str, Any] = {}
        self.metadata: Dict[str, ResourceMetadata] = {}
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_usage = 0
        self.logger = logging.getLogger('ResourceCache')
        self._lock = threading.RLock()
    
    def add(self, key: str, resource: Any, metadata: ResourceMetadata):
        """Ajoute une ressource au cache"""
        with self._lock:
            # Estimation de la taille mémoire
            estimated_size = self._estimate_memory_size(resource, metadata.resource_type)
            metadata.memory_size = estimated_size
            
            # Vérification de l'espace disponible
            if self._should_cache(metadata):
                self._ensure_memory_available(estimated_size)
                
                self.resources[key] = resource
                self.metadata[key] = metadata
                self.current_memory_usage += estimated_size
                
                self.logger.debug(f"Ressource mise en cache: {key} ({estimated_size} bytes)")
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une ressource du cache"""
        with self._lock:
            if key in self.resources:
                self.metadata[key].update_access()
                return self.resources[key]
            return None
    
    def remove(self, key: str) -> bool:
        """Supprime une ressource du cache"""
        with self._lock:
            if key in self.resources:
                metadata = self.metadata[key]
                self.current_memory_usage -= metadata.memory_size
                
                del self.resources[key]
                del self.metadata[key]
                
                self.logger.debug(f"Ressource supprimée du cache: {key}")
                return True
            return False
    
    def _should_cache(self, metadata: ResourceMetadata) -> bool:
        """Détermine si une ressource doit être mise en cache"""
        return metadata.cache_policy != CachePolicy.NEVER
    
    def _ensure_memory_available(self, required_size: int):
        """S'assure qu'il y a assez de mémoire disponible"""
        while (self.current_memory_usage + required_size > self.max_memory_bytes and
               self.resources):
            
            # Trouve la ressource la moins récemment utilisée avec politique TEMPORARY
            lru_key = None
            lru_time = float('inf')
            
            for key, metadata in self.metadata.items():
                if (metadata.cache_policy == CachePolicy.TEMPORARY and
                    metadata.last_accessed < lru_time):
                    lru_key = key
                    lru_time = metadata.last_accessed
            
            if lru_key:
                self.remove(lru_key)
                self.logger.debug(f"Ressource LRU supprimée pour libérer de l'espace: {lru_key}")
            else:
                break  # Aucune ressource TEMPORARY à supprimer
    
    def _estimate_memory_size(self, resource: Any, resource_type: ResourceType) -> int:
        """Estime la taille mémoire d'une ressource"""
        if resource_type == ResourceType.TEXTURE:
            if hasattr(resource, 'width') and hasattr(resource, 'height'):
                # Estimation pour une texture (4 bytes par pixel pour RGBA)
                return resource.width * resource.height * 4
            return 1024  # Estimation par défaut
        
        elif resource_type == ResourceType.SOUND:
            return 50 * 1024  # 50KB estimation pour un son
        
        elif resource_type == ResourceType.MUSIC:
            return 5 * 1024 * 1024  # 5MB estimation pour de la musique
        
        elif resource_type == ResourceType.DATA:
            # Utilise la taille approximative en mémoire
            import sys
            return sys.getsizeof(resource)
        
        return 1024  # Taille par défaut
    
    def cleanup_expired(self, max_age_seconds: int = 3600):
        """Nettoie les ressources expirées"""
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, metadata in self.metadata.items():
                if (metadata.cache_policy == CachePolicy.TEMPORARY and
                    current_time - metadata.last_accessed > max_age_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.remove(key)
            
            if expired_keys:
                self.logger.info(f"Nettoyage: {len(expired_keys)} ressources expirées supprimées")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        with self._lock:
            type_counts = {}
            policy_counts = {}
            
            for metadata in self.metadata.values():
                # Comptage par type
                type_name = metadata.resource_type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
                
                # Comptage par politique
                policy_name = metadata.cache_policy.value
                policy_counts[policy_name] = policy_counts.get(policy_name, 0) + 1
            
            return {
                'total_resources': len(self.resources),
                'memory_usage_mb': self.current_memory_usage / (1024 * 1024),
                'memory_limit_mb': self.max_memory_bytes / (1024 * 1024),
                'memory_usage_percent': (self.current_memory_usage / self.max_memory_bytes) * 100,
                'resource_types': type_counts,
                'cache_policies': policy_counts
            }
    
    def clear(self, policy_filter: Optional[CachePolicy] = None):
        """Vide le cache (partiellement ou totalement)"""
        with self._lock:
            if policy_filter is None:
                # Vider tout
                count = len(self.resources)
                self.resources.clear()
                self.metadata.clear()
                self.current_memory_usage = 0
                self.logger.info(f"Cache entièrement vidé ({count} ressources)")
            else:
                # Vider seulement les ressources avec une politique donnée
                keys_to_remove = [
                    key for key, meta in self.metadata.items()
                    if meta.cache_policy == policy_filter
                ]
                
                for key in keys_to_remove:
                    self.remove(key)
                
                self.logger.info(f"Cache vidé pour politique {policy_filter.value} "
                               f"({len(keys_to_remove)} ressources)")


class ResourceManager:
    """
    Gestionnaire principal des ressources du jeu
    Gère le chargement, le cache et la libération automatique
    """
    
    def __init__(self, cache_size_mb: int = 100):
        self.logger = logging.getLogger('ResourceManager')
        self.cache = ResourceCache(cache_size_mb)
        
        # Chargeurs de ressources par type
        self.loaders: Dict[ResourceType, Callable] = {
            ResourceType.TEXTURE: self._load_texture,
            ResourceType.SOUND: self._load_sound,
            ResourceType.MUSIC: self._load_music,
            ResourceType.FONT: self._load_font,
            ResourceType.DATA: self._load_data,
            ResourceType.CONFIG: self._load_config,
        }
        
        # Ressources préchargées
        self.preload_list: List[Dict[str, Any]] = []
        self.preloading_complete = False
        
        # Thread de nettoyage automatique
        self.cleanup_thread = None
        self.cleanup_interval = 300  # 5 minutes
        self.shutdown_event = threading.Event()
        
        # Chemins de ressources
        self.base_paths = {
            ResourceType.TEXTURE: Path("assets/textures"),
            ResourceType.SOUND: Path("assets/sounds"),
            ResourceType.MUSIC: Path("assets/music"),
            ResourceType.FONT: Path("assets/fonts"),
            ResourceType.DATA: Path("assets/data"),
            ResourceType.CONFIG: Path("config"),
        }
        
        self.logger.info("ResourceManager initialisé")
    
    def set_base_path(self, resource_type: ResourceType, path: Path):
        """Définit le chemin de base pour un type de ressource"""
        self.base_paths[resource_type] = path
        self.logger.debug(f"Chemin de base défini pour {resource_type.value}: {path}")
    
    def register_loader(self, resource_type: ResourceType, loader_func: Callable):
        """Enregistre un chargeur personnalisé pour un type de ressource"""
        self.loaders[resource_type] = loader_func
        self.logger.debug(f"Chargeur personnalisé enregistré pour {resource_type.value}")
    
    def load_resource(self, resource_id: str, resource_type: ResourceType,
                     file_path: Optional[str] = None,
                     cache_policy: CachePolicy = CachePolicy.TEMPORARY,
                     force_reload: bool = False) -> Optional[Any]:
        """
        Charge une ressource
        
        Args:
            resource_id: Identifiant unique de la ressource
            resource_type: Type de ressource
            file_path: Chemin du fichier (optionnel)
            cache_policy: Politique de cache
            force_reload: Force le rechargement même si en cache
            
        Returns:
            La ressource chargée ou None en cas d'erreur
        """
        # Vérification du cache
        if not force_reload:
            cached_resource = self.cache.get(resource_id)
            if cached_resource is not None:
                self.logger.debug(f"Ressource trouvée en cache: {resource_id}")
                return cached_resource
        
        # Détermination du chemin du fichier
        if file_path is None:
            file_path = resource_id
        
        full_path = self._resolve_path(resource_type, file_path)
        
        # Chargement de la ressource
        try:
            loader = self.loaders.get(resource_type)
            if loader is None:
                self.logger.error(f"Aucun chargeur disponible pour {resource_type.value}")
                return None
            
            resource = loader(full_path)
            
            if resource is not None:
                # Ajout au cache
                metadata = ResourceMetadata(
                    resource_type=resource_type,
                    file_path=full_path,
                    cache_policy=cache_policy
                )
                
                self.cache.add(resource_id, resource, metadata)
                self.logger.debug(f"Ressource chargée: {resource_id}")
                
                return resource
            else:
                self.logger.error(f"Échec du chargement de la ressource: {resource_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de {resource_id}: {e}")
            return None
    
    def _resolve_path(self, resource_type: ResourceType, file_path: str) -> Path:
        """Résout le chemin complet d'un fichier de ressource"""
        base_path = self.base_paths.get(resource_type, Path("."))
        
        # Si le chemin est déjà absolu, l'utiliser tel quel
        path = Path(file_path)
        if path.is_absolute():
            return path
        
        # Sinon, le combiner avec le chemin de base
        return base_path / path
    
    def _load_texture(self, path: Path) -> Optional[arcade.Texture]:
        """Charge une texture"""
        try:
            if path.exists():
                return arcade.load_texture(str(path))
            else:
                self.logger.warning(f"Fichier texture introuvable: {path}")
                return None
        except Exception as e:
            self.logger.error(f"Erreur chargement texture {path}: {e}")
            return None
    
    def _load_sound(self, path: Path) -> Optional[arcade.Sound]:
        """Charge un effet sonore"""
        try:
            if path.exists():
                return arcade.load_sound(str(path))
            else:
                self.logger.warning(f"Fichier son introuvable: {path}")
                return None
        except Exception as e:
            self.logger.error(f"Erreur chargement son {path}: {e}")
            return None
    
    def _load_music(self, path: Path) -> Optional[arcade.Sound]:
        """Charge un fichier musical"""
        # Dans Arcade, la musique utilise le même système que les sons
        return self._load_sound(path)
    
    def _load_font(self, path: Path) -> Optional[str]:
        """Charge une police (retourne le nom de famille)"""
        try:
            if path.exists():
                # Arcade ne fournit pas de chargement de police direct
                # On retourne le chemin pour utilisation avec PIL ou autres
                return str(path)
            else:
                self.logger.warning(f"Fichier police introuvable: {path}")
                return None
        except Exception as e:
            self.logger.error(f"Erreur chargement police {path}: {e}")
            return None
    
    def _load_data(self, path: Path) -> Optional[Any]:
        """Charge un fichier de données JSON"""
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.logger.warning(f"Fichier données introuvable: {path}")
                return None
        except Exception as e:
            self.logger.error(f"Erreur chargement données {path}: {e}")
            return None
    
    def _load_config(self, path: Path) -> Optional[Dict[str, Any]]:
        """Charge un fichier de configuration"""
        return self._load_data(path)  # Même format que les données
    
    def get_texture(self, texture_id: str, file_path: Optional[str] = None) -> Optional[arcade.Texture]:
        """Raccourci pour charger une texture"""
        return self.load_resource(texture_id, ResourceType.TEXTURE, file_path)
    
    def get_sound(self, sound_id: str, file_path: Optional[str] = None) -> Optional[arcade.Sound]:
        """Raccourci pour charger un son"""
        return self.load_resource(sound_id, ResourceType.SOUND, file_path)
    
    def get_music(self, music_id: str, file_path: Optional[str] = None) -> Optional[arcade.Sound]:
        """Raccourci pour charger de la musique"""
        return self.load_resource(music_id, ResourceType.MUSIC, file_path)
    
    def get_data(self, data_id: str, file_path: Optional[str] = None) -> Optional[Any]:
        """Raccourci pour charger des données"""
        return self.load_resource(data_id, ResourceType.DATA, file_path)
    
    def get_config(self, config_id: str, file_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Raccourci pour charger une configuration"""
        return self.load_resource(config_id, ResourceType.CONFIG, file_path)
    
    def add_generated_resource(self, resource_id: str, resource: Any,
                             cache_policy: CachePolicy = CachePolicy.TEMPORARY):
        """Ajoute une ressource générée au cache"""
        metadata = ResourceMetadata(
            resource_type=ResourceType.GENERATED_SPRITE,
            cache_policy=cache_policy
        )
        
        self.cache.add(resource_id, resource, metadata)
        self.logger.debug(f"Ressource générée ajoutée: {resource_id}")
    
    def remove_resource(self, resource_id: str) -> bool:
        """Supprime une ressource du cache"""
        return self.cache.remove(resource_id)
    
    def preload_essential_resources(self):
        """Précharge les ressources essentielles"""
        self.logger.info("Préchargement des ressources essentielles...")
        
        # Configuration des ressources à précharger
        essential_resources = [
            # Textures de base
            {"id": "missing_texture", "type": ResourceType.TEXTURE, "path": "missing.png"},
            
            # Sons de base
            {"id": "ui_click", "type": ResourceType.SOUND, "path": "ui/click.wav"},
            {"id": "ui_hover", "type": ResourceType.SOUND, "path": "ui/hover.wav"},
            
            # Configuration
            {"id": "game_config", "type": ResourceType.CONFIG, "path": "game.json"},
            {"id": "enemy_stats", "type": ResourceType.DATA, "path": "enemies.json"},
            {"id": "tower_stats", "type": ResourceType.DATA, "path": "towers.json"},
        ]
        
        loaded_count = 0
        for resource_info in essential_resources:
            resource = self.load_resource(
                resource_info["id"],
                resource_info["type"],
                resource_info.get("path"),
                CachePolicy.PERSISTENT
            )
            
            if resource is not None:
                loaded_count += 1
        
        self.preloading_complete = True
        self.logger.info(f"Préchargement terminé: {loaded_count}/{len(essential_resources)} ressources")
    
    def start_background_cleanup(self):
        """Démarre le nettoyage automatique en arrière-plan"""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                name="ResourceCleanup",
                daemon=True
            )
            self.cleanup_thread.start()
            self.logger.info("Nettoyage automatique démarré")
    
    def _cleanup_worker(self):
        """Worker thread pour le nettoyage automatique"""
        while not self.shutdown_event.wait(self.cleanup_interval):
            try:
                self.cache.cleanup_expired()
            except Exception as e:
                self.logger.error(f"Erreur pendant le nettoyage automatique: {e}")
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes des ressources"""
        cache_stats = self.cache.get_stats()
        
        return {
            'cache': cache_stats,
            'preloading_complete': self.preloading_complete,
            'loaders_registered': len(self.loaders),
            'base_paths': {k.value: str(v) for k, v in self.base_paths.items()}
        }
    
    def create_resource_hash(self, file_path: Path) -> str:
        """Crée un hash unique pour un fichier de ressource"""
        try:
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    content = f.read()
                return hashlib.md5(content).hexdigest()
            else:
                return hashlib.md5(str(file_path).encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Erreur création hash pour {file_path}: {e}")
            return str(hash(str(file_path)))
    
    def invalidate_cache(self, resource_type: Optional[ResourceType] = None):
        """Invalide le cache (partiellement ou totalement)"""
        if resource_type is None:
            self.cache.clear()
            self.logger.info("Cache entièrement invalidé")
        else:
            # Invalider seulement les ressources d'un type donné
            keys_to_remove = []
            for key, metadata in self.cache.metadata.items():
                if metadata.resource_type == resource_type:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.cache.remove(key)
            
            self.logger.info(f"Cache invalidé pour {resource_type.value} "
                           f"({len(keys_to_remove)} ressources)")
    
    def verify_resources(self) -> Dict[str, List[str]]:
        """Vérifie l'intégrité des ressources sur disque"""
        results = {
            'missing_files': [],
            'corrupted_files': [],
            'valid_files': []
        }
        
        for key, metadata in self.cache.metadata.items():
            if metadata.file_path and metadata.file_path.exists():
                try:
                    # Test de chargement rapide
                    if metadata.resource_type == ResourceType.DATA:
                        with open(metadata.file_path, 'r') as f:
                            json.load(f)
                    
                    results['valid_files'].append(str(metadata.file_path))
                    
                except Exception as e:
                    results['corrupted_files'].append(str(metadata.file_path))
                    self.logger.warning(f"Fichier corrompu détecté: {metadata.file_path}")
            
            elif metadata.file_path:
                results['missing_files'].append(str(metadata.file_path))
                self.logger.warning(f"Fichier manquant: {metadata.file_path}")
        
        return results
    
    def cleanup(self):
        """Nettoyage complet du gestionnaire de ressources"""
        self.logger.info("Nettoyage du ResourceManager...")
        
        # Arrêt du thread de nettoyage
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.shutdown_event.set()
            self.cleanup_thread.join(timeout=5.0)
        
        # Vidage du cache
        self.cache.clear()
        
        # Nettoyage des références
        self.loaders.clear()
        self.preload_list.clear()
        
        self.logger.info("ResourceManager nettoyé")
    
    def __del__(self):
        self.cleanup()