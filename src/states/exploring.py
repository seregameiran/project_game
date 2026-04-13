"""
Модуль states/exploring.py
Состояние исследования карты.

Содержит класс ExploringState, который отвечает за:
    - Загрузку TMX карты нужной локации
    - Отрисовку карты и игрока
    - Движение игрока с коллизиями и ограничением по границам карты
    - Камеру, следующую за игроком
    - Обработку взаимодействия с NPC (клавиша E)
    - Обработку переходов между локациями (клавиша E у двери)
    - Отладочный режим отображения коллизий (клавиша F1)
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.world.map_renderer import TiledMapRenderer
from src.world.camera import Camera
from src.entities.player import AnimatedPlayer

from src.core.audio_manager import SoundType



class ExploringState:
    """
    Состояние исследования карты.

    Загружает TMX карту по номеру локации, создаёт игрока и камеру.
    Обрабатывает движение, коллизии, взаимодействие с объектами.

    Локации:
        1 — дорога с деревьями, морем и остановками
        2 — вход в школу
        3 — класс с первым боссом (Внучка)
        4 — класс со вторым боссом (Отец)
        5 — класс с третьим боссом (Бабушка)

    Управление:
        W/A/S/D или стрелки — движение персонажа
        E                   — взаимодействие с NPC / переход между локациями
        ESC                 — пауза
        F1                  — включить/выключить отладку коллизий
    """

    def __init__(self, game):
        """
        Инициализация состояния исследования.

        Создаёт рендерер карты, игрока и камеру для первой локации.

        Аргументы:
            game: ссылка на главный объект Game
                  (для доступа к screen, change_state, running)
        """
        self.game   = game
        self.screen = game.virtual_screen

        # Номер текущей локации (1-5)
        self.current_location = 1

        # Рендерер TMX карты (TiledMapRenderer)
        self.map_renderer = None

        # Игрок (AnimatedPlayer)
        self.player = None

        # Камера (Camera)
        self.camera = None

        # Границы карты для ограничения движения игрока (pygame.Rect)
        self.map_bounds = None

        # Флаг отладки — показывать ли коллизии на экране (F1)
        self.show_debug = False

        # Загружаем первую локацию при старте
        self.load_location(1)

        # NPC рядом с игроком
        self.nearby_npc = None

        # Поле перехода рядом с игроком
        self.nearby_transition = None

        self.fade_alpha = 0  # текущая прозрачность (0=прозрачно, 255=черный)
        self.fading_out = False  # затемняем?
        self.fading_in = False  # высветляем?
        self.fade_speed = 400  # скорость затемнения
        self.pending_transition = None  # переход ожидающий выполнения
        self.fade_surface = pygame.Surface((game.screen.get_width(), game.screen.get_height()))
        self.fade_surface.fill((0, 0, 0))

    def load_location(self, location_id):
        """
        Загружает карту, создаёт игрока и камеру для указанной локации.

        При успешной загрузке:
            - self.map_renderer содержит рендерер новой карты
            - self.player создаётся в центре карты
            - self.camera настраивается под размеры карты и экрана
            - self.map_bounds обновляется под новую карту

        При ошибке загрузки карты все поля остаются None,
        и на экране будет показано сообщение об ошибке.

        Аргументы:
            location_id: номер локации от 1 до 5
        """
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        tmx_path = os.path.join(root_dir, "assets", f"location{location_id}", f"location{location_id}.tmx")

        try:
            # Создаём рендерер карты с масштабом 1.5
            self.map_renderer = TiledMapRenderer(tmx_path, zoom=1.5)
            print(f"Загружена локация {location_id}: "
                  f"{self.map_renderer.width}x{self.map_renderer.height}")

            # Границы карты — прямоугольник от (0,0) до (width, height)
            self.map_bounds = pygame.Rect(
                0, 0,
                self.map_renderer.width,
                self.map_renderer.height
            )

            # Создаём игрока в центре карты
            start_x = self.map_renderer.width  // 2
            start_y = self.map_renderer.height // 2
            self.player = AnimatedPlayer(
                start_x, start_y,
                os.path.join(root_dir, "assets", f"location{location_id}", "Billy.png"),
                scale=1.5
            )

            # Создаём камеру под размеры карты и окна
            self.camera = Camera(
                self.map_renderer.width,
                self.map_renderer.height,
                self.screen.get_width(),
                self.screen.get_height()
            )

            # Обновляем номер текущей локации
            self.current_location = location_id

        except Exception as e:
            print(f"Ошибка загрузки локации {location_id}: {e}")
            self.map_renderer = None
            self.player       = None
            self.camera       = None
            self.map_bounds   = None

    def handle_events(self, events):
        """
        Обработка событий клавиатуры в состоянии исследования.

        Реагирует на:
            ESC  — пауза (TODO: переключение в PAUSE_MENU)
            F1   — включение/выключение отладки коллизий
            E    — взаимодействие (NPC или переход между локациями)

        Аргументы:
            events: список событий Pygame из pygame.event.get()
        """
        for event in events:
            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    # Переключаемся в состояние паузы
                    pause_state = self.game.states.get(GameState.PAUSE)
                    if pause_state:
                        pause_state.enter(GameState.EXPLORING)
                        self.game.change_state(GameState.PAUSE)

                elif event.key == pygame.K_F1:
                    # Переключаем отладочный режим коллизий
                    self.show_debug = not self.show_debug

                elif event.key == pygame.K_e or event.unicode.lower() == "у":
                    # Проверяем взаимодействие с объектами на карте
                    self._check_interaction()

    def load_location_from_tmx(self, transition):
        """Загружает локацию по данным из перехода TMX."""
        tmx_path = transition["tmx_path"]
        spawn_x = transition["spawn_x"]
        spawn_y = transition["spawn_y"]

        try:
            self.map_renderer = TiledMapRenderer(tmx_path, zoom=1.5)
            self.map_bounds = pygame.Rect(
                0, 0,
                self.map_renderer.width,
                self.map_renderer.height
            )

            # Определяем номер локации из пути
            for i in range(1, 6):
                if f"location{i}" in tmx_path:
                    self.current_location = i
                    break

            root_dir = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))

            self.player = AnimatedPlayer(
                int(spawn_x * 1.5), int(spawn_y * 1.5),
                os.path.join(root_dir, "assets",
                             f"location{self.current_location}", "Billy.png"),
                scale=1.5
            )

            self.camera = Camera(
                self.map_renderer.width,
                self.map_renderer.height,
                self.screen.get_width(),
                self.screen.get_height()
            )

            print(f"Переход на локацию {self.current_location}")

        except Exception as e:
            print(f"Ошибка перехода: {e}")

    def draw_world(self, screen):
        """Рисует только карту и игрока (без UI) — для использования в диалоге."""
        if self.map_renderer is None:
            screen.fill((0, 0, 0))
            return

        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)
        self.map_renderer.draw(screen, cam_x, cam_y)
        self.player.draw(screen, cam_x, cam_y)

    def _check_interaction(self):
        """
        Проверяет, есть ли рядом с игроком объект для взаимодействия.

        Порядок проверки:
            1. NPC — если рядом есть NPC, запускает диалог
            2. Переход — если игрок стоит в зоне перехода, меняет локацию

        Вызывается при нажатии клавиши E.
        """
        if self.map_renderer is None or self.player is None:
            return

            # Проверяем NPC
        npc = self.map_renderer.check_npc_interaction(self.player.rect, radius=48)
        if npc:

            self.game.audio.play_sound(SoundType.INTERACT)

            root_dir = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))

            # Пути к портретам
            portrait_paths = {
                "billy": os.path.join(root_dir, "assets",
                                      f"location{self.current_location}", "Billy-Head.png"),
                f"npc-{self.current_location}": os.path.join(root_dir, "assets",
                                                             f"location{self.current_location}",
                                                             f"NPC-{self.current_location}-Head.png"),
            }

            # Запускаем диалог
            dialogue_state = self.game.states.get(GameState.DIALOGUE)
            if dialogue_state:
                dialogue_state.start(
                    npc["dialog_file"],
                    self.current_location,
                    portrait_paths
                )
                self.game.change_state(GameState.DIALOGUE)
            return

        # Проверяем переход
        transition = self.map_renderer.check_transition(self.player.rect)
        if transition:
            self.game.audio.play_sound(SoundType.TRANSITION)
            self.pending_transition = transition
            self.fading_out = True
            self.fade_alpha = 0

    def update(self, dt):
        """
        Обновление логики состояния исследования.

        Каждый кадр:
            1. Считывает нажатые клавиши
            2. Обновляет позицию игрока (движение + коллизии + границы)
            3. Обновляет анимацию игрока
            4. Обновляет позицию камеры

        Аргументы:
            dt: время прошедшее с прошлого кадра (секунд, delta time)
        """
        if self.player is None or self.camera is None:
            return

        keys = pygame.key.get_pressed()

        # Обновляем позицию игрока
        self.player.update(
            keys,
            self.map_renderer.check_collision,
            self.map_bounds
        )

        # Обновляем анимацию игрока
        self.player.update_animation(dt)

        # Обновляем камеру — она следует за игроком
        self.camera.follow(self.player.rect)

        # Проверяем есть ли NPC рядом
        self.nearby_npc = self.map_renderer.check_npc_interaction(
            self.player.rect, radius=48
        ) if self.map_renderer else None

        # Проверяем есть ли зона перехода рядом
        self.nearby_transition = self.map_renderer.check_transition(
            self.player.rect
        ) if self.map_renderer else None

        # Обновляем анимацию тайлов карты
        if self.map_renderer:
            self.map_renderer.update(dt)

        # Затемнение
        if self.fading_out:
            self.fade_alpha += self.fade_speed * dt
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                self.fading_out = False
                # Загружаем новую локацию
                self.load_location_from_tmx(self.pending_transition)
                self.pending_transition = None
                self.fading_in = True

        if self.fading_in:
            self.fade_alpha -= self.fade_speed * dt
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.fading_in = False

    def draw(self, screen):
        """
        Отрисовка состояния исследования.

        Порядок отрисовки:
            1. Карта (все видимые слои TMX)
            2. Отладочные прямоугольники коллизий/переходов/NPC (если F1)
            3. Игрок
            4. Отладочная строка с позицией и количеством коллизий

        Если карта не загружена — показывает сообщение об ошибке.

        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
        if self.map_renderer is None:
            # Карта не загружена — показываем ошибку
            screen.fill((0, 0, 0))
            font = pygame.font.Font(None, 36)
            text = font.render("Ошибка загрузки карты", True, (255, 0, 0))
            screen.blit(text, (
                screen.get_width()  // 2 - 150,
                screen.get_height() // 2
            ))
            return

        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)

        # Рисуем карту
        self.map_renderer.draw(screen, cam_x, cam_y)

        # Рисуем отладочные прямоугольники если включено (F1)
        # Красный   — коллизии
        # Голубой   — зоны переходов между локациями
        # Зелёный   — зоны NPC
        if self.show_debug:
            self.map_renderer.draw_collisions_debug(screen, cam_x, cam_y)

        # Рисуем игрока поверх карты
        self.player.draw(screen, cam_x, cam_y)

        # Отладочная строка в левом верхнем углу
        font = pygame.font.Font(None, 24)
        info_text = font.render(
            f"Локация: {self.current_location}  "
            f"Позиция: ({self.player.rect.x}, {self.player.rect.y})  "
            f"Камера: ({cam_x}, {cam_y})  "
            f"Коллизий: {len(self.map_renderer.collision_rects)}  "
            f"F1: отладка",
            True,
            (255, 255, 255)
        )
        # Подсказка "Нажми E" если рядом NPC
        if self.nearby_npc:
            hint_font = pygame.font.Font(None, 28)
            hint = hint_font.render("Нажми E для взаимодействия", True, (255, 255, 0))
            hint_rect = hint.get_rect(center=(screen.get_width() // 2, screen.get_height() - 40))
            screen.blit(hint, hint_rect)

        # Подсказка "Нажми E" при переходе на другую локацию
        if self.nearby_transition:
            hint_font = pygame.font.Font(None, 28)
            hint = hint_font.render("Нажми E для перехода", True, (0, 255, 255))
            hint_rect = hint.get_rect(center=(screen.get_width() // 2, screen.get_height() - 40))
            screen.blit(hint, hint_rect)

        screen.blit(info_text, (10, 10))

        # Рисуем затемнение поверх всего
        if self.fade_alpha > 0:
            self.fade_surface.set_alpha(int(self.fade_alpha))
            screen.blit(self.fade_surface, (0, 0))