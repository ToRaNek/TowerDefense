import pygame
from .base_state import BaseState
from .pause_state import PauseState
from .game_over_state import GameOverState
from ..managers.wave_manager import WaveManager
from ..managers.tower_manager import TowerManager
from ..managers.enemy_manager import EnemyManager
from ..managers.projectile_manager import ProjectileManager
from ..managers.sound_manager import SoundManager
from ..ui.hud import HUD
from ..ui.tower_shop import TowerShop
from ..core.game_map import GameMap
from ..core.player import Player


class GameplayState(BaseState):
    """État principal du jeu Tower Defense"""
    
    def __init__(self, game):
        super().__init__(game)
        self.game_map = None
        self.player = None
        self.wave_manager = None
        self.tower_manager = None
        self.enemy_manager = None
        self.projectile_manager = None
        self.hud = None
        self.tower_shop = None
        
        self.selected_tower = None
        self.placing_tower = False
        self.tower_type_to_place = None
        self.game_speed = 1.0
        self.paused = False
        
        self.setup_game()
    
    def setup_game(self):
        """Initialise tous les composants du jeu"""
        # Initialisation du joueur
        self.player = Player(
            health=100,
            money=500,
            score=0
        )
        
        # Chargement de la carte
        self.game_map = GameMap("maps/level_1.json")
        
        # Initialisation des gestionnaires
        self.wave_manager = WaveManager(self.game_map.spawn_points)
        self.tower_manager = TowerManager()
        self.enemy_manager = EnemyManager(self.game_map.path)
        self.projectile_manager = ProjectileManager()
        
        # Interface utilisateur
        self.hud = HUD(self.player)
        self.tower_shop = TowerShop(self.player, self.on_tower_selected)
        
        # Démarrage de la première vague
        self.wave_manager.start_next_wave()
        
        # Musique de jeu
        SoundManager.play_music("gameplay_music", loop=True)
    
    def handle_event(self, event):
        """Gère les événements pendant le jeu"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.pause_game()
            elif event.key == pygame.K_SPACE:
                self.toggle_game_speed()
            elif event.key == pygame.K_1:
                self.select_tower_type("basic")
            elif event.key == pygame.K_2:
                self.select_tower_type("cannon")
            elif event.key == pygame.K_3:
                self.select_tower_type("laser")
            elif event.key == pygame.K_s:
                self.tower_manager.sell_selected_tower(self.player)
            elif event.key == pygame.K_u:
                self.tower_manager.upgrade_selected_tower(self.player)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clic gauche
                self.handle_left_click(event.pos)
            elif event.button == 3:  # Clic droit
                self.handle_right_click(event.pos)
        
        # Gestion des événements de l'interface
        self.hud.handle_event(event)
        self.tower_shop.handle_event(event)
    
    def handle_left_click(self, pos):
        """Gère le clic gauche"""
        if self.placing_tower and self.tower_type_to_place:
            # Placement d'une tour
            if self.game_map.can_place_tower(pos):
                tower_cost = self.get_tower_cost(self.tower_type_to_place)
                if self.player.money >= tower_cost:
                    tower = self.tower_manager.place_tower(
                        self.tower_type_to_place, 
                        pos[0], 
                        pos[1]
                    )
                    if tower:
                        self.player.spend_money(tower_cost)
                        SoundManager.play_sound("tower_place")
                        self.placing_tower = False
                        self.tower_type_to_place = None
                else:
                    SoundManager.play_sound("error")
            else:
                SoundManager.play_sound("error")
        else:
            # Sélection d'une tour
            clicked_tower = self.tower_manager.get_tower_at_position(pos)
            if clicked_tower:
                self.selected_tower = clicked_tower
                SoundManager.play_sound("tower_select")
            else:
                self.selected_tower = None
    
    def handle_right_click(self, pos):
        """Gère le clic droit"""
        # Annuler le placement de tour
        if self.placing_tower:
            self.placing_tower = False
            self.tower_type_to_place = None
    
    def update(self, dt):
        """Met à jour l'état du jeu"""
        if self.paused:
            return
        
        # Application de la vitesse de jeu
        effective_dt = dt * self.game_speed
        
        # Mise à jour des gestionnaires
        self.wave_manager.update(effective_dt)
        
        # Génération des ennemis
        new_enemies = self.wave_manager.get_enemies_to_spawn()
        for enemy_type in new_enemies:
            enemy = self.enemy_manager.spawn_enemy(enemy_type)
            if enemy:
                self.enemy_manager.add_enemy(enemy)
        
        # Mise à jour des entités
        self.enemy_manager.update(effective_dt)
        self.tower_manager.update(effective_dt)
        self.projectile_manager.update(effective_dt)
        
        # Gestion des attaques des tours
        for tower in self.tower_manager.towers:
            target = tower.find_target(self.enemy_manager.enemies)
            if target and tower.can_attack():
                projectile = tower.attack(target)
                if projectile:
                    self.projectile_manager.add_projectile(projectile)
        
        # Gestion des collisions projectiles-ennemis
        self.handle_projectile_collisions()
        
        # Gestion des ennemis qui atteignent la fin
        self.handle_enemies_reaching_end()
        
        # Vérification de la fin de vague
        if self.wave_manager.is_wave_complete() and len(self.enemy_manager.enemies) == 0:
            self.complete_wave()
        
        # Vérification de game over
        if self.player.health <= 0:
            self.game_over()
        
        # Mise à jour de l'interface
        self.hud.update(effective_dt)
        self.tower_shop.update(effective_dt)
    
    def handle_projectile_collisions(self):
        """Gère les collisions entre les projectiles et les ennemis"""
        for projectile in self.projectile_manager.projectiles[:]:
            for enemy in self.enemy_manager.enemies[:]:
                if projectile.collides_with(enemy):
                    # Dégâts à l'ennemi
                    enemy.take_damage(projectile.damage)
                    
                    # Suppression du projectile
                    self.projectile_manager.remove_projectile(projectile)
                    
                    # Si l'ennemi est mort
                    if enemy.health <= 0:
                        self.player.add_money(enemy.reward)
                        self.player.add_score(enemy.score_value)
                        self.enemy_manager.remove_enemy(enemy)
                        SoundManager.play_sound("enemy_death")
                    
                    break
    
    def handle_enemies_reaching_end(self):
        """Gère les ennemis qui atteignent la fin du chemin"""
        for enemy in self.enemy_manager.enemies[:]:
            if enemy.reached_end():
                self.player.take_damage(enemy.damage_to_player)
                self.enemy_manager.remove_enemy(enemy)
                SoundManager.play_sound("player_damage")
    
    def complete_wave(self):
        """Termine la vague actuelle"""
        wave_bonus = self.wave_manager.get_wave_bonus()
        self.player.add_money(wave_bonus)
        self.player.add_score(wave_bonus * 10)
        
        SoundManager.play_sound("wave_complete")
        
        # Démarrer la prochaine vague après un délai
        self.wave_manager.start_next_wave()
    
    def render(self, screen):
        """Affiche l'état du jeu"""
        # Fond de la carte
        screen.fill((34, 139, 34))  # Vert pour l'herbe
        
        # Rendu de la carte
        self.game_map.render(screen)
        
        # Rendu des entités
        self.enemy_manager.render(screen)
        self.tower_manager.render(screen)
        self.projectile_manager.render(screen)
        
        # Rendu de la tour sélectionnée
        if self.selected_tower:
            self.selected_tower.render_selection(screen)
            self.selected_tower.render_range(screen)
        
        # Rendu du placement de tour
        if self.placing_tower and self.tower_type_to_place:
            self.render_tower_placement(screen)
        
        # Interface utilisateur
        self.hud.render(screen)
        self.tower_shop.render(screen)
    
    def render_tower_placement(self, screen):
        """Affiche l'aperçu du placement de tour"""
        mouse_pos = pygame.mouse.get_pos()
        can_place = self.game_map.can_place_tower(mouse_pos)
        
        # Couleur selon la possibilité de placement
        color = (0, 255, 0, 100) if can_place else (255, 0, 0, 100)
        
        # Cercle de portée
        range_radius = self.get_tower_range(self.tower_type_to_place)
        pygame.draw.circle(screen, color, mouse_pos, range_radius, 2)
        
        # Aperçu de la tour
        tower_size = 20
        pygame.draw.circle(screen, color[:3], mouse_pos, tower_size)
    
    def on_tower_selected(self, tower_type):
        """Callback pour la sélection d'un type de tour"""
        self.tower_type_to_place = tower_type
        self.placing_tower = True
    
    def select_tower_type(self, tower_type):
        """Sélectionne un type de tour pour le placement"""
        if self.player.money >= self.get_tower_cost(tower_type):
            self.on_tower_selected(tower_type)
        else:
            SoundManager.play_sound("error")
    
    def get_tower_cost(self, tower_type):
        """Retourne le coût d'un type de tour"""
        costs = {
            "basic": 50,
            "cannon": 100,
            "laser": 150,
            "ice": 75,
            "poison": 125
        }
        return costs.get(tower_type, 50)
    
    def get_tower_range(self, tower_type):
        """Retourne la portée d'un type de tour"""
        ranges = {
            "basic": 80,
            "cannon": 60,
            "laser": 120,
            "ice": 70,
            "poison": 90
        }
        return ranges.get(tower_type, 80)
    
    def toggle_game_speed(self):
        """Alterne la vitesse de jeu"""
        if self.game_speed == 1.0:
            self.game_speed = 2.0
        elif self.game_speed == 2.0:
            self.game_speed = 0.5
        else:
            self.game_speed = 1.0
        
        SoundManager.play_sound("speed_change")
    
    def pause_game(self):
        """Met le jeu en pause"""
        pause_state = PauseState(self.game, self)
        self.game.push_state(pause_state)
    
    def game_over(self):
        """Termine le jeu"""
        game_over_state = GameOverState(self.game, self.player.score)
        self.game.change_state(game_over_state)
    
    def enter(self):
        """Appelé lors de l'entrée dans cet état"""
        self.paused = False
    
    def exit(self):
        """Appelé lors de la sortie de cet état"""
        SoundManager.stop_music()