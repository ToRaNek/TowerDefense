# gameplay/states/main_menu_state.py
"""
Steam Defense - État du menu principal
Version simplifiée compatible avec le nouveau système
"""

import arcade
from .base_state import BaseState
from graphics.renderer import RenderLayer
from config.settings import SteampunkColors


class MainMenuState(BaseState):
    """État du menu principal du jeu Tower Defense"""
    
    def __init__(self, game):
        super().__init__(game)
        self.title_text = "STEAM DEFENSE"
        self.menu_options = [
            "JOUER",
            "OPTIONS", 
            "SCORES",
            "QUITTER"
        ]
        self.selected_option = 0
        self.title_y_offset = 0.0
        self.time_elapsed = 0.0
        
    def enter(self, previous_state=None, **kwargs):
        """Entrée dans l'état du menu"""
        super().enter(previous_state, **kwargs)
        
        # Configuration de la caméra pour le menu
        screen_center_x = self.game.camera.viewport_width / 2
        screen_center_y = self.game.camera.viewport_height / 2
        self.game.camera.set_position(screen_center_x, screen_center_y, immediate=True)
        self.game.camera.set_zoom(1.0, immediate=True)
        
        # Couleur de fond pour le menu
        self.game.renderer.set_background_color(SteampunkColors.DARK_STEEL)
        
        self.logger.info("Menu principal affiché")
    
    def update(self, delta_time: float):
        """Met à jour le menu principal"""
        self.time_elapsed += delta_time
        
        # Animation du titre (léger mouvement vertical)
        import math
        self.title_y_offset = math.sin(self.time_elapsed * 2.0) * 10.0
    
    def render(self, renderer):
        """Rendu du menu principal"""
        screen_width = self.game.camera.viewport_width
        screen_height = self.game.camera.viewport_height
        screen_center_x = screen_width / 2
        screen_center_y = screen_height / 2
        
        # Titre du jeu avec animation
        title_y = screen_center_y + 150 + self.title_y_offset
        renderer.draw_text(
            self.title_text,
            screen_center_x, title_y,
            SteampunkColors.BRASS,
            font_size=48,
            font_name="Arial",
            layer=RenderLayer.UI_ELEMENTS
        )
        
        # Sous-titre
        subtitle_y = title_y - 60
        renderer.draw_text(
            "Tower Defense Steampunk",
            screen_center_x, subtitle_y,
            SteampunkColors.COPPER,
            font_size=24,
            font_name="Arial", 
            layer=RenderLayer.UI_ELEMENTS
        )
        
        # Options du menu
        start_y = screen_center_y - 50
        option_spacing = 50
        
        for i, option in enumerate(self.menu_options):
            y_pos = start_y - (i * option_spacing)
            
            # Couleur selon la sélection
            if i == self.selected_option:
                color = SteampunkColors.FIRE_ORANGE
                # Rectangle de sélection
                renderer.draw_rectangle_filled(
                    screen_center_x, y_pos,
                    200, 35,
                    (*SteampunkColors.FIRE_ORANGE, 50),
                    layer=RenderLayer.UI_BACKGROUND
                )
            else:
                color = SteampunkColors.STEAM_WHITE
            
            renderer.draw_text(
                option,
                screen_center_x, y_pos,
                color,
                font_size=20,
                font_name="Arial",
                layer=RenderLayer.UI_ELEMENTS
            )
        
        # Instructions
        instruction_y = screen_center_y - 250
        renderer.draw_text(
            "Utilisez ↑↓ pour naviguer, ENTRÉE pour sélectionner",
            screen_center_x, instruction_y,
            SteampunkColors.STEAM_WHITE,
            font_size=14,
            font_name="Arial",
            layer=RenderLayer.UI_ELEMENTS
        )
    
    def handle_event(self, event_type: str, event_data=None):
        """Gère les événements du menu"""
        super().handle_event(event_type, event_data)
        
        # Gestion de la navigation au clavier via les actions d'input
        if event_type == 'input_action_triggered' and event_data:
            action = event_data.get('action')
            pressed = event_data.get('pressed', False)
            
            if pressed:  # Seulement sur l'appui
                if action == 'move_up':
                    self.selected_option = (self.selected_option - 1) % len(self.menu_options)
                elif action == 'move_down':
                    self.selected_option = (self.selected_option + 1) % len(self.menu_options)
                elif action in ['select', 'confirm']:
                    self._execute_selected_option()
                elif action == 'cancel':
                    self.quit_game()
    
    def _execute_selected_option(self):
        """Exécute l'option sélectionnée"""
        option = self.menu_options[self.selected_option]
        
        if option == "JOUER":
            self.start_game()
        elif option == "OPTIONS":
            self.open_options()
        elif option == "SCORES":
            self.show_scores()
        elif option == "QUITTER":
            self.quit_game()
        
        self.logger.info(f"Option sélectionnée: {option}")