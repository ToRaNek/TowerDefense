# gameplay/states/gameplay_state.py
"""
Steam Defense - État de gameplay principal
Version simplifiée pour démonstration
"""

import arcade
from .base_state import BaseState
from graphics.renderer import RenderLayer
from config.settings import SteampunkColors, GRID_CONFIG


class GameplayState(BaseState):
    """État principal du jeu Tower Defense"""
    
    def __init__(self, game):
        super().__init__(game)
        self.game_time = 0.0
        self.score = 0
        self.money = 500
        self.lives = 20
        self.wave = 1
        self.paused = False
        self.game_speed = 1.0
        
    def enter(self, previous_state=None, **kwargs):
        """Entrée dans l'état de gameplay"""
        super().enter(previous_state, **kwargs)
        
        # Configuration de la caméra pour le gameplay
        self.game.camera.fit_to_grid()
        self.game.camera.center_on_grid()
        
        # Couleur de fond pour le gameplay
        self.game.renderer.set_background_color(SteampunkColors.DARK_STEEL)
        
        self.logger.info("Gameplay démarré")
    
    def update(self, delta_time: float):
        """Met à jour le gameplay"""
        if not self.paused:
            self.game_time += delta_time * self.game_speed
            
            # Simulation simple d'augmentation du score
            self.score += int(delta_time * 10)
    
    def render(self, renderer):
        """Rendu du gameplay"""
        # Rendu de la grille de debug
        if self.game.debug_mode:
            renderer.draw_debug_grid(
                GRID_CONFIG['TILE_SIZE'], 
                (*SteampunkColors.COPPER, 100)
            )
        
        # Interface de jeu (HUD)
        self._render_hud(renderer)
        
        # Message de démonstration
        screen_center_x = self.game.camera.viewport_width / 2
        screen_center_y = self.game.camera.viewport_height / 2
        
        renderer.draw_text(
            "MODE GAMEPLAY - DÉMO",
            screen_center_x, screen_center_y,
            SteampunkColors.FIRE_ORANGE,
            font_size=32,
            layer=RenderLayer.UI_ELEMENTS
        )
        
        renderer.draw_text(
            "Appuyez ÉCHAP pour pause, F1 pour debug",
            screen_center_x, screen_center_y - 50,
            SteampunkColors.STEAM_WHITE,
            font_size=16,
            layer=RenderLayer.UI_ELEMENTS
        )
    
    def _render_hud(self, renderer):
        """Rendu de l'interface utilisateur"""
        # Position de l'HUD en haut de l'écran
        hud_y = self.game.camera.viewport_height - 30
        margin = 20
        
        # Informations de jeu
        info_texts = [
            f"Score: {self.score:,}",
            f"Argent: ${self.money}",
            f"Vies: {self.lives}",
            f"Vague: {self.wave}",
            f"Temps: {self.game_time:.1f}s"
        ]
        
        x_pos = margin
        for text in info_texts:
            renderer.draw_text(
                text,
                x_pos, hud_y,
                SteampunkColors.BRASS,
                font_size=16,
                layer=RenderLayer.UI_OVERLAY
            )
            x_pos += 150
        
        # Indicateur de vitesse si différent de 1x
        if self.game_speed != 1.0:
            renderer.draw_text(
                f"Vitesse: {self.game_speed}x",
                self.game.camera.viewport_width - 150, hud_y,
                SteampunkColors.FIRE_ORANGE,
                font_size=16,
                layer=RenderLayer.UI_OVERLAY
            )
    
    def handle_event(self, event_type: str, event_data=None):
        """Gère les événements du gameplay"""
        super().handle_event(event_type, event_data)
        
        if event_type == 'input_action_triggered' and event_data:
            action = event_data.get('action')
            pressed = event_data.get('pressed', False)
            
            if pressed:
                if action == 'pause':
                    self.pause_game()
                elif action == 'speed_up':
                    self.toggle_game_speed()
                elif action == 'cancel':
                    self.pause_game()
    
    def get_debug_info(self) -> list:
        """Informations de debug pour le gameplay"""
        debug_info = super().get_debug_info()
        debug_info.extend([
            f"Score: {self.score:,}",
            f"Argent: ${self.money}",
            f"Vies: {self.lives}",
            f"Vague: {self.wave}",
            f"Temps de jeu: {self.game_time:.1f}s"
        ])
        return debug_info