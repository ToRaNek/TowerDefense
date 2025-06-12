# core/timer.py
"""
Steam Defense - Système de gestion du temps
Gère le temps de jeu, les pauses, la vitesse et les événements temporels
"""

import time
import logging
from typing import List, Dict, Any, Callable, Optional
from enum import Enum
from dataclasses import dataclass
from collections import deque


class TimerState(Enum):
    """États du timer"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class ScheduledEvent:
    """Événement programmé dans le temps"""
    name: str
    callback: Callable
    target_time: float
    repeat_interval: Optional[float] = None
    repeat_count: int = -1  # -1 = infini
    is_active: bool = True
    data: Any = None
    
    def should_execute(self, current_time: float) -> bool:
        """Vérifie si l'événement doit être exécuté"""
        return self.is_active and current_time >= self.target_time
    
    def execute(self, current_time: float):
        """Exécute l'événement"""
        if not self.is_active:
            return
        
        try:
            if self.data is not None:
                self.callback(self.data)
            else:
                self.callback()
        except Exception as e:
            logging.getLogger('ScheduledEvent').error(f"Erreur dans l'événement {self.name}: {e}")
        
        # Gestion de la répétition
        if self.repeat_interval is not None and self.repeat_count != 0:
            self.target_time = current_time + self.repeat_interval
            if self.repeat_count > 0:
                self.repeat_count -= 1
                if self.repeat_count == 0:
                    self.is_active = False
        else:
            self.is_active = False


class GameTimer:
    """
    Gestionnaire principal du temps dans le jeu
    Gère les pauses, la vitesse de jeu, et les événements programmés
    """
    
    def __init__(self):
        self.logger = logging.getLogger('GameTimer')
        
        # État du timer
        self.state = TimerState.STOPPED
        self.speed_multiplier = 1.0
        
        # Temps
        self.real_start_time = 0.0
        self.game_time = 0.0  # Temps de jeu total (sans pauses)
        self.total_real_time = 0.0  # Temps réel total
        self.last_update_time = 0.0
        
        # Temps accumulé pendant les pauses
        self.paused_time = 0.0
        self.pause_start_time = 0.0
        
        # Événements programmés
        self.scheduled_events: List[ScheduledEvent] = []
        self.completed_events: List[ScheduledEvent] = []
        
        # Historique des FPS pour statistiques
        self.fps_history: deque = deque(maxlen=60)  # 1 seconde d'historique à 60 FPS
        self.frame_count = 0
        self.fps_update_timer = 0.0
        
        # Statistiques de performance
        self.stats = {
            'total_frames': 0,
            'average_fps': 0.0,
            'min_fps': float('inf'),
            'max_fps': 0.0,
            'total_pause_time': 0.0,
            'pause_count': 0
        }
        
        self.logger.info("GameTimer initialisé")
    
    def start(self):
        """Démarre le timer"""
        if self.state == TimerState.STOPPED:
            self.real_start_time = time.time()
            self.last_update_time = self.real_start_time
            self.game_time = 0.0
            self.paused_time = 0.0
        elif self.state == TimerState.PAUSED:
            # Reprise après pause
            pause_duration = time.time() - self.pause_start_time
            self.paused_time += pause_duration
            self.stats['total_pause_time'] += pause_duration
        
        self.state = TimerState.RUNNING
        self.last_update_time = time.time()
        self.logger.info("Timer démarré")
    
    def pause(self):
        """Met le timer en pause"""
        if self.state == TimerState.RUNNING:
            self.state = TimerState.PAUSED
            self.pause_start_time = time.time()
            self.stats['pause_count'] += 1
            self.logger.info("Timer mis en pause")
    
    def resume(self):
        """Reprend le timer après une pause"""
        if self.state == TimerState.PAUSED:
            self.start()  # start() gère la reprise
            self.logger.info("Timer repris")
    
    def stop(self):
        """Arrête le timer"""
        if self.state == TimerState.PAUSED:
            # Finalise le calcul du temps de pause
            pause_duration = time.time() - self.pause_start_time
            self.paused_time += pause_duration
            self.stats['total_pause_time'] += pause_duration
        
        self.state = TimerState.STOPPED
        self.logger.info(f"Timer arrêté - Temps de jeu total: {self.game_time:.2f}s")
    
    def update(self, delta_time: float):
        """
        Met à jour le timer
        
        Args:
            delta_time: Temps écoulé depuis la dernière frame (fourni par Arcade)
        """
        if self.state != TimerState.RUNNING:
            return
        
        current_real_time = time.time()
        
        # Mise à jour du temps de jeu (affecté par la vitesse)
        game_delta = delta_time * self.speed_multiplier
        self.game_time += game_delta
        
        # Mise à jour du temps réel total
        self.total_real_time = current_real_time - self.real_start_time
        
        # Mise à jour des statistiques FPS
        self._update_fps_stats(delta_time)
        
        # Traitement des événements programmés
        self._process_scheduled_events()
        
        self.last_update_time = current_real_time
        self.stats['total_frames'] += 1
    
    def set_speed(self, multiplier: float):
        """
        Définit la vitesse du jeu
        
        Args:
            multiplier: Multiplicateur de vitesse (1.0 = normal, 2.0 = double, 0.5 = moitié)
        """
        old_speed = self.speed_multiplier
        self.speed_multiplier = max(0.0, min(5.0, multiplier))  # Limite entre 0x et 5x
        
        if old_speed != self.speed_multiplier:
            self.logger.info(f"Vitesse de jeu changée: {old_speed:.1f}x -> {self.speed_multiplier:.1f}x")
    
    def get_speed(self) -> float:
        """Retourne la vitesse actuelle du jeu"""
        return self.speed_multiplier
    
    def is_running(self) -> bool:
        """Vérifie si le timer est en cours d'exécution"""
        return self.state == TimerState.RUNNING
    
    def is_paused(self) -> bool:
        """Vérifie si le timer est en pause"""
        return self.state == TimerState.PAUSED
    
    def get_game_time(self) -> float:
        """Retourne le temps de jeu actuel"""
        return self.game_time
    
    def get_real_time(self) -> float:
        """Retourne le temps réel écoulé"""
        if self.state == TimerState.STOPPED:
            return 0.0
        
        current_time = time.time()
        if self.state == TimerState.PAUSED:
            return self.pause_start_time - self.real_start_time - self.paused_time
        else:
            return current_time - self.real_start_time - self.paused_time
    
    def get_total_real_time(self) -> float:
        """Retourne le temps réel total (incluant les pauses)"""
        return self.total_real_time
    
    def schedule_event(self, name: str, callback: Callable, delay: float, 
                      repeat_interval: Optional[float] = None, 
                      repeat_count: int = 1, data: Any = None) -> ScheduledEvent:
        """
        Programme un événement dans le futur
        
        Args:
            name: Nom de l'événement
            callback: Fonction à appeler
            delay: Délai avant exécution (en secondes de jeu)
            repeat_interval: Intervalle de répétition (optionnel)
            repeat_count: Nombre de répétitions (-1 = infini)
            data: Données à passer au callback
            
        Returns:
            L'événement programmé
        """
        target_time = self.game_time + delay
        
        event = ScheduledEvent(
            name=name,
            callback=callback,
            target_time=target_time,
            repeat_interval=repeat_interval,
            repeat_count=repeat_count,
            data=data
        )
        
        self.scheduled_events.append(event)
        self.logger.debug(f"Événement programmé: {name} dans {delay:.2f}s")
        
        return event
    
    def schedule_real_time_event(self, name: str, callback: Callable, delay: float,
                                data: Any = None) -> ScheduledEvent:
        """
        Programme un événement en temps réel (non affecté par la vitesse du jeu)
        
        Args:
            name: Nom de l'événement
            callback: Fonction à appeler
            delay: Délai en temps réel
            data: Données à passer au callback
        """
        # Conversion en temps de jeu équivalent
        game_delay = delay / self.speed_multiplier if self.speed_multiplier > 0 else delay
        return self.schedule_event(name, callback, game_delay, data=data)
    
    def cancel_event(self, event: ScheduledEvent):
        """Annule un événement programmé"""
        event.is_active = False
        self.logger.debug(f"Événement annulé: {event.name}")
    
    def cancel_events_by_name(self, name: str) -> int:
        """
        Annule tous les événements avec un nom donné
        
        Returns:
            Nombre d'événements annulés
        """
        cancelled_count = 0
        for event in self.scheduled_events:
            if event.name == name and event.is_active:
                event.is_active = False
                cancelled_count += 1
        
        self.logger.debug(f"Événements annulés avec le nom '{name}': {cancelled_count}")
        return cancelled_count
    
    def get_scheduled_events(self) -> List[ScheduledEvent]:
        """Retourne la liste des événements programmés actifs"""
        return [event for event in self.scheduled_events if event.is_active]
    
    def _process_scheduled_events(self):
        """Traite les événements programmés"""
        current_time = self.game_time
        
        # Traitement des événements
        for event in self.scheduled_events[:]:  # Copie pour éviter les modifications concurrentes
            if event.should_execute(current_time):
                event.execute(current_time)
                
                # Si l'événement n'est plus actif, le déplacer vers les événements terminés
                if not event.is_active:
                    self.scheduled_events.remove(event)
                    self.completed_events.append(event)
                    
                    # Limitation de l'historique
                    if len(self.completed_events) > 1000:
                        self.completed_events.pop(0)
    
    def _update_fps_stats(self, delta_time: float):
        """Met à jour les statistiques de FPS"""
        if delta_time > 0:
            current_fps = 1.0 / delta_time
            self.fps_history.append(current_fps)
            
            # Mise à jour des statistiques
            self.stats['min_fps'] = min(self.stats['min_fps'], current_fps)
            self.stats['max_fps'] = max(self.stats['max_fps'], current_fps)
            
            # Calcul de la moyenne sur l'historique
            if self.fps_history:
                self.stats['average_fps'] = sum(self.fps_history) / len(self.fps_history)
    
    def get_fps_stats(self) -> Dict[str, float]:
        """Retourne les statistiques de FPS"""
        return {
            'current_fps': self.fps_history[-1] if self.fps_history else 0.0,
            'average_fps': self.stats['average_fps'],
            'min_fps': self.stats['min_fps'] if self.stats['min_fps'] != float('inf') else 0.0,
            'max_fps': self.stats['max_fps']
        }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques détaillées"""
        fps_stats = self.get_fps_stats()
        
        return {
            'game_time': self.game_time,
            'real_time': self.get_real_time(),
            'total_real_time': self.total_real_time,
            'speed_multiplier': self.speed_multiplier,
            'state': self.state.value,
            'total_pause_time': self.stats['total_pause_time'],
            'pause_count': self.stats['pause_count'],
            'total_frames': self.stats['total_frames'],
            'scheduled_events_count': len(self.get_scheduled_events()),
            'completed_events_count': len(self.completed_events),
            **fps_stats
        }
    
    def reset(self):
        """Remet le timer à zéro"""
        self.stop()
        
        # Réinitialisation des temps
        self.real_start_time = 0.0
        self.game_time = 0.0
        self.total_real_time = 0.0
        self.paused_time = 0.0
        self.pause_start_time = 0.0
        
        # Nettoyage des événements
        self.scheduled_events.clear()
        self.completed_events.clear()
        
        # Réinitialisation des statistiques
        self.fps_history.clear()
        self.stats = {
            'total_frames': 0,
            'average_fps': 0.0,
            'min_fps': float('inf'),
            'max_fps': 0.0,
            'total_pause_time': 0.0,
            'pause_count': 0
        }
        
        self.logger.info("Timer remis à zéro")
    
    def format_time(self, time_seconds: float, show_milliseconds: bool = False) -> str:
        """
        Formate un temps en chaîne lisible
        
        Args:
            time_seconds: Temps en secondes
            show_milliseconds: Afficher les millisecondes
            
        Returns:
            Temps formaté (ex: "1:23.45" ou "1:23")
        """
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        
        if show_milliseconds:
            return f"{minutes}:{seconds:06.3f}"
        else:
            return f"{minutes}:{int(seconds):02d}"
    
    def get_formatted_game_time(self, show_milliseconds: bool = False) -> str:
        """Retourne le temps de jeu formaté"""
        return self.format_time(self.game_time, show_milliseconds)
    
    def get_formatted_real_time(self, show_milliseconds: bool = False) -> str:
        """Retourne le temps réel formaté"""
        return self.format_time(self.get_real_time(), show_milliseconds)


# ═══════════════════════════════════════════════════════════
# DÉCORATEURS UTILITAIRES
# ═══════════════════════════════════════════════════════════

def timed_function(timer: GameTimer):
    """Décorateur pour mesurer le temps d'exécution d'une fonction"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            timer.logger.debug(f"Fonction {func.__name__} exécutée en {execution_time*1000:.2f}ms")
            
            return result
        return wrapper
    return decorator


class PerformanceProfiler:
    """Profileur de performance simple pour mesurer les temps d'exécution"""
    
    def __init__(self, timer: GameTimer):
        self.timer = timer
        self.measurements: Dict[str, List[float]] = {}
        self.logger = logging.getLogger('PerformanceProfiler')
    
    def start_measurement(self, name: str):
        """Démarre une mesure"""
        if not hasattr(self, '_start_times'):
            self._start_times = {}
        self._start_times[name] = time.time()
    
    def end_measurement(self, name: str):
        """Termine une mesure"""
        if not hasattr(self, '_start_times') or name not in self._start_times:
            self.logger.warning(f"Mesure '{name}' non démarrée")
            return
        
        duration = time.time() - self._start_times[name]
        
        if name not in self.measurements:
            self.measurements[name] = []
        
        self.measurements[name].append(duration)
        
        # Limitation de l'historique
        if len(self.measurements[name]) > 100:
            self.measurements[name].pop(0)
        
        del self._start_times[name]
    
    def get_average_time(self, name: str) -> float:
        """Retourne le temps d'exécution moyen pour une mesure"""
        if name not in self.measurements or not self.measurements[name]:
            return 0.0
        
        return sum(self.measurements[name]) / len(self.measurements[name])
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Retourne les statistiques détaillées pour une mesure"""
        if name not in self.measurements or not self.measurements[name]:
            return {'min': 0.0, 'max': 0.0, 'average': 0.0, 'count': 0}
        
        times = self.measurements[name]
        return {
            'min': min(times),
            'max': max(times),
            'average': sum(times) / len(times),
            'count': len(times)
        }
    
    def clear_measurements(self, name: Optional[str] = None):
        """Efface les mesures"""
        if name:
            if name in self.measurements:
                del self.measurements[name]
        else:
            self.measurements.clear()


class Countdown:
    """Compteur à rebours simple"""
    
    def __init__(self, timer: GameTimer, duration: float, callback: Optional[Callable] = None):
        self.timer = timer
        self.duration = duration
        self.remaining_time = duration
        self.callback = callback
        self.is_active = True
        self.is_completed = False
    
    def update(self, delta_time: float):
        """Met à jour le countdown"""
        if not self.is_active or self.is_completed:
            return
        
        self.remaining_time -= delta_time
        
        if self.remaining_time <= 0:
            self.remaining_time = 0
            self.is_completed = True
            self.is_active = False
            
            if self.callback:
                self.callback()
    
    def get_progress(self) -> float:
        """Retourne le progrès (0.0 à 1.0)"""
        if self.duration <= 0:
            return 1.0
        return 1.0 - (self.remaining_time / self.duration)
    
    def get_remaining_time(self) -> float:
        """Retourne le temps restant"""
        return max(0.0, self.remaining_time)
    
    def reset(self):
        """Remet le countdown à zéro"""
        self.remaining_time = self.duration
        self.is_active = True
        self.is_completed = False
    
    def pause(self):
        """Met en pause le countdown"""
        self.is_active = False
    
    def resume(self):
        """Reprend le countdown"""
        if not self.is_completed:
            self.is_active = True
    
    def stop(self):
        """Arrête le countdown"""
        self.is_active = False
        self.is_completed = True


class Stopwatch:
    """Chronomètre simple"""
    
    def __init__(self, timer: GameTimer):
        self.timer = timer
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.is_running = False
    
    def start(self):
        """Démarre le chronomètre"""
        if not self.is_running:
            self.start_time = self.timer.get_game_time()
            self.is_running = True
    
    def stop(self):
        """Arrête le chronomètre"""
        if self.is_running:
            self.elapsed_time += self.timer.get_game_time() - self.start_time
            self.is_running = False
    
    def reset(self):
        """Remet le chronomètre à zéro"""
        self.elapsed_time = 0.0
        if self.is_running:
            self.start_time = self.timer.get_game_time()
    
    def get_elapsed_time(self) -> float:
        """Retourne le temps écoulé"""
        if self.is_running:
            return self.elapsed_time + (self.timer.get_game_time() - self.start_time)
        return self.elapsed_time
    
    def lap(self) -> float:
        """Enregistre un tour et retourne le temps écoulé"""
        lap_time = self.get_elapsed_time()
        self.reset()
        if not self.is_running:
            self.start()
        return lap_time
