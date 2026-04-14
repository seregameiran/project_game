"""
Точка входа в игру.
"""
import pygame
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game import Game

# Базовое (виртуальное) разрешение — вся логика работает в этих координатах
VIRTUAL_WIDTH  = 800
VIRTUAL_HEIGHT = 608

def main():
    """Запуск игры."""
    pygame.init()

    # Получаем реальное разрешение монитора
    info = pygame.display.Info()
    SCREEN_WIDTH  = info.current_w
    SCREEN_HEIGHT = info.current_h

    # На Маке используем обычное окно без NOFRAME
    # На Windows используем NOFRAME для полноэкранного вида
    if sys.platform == "darwin":
        # Mac: обычное окно максимального размера
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.RESIZABLE
        )
    else:
        # Windows/Linux: без рамки на весь экран
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.NOFRAME
        )

    pygame.display.set_caption("Billy's Adventure")

    # Виртуальная поверхность — вся игра рисуется сюда в 800x608
    virtual_screen = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

    game = Game(screen, virtual_screen, SCREEN_WIDTH, SCREEN_HEIGHT)
    game.run()

if __name__ == "__main__":
    main()