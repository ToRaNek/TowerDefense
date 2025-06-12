# gameplay/ui/button.py
"""
Composant Button pour Steam Defense
"""

import pygame
from typing import Callable, Optional, Tuple


class Button:
    """
    Classe pour créer des boutons interactifs
    """
    
    def __init__(self, 
                 x: int, 
                 y: int, 
                 width: int, 
                 height: int,
                 text: str = "",
                 callback: Optional[Callable] = None,
                 color: Tuple[int, int, int] = (100, 100, 100),
                 hover_color: Tuple[int, int, int] = (150, 150, 150),
                 text_color: Tuple[int, int, int] = (255, 255, 255),
                 font_size: int = 24,
                 border_width: int = 2,
                 border_color: Tuple[int, int, int] = (200, 200, 200)):
        """
        Initialise un bouton
        
        Args:
            x, y: Position du bouton
            width, height: Dimensions du bouton
            text: Texte affiché sur le bouton
            callback: Fonction appelée lors du clic
            color: Couleur normale du bouton
            hover_color: Couleur lors du survol
            text_color: Couleur du texte
            font_size: Taille de la police
            border_width: Épaisseur de la bordure
            border_color: Couleur de la bordure
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_width = border_width
        self.border_color = border_color
        
        # État du bouton
        self.is_hovered = False
        self.is_pressed = False
        self.is_enabled = True
        
        # Police
        try:
            self.font = pygame.font.Font(None, font_size)
        except:
            # Police par défaut si problème
            self.font = pygame.font.Font(pygame.font.get_default_font(), font_size)
        
        # Surface de texte
        self.text_surface = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
    
    def handle_event(self, event):
        """
        Gère les événements du bouton
        
        Args:
            event: Événement pygame
        """
        if not self.is_enabled:
            return
        
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                self.is_pressed = True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.is_pressed and self.rect.collidepoint(event.pos):
                self.is_pressed = False
                if self.callback:
                    self.callback()
            else:
                self.is_pressed = False
    
    def update(self, dt: float):
        """
        Met à jour le bouton
        
        Args:
            dt: Temps écoulé depuis la dernière frame
        """
        # Mise à jour de la position du texte si le bouton a bougé
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
    
    def render(self, screen: pygame.Surface):
        """
        Affiche le bouton
        
        Args:
            screen: Surface de rendu
        """
        if not self.is_enabled:
            # Bouton désactivé - couleur grisée
            current_color = (80, 80, 80)
            text_color = (120, 120, 120)
        elif self.is_pressed:
            # Bouton pressé - couleur plus sombre
            current_color = tuple(max(0, c - 30) for c in self.hover_color)
            text_color = self.text_color
        elif self.is_hovered:
            # Bouton survolé
            current_color = self.hover_color
            text_color = self.text_color
        else:
            # État normal
            current_color = self.color
            text_color = self.text_color
        
        # Dessiner le fond du bouton
        pygame.draw.rect(screen, current_color, self.rect)
        
        # Dessiner la bordure
        if self.border_width > 0:
            pygame.draw.rect(screen, self.border_color, self.rect, self.border_width)
        
        # Dessiner le texte
        if self.text:
            if text_color != self.text_color:
                # Recréer la surface de texte avec la nouvelle couleur
                text_surface = self.font.render(self.text, True, text_color)
            else:
                text_surface = self.text_surface
            
            screen.blit(text_surface, self.text_rect)
    
    def set_text(self, new_text: str):
        """
        Change le texte du bouton
        
        Args:
            new_text: Nouveau texte
        """
        self.text = new_text
        self.text_surface = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
    
    def set_position(self, x: int, y: int):
        """
        Change la position du bouton
        
        Args:
            x, y: Nouvelle position
        """
        self.rect.x = x
        self.rect.y = y
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
    
    def set_enabled(self, enabled: bool):
        """
        Active ou désactive le bouton
        
        Args:
            enabled: True pour activer, False pour désactiver
        """
        self.is_enabled = enabled
        if not enabled:
            self.is_hovered = False
            self.is_pressed = False