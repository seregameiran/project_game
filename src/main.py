"""
Точка входа в игру.
"""

import pygame
from core.game import Game

# Константы
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