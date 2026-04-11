"""
Точка входа в игру.
"""
import pygame
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game import Game

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 608

def main():
    """Запуск игры."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Billy's Adventure")
    
    game = Game(screen)
    game.run()

if __name__ == "__main__":
    main()