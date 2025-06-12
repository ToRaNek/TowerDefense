import pygame
from .base_state import BaseState
from ..ui.button import Button
from ..ui.text import Text
from ..managers.sound_manager import SoundManager
from ..core.score_manager import ScoreManager


class GameOverState(BaseState):
    """État de fin de partie (Game Over)"""
    
    def __init__(self, game, final_score, is_victory=False):
        super().__init__(game)
        self.final_score = final_score
        self.is_victory = is_victory
        self.score_manager = ScoreManager()
        self.is_high_score = False
        self.player_name = ""
        self.entering_name = False
        
        self.overlay = None
        self.title = None
        self.score_text = None
        self.high_score_text = None
        self.name_input_text = None
        self.buttons = []
        
        self.setup_ui()
        self.check_high_score()
    
    def setup_ui(self):
        """Configure l'interface de game over"""
        screen_width = self.game.screen.get_width()
        screen_height = self.game.screen.get_height()
        
        # Overlay semi-transparent
        self.overlay = pygame.Surface((screen_width, screen_height))
        self.overlay.set_alpha(180)
        color = (0, 50, 0) if self.is_victory else (50, 0, 0)
        self.overlay.fill(color)
        
        # Titre selon le résultat
        title_text = "VICTOIRE !" if self.is_victory else "GAME OVER"
        title_color = (0, 255, 0) if self.is_victory else (255, 100, 100)
        
        self.title = Text(
            title_text,
            x=screen_width // 2,
            y=screen_height // 4,
            size=64,
            color=title_color,
            center=True
        )
        
        # Score final
        self.score_text = Text(
            f"Score Final: {self.final_score:,}",
            x=screen_width // 2,
            y=screen_height // 3,
            size=32,
            color=(255, 255, 255),
            center=True
        )
        
        # Texte pour nouveau record
        self.high_score_text = Text(
            "NOUVEAU RECORD !",
            x=screen_width // 2,
            y=screen_height // 3 + 50,
            size=24,
            color=(255, 215, 0),
            center=True
        )
        
        # Champ de saisie du nom
        self.name_input_text = Text(
            f"Entrez votre nom: {self.player_name}_",
            x=screen_width // 2,
            y=screen_height // 2 - 50,
            size=20,
            color=(255, 255, 255),
            center=True
        )
        
        self.setup_buttons()
    
    def setup_buttons(self):
        """Configure les boutons selon l'état"""
        screen_width = self.game.screen.get_width()
        screen_height = self.game.screen.get_height()
        
        button_width = 200
        button_height = 50
        button_x = screen_width // 2 - button_width // 2
        start_y = screen_height // 2 + (50 if self.entering_name else 0)
        button_spacing = 70
        
        self.buttons = []
        
        if self.entering_name:
            # Bouton Confirmer le nom
            confirm_button = Button(
                x=button_x,
                y=start_y,
                width=button_width,
                height=button_height,
                text="CONFIRMER",
                callback=self.confirm_name,
                color=(34, 139, 34),
                hover_color=(50, 205, 50),
                text_color=(255, 255, 255)
            )
            self.buttons.append(confirm_button)
            start_y += button_spacing
        
        # Bouton Rejouer
        replay_button = Button(
            x=button_x,
            y=start_y,
            width=button_width,
            height=button_height,
            text="REJOUER",
            callback=self.restart_game,
            color=(34, 139, 34),
            hover_color=(50, 205, 50),
            text_color=(255, 255, 255)
        )
        
        # Bouton Scores
        scores_button = Button(
            x=button_x,
            y=start_y + button_spacing,
            width=button_width,
            height=button_height,
            text="MEILLEURS SCORES",
            callback=self.show_high_scores,
            color=(70, 130, 180),
            hover_color=(100, 149, 237),
            text_color=(255, 255, 255)
        )
        
        # Bouton Menu Principal
        menu_button = Button(
            x=button_x,
            y=start_y + button_spacing * 2,
            width=button_width,
            height=button_height,
            text="MENU PRINCIPAL",
            callback=self.return_to_menu,
            color=(220, 20, 60),
            hover_color=(255, 69, 0),
            text_color=(255, 255, 255)
        )
        
        # Bouton Quitter
        quit_button = Button(
            x=button_x,
            y=start_y + button_spacing * 3,
            width=button_width,
            height=button_height,
            text="QUITTER",
            callback=self.quit_game,
            color=(128, 128, 128),
            hover_color=(160, 160, 160),
            text_color=(255, 255, 255)
        )
        
        self.buttons.extend([replay_button, scores_button, menu_button, quit_button])
    
    def check_high_score(self):
        """Vérifie si le score est un nouveau record"""
        self.is_high_score = self.score_manager.is_high_score(self.final_score)
        if self.is_high_score:
            self.entering_name = True
            self.setup_buttons()
    
    def handle_event(self, event):
        """Gère les événements de game over"""
        if event.type == pygame.KEYDOWN:
            if self.entering_name:
                if event.key == pygame.K_RETURN:
                    self.confirm_name()
                elif event.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                    self.update_name_display()
                elif event.unicode.isprintable() and len(self.player_name) < 15:
                    self.player_name += event.unicode.upper()
                    self.update_name_display()
            else:
                if event.key == pygame.K_ESCAPE:
                    self.return_to_menu()
                elif event.key == pygame.K_RETURN:
                    self.restart_game()
                elif event.key == pygame.K_r:
                    self.restart_game()
        
        # Gestion des événements des boutons
        for button in self.buttons:
            button.handle_event(event)
    
    def update_name_display(self):
        """Met à jour l'affichage du nom en cours de saisie"""
        screen_width = self.game.screen.get_width()
        self.name_input_text = Text(
            f"Entrez votre nom: {self.player_name}_",
            x=screen_width // 2,
            y=self.game.screen.get_height() // 2 - 50,
            size=20,
            color=(255, 255, 255),
            center=True
        )
    
    def update(self, dt):
        """Met à jour l'état de game over"""
        # Mise à jour des boutons
        for button in self.buttons:
            button.update(dt)
        
        # Animation du titre (effet de pulsation)
        import math
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        base_size = 64
        self.title.size = int(base_size + pulse * 8)
    
    def render(self, screen):
        """Affiche l'écran de game over"""
        # Fond noir
        screen.fill((0, 0, 0))
        
        # Overlay coloré
        screen.blit(self.overlay, (0, 0))
        
        # Titre
        self.title.render(screen)
        
        # Score
        self.score_text.render(screen)
        
        # Nouveau record
        if self.is_high_score:
            self.high_score_text.render(screen)
        
        # Saisie du nom
        if self.entering_name:
            self.name_input_text.render(screen)
        
        # Boutons
        for button in self.buttons:
            button.render(screen)
        
        # Statistiques de la partie
        self.render_game_stats(screen)
        
        # Instructions
        if not self.entering_name:
            instructions = [
                "R - Rejouer",
                "ESC - Menu Principal",
                "ENTRÉE - Rejouer"
            ]
            
            for i, instruction in enumerate(instructions):
                instruction_text = Text(
                    instruction,
                    x=50,
                    y=screen.get_height() - 80 + i * 20,
                    size=14,
                    color=(150, 150, 150)
                )
                instruction_text.render(screen)
    
    def render_game_stats(self, screen):
        """Affiche les statistiques de la partie"""
        # TODO: Ajouter les statistiques de jeu
        # (ennemis tués, tours construites, vagues complétées, etc.)
        pass
    
    def confirm_name(self):
        """Confirme le nom du joueur pour le high score"""
        if self.player_name.strip():
            self.score_manager.add_high_score(self.player_name.strip(), self.final_score)
            self.entering_name = False
            self.setup_buttons()
            SoundManager.play_sound("high_score_saved")
        else:
            SoundManager.play_sound("error")
    
    def restart_game(self):
        """Recommence une nouvelle partie"""
        SoundManager.play_sound("button_click")
        from .gameplay_state import GameplayState
        new_game = GameplayState(self.game)
        self.game.change_state(new_game)
    
    def show_high_scores(self):
        """Affiche les meilleurs scores"""
        SoundManager.play_sound("button_click")
        # TODO: Implémenter l'état d'affichage des scores
        print("Affichage des meilleurs scores - À implémenter")
    
    def return_to_menu(self):
        """Retourne au menu principal"""
        SoundManager.play_sound("button_click")
        from .main_menu_state import MainMenuState
        main_menu = MainMenuState(self.game)
        self.game.change_state(main_menu)
    
    def quit_game(self):
        """Quitte le jeu"""
        SoundManager.play_sound("button_click")
        self.game.quit()
    
    def enter(self):
        """Appelé lors de l'entrée dans l'état"""
        # Jouer le son approprié
        if self.is_victory:
            SoundManager.play_sound("victory")
            SoundManager.play_music("victory_music", loop=False)
        else:
            SoundManager.play_sound("game_over")
            SoundManager.play_music("game_over_music", loop=False)
    
    def exit(self):
        """Appelé lors de la sortie de l'état"""
        SoundManager.stop_music()