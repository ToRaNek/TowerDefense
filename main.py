# main.py
"""
Steam Defense - Tower Defense Steampunk 2D
Point d'entrée principal du jeu

Architecture: Python + Arcade
Auteur: Game Development Team
Version: 1.0
"""

import arcade
import sys
import os
from pathlib import Path

# Ajout du répertoire source au path Python
sys.path.append(str(Path(__file__).parent))

from core.game import Game
from core.state_manager import StateManager
from core.resource_manager import ResourceManager
from config.settings import SETTINGS


def main():
    """Point d'entrée principal de l'application"""
    try:
        # Initialisation d'Arcade
        arcade.open_window(
            SETTINGS['SCREEN_WIDTH'], 
            SETTINGS['SCREEN_HEIGHT'], 
            SETTINGS['SCREEN_TITLE']
        )
        
        # Configuration de l'antialiasing
        arcade.set_background_color(SETTINGS['BACKGROUND_COLOR'])
        
        # Initialisation du gestionnaire de ressources
        resource_manager = ResourceManager()
        resource_manager.preload_essential_resources()
        
        # Création et démarrage du jeu
        game = Game(resource_manager)
        
        # Lancement de la boucle principale
        game.run()
        
    except Exception as e:
        print(f"Erreur fatale lors du démarrage: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Nettoyage des ressources
        arcade.close_window()
    
    return 0


def check_system_requirements():
    """Vérifie la compatibilité système"""
    import platform
    
    system_info = {
        'os': platform.system(),
        'version': platform.version(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture()[0]
    }
    
    print(f"Steam Defense - Informations système:")
    print(f"OS: {system_info['os']} {system_info['version']}")
    print(f"Python: {system_info['python_version']}")
    print(f"Architecture: {system_info['architecture']}")
    
    # Vérifications minimales
    if system_info['python_version'] < '3.8':
        print("ATTENTION: Python 3.8+ recommandé")
        
    return True


def setup_logging():
    """Configure le système de logging"""
    import logging
    from datetime import datetime
    
    # Création du répertoire de logs s'il n'existe pas
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configuration du logging
    log_filename = f"steam_defense_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('SteamDefense')
    logger.info("=== STEAM DEFENSE - DÉMARRAGE ===")
    
    return logger


if __name__ == "__main__":
    # Configuration du logging
    logger = setup_logging()
    
    # Vérification système
    if not check_system_requirements():
        sys.exit(1)
    
    # Affichage du splash screen ASCII
    print("""
    ╔═══════════════════════════════════════╗
    ║         STEAM DEFENSE v1.0            ║
    ║     Tower Defense Steampunk 2D        ║
    ║                                       ║
    ║  ⚙️ Préparez vos défenses mécaniques  ║
    ║  🔧 L'invasion steampunk commence !   ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Lancement du jeu
    logger.info("Démarrage de Steam Defense...")
    exit_code = main()
    
    if exit_code == 0:
        logger.info("Steam Defense fermé proprement")
    else:
        logger.error(f"Steam Defense fermé avec erreur (code: {exit_code})")
    
    sys.exit(exit_code)