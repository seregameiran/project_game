"""
Модуль states/main_menu.py
Главное меню игры.

Содержит класс MainMenuState, который отвечает за отображение главного меню,
навигацию по пунктам и переход в другие состояния игры (карта или выход).

Все размеры и поверхности создаются под виртуальный экран (800x608),
чтобы корректно отображаться при масштабировании на реальный монитор.
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.core.audio_manager import SoundType



class MainMenuState:
    """
    Состояние главного меню.

    Отображает заголовок игры и список пунктов меню.
    Позволяет пользователю перемещаться по пунктам (W/S/↑/↓) и выбирать (Enter).

    Пункты меню:
        0. "Начать игру" - переход в состояние EXPLORING (карта)
        1. "Выйти"       - завершение игры

    Анимации:
        - Fade-in: меню плавно появляется из чёрного экрана
        - Заголовок "Billy's Adventure" падает сверху вниз
        - "Начать игру" выезжает справа налево
        - "Выйти" выезжает слева направо
        - Выбранный пункт плавно увеличивается в размере

    Важно:
        Все поверхности создаются под виртуальный экран (800x608) через
        game.virtual_screen, а не под реальный game.screen — иначе при
        масштабировании на монитор фон и overlay будут неправильного размера.
    """

    # Константы анимации
    FONT_SIZE_NORMAL   = 48     # размер шрифта для невыбранного пункта
    FONT_SIZE_SELECTED = 62     # размер шрифта для выбранного пункта
    ANIM_SPEED         = 8.0    # скорость анимации изменения размера шрифта
    APPEAR_SPEED       = 1.5    # скорость анимации появления (fade-in)
    TITLE_SLIDE_FROM   = -200   # начальное смещение заголовка (за верхним краем)
    TITLE_SLIDE_TO     = 120    # конечное смещение заголовка (Y позиция)
    ITEM_SLIDE_DIST    = 300    # дистанция slide-in для пунктов меню
    MENU_Y_START       = 320    # Y позиция первого пункта меню
    MENU_Y_STEP        = 80     # расстояние между пунктами меню по Y

    def __init__(self, game):
        """
        Инициализация главного меню.

        Загружает шрифты и фоновое изображение под размер виртуального
        экрана (800x608). Инициализирует параметры анимации появления.

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

        # Шрифт для заголовка (фиксированный размер)
        self.font_title = pygame.font.Font(self.font_path, 72)

        # Кеш шрифтов по размеру — создаём шрифт один раз для каждого размера
        # вместо создания нового объекта каждый кадр в draw()
        self._font_cache: dict = {}

        # Список пунктов меню
        self.menu_items = ["Начать игру", "Выйти"]

        # Индекс выбранного пункта (0 — первый пункт)
        self.selected = 0

        # Текущие размеры шрифтов для каждого пункта (для плавной анимации)
        self.item_sizes = [float(self.FONT_SIZE_NORMAL)] * len(self.menu_items)
        self.item_sizes[0] = float(self.FONT_SIZE_SELECTED)  # первый выбран по умолчанию

        # --- АНИМАЦИЯ ПОЯВЛЕНИЯ (FADE-IN + SLIDE-IN) ---

        # Прогресс анимации появления: 0.0 = не видно, 1.0 = полностью видно
        self.appear_progress = 0.0

        # Текущее смещение заголовка по Y (анимация падения сверху)
        self.title_offset = self.TITLE_SLIDE_FROM

        # Текущие смещения пунктов меню по X (анимация выезжания)
        # "Начать игру" — выезжает справа (положительное смещение)
        # "Выйти"       — выезжает слева (отрицательное смещение)
        self.start_game_offset = self.ITEM_SLIDE_DIST
        self.exit_offset       = -self.ITEM_SLIDE_DIST

        # Поверхность для fade-in затемнения (чёрный экран в начале)
        # Создаём под виртуальный экран 800x608
        self.fade_surface = pygame.Surface((
            self.screen.get_width(),
            self.screen.get_height()
        ))
        self.fade_surface.fill((0, 0, 0))

        # Загружаем фоновое изображение и масштабируем под виртуальный экран
        bg_path = os.path.join(self.menu_dir, "image.png")
        bg = pygame.image.load(bg_path)
        self.bg = pygame.transform.scale(bg, (
            self.screen.get_width(),
            self.screen.get_height()
        ))

        # Полупрозрачный чёрный overlay поверх фона (постоянный)
        # Создаём под виртуальный экран 800x608
        self.overlay = pygame.Surface((
            self.screen.get_width(),
            self.screen.get_height()
        ))
        self.overlay.set_alpha(100)  # 100 из 255 — лёгкое затемнение
        self.overlay.fill((0, 0, 0))

        self.last_selected = 0

    def _get_font(self, size: int) -> pygame.font.Font:
        """
        Возвращает шрифт нужного размера из кеша.

        Создаёт объект шрифта только один раз для каждого размера,
        затем переиспользует его. Это важно потому что pygame.font.Font()
        вызывается каждый кадр в draw() — без кеша это дорогая операция.

        Аргументы:
            size: размер шрифта в пикселях

        Возвращает:
            pygame.font.Font — объект шрифта нужного размера
        """
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.Font(self.font_path, size)
        return self._font_cache[size]

    def handle_events(self, events):
        """
        Обработка событий в главном меню.

        Реагирует на нажатия клавиш:
            UP / W    — перемещение вверх по меню
            DOWN / S  — перемещение вниз по меню
            ENTER     — выбор текущего пункта

        Управление заблокировано пока анимация появления не завершена
        (appear_progress < 1.0) — чтобы нельзя было выбрать пункт
        пока меню ещё появляется на экране.

        Аргументы:
            events: список событий Pygame из pygame.event.get()
        """
        # Блокируем управление пока анимация появления не завершена
        if self.appear_progress < 1.0:
            return

        for event in events:
            if event.type == pygame.KEYDOWN:

                # Навигация вверх по меню
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    old_selected = self.selected
                    self.selected = (self.selected - 1) % len(self.menu_items)
                    if self.selected != old_selected:
                        # Звук наведения на пункт меню
                        self.game.audio.play_sound(SoundType.UI_HOVER)

                # Навигация вниз по меню
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    old_selected = self.selected
                    self.selected = (self.selected + 1) % len(self.menu_items)
                    if self.selected != old_selected:
                        self.game.audio.play_sound(SoundType.UI_HOVER)

                # Выбор текущего пункта
                elif event.key == pygame.K_RETURN:
                    self.game.audio.play_sound(SoundType.UI_SELECT)
                    if self.selected == 0:
                        # "Начать игру" — переходим в режим исследования карты
                        self.game.change_state(GameState.EXPLORING)
                    elif self.selected == 1:
                        # "Выйти" — завершаем игру
                        self.game.running = False

    def update(self, dt):
        """
        Обновление логики меню.

        Каждый кадр обновляет:
            1. Прогресс анимации появления (appear_progress 0.0 → 1.0)
            2. Смещение заголовка (падает сверху вниз)
            3. Смещения пунктов меню (выезжают с разных сторон)
            4. Размеры шрифтов пунктов (плавное увеличение выбранного)

        Аргументы:
            dt: время прошедшее с прошлого кадра (секунд, delta time)
        """
        # Обновляем прогресс анимации появления (0.0 → 1.0)
        if self.appear_progress < 1.0:
            self.appear_progress += self.APPEAR_SPEED * dt
            if self.appear_progress > 1.0:
                self.appear_progress = 1.0

        # Заголовок падает сверху: от TITLE_SLIDE_FROM до TITLE_SLIDE_TO
        self.title_offset = int(
            self.TITLE_SLIDE_FROM +
            (self.TITLE_SLIDE_TO - self.TITLE_SLIDE_FROM) * self.appear_progress
        )

        # Пункты меню выезжают с разных сторон: от ±ITEM_SLIDE_DIST до 0
        self.start_game_offset = int(self.ITEM_SLIDE_DIST  * (1.0 - self.appear_progress))
        self.exit_offset       = int(-self.ITEM_SLIDE_DIST * (1.0 - self.appear_progress))

        # Плавно меняем размер шрифта для каждого пункта меню
        for i in range(len(self.menu_items)):
            # Целевой размер: крупный для выбранного, обычный для остальных
            target = float(self.FONT_SIZE_SELECTED if i == self.selected
                           else self.FONT_SIZE_NORMAL)

            # Интерполируем к целевому размеру
            diff = target - self.item_sizes[i]
            self.item_sizes[i] += diff * self.ANIM_SPEED * dt

    def draw(self, screen):
        """
        Отрисовка главного меню.

        Порядок отрисовки:
            1. Фоновое изображение на весь виртуальный экран
            2. Полупрозрачный чёрный overlay поверх фона
            3. Заголовок "Billy's Adventure" с анимацией падения сверху
            4. Пункты меню с анимацией выезжания и изменения размера:
               - "Начать игру" — выезжает справа налево
               - "Выйти"       — выезжает слева направо
               - Выбранный пункт подсвечивается жёлтым и крупнее
            5. Чёрный fade-in overlay (в начале затем исчезает)

        Аргументы:
            screen: виртуальная поверхность Pygame 800x608 для отрисовки
                    (передаётся из game.run() как virtual_screen)
        """
        # Фоновое изображение
        screen.blit(self.bg, (0, 0))

        # Полупрозрачный overlay поверх фона
        screen.blit(self.overlay, (0, 0))

        # Прозрачность всех элементов зависит от прогресса появления
        alpha = int(255 * self.appear_progress)

        # --- ЗАГОЛОВОК (падает сверху + fade-in) ---
        title = self.font_title.render("Billy's Adventure", True, (255, 255, 255))
        title.set_alpha(alpha)
        title_rect = title.get_rect(
            center=(screen.get_width() // 2, self.title_offset)
        )
        screen.blit(title, title_rect)

        # --- ПУНКТЫ МЕНЮ (выезжают с разных сторон + fade-in) ---
        for i, item in enumerate(self.menu_items):

            # Выбранный пункт — жёлтый, остальные — белые
            color = (255, 255, 0) if i == self.selected else (255, 255, 255)

            # Берём шрифт из кеша по текущему анимированному размеру
            font = self._get_font(int(self.item_sizes[i]))
            text = font.render(item, True, color)
            text.set_alpha(alpha)

            # Позиция каждого пункта — Y фиксирован, X меняется при slide-in
            y = self.MENU_Y_START + i * self.MENU_Y_STEP
            if i == 0:
                # "Начать игру" — выезжает справа налево
                x = screen.get_width() // 2 + self.start_game_offset
            else:
                # "Выйти" — выезжает слева направо
                x = screen.get_width() // 2 + self.exit_offset

            text_rect = text.get_rect(center=(x, y))
            screen.blit(text, text_rect)

        # --- FADE-IN OVERLAY (чёрный экран в начале, исчезает по мере появления) ---
        if self.appear_progress < 1.0:
            fade_alpha = int(255 * (1.0 - self.appear_progress))
            self.fade_surface.set_alpha(fade_alpha)
            screen.blit(self.fade_surface, (0, 0))