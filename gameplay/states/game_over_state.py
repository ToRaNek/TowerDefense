# gameplay/states/game_over_state.py
"""
Steam Defense - État de fin de partie
Version simplifiée
"""

import arcade
from .base_state import BaseState
from graphics.renderer import RenderLayer
from config.settings import SteampunkColors


class GameOverState(BaseState):
    """État de fin de partie (Game Over)"""
    
    def __init__(self, game):
        super().__init__(game)
        self.final_score = 0
        self.is_victory = False
        self.menu_options = [
            "RECOMMENCER",
            "MENU PRINCIPAL",
            "QUITTER"
        ]
        self.selected_option = 0
        
    def enter(self, previous_state=None, **kwargs):
        """Entrée dans l'état de game over"""
        super().enter(previous_state, **kwargs)
        
        # Récupération des données de fin de partie
        self.final_score = kwargs.get('score', 0)
        self.is_victory = kwargs.get('is_victory', False)
        
        result = "VICTOIRE" if self.is_victory else "DÉFAITE"
        self.logger.info(f"Fin de partie: {result}, Score: {self.final_score}")
    
    def update(self, delta_time: float):
        """Met à jour l'état de game over"""
        pass
    
    def render(self, renderer):
        """Rendu de l'écran de game over"""
        screen_width = self.game.camera.viewport_width
        screen_height = self.game.camera.viewport_height
        screen_center_x = screen_width / 2
        screen_center_y = screen_height / 2
        
        # Overlay avec couleur selon le résultat
        overlay_color = SteampunkColors.DARK_GREEN if self.is_victory else SteampunkColors.DARK_RED
        renderer.draw_rectangle_filled(
            screen_center_x, screen_center_y,
            screen_width, screen_height,
            (*overlay_color, 180),
            layer=RenderLayer.UI_BACKGROUND
        )
        
        # Titre selon le résultat
        title_text = "VICTOIRE !" if self.is_victory else "DÉFAITE"
        title_color = SteampunkColors.ELECTRIC_GREEN if self.is_victory else SteampunkColors.FIRE_ORANGE
        
        renderer.draw_text(
            title_text,
            screen_center_x, screen_center_y + 150,
            title_color,
            font_size=48,
            layer=RenderLayer.UI_OVERLAY
        )
        
        # Score final
        renderer.draw_text(
            f"Score Final: {self.final_score:,}",
            screen_center_x, screen_center_y + 80,
            SteampunkColors.BRASS,
            font_size=24,
            layer=RenderLayer.UI_OVERLAY
        )
        
        # Options du menu
        start_y = screen_center_y
        option_spacing = 50
        
        for i, option in enumerate(self.menu_options):
            y_pos = start_y - (i * option_spacing)
            
            # Couleur selon la sélection
            if i == self.selected_option:
                color = SteampunkColors.FIRE_ORANGE
                # Rectangle de sélection
                renderer.draw_rectangle_filled(
                    screen_center_x, y_pos,
                    250, 35,
                    (*SteampunkColors.FIRE_ORANGE, 50),
                    layer=RenderLayer.UI_OVERLAY
                )
            else:
                color = SteampunkColors.STEAM_WHITE
            
            renderer.draw_text(
                option,
                screen_center_x, y_pos,
                color,
                font_size=20,
                layer=RenderLayer.UI_OVERLAY
            )
        
        # Instructions
        instruction_y = screen_center_y - 200
        renderer.draw_text(
            "↑↓ pour naviguer, ENTRÉE pour sélectionner",
            screen_center_x, instruction_y,
            SteampunkColors.STEAM_WHITE,
            font_size=14,
            layer=RenderLayer.UI_OVERLAY
        )
    
    def handle_event(self, event_type: str, event_data=None):
        """Gère les événements de game over"""
        super().handle_event(event_type, event_data)
        
        if event_type == 'input_action_triggered' and event_data:
            action = event_data.get('action')
            pressed = event_data.get('pressed', False)
            
            if pressed:
                if action == 'move_up':
                    self.selected_option = (self.selected_option - 1) % len(self.menu_options)
                elif action == 'move_down':
                    self.selected_option = (self.selected_option + 1) % len(self.menu_options)
                elif action in ['select', 'confirm']:
                    self._execute_selected_option()
                elif action == 'cancel':
                    self.return_to_menu()
    
    def _execute_selected_option(self):
        """Exécute l'option sélectionnée"""
        option = self.menu_options[self.selected_option]
        
        if option == "RECOMMENCER":
            self.restart_game()
        elif option == "MENU PRINCIPAL":
            self.return_to_menu()
        elif option == "QUITTER":
            self.quit_game()
        
        self.logger.info(f"Option de game over sélectionnée: {option}")