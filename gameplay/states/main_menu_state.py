import pygame
from .base_state import BaseState
from ..ui.button import Button
from ..ui.text import Text
from ..managers.sound_manager import SoundManager


class MainMenuState(BaseState):
    """État du menu principal du jeu Tower Defense"""
    
    def __init__(self, game):
        super().__init__(game)
        self.title = None
        self.buttons = []
        self.background = None
        self.background_music_started = False
        self.setup_ui()
    
    def setup_ui(self):
        """Configure l'interface utilisateur du menu principal"""
        screen_width = self.game.screen.get_width()
        screen_height = self.game.screen.get_height()
        
        # Titre du jeu
        self.title = Text(
            "TOWER DEFENSE",
            x=screen_width // 2,
            y=screen_height // 4,
            size=72,
            color=(255, 255, 255),
            center=True,
            font_name="Arial"
        )
        
        # Boutons du menu
        button_width = 200
        button_height = 50
        button_x = screen_width // 2 - button_width // 2
        start_y = screen_height // 2
        button_spacing = 70
        
        # Bouton Jouer
        play_button = Button(
            x=button_x,
            y=start_y,
            width=button_width,
            height=button_height,
            text="JOUER",
            callback=self.start_game,
            color=(34, 139, 34),
            hover_color=(50, 205, 50),
            text_color=(255, 255, 255)
        )
        
        # Bouton Options
        options_button = Button(
            x=button_x,
            y=start_y + button_spacing,
            width=button_width,
            height=button_height,
            text="OPTIONS",
            callback=self.open_options,
            color=(70, 130, 180),
            hover_color=(100, 149, 237),
            text_color=(255, 255, 255)
        )
        
        # Bouton Scores
        scores_button = Button(
            x=button_x,
            y=start_y + button_spacing * 2,
            width=button_width,
            height=button_height,
            text="SCORES",
            callback=self.show_scores,
            color=(255, 165, 0),
            hover_color=(255, 200, 0),
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
            color=(220, 20, 60),
            hover_color=(255, 69, 0),
            text_color=(255, 255, 255)
        )
        
        self.buttons = [play_button, options_button, scores_button, quit_button]
        
        # Chargement du fond d'écran
        try:
            self.background = pygame.image.load("assets/images/menu_background.png")
            self.background = pygame.transform.scale(self.background, (screen_width, screen_height))
        except pygame.error:
            # Fond par défaut si l'image n'existe pas
            self.background = None
    
    def handle_event(self, event):
        """Gère les événements du menu principal"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.quit_game()
            elif event.key == pygame.K_RETURN:
                self.start_game()
        
        # Gestion des événements des boutons
        for button in self.buttons:
            button.handle_event(event)
    
    def update(self, dt):
        """Met à jour l'état du menu principal"""
        # Démarrer la musique de fond
        if not self.background_music_started:
            SoundManager.play_music("menu_music", loop=True)
            self.background_music_started = True
        
        # Mise à jour des boutons
        for button in self.buttons:
            button.update(dt)
    
    def render(self, screen):
        """Affiche le menu principal"""
        # Fond d'écran
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((25, 25, 112))  # Bleu nuit par défaut
        
        # Titre
        self.title.render(screen)
        
        # Boutons
        for button in self.buttons:
            button.render(screen)
        
        # Version du jeu
        version_text = Text(
            "v1.0.0",
            x=screen.get_width() - 50,
            y=screen.get_height() - 30,
            size=16,
            color=(128, 128, 128),
            center=True
        )
        version_text.render(screen)
    
    def start_game(self):
        """Démarre une nouvelle partie"""
        SoundManager.play_sound("button_click")
        from .gameplay_state import GameplayState
        self.game.change_state(GameplayState(self.game))
    
    def open_options(self):
        """Ouvre le menu des options"""
        SoundManager.play_sound("button_click")
        # TODO: Implémenter l'état des options
        print("Options menu - À implémenter")
    
    def show_scores(self):
        """Affiche les meilleurs scores"""
        SoundManager.play_sound("button_click")
        # TODO: Implémenter l'état des scores
        print("High scores - À implémenter")
    
    def quit_game(self):
        """Quitte le jeu"""
        SoundManager.play_sound("button_click")
        self.game.quit()
    
    def enter(self):
        """Appelé lors de l'entrée dans cet état"""
        self.background_music_started = False
    
    def exit(self):
        """Appelé lors de la sortie de cet état"""
        SoundManager.stop_music()