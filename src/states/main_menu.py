"""
Модуль states/main_menu.py
Главное меню игры.

Содержит класс MainMenuState, который отвечает за отображение главного меню,
навигацию по пунктам и переход в другие состояния игры (карта или выход).
"""

import pygame
import sys
import os

# Добавляем корневую папку проекта в путь поиска для корректного импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState


class MainMenuState:
    """
    Состояние главного меню.

    Отображает заголовок игры и список пунктов меню.
    Позволяет пользователю перемещаться по пунктам (W/S/↑/↓) и выбирать (Enter).
    
    Пункты меню:
        0. "Новая игра" - переход в состояние EXPLORING (карта)
        1. "Выйти" - завершение игры
    """

    def __init__(self, game):
        """
        Инициализация главного меню.

        Аргументы:
            game: ссылка на главный объект Game (для доступа к change_state и running)
        """
        self.game = game

        # Шрифты для заголовка и пунктов меню
        self.font_title = pygame.font.Font(None, 72)   # крупный шрифт для заголовка
        self.font_items = pygame.font.Font(None, 48)   # средний шрифт для пунктов

        # Список пунктов меню
        self.menu_items = ["Новая игра", "Выйти"]

        # Индекс выбранного пункта (0 - первый пункт)
        self.selected = 0

    def handle_events(self, events):
        """
        Обработка событий в главном меню.

        Реагирует на нажатия клавиш:
            - UP / W     : перемещение вверх по меню
            - DOWN / S   : перемещение вниз по меню
            - ENTER      : выбор текущего пункта

        Аргументы:
            events: список событий Pygame
        """
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Навигация вверх
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self.selected = (self.selected - 1) % len(self.menu_items)

                # Навигация вниз
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self.selected = (self.selected + 1) % len(self.menu_items)

                # Выбор пункта
                elif event.key == pygame.K_RETURN:
                    if self.selected == 0:
                        # "Новая игра" - переходим в режим исследования карты
                        self.game.change_state(GameState.EXPLORING)
                    elif self.selected == 1:
                        # "Выйти" - завершаем игру
                        self.game.running = False

    def update(self, dt):
        """
        Обновление логики меню.

        В главном меню нет анимаций или движущихся элементов,
        поэтому метод пустой. Оставлен для единообразия интерфейса состояний.

        Аргументы:
            dt: время между кадрами (delta time) - не используется
        """
        pass

    def draw(self, screen):
        """
        Отрисовка главного меню.

        Рисует:
            - Чёрный фон
            - Заголовок "MATH RPG" в центре верхней части экрана
            - Пункты меню с подсветкой выбранного (жёлтый цвет)

        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
        # Заливка экрана чёрным цветом
        screen.fill((0, 0, 0))

        # Отрисовка заголовка
        title = self.font_title.render("MATH RPG", True, (255, 255, 255))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 150))
        screen.blit(title, title_rect)

        # Отрисовка пунктов меню
        for i, item in enumerate(self.menu_items):
            # Выбранный пункт подсвечивается жёлтым, остальные — белым
            color = (255, 255, 0) if i == self.selected else (255, 255, 255)

            text = self.font_items.render(item, True, color)
            text_rect = text.get_rect(center=(screen.get_width() // 2, 300 + i * 60))
            screen.blit(text, text_rect)