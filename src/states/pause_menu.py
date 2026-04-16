"""
Модуль states/pause_menu.py
Состояние меню паузы.

Содержит класс PauseMenuState, который отвечает за отображение меню паузы,
навигацию по пунктам и обработку выхода в главное меню.

Управление:
    LEFT / RIGHT    — переключение между кнопками "Да" и "Нет"
    ENTER           — подтверждение выбора
    ESC             — закрыть меню паузы и вернуться в игру
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.core.audio_manager import SoundType



class PauseMenuState:
    """
    Состояние меню паузы.

    Отображает полупрозрачное окно с вопросом "Вы уверены, что хотите выйти?"
    и двумя кнопками: "Да" и "Нет".
    Позволяет пользователю переключаться между кнопками (←/→) и выбирать (Enter).

    При выборе "Да" — возврат в главное меню.
    При выборе "Нет" — закрытие паузы и возврат в предыдущее состояние.
    При нажатии ESC — закрытие паузы и возврат в игру.

    Важно:
        Все поверхности создаются под виртуальный экран (800x608) через
        game.virtual_screen, чтобы корректно отображаться при масштабировании.
    """

    # Константы анимации и отображения
    FONT_SIZE_NORMAL = 32  # размер шрифта для обычного текста
    FONT_SIZE_BUTTON = 36  # размер шрифта для кнопок
    FONT_SIZE_SELECTED = 42  # размер шрифта для выбранной кнопки
    ANIM_SPEED = 8.0  # скорость анимации изменения размера шрифта

    # Размеры окна паузы (относительно виртуального экрана 800x608)
    BOX_WIDTH = 500
    BOX_HEIGHT = 200
    BUTTON_WIDTH = 120
    BUTTON_HEIGHT = 50
    BUTTON_SPACING = 40  # расстояние между кнопками

    def __init__(self, game):
        """
        Инициализация меню паузы.

        Загружает шрифты и создает поверхности для отображения.

        Аргументы:
            game: ссылка на главный объект Game
                  (для доступа к change_state, running и virtual_screen)
        """
        self.game = game

        # Используем виртуальный экран — все поверхности создаём под 800x608
        self.screen = game.virtual_screen

        # Путь к папке assets/menu
        self.menu_dir = os.path.join(
            os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))),
            "assets", "menu"
        )

        # Путь к шрифту
        self.font_path = os.path.join(self.menu_dir, "Compilance-Sans.ttf")

        # Кэш шрифтов по размеру
        self._font_cache: dict = {}

        # Текст вопроса и кнопки
        self.question_text = "Вы уверены, что хотите выйти?"
        self.options = ["Да", "Нет"]

        # Индекс выбранной кнопки (0 — "Да", 1 — "Нет")
        self.selected = 0

        # Текущие размеры шрифтов для кнопок (для плавной анимации)
        self.button_sizes = [float(self.FONT_SIZE_BUTTON)] * len(self.options)
        self.button_sizes[self.selected] = float(self.FONT_SIZE_SELECTED)

        # Полупрозрачная поверхность для затемнения экрана
        self.overlay = pygame.Surface((
            self.screen.get_width(),
            self.screen.get_height()
        ))
        self.overlay.set_alpha(180)  # 180 из 255 — сильное затемнение
        self.overlay.fill((0, 0, 0))

        # Поверхность для окна паузы (белый фон с рамкой)
        self.box_surface = pygame.Surface((self.BOX_WIDTH, self.BOX_HEIGHT))
        self.box_surface.fill((30, 30, 40))  # тёмно-серый фон

        # Рамка окна
        pygame.draw.rect(
            self.box_surface,
            (100, 100, 120),
            (0, 0, self.BOX_WIDTH, self.BOX_HEIGHT),
            3,
            border_radius=10
        )

        # Поверхности для кнопок (будут пересоздаваться при изменении размера)
        self.button_surfaces = {}

        # Сохраняем предыдущее состояние для возврата
        self.previous_state = None

        # Анимация появления
        self.appear_progress = 0.0
        self.appear_speed = 8.0

    def _get_font(self, size: int) -> pygame.font.Font:
        """
        Возвращает шрифт нужного размера из кэша.

        Создаёт объект шрифта только один раз для каждого размера,
        затем переиспользует его.

        Аргументы:
            size: размер шрифта в пикселях

        Возвращает:
            pygame.font.Font — объект шрифта нужного размера
        """
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.Font(self.font_path, size)
        return self._font_cache[size]

    def _update_button_surfaces(self):
        """Обновляет поверхности кнопок с текущими размерами шрифтов."""
        for i, option in enumerate(self.options):
            # Цвет: жёлтый для выбранной кнопки, белый для остальных
            color = (255, 255, 0) if i == self.selected else (255, 255, 255)

            font = self._get_font(int(self.button_sizes[i]))
            text = font.render(option, True, color)

            self.button_surfaces[i] = text

    def enter(self, previous_state):
        """
        Вход в состояние паузы.

        Сохраняет предыдущее состояние для возврата и сбрасывает анимацию.

        Аргументы:
            previous_state: состояние, из которого пришли (EXPLORING или BATTLE)
        """
        self.previous_state = previous_state
        self.selected = 1  # По умолчанию выбираем "Нет" (безопасный выбор)
        self.button_sizes = [float(self.FONT_SIZE_BUTTON)] * len(self.options)
        self.button_sizes[self.selected] = float(self.FONT_SIZE_SELECTED)
        self.appear_progress = 0.0
        self._update_button_surfaces()

    def handle_events(self, events):
        """
        Обработка событий в меню паузы.

        Реагирует на нажатия клавиш:
            LEFT / A   — переключение влево по кнопкам
            RIGHT / D  — переключение вправо по кнопкам
            ENTER      — подтверждение выбора
            ESC        — закрыть меню паузы

        Аргументы:
            events: список событий Pygame из pygame.event.get()
        """
        for event in events:
            if event.type == pygame.KEYDOWN:

                # ESC — закрыть паузу и вернуться в игру
                if event.key == pygame.K_ESCAPE:
                    self.game.audio.play_sound(SoundType.UI_BACK)
                    if self.previous_state:
                        self.game.change_state(self.previous_state)
                    return

                # Навигация влево
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    old_selected = self.selected
                    self.selected = (self.selected - 1) % len(self.options)
                    if self.selected != old_selected:
                        self.game.audio.play_sound(SoundType.UI_HOVER)
                    # Сбрасываем анимацию размера
                    for i in range(len(self.options)):
                        target = float(self.FONT_SIZE_SELECTED if i == self.selected
                                      else self.FONT_SIZE_BUTTON)
                        self.button_sizes[i] = target
                    self._update_button_surfaces()

                # Навигация вправо
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    old_selected = self.selected
                    self.selected = (self.selected + 1) % len(self.options)
                    if self.selected != old_selected:
                        self.game.audio.play_sound(SoundType.UI_HOVER)
                    for i in range(len(self.options)):
                        target = float(self.FONT_SIZE_SELECTED if i == self.selected
                                      else self.FONT_SIZE_BUTTON)
                        self.button_sizes[i] = target
                    self._update_button_surfaces()

                # Выбор текущей кнопки
                elif event.key == pygame.K_RETURN:
                    self.game.audio.play_sound(SoundType.UI_SELECT)
                    if self.selected == 0:
                        # "Да" — выходим в главное меню и сбрасываем прогресс,
                        # чтобы новая игра всегда стартовала с начала
                        self.game.reset_game()
                        self.game.change_state(GameState.MAIN_MENU)
                    else:
                        # "Нет" — возвращаемся в игру
                        if self.previous_state:
                            self.game.change_state(self.previous_state)

    def update(self, dt):
        """
        Обновление логики меню паузы.

        Обновляет анимацию появления и плавное изменение размера кнопок.

        Аргументы:
            dt: время прошедшее с прошлого кадра (секунд, delta time)
        """
        # Анимация появления (0.0 → 1.0)
        if self.appear_progress < 1.0:
            self.appear_progress += self.appear_speed * dt
            if self.appear_progress > 1.0:
                self.appear_progress = 1.0

        # Плавное изменение размера шрифтов кнопок
        for i in range(len(self.options)):
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
        Отрисовка меню паузы.

        Порядок отрисовки:
            1. Затемнённый overlay поверх всего экрана
            2. Окно паузы с вопросом и кнопками
            3. Анимация появления (fade-in)

        Аргументы:
            screen: виртуальная поверхность Pygame 800x608 для отрисовки
                    (передаётся из game.run() как virtual_screen)
        """
        # Сначала рисуем предыдущее состояние (игру) размытым/затемнённым
        if self.previous_state:
            # Получаем состояние и рисуем его
            state_obj = self.game.states.get(self.previous_state)
            if state_obj and hasattr(state_obj, 'draw_world'):
                # Для ExploringState — рисуем мир без UI
                state_obj.draw_world(screen)
            elif state_obj and hasattr(state_obj, 'draw'):
                # Для других состояний (BATTLE) — рисуем как обычно
                # Но в бою пауза будет обрабатываться отдельно
                pass

        # Затемняющий overlay
        screen.blit(self.overlay, (0, 0))

        # Вычисляем позицию окна (центр экрана)
        box_x = (screen.get_width() - self.BOX_WIDTH) // 2
        box_y = (screen.get_height() - self.BOX_HEIGHT) // 2

        # Применяем анимацию появления (масштабирование)
        if self.appear_progress < 1.0:
            scale = 0.5 + self.appear_progress * 0.5
            scaled_width = int(self.BOX_WIDTH * scale)
            scaled_height = int(self.BOX_HEIGHT * scale)
            scaled_box = pygame.transform.scale(self.box_surface, (scaled_width, scaled_height))
            box_x = (screen.get_width() - scaled_width) // 2
            box_y = (screen.get_height() - scaled_height) // 2
            screen.blit(scaled_box, (box_x, box_y))
        else:
            screen.blit(self.box_surface, (box_x, box_y))

        # Рисуем текст вопроса
        font_normal = self._get_font(self.FONT_SIZE_NORMAL)
        alpha = int(255 * self.appear_progress)
        question_surf = font_normal.render(self.question_text, True, (255, 255, 255))
        question_surf.set_alpha(alpha)
        question_rect = question_surf.get_rect(
            center=(screen.get_width() // 2, box_y + 60)
        )
        screen.blit(question_surf, question_rect)

        # Рисуем кнопки
        buttons_y = box_y + self.BOX_HEIGHT - 70
        total_buttons_width = (self.BUTTON_WIDTH * len(self.options) +
                               self.BUTTON_SPACING * (len(self.options) - 1))
        start_x = (screen.get_width() - total_buttons_width) // 2

        for i, option in enumerate(self.options):
            button_surf = self.button_surfaces.get(i)
            if button_surf:
                button_surf.set_alpha(alpha)
                button_rect = button_surf.get_rect(
                    center=(start_x + self.BUTTON_WIDTH // 2 +
                            i * (self.BUTTON_WIDTH + self.BUTTON_SPACING),
                            buttons_y)
                )
                screen.blit(button_surf, button_rect)

                # Рисуем рамку вокруг кнопки если она выбрана
                if i == self.selected and self.appear_progress >= 1.0:
                    pygame.draw.rect(
                        screen,
                        (255, 255, 0),
                        (button_rect.x - 10, button_rect.y - 5,
                         button_rect.width + 20, button_rect.height + 10),
                        2,
                        border_radius=5
                    )