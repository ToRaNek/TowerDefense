# gameplay/ui/text.py
"""
Composant Text pour Steam Defense
"""

import pygame
from typing import Tuple, Optional


class Text:
    """
    Classe pour afficher du texte formaté
    """
    
    def __init__(self,
                 text: str,
                 x: int,
                 y: int,
                 size: int = 24,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 font_name: Optional[str] = None,
                 center: bool = False,
                 bold: bool = False,
                 italic: bool = False):
        """
        Initialise un composant texte
        
        Args:
            text: Texte à afficher
            x, y: Position du texte
            size: Taille de la police
            color: Couleur du texte (R, G, B)
            font_name: Nom de la police (None pour police par défaut)
            center: Si True, centre le texte sur la position x, y
            bold: Si True, texte en gras
            italic: Si True, texte en italique
        """
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.center = center
        self.bold = bold
        self.italic = italic
        
        # Initialiser la police
        self._init_font(font_name)
        
        # Créer la surface de texte
        self._create_surface()
    
    def _init_font(self, font_name: Optional[str]):
        """
        Initialise la police
        
        Args:
            font_name: Nom de la police
        """
        try:
            if font_name:
                self.font = pygame.font.Font(font_name, self.size)
            else:
                self.font = pygame.font.Font(None, self.size)
            
            # Appliquer les styles
            if hasattr(self.font, 'set_bold'):
                self.font.set_bold(self.bold)
            if hasattr(self.font, 'set_italic'):
                self.font.set_italic(self.italic)
                
        except (pygame.error, FileNotFoundError):
            # Police par défaut si problème
            self.font = pygame.font.Font(pygame.font.get_default_font(), self.size)
    
    def _create_surface(self):
        """
        Crée la surface de rendu du texte
        """
        self.surface = self.font.render(self.text, True, self.color)
        self.rect = self.surface.get_rect()
        
        # Positionner le rectangle
        if self.center:
            self.rect.center = (self.x, self.y)
        else:
            self.rect.x = self.x
            self.rect.y = self.y
    
    def render(self, screen: pygame.Surface):
        """
        Affiche le texte sur l'écran
        
        Args:
            screen: Surface de rendu
        """
        screen.blit(self.surface, self.rect)
    
    def set_text(self, new_text: str):
        """
        Change le texte affiché
        
        Args:
            new_text: Nouveau texte
        """
        if new_text != self.text:
            self.text = new_text
            self._create_surface()
    
    def set_color(self, new_color: Tuple[int, int, int]):
        """
        Change la couleur du texte
        
        Args:
            new_color: Nouvelle couleur (R, G, B)
        """
        if new_color != self.color:
            self.color = new_color
            self._create_surface()
    
    def set_position(self, x: int, y: int):
        """
        Change la position du texte
        
        Args:
            x, y: Nouvelle position
        """
        self.x = x
        self.y = y
        
        if self.center:
            self.rect.center = (self.x, self.y)
        else:
            self.rect.x = self.x
            self.rect.y = self.y
    
    def get_width(self) -> int:
        """
        Retourne la largeur du texte
        
        Returns:
            Largeur en pixels
        """
        return self.rect.width
    
    def get_height(self) -> int:
        """
        Retourne la hauteur du texte
        
        Returns:
            Hauteur en pixels
        """
        return self.rect.height
    
    def get_size(self) -> Tuple[int, int]:
        """
        Retourne les dimensions du texte
        
        Returns:
            (largeur, hauteur) en pixels
        """
        return (self.rect.width, self.rect.height)
    
    def contains_point(self, x: int, y: int) -> bool:
        """
        Vérifie si un point est dans le rectangle du texte
        
        Args:
            x, y: Coordonnées du point
            
        Returns:
            True si le point est dans le texte
        """
        return self.rect.collidepoint(x, y)