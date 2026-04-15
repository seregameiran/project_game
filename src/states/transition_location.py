"""
Модуль states/transition_location.py
Состояние перехода между локациями.

Показывает диалог подтверждения перехода на следующую локацию.
При выборе "Да" — загружает следующую локацию и возвращает в EXPLORING.
При выборе "Нет" — возвращает в EXPLORING без перехода.

Управление:
    LEFT / RIGHT — переключение между "Да" и "Нет"
    ENTER        — подтверждение выбора
    ESC          — отмена, возврат в EXPLORING
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.core.audio_manager import SoundType


class TransitionLocationState:
    """
    Состояние перехода между локациями.

    Отображает полупрозрачное окно поверх карты с вопросом
    "Вы уверены, что хотите перейти на следующую локацию?"
    и двумя кнопками: "Да" и "Нет".

    Важно:
        Все поверхности создаются под виртуальный экран (800x608).
    """

    # Константы шрифтов
    FONT_SIZE_QUESTION = 28
    FONT_SIZE_BUTTON   = 36
    FONT_SIZE_SELECTED = 44
    ANIM_SPEED         = 8.0

    # Размеры окна
    BOX_WIDTH   = 540
    BOX_HEIGHT  = 180
    BUTTON_WIDTH   = 120
    BUTTON_SPACING = 60

    # Константы анимации затемнения
    FADE_SPEED = 3.0  # Скорость затемнения (секунды на полный цикл)
    FADE_STEPS = 255   # Максимальная альфа (полностью черный)

    def __init__(self, game):
        """
        Инициализация состояния перехода.

        Аргументы:
            game: ссылка на главный объект Game
        """
        self.game   = game
        self.screen = game.virtual_screen

        # Путь к шрифту
        menu_dir = os.path.join(
            os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))),
            "assets", "menu"
        )
        self.font_path = os.path.join(menu_dir, "Compilance-Sans.ttf")

        # Кеш шрифтов
        self._font_cache: dict = {}

        # Пункты выбора: 0 — "Да", 1 — "Нет"
        self.options  = ["Да", "Нет"]
        self.selected = 1  # по умолчанию "Нет" — безопасный выбор

        # Состояние анимации затемнения:
        # None - нет анимации, "fade_out" - затемнение, "fade_in" - осветление
        self.fade_state = None
        self.fade_alpha = 0  # Текущая прозрачность (0 = прозрачный, 255 = черный)

        # Поверхность для затемнения
        self.fade_surface = pygame.Surface((
            self.screen.get_width(),
            self.screen.get_height()
        ))
        self.fade_surface.fill((0, 0, 0))

        # Размеры шрифтов кнопок для анимации
        self.button_sizes = [float(self.FONT_SIZE_BUTTON)] * 2
        self.button_sizes[self.selected] = float(self.FONT_SIZE_SELECTED)

        # Данные перехода (dict из map_renderer) — задаются через enter()
        self.transition_data = None

        # Анимация появления
        self.appear_progress = 0.0
        self.appear_speed    = 6.0

        # Полупрозрачный overlay
        self.overlay = pygame.Surface((
            self.screen.get_width(),
            self.screen.get_height()
        ))
        self.overlay.set_alpha(160)
        self.overlay.fill((0, 0, 0))

        # Фон окна
        self.box_surface = pygame.Surface(
            (self.BOX_WIDTH, self.BOX_HEIGHT),
            pygame.SRCALPHA
        )
        pygame.draw.rect(
            self.box_surface,
            (20, 20, 30, 230),
            (0, 0, self.BOX_WIDTH, self.BOX_HEIGHT),
            border_radius=12
        )
        pygame.draw.rect(
            self.box_surface,
            (100, 100, 130, 255),
            (0, 0, self.BOX_WIDTH, self.BOX_HEIGHT),
            2,
            border_radius=12
        )

        # Поверхности для кнопок
        self.button_surfaces = {}

    def _get_font(self, size: int) -> pygame.font.Font:
        """
        Возвращает шрифт нужного размера из кеша.

        Аргументы:
            size: размер шрифта в пикселях

        Возвращает:
            pygame.font.Font
        """
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.Font(self.font_path, size)
        return self._font_cache[size]

    def _update_button_surfaces(self):
        """Обновляет поверхности кнопок с текущими размерами шрифтов."""
        for i, option in enumerate(self.options):
            color = (255, 255, 0) if i == self.selected else (255, 255, 255)
            font = self._get_font(int(self.button_sizes[i]))
            text = font.render(option, True, color)
            self.button_surfaces[i] = text

    def enter(self, transition_data):
        """
        Вход в состояние перехода.

        Сохраняет данные перехода и сбрасывает анимацию.

        Аргументы:
            transition_data: dict с ключами tmx_path, spawn_x, spawn_y
                             (возвращается из map_renderer.check_transition)
        """
        self.transition_data  = transition_data
        self.selected         = 1  # по умолчанию "Нет"
        self.appear_progress  = 0.0
        self.button_sizes     = [float(self.FONT_SIZE_BUTTON)] * 2
        self.button_sizes[self.selected] = float(self.FONT_SIZE_SELECTED)
        self._update_button_surfaces()

        self.fade_state = None
        self.fade_alpha = 0

    def handle_events(self, events):
        """
        Обработка событий.

        Реагирует на:
            LEFT / A  — переключить на "Да"
            RIGHT / D — переключить на "Нет"
            ENTER     — подтвердить выбор
            ESC       — отмена, вернуться в EXPLORING

        Аргументы:
            events: список событий Pygame
        """
        if self.fade_state is not None:
            return

        for event in events:
            if event.type == pygame.KEYDOWN:

                # Отмена (ESC)
                if event.key == pygame.K_ESCAPE:
                    self.game.audio.play_sound(SoundType.UI_BACK)
                    self.game.change_state(GameState.EXPLORING)
                    return

                # Навигация влево — "Да"
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if self.selected != 0:
                        self.game.audio.play_sound(SoundType.UI_HOVER)
                    self.selected = 0
                    self.button_sizes = [float(self.FONT_SIZE_SELECTED),
                                         float(self.FONT_SIZE_BUTTON)]
                    self._update_button_surfaces()

                # Навигация вправо — "Нет"
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if self.selected != 1:
                        self.game.audio.play_sound(SoundType.UI_HOVER)
                    self.selected = 1
                    self.button_sizes = [float(self.FONT_SIZE_BUTTON),
                                         float(self.FONT_SIZE_SELECTED)]
                    self._update_button_surfaces()

                # Подтверждение
                elif event.key == pygame.K_RETURN:
                    self.game.audio.play_sound(SoundType.UI_SELECT)
                    if self.selected == 0 and self.transition_data:
                        self.game.audio.play_sound(SoundType.TRANSITION)
                        # ТОЛЬКО начинаем анимацию затемнения
                        self.fade_state = "fade_out"
                        self.fade_alpha = 0
                        # НЕ загружаем локацию и НЕ переключаем состояние здесь!
                    else:
                        # "Нет" — возвращаемся без перехода
                        self.game.change_state(GameState.EXPLORING)

    def _perform_transition(self):
        """
        Выполняет фактическую загрузку новой локации.
        Вызывается после полного затемнения экрана.
        """
        if not self.transition_data:
            return

        print(f"Выполнение перехода на локацию: {self.transition_data.get('tmx_path', 'unknown')}")

        exploring = self.game.states.get(GameState.EXPLORING)
        if exploring:
            exploring.load_location_from_tmx(self.transition_data)

            # ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ КАМЕРУ СРАЗУ
            if exploring.player and exploring.camera:
                exploring.camera.follow(exploring.player.rect)

        # Очищаем данные перехода
        self.transition_data = None

    def update(self, dt):
        """
        Обновление анимации затемнения и появления UI.

        Аргументы:
            dt: delta time в секундах
        """
        # Анимация появления UI (только когда нет анимации затемнения)
        if self.fade_state is None and self.appear_progress < 1.0:
            self.appear_progress += self.appear_speed * dt
            if self.appear_progress > 1.0:
                self.appear_progress = 1.0

        # Анимация затемнения/осветления
        if self.fade_state == "fade_out":
            # Затемнение экрана
            self.fade_alpha += int(self.FADE_SPEED * 255 * dt)

            if self.fade_alpha >= self.FADE_STEPS:
                self.fade_alpha = self.FADE_STEPS
                # Затемнение завершено — загружаем новую локацию
                self._perform_transition()  # <-- ВЫЗЫВАЕМ ЗДЕСЬ
                # Начинаем осветление
                self.fade_state = "fade_in"

        elif self.fade_state == "fade_in":
            # Осветление экрана
            self.fade_alpha -= int(self.FADE_SPEED * 255 * dt)

            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.fade_state = None  # Анимация завершена
                # Возвращаемся в состояние исследования
                self.game.change_state(GameState.EXPLORING)  # <-- ПЕРЕКЛЮЧАЕМСЯ ЗДЕСЬ

        # Плавное изменение размера кнопок (только когда нет анимации затемнения)
        if self.fade_state is None:
            for i in range(2):
                target = float(self.FONT_SIZE_SELECTED if i == self.selected
                               else self.FONT_SIZE_BUTTON)
                diff = target - self.button_sizes[i]
                if abs(diff) > 0.5:
                    self.button_sizes[i] += diff * self.ANIM_SPEED * dt
                else:
                    self.button_sizes[i] = target
            self._update_button_surfaces()

    def draw(self, screen):
        """
        Отрисовка состояния перехода.

        Порядок:
            1. Карта под окном (через exploring.draw_world)
            2. Полупрозрачный overlay
            3. Окно с вопросом и кнопками

        Аргументы:
            screen: виртуальная поверхность 800x608
        """
        # Рисуем карту под окном
        exploring = self.game.states.get(GameState.EXPLORING)
        if exploring and hasattr(exploring, 'draw_world'):
            exploring.draw_world(screen)

        # Если идет анимация затемнения/осветления, показываем затемнение поверх всего
        if self.fade_state is not None:
            if self.fade_alpha > 0:
                self.fade_surface.set_alpha(self.fade_alpha)
                screen.blit(self.fade_surface, (0, 0))
            return

            # Затемняющий overlay
        screen.blit(self.overlay, (0, 0))

        alpha = int(255 * self.appear_progress)

        # Позиция окна — по центру экрана
        box_x = (screen.get_width()  - self.BOX_WIDTH)  // 2
        box_y = (screen.get_height() - self.BOX_HEIGHT) // 2

        # Рисуем фон окна
        box_copy = self.box_surface.copy()
        box_copy.set_alpha(alpha)
        screen.blit(box_copy, (box_x, box_y))

        # Вопрос (первая строка)
        font_q = self._get_font(self.FONT_SIZE_QUESTION)
        question = font_q.render(
            "Вы уверены, что хотите перейти на",
            True, (255, 255, 255)
        )
        question.set_alpha(alpha)
        screen.blit(question, question.get_rect(
            center=(screen.get_width() // 2, box_y + 50)
        ))

        # Вопрос (вторая строка)
        question2 = font_q.render(
            "следующую локацию?",
            True, (255, 255, 255)
        )
        question2.set_alpha(alpha)
        screen.blit(question2, question2.get_rect(
            center=(screen.get_width() // 2, box_y + 85)
        ))

        # Кнопки "Да" и "Нет"
        buttons_y  = box_y + self.BOX_HEIGHT - 45
        total_w    = self.BUTTON_WIDTH * 2 + self.BUTTON_SPACING
        start_x    = (screen.get_width() - total_w) // 2

        for i, option in enumerate(self.options):
            button_surf = self.button_surfaces.get(i)
            if button_surf:
                button_surf.set_alpha(alpha)
                rect = button_surf.get_rect(
                    center=(start_x + self.BUTTON_WIDTH // 2 +
                            i * (self.BUTTON_WIDTH + self.BUTTON_SPACING),
                            buttons_y)
                )
                screen.blit(button_surf, rect)

                # Рамка вокруг выбранной кнопки
                if i == self.selected and self.appear_progress >= 1.0:
                    pygame.draw.rect(
                        screen, (255, 255, 0),
                        (rect.x - 8, rect.y - 4,
                         rect.width + 16, rect.height + 8),
                        2, border_radius=5
                    )