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
        0. "Начать игру" - переход в состояние EXPLORING (карта)
        1. "Выйти" - завершение игры

    Анимации:
        - Fade-in: меню плавно появляется из чёрного экрана
        - Заголовок "Billy's Adventure" падает сверху вниз
        - "Начать игру" выезжает справа налево
        - "Выйти" выезжает слева направо
        - Выбранный пункт плавно увеличивается в размере
    """

    def __init__(self, game):
        """
        Инициализация главного меню.

        Аргументы:
            game: ссылка на главный объект Game (для доступа к change_state и running)
        """
        self.game = game

        # Путь к папке assets/menu
        self.menu_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "assets", "menu")

        # Путь к шрифту
        self.font_path = os.path.join(self.menu_dir, "Compilance-Sans.ttf")

        # Шрифт для заголовка (фиксированный)
        self.font_title = pygame.font.Font(self.font_path, 72)

        # Список пунктов меню
        self.menu_items = ["Начать игру", "Выйти"]

        # Индекс выбранного пункта (0 - первый пункт)
        self.selected = 0

        # Текущие размеры шрифтов для каждого пункта (для плавной анимации)
        self.item_sizes = [48.0] * len(self.menu_items)
        self.item_sizes[0] = 62.0  # первый выбран по умолчанию

        # Скорость анимации размера
        self.anim_speed = 8.0

        # --- АНИМАЦИЯ ПОЯВЛЕНИЯ (FADE-IN + SLIDE-IN) ---
        self.appear_progress = 0.0      # 0 = не видно, 1 = полностью видно
        self.appear_speed = 1.5         # скорость появления (чем выше, тем быстрее)

        # Смещение для заголовка (падает сверху)
        self.title_offset = -200        # начинаем за верхним краем экрана

        # Разные смещения для slide-in
        self.start_game_offset = 300    # "Начать игру" выезжает справа
        self.exit_offset = -300         # "Выйти" выезжает слева

        # Поверхность для затемнения (fade-in)
        self.fade_surface = pygame.Surface((self.game.screen.get_width(), 
                                            self.game.screen.get_height()))
        self.fade_surface.fill((0, 0, 0))

        # Загружаем фоновое изображение
        bg_path = os.path.join(self.menu_dir, "image.png")
        bg = pygame.image.load(bg_path)
        self.bg = pygame.transform.scale(bg, (self.game.screen.get_width(), 
                                               self.game.screen.get_height()))

        # Создаём затемняющий слой поверх фона (постоянный)
        self.overlay = pygame.Surface((self.game.screen.get_width(), 
                                        self.game.screen.get_height()))
        self.overlay.set_alpha(100)  # прозрачность 0-255, 100 = лёгкое затемнение
        self.overlay.fill((0, 0, 0))

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
        # Блокируем управление, пока анимация появления не завершена
        if self.appear_progress < 1.0:
            return

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
                        # "Начать игру" - переходим в режим исследования карты
                        self.game.change_state(GameState.EXPLORING)
                    elif self.selected == 1:
                        # "Выйти" - завершаем игру
                        self.game.running = False

    def update(self, dt):
        """
        Обновление логики меню.

        Плавно меняет размер шрифтов пунктов меню при переключении.
        Обновляет анимацию появления (fade-in + slide-in).

        Аргументы:
            dt: время между кадрами (delta time)
        """
        # --- АНИМАЦИЯ ПОЯВЛЕНИЯ ---
        if self.appear_progress < 1.0:
            self.appear_progress += self.appear_speed * dt
            if self.appear_progress > 1.0:
                self.appear_progress = 1.0

        # Обновляем смещение для заголовка (падает сверху)
        # От -200 до 120
        self.title_offset = int(-200 + 320 * self.appear_progress)
        if self.title_offset > 120:
            self.title_offset = 120

        # Обновляем смещения для slide-in (разные направления)
        self.start_game_offset = int(300 * (1.0 - self.appear_progress))
        self.exit_offset = int(-300 * (1.0 - self.appear_progress))

        # --- АНИМАЦИЯ РАЗМЕРА ПУНКТОВ МЕНЮ ---
        for i in range(len(self.menu_items)):
            # Целевой размер — крупный для выбранного, обычный для остальных
            target = 62.0 if i == self.selected else 48.0

            # Плавно двигаемся к целевому размеру
            diff = target - self.item_sizes[i]
            self.item_sizes[i] += diff * self.anim_speed * dt

    def draw(self, screen):
        """
        Отрисовка главного меню.

        Рисует:
            - Фоновое изображение на весь экран
            - Полупрозрачное затемнение поверх фона
            - Заголовок "Billy's Adventure" с анимацией падения сверху
            - Пункт "Начать игру" с анимацией выезжания справа налево
            - Пункт "Выйти" с анимацией выезжания слева направо
            - Выбранный пункт подсвечивается жёлтым цветом и увеличивается

        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
        # Фоновое изображение
        screen.blit(self.bg, (0, 0))

        # Полупрозрачное затемнение поверх фона
        screen.blit(self.overlay, (0, 0))

        # --- ВЫЧИСЛЯЕМ ПРОЗРАЧНОСТЬ ДЛЯ FADE-IN ---
        alpha = int(255 * self.appear_progress)

        # --- ЗАГОЛОВОК (падает сверху + fade-in) ---
        title = self.font_title.render("Billy's Adventure", True, (255, 255, 255))
        title.set_alpha(alpha)
        title_rect = title.get_rect(center=(screen.get_width() // 2, self.title_offset))
        screen.blit(title, title_rect)

        # --- ПУНКТЫ МЕНЮ (с fade-in + slide-in) ---
        for i, item in enumerate(self.menu_items):
            # Выбранный пункт — жёлтый, остальные — белые
            color = (255, 255, 0) if i == self.selected else (255, 255, 255)

            # Создаём шрифт с текущим анимированным размером
            font = pygame.font.Font(self.font_path, int(self.item_sizes[i]))

            text = font.render(item, True, color)
            text.set_alpha(alpha)

            # Разные координаты для каждого пункта
            if i == 0:  # "Начать игру" — выезжает справа налево
                x = screen.get_width() // 2 + self.start_game_offset
                y = 320
            else:       # "Выйти" — выезжает слева направо
                x = screen.get_width() // 2 + self.exit_offset
                y = 400

            text_rect = text.get_rect(center=(x, y))
            screen.blit(text, text_rect)

        # --- ЗАТЕМНЕНИЕ ДЛЯ FADE-IN (поверх всего в начале) ---
        if self.appear_progress < 1.0:
            # Чем ближе к 1, тем прозрачнее чёрный слой
            fade_alpha = int(255 * (1.0 - self.appear_progress))
            self.fade_surface.set_alpha(fade_alpha)
            screen.blit(self.fade_surface, (0, 0))