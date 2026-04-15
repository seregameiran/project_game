"""
Модуль states/exploring.py
Состояние исследования карты.

Содержит класс ExploringState, который отвечает за:
    - Загрузку TMX карты нужной локации
    - Отрисовку карты и игрока
    - Движение игрока с коллизиями и ограничением по границам карты
    - Камеру, следующую за игроком
    - Обработку взаимодействия с NPC (клавиша E)
    - Обработку переходов между локациями (клавиша E у двери) через состояние TRANSITION_LOCATION
    - Отладочный режим отображения коллизий (клавиша F1)

Примечание:
    Логика затемнения при переходах между локациями вынесена в состояние TRANSITION_LOCATION.
    ExploringState больше не управляет fade-эффектами.
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
        self.game = game
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
            start_x = self.map_renderer.width // 2
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
            self.player = None
            self.camera = None
            self.map_bounds = None

    def load_location_from_tmx(self, transition_data):
        """
        Загружает локацию по данным из перехода (TMX).

        Используется для загрузки новой локации после подтверждения перехода.

        Аргументы:
            transition_data: dict с ключами tmx_path, spawn_x, spawn_y
                             (возвращается из map_renderer.check_transition)
        """
        tmx_path = transition_data["tmx_path"]
        spawn_x = transition_data["spawn_x"]
        spawn_y = transition_data["spawn_y"]

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

            print(f"Переход на локацию {self.current_location} (спавн: {spawn_x}, {spawn_y})")

        except Exception as e:
            print(f"Ошибка перехода: {e}")
            self.map_renderer = None
            self.player = None
            self.camera = None
            self.map_bounds = None

    def handle_events(self, events):
        """
        Обработка событий клавиатуры в состоянии исследования.

        Реагирует на:
            ESC  — пауза (переключение в PAUSE_MENU)
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
                elif event.key == pygame.K_BACKQUOTE:
                    # Запасной хоткей для macOS, где F1 часто перехватывается системой
                    self.show_debug = not self.show_debug

                elif event.key == pygame.K_e or event.unicode.lower() == "у":
                    # Проверяем взаимодействие с объектами на карте
                    self._check_interaction()

    def draw_world(self, screen):
        """
        Рисует только карту и игрока (без UI).

        Используется диалоговым состоянием для отображения фона под окном диалога.

        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
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
            2. Переход — если игрок стоит в зоне перехода,
               передаёт данные в состояние TRANSITION_LOCATION

        Вызывается при нажатии клавиши E.
        """
        if self.map_renderer is None or self.player is None:
            return

        # Взаимодействие проверяем небольшими "пробниками" вокруг игрока (центр + стороны),
        # чтобы можно было подойти к зоне NPC с любой стороны, но без слишком раннего срабатывания.
        probe_half = 7  # px (должен совпадать с update())
        pr = self.player.rect
        probe_points = (
            pr.center,
            pr.midbottom,
            pr.midtop,
            pr.midleft,
            pr.midright,
        )
        probe_rects = [
            pygame.Rect(px - probe_half, py - probe_half, probe_half * 2 + 1, probe_half * 2 + 1)
            for (px, py) in probe_points
        ]

        # Проверяем NPC
        # Старт диалога — только когда игрок действительно в "зелёной зоне" NPC.
        # (Подсказка "Нажми E" остаётся по радиусу в update().)
        npc = None
        for probe_rect in probe_rects:
            npc = self.map_renderer.check_npc_interaction(probe_rect, radius=0)
            if npc:
                break
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

        # Проверяем переход (дверь, портал и т.п.)
        transition = self.map_renderer.check_transition(self.player.rect)
        if transition:
            # Передаём данные перехода в состояние TRANSITION_LOCATION
            transition_state = self.game.states.get(GameState.TRANSITION_LOCATION)
            if transition_state:
                transition_state.enter(transition)
                self.game.change_state(GameState.TRANSITION_LOCATION)

    def update(self, dt):
        """
        Обновление логики состояния исследования.

        Каждый кадр:
            1. Считывает нажатые клавиши
            2. Обновляет позицию игрока (движение + коллизии + границы)
            3. Обновляет анимацию игрока
            4. Обновляет позицию камеры
            5. Проверяет наличие NPC и зон перехода рядом с игроком

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
        probe_half = 7  # px (должен совпадать с _check_interaction)
        pr = self.player.rect
        probe_points = (
            pr.center,
            pr.midbottom,
            pr.midtop,
            pr.midleft,
            pr.midright,
        )
        probe_rects = [
            pygame.Rect(px - probe_half, py - probe_half, probe_half * 2 + 1, probe_half * 2 + 1)
            for (px, py) in probe_points
        ]
        self.nearby_npc = None
        if self.map_renderer:
            for probe_rect in probe_rects:
                self.nearby_npc = self.map_renderer.check_npc_interaction(probe_rect, radius=0)
                if self.nearby_npc:
                    break

        # Проверяем есть ли зона перехода рядом
        self.nearby_transition = self.map_renderer.check_transition(
            self.player.rect
        ) if self.map_renderer else None

        # Обновляем анимацию тайлов карты
        if self.map_renderer:
            self.map_renderer.update(dt)

    def draw(self, screen):
        """
        Отрисовка состояния исследования.

        Порядок отрисовки:
            1. Карта (все видимые слои TMX)
            2. Отладочные прямоугольники коллизий/переходов/NPC (если F1)
            3. Игрок
            4. Подсказки (E для взаимодействия, E для перехода)
            5. Отладочная строка с позицией и количеством коллизий

        Если карта не загружена — показывает сообщение об ошибке.

        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
        screen.fill((0, 0, 0))  # Очистка экрана

        if self.map_renderer is None:
            # Карта не загружена — показываем ошибку
            font = pygame.font.Font(None, 36)
            text = font.render("Ошибка загрузки карты", True, (255, 0, 0))
            screen.blit(text, (
                screen.get_width() // 2 - 150,
                screen.get_height() // 2
            ))
            return

        cam_x = int(self.camera.x)
        cam_y = int(self.camera.y)

        # Рисуем карту
        self.map_renderer.draw(screen, cam_x, cam_y)

        # Рисуем отладочные прямоугольники если включено (F1)
        if self.show_debug:
            self.map_renderer.draw_collisions_debug(screen, cam_x, cam_y)

        # Рисуем игрока поверх карты
        self.player.draw(screen, cam_x, cam_y)

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

        # Отладочная строка в левом верхнем углу
        font = pygame.font.Font(None, 24)
        info_text = font.render(
            f"Локация: {self.current_location}  "
            f"Позиция: ({self.player.rect.x}, {self.player.rect.y})  "
            f"Камера: ({cam_x}, {cam_y})  "
            f"Коллизий: {len(self.map_renderer.collision_rects)}  "
            f"F1 / `: отладка",
            True,
            (255, 255, 255)
        )
        screen.blit(info_text, (10, 10))