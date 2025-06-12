# config/settings.py
"""
Steam Defense - Configuration globale du jeu
Centralise tous les paramètres configurables
"""

import arcade
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CONFIGURATION ÉCRAN ET FENÊTRE
# ═══════════════════════════════════════════════════════════

SETTINGS = {
    # Dimensions de l'écran
    'SCREEN_WIDTH': 1280,
    'SCREEN_HEIGHT': 720,
    'SCREEN_TITLE': "Steam Defense - Tower Defense Steampunk",
    
    # Configuration de rendu
    'TARGET_FPS': 60,
    'VSYNC': True,
    'ANTIALIASING': True,
    'FULLSCREEN': False,
    
    # Couleurs de base (steampunk)
    'BACKGROUND_COLOR': arcade.color.DARK_SLATE_GRAY,
}

# ═══════════════════════════════════════════════════════════
# PALETTE STEAMPUNK
# ═══════════════════════════════════════════════════════════

class SteampunkColors:
    """Palette de couleurs thématiques steampunk"""
    
    # Métaux primaires
    BRONZE = (205, 127, 50)          # #CD7F32
    COPPER = (184, 115, 51)          # #B87333  
    BRASS = (225, 193, 110)          # #E1C16E
    IRON = (71, 71, 71)              # #474747
    STEEL = (112, 128, 144)          # #708090
    DARK_STEEL = (34, 38, 49)
    
    # Accent colors
    RUST = (183, 65, 14)             # #B7410E
    VERDIGRIS = (67, 121, 107)       # #43796B
    GOLD = (255, 191, 0)             # #FFBF00
    
    # Éléments fonctionnels
    STEAM_WHITE = (248, 248, 255)    # #F8F8FF
    FIRE_ORANGE = (255, 140, 0)      # #FF8C00
    ELECTRIC_BLUE = (30, 144, 255)   # #1E90FF
    
    # Interface
    UI_BRONZE_DARK = (139, 69, 19)   # #8B4513
    UI_BRONZE_LIGHT = (244, 164, 96) # #F4A460
    TEXT_GOLD = (255, 215, 0)        # #FFD700
    TEXT_DARK = (47, 79, 79)         # #2F4F4F

# ═══════════════════════════════════════════════════════════
# CONFIGURATION DE LA GRILLE DE JEU
# ═══════════════════════════════════════════════════════════

GRID_CONFIG = {
    # Dimensions de la grille
    'GRID_WIDTH': 24,        # Nombre de colonnes
    'GRID_HEIGHT': 16,       # Nombre de lignes
    'TILE_SIZE': 32,         # Taille d'une tuile en pixels
    
    # Types de tuiles
    'TILE_TYPES': {
        'EMPTY': 0,          # Vide/constructible
        'PATH': 1,           # Chemin pour ennemis
        'WALL': 2,           # Obstacle
        'SPAWN': 3,          # Point d'apparition
        'BASE': 4,           # Base à défendre
        'DECORATION': 5      # Élément décoratif
    },
    
    # Contraintes de génération
    'MIN_PATH_LENGTH': 40,   # Longueur minimale du chemin
    'MAX_PATH_LENGTH': 60,   # Longueur maximale du chemin
    'PATH_WIDTH': 2,         # Largeur du chemin
    'MIN_PLACEMENT_ZONES': 8 # Zones de placement minimum
}

# ═══════════════════════════════════════════════════════════
# ÉQUILIBRAGE DU GAMEPLAY
# ═══════════════════════════════════════════════════════════

GAMEPLAY_BALANCE = {
    # Ressources de départ
    'STARTING_MONEY': 150,
    'STARTING_LIVES': 20,
    
    # Système de vagues
    'WAVE_SETTINGS': {
        'PREPARATION_TIME': 10.0,    # Temps entre les vagues (secondes)
        'SPAWN_INTERVAL_BASE': 1.0,  # Intervalle de spawn de base
        'DIFFICULTY_SCALING': 1.15,  # Multiplicateur de difficulté par vague
        'MAX_ENEMIES_PER_WAVE': 50   # Maximum d'ennemis par vague
    },
    
    # Économie
    'ECONOMY': {
        'KILL_BONUS_MULTIPLIER': 1.0,     # Multiplicateur de récompense
        'INTEREST_RATE': 0.02,             # Intérêts sur l'argent en banque
        'TOWER_SELL_RATIO': 0.7            # Ratio de revente des tours
    }
}

# ═══════════════════════════════════════════════════════════
# CONFIGURATION AUDIO
# ═══════════════════════════════════════════════════════════

AUDIO_CONFIG = {
    # Volumes (0.0 à 1.0)
    'MASTER_VOLUME': 0.8,
    'MUSIC_VOLUME': 0.6,
    'SFX_VOLUME': 0.8,
    'UI_VOLUME': 0.5,
    
    # Paramètres techniques
    'AUDIO_FREQUENCY': 44100,
    'AUDIO_CHANNELS': 2,
    'AUDIO_BUFFER': 1024,
    
    # Distance pour l'audio spatialisé
    'MAX_AUDIO_DISTANCE': 500,
    'AUDIO_ROLLOFF': 0.5
}

# ═══════════════════════════════════════════════════════════
# CONFIGURATION DES EFFETS VISUELS
# ═══════════════════════════════════════════════════════════

VISUAL_EFFECTS = {
    # Particules
    'MAX_PARTICLES': 500,
    'PARTICLE_LIFETIME': 3.0,
    
    # Animation de vapeur
    'STEAM_DENSITY': 0.3,
    'STEAM_VELOCITY': (0, 50),
    'STEAM_FADE_TIME': 2.0,
    
    # Effets d'explosion
    'EXPLOSION_PARTICLES': 20,
    'EXPLOSION_SPREAD': 64,
    
    # Éclairs électriques
    'LIGHTNING_SEGMENTS': 8,
    'LIGHTNING_JITTER': 16,
    'LIGHTNING_DURATION': 0.3
}

# ═══════════════════════════════════════════════════════════
# CONFIGURATION DE PERFORMANCE
# ═══════════════════════════════════════════════════════════

PERFORMANCE = {
    # Limits pour optimisation
    'MAX_PROJECTILES': 200,
    'MAX_ENEMIES_ON_SCREEN': 100,
    'MAX_TOWERS': 50,
    
    # Culling et LOD
    'CULLING_MARGIN': 100,       # Marge pour le culling en pixels
    'LOD_DISTANCE_1': 200,       # Distance pour LOD niveau 1
    'LOD_DISTANCE_2': 400,       # Distance pour LOD niveau 2
    
    # Cache
    'SPRITE_CACHE_SIZE': 100,    # Nombre de sprites en cache
    'TEXTURE_CACHE_SIZE': 50     # Nombre de textures en cache
}

# ═══════════════════════════════════════════════════════════
# CONFIGURATION DEBUG
# ═══════════════════════════════════════════════════════════

DEBUG_CONFIG = {
    # Flags de debug
    'SHOW_FPS': False,
    'SHOW_GRID': False,
    'SHOW_PATHFINDING': False,
    'SHOW_COLLISION_BOXES': False,
    'SHOW_TOWER_RANGES': False,
    
    # Debug visuel
    'DEBUG_COLORS': {
        'GRID': arcade.color.WHITE,
        'PATH': arcade.color.GREEN,
        'COLLISION': arcade.color.RED,
        'RANGE': arcade.color.YELLOW
    },
    
    # Performance monitoring
    'PROFILE_PERFORMANCE': False,
    'LOG_FRAME_TIME': False
}

# ═══════════════════════════════════════════════════════════
# CHEMINS DES RESSOURCES
# ═══════════════════════════════════════════════════════════

class ResourcePaths:
    """Chemins vers les différentes ressources du jeu"""
    
    BASE_DIR = Path(__file__).parent.parent
    ASSETS_DIR = BASE_DIR / "assets"
    
    # Dossiers de ressources
    FONTS_DIR = ASSETS_DIR / "fonts"
    AUDIO_DIR = ASSETS_DIR / "audio"
    DATA_DIR = ASSETS_DIR / "data"
    
    # Fichiers de configuration
    ENEMIES_CONFIG = DATA_DIR / "enemies.json"
    TOWERS_CONFIG = DATA_DIR / "towers.json"
    WAVES_CONFIG = DATA_DIR / "waves.json"
    
    # Logs
    LOGS_DIR = BASE_DIR / "logs"

# ═══════════════════════════════════════════════════════════
# VALIDATION DE LA CONFIGURATION
# ═══════════════════════════════════════════════════════════

def validate_settings():
    """Valide la cohérence de la configuration"""
    errors = []
    
    # Vérification des dimensions d'écran
    if SETTINGS['SCREEN_WIDTH'] < 800 or SETTINGS['SCREEN_HEIGHT'] < 600:
        errors.append("Résolution trop faible (minimum 800x600)")
    
    # Vérification de la grille
    total_tiles = GRID_CONFIG['GRID_WIDTH'] * GRID_CONFIG['GRID_HEIGHT']
    if total_tiles > 1000:
        errors.append("Grille trop grande (performance)")
    
    # Vérification des volumes audio
    for key, value in AUDIO_CONFIG.items():
        if key.endswith('_VOLUME') and not (0.0 <= value <= 1.0):
            errors.append(f"Volume {key} invalide: {value}")
    
    return errors

# ═══════════════════════════════════════════════════════════
# INITIALISATION
# ═══════════════════════════════════════════════════════════

# Validation automatique au chargement
_validation_errors = validate_settings()
if _validation_errors:
    print("ERREURS DE CONFIGURATION:")
    for error in _validation_errors:
        print(f"  - {error}")
    
# Création des dossiers nécessaires
ResourcePaths.LOGS_DIR.mkdir(exist_ok=True)
ResourcePaths.ASSETS_DIR.mkdir(exist_ok=True)