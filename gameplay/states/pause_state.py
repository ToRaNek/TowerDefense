import pygame
from .base_state import BaseState
from ..ui.button import Button
from ..ui.text import Text
from ..managers.sound_manager import SoundManager

class PauseState(BaseState):
    """État de pause du jeu"""
    
    def __init__(self, game, gameplay_state):
        super().__init__(game)
        self.gameplay_state = gameplay_state
        self.overlay = None
        self.title = None
        self.buttons = []
        self.setup_ui()
    
    def setup_ui(self):
        # Initialisation de pygame et du module font si ce n'est pas déjà fait
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        screen_width = self.game.width
        screen_height = self.game.height
        
        # Overlay semi-transparent
        self.overlay = pygame.Surface((screen_width, screen_height))
        self.overlay.set_alpha(128)
        self.overlay.fill((0, 0, 0))
        
        # Titre
        self.title = Text(
            "JEU EN PAUSE",
            x=screen_width // 2,
            y=screen_height // 3,
            size=48,
            color=(255, 255, 255),
            center=True
        )
        
        # Dimensions des boutons
        button_width = 200
        button_height = 50
        button_x = screen_width // 2 - button_width // 2
        start_y = screen_height // 2
        button_spacing = 70
        
        # Bouton Reprendre
        resume_button = Button(
            x=button_x,
            y=start_y,
            width=button_width,
            height=button_height,
            text="REPRENDRE",
            callback=self.resume_game,
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
        
        # Bouton Recommencer
        restart_button = Button(
            x=button_x,
            y=start_y + button_spacing * 2,
            width=button_width,
            height=button_height,
            text="RECOMMENCER",
            callback=self.restart_game,
            color=(255, 165, 0),
            hover_color=(255, 200, 0),
            text_color=(255, 255, 255)
        )
        
        # Bouton Menu Principal
        menu_button = Button(
            x=button_x,
            y=start_y + button_spacing * 3,
            width=button_width,
            height=button_height,
            text="MENU PRINCIPAL",
            callback=self.return_to_menu,
            color=(220, 20, 60),
            hover_color=(255, 69, 0),
            text_color=(255, 255, 255)
        )
        
        self.buttons = [resume_button, options_button, restart_button, menu_button]
    
    def handle_event(self, event):
        """Gère les événements de l'état de pause"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.resume_game()
            elif event.key == pygame.K_RETURN:
                self.resume_game()
        
        # Gestion des événements des boutons
        for button in self.buttons:
            button.handle_event(event)
    
    def update(self, dt):
        """Met à jour l'état de pause"""
        # Mise à jour des boutons
        for button in self.buttons:
            button.update(dt)
    
    def render(self, screen):
        """Affiche l'état de pause"""
        # Affichage du jeu en arrière-plan (figé)
        self.gameplay_state.render(screen)
        
        # Overlay semi-transparent
        screen.blit(self.overlay, (0, 0))
        
        # Titre
        self.title.render(screen)
        
        # Boutons
        for button in self.buttons:
            button.render(screen)
        
        # Instructions
        instructions = [
            "ESC ou ENTRÉE pour reprendre",
            "Utilisez les boutons ou les raccourcis clavier"
        ]
        
        for i, instruction in enumerate(instructions):
            instruction_text = Text(
                instruction,
                x=screen.get_width() // 2,
                y=screen.get_height() - 80 + i * 25,
                size=16,
                color=(200, 200, 200),
                center=True
            )
            instruction_text.render(screen)
    
    def resume_game(self):
        """Reprend le jeu"""
        SoundManager.play_sound("button_click")
        self.game.pop_state()
    
    def open_options(self):
        """Ouvre le menu des options"""
        SoundManager.play_sound("button_click")
        # TODO: Implémenter l'état des options depuis la pause
        print("Options depuis pause - À implémenter")
    
    def restart_game(self):
        """Recommence la partie"""
        SoundManager.play_sound("button_click")
        from .gameplay_state import GameplayState
        # Retour au gameplay en créant une nouvelle instance
        self.game.pop_state()  # Sortir de la pause
        new_gameplay = GameplayState(self.game)
        self.game.change_state(new_gameplay)
    
    def return_to_menu(self):
        """Retourne au menu principal"""
        SoundManager.play_sound("button_click")
        from .main_menu_state import MainMenuState
        # Sortir de la pause et retourner au menu
        self.game.pop_state()  # Sortir de la pause
        main_menu = MainMenuState(self.game)
        self.game.change_state(main_menu)
    
    def enter(self):
        """Appelé lors de l'entrée dans l'état de pause"""
        # Mettre la musique en pause
        SoundManager.pause_music()
        # Jouer le son de pause
        SoundManager.play_sound("game_pause")
    
    def exit(self):
        """Appelé lors de la sortie de l'état de pause"""
        # Reprendre la musique
        SoundManager.resume_music()