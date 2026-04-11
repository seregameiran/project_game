"""
Модуль states/exploring_dialogue.py
Состояние диалога с NPC во время исследования карты.
"""

import pygame
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState


class ExploringDialogueState:
    """
    Состояние диалога с NPC.

    Показывает диалоговое окно с портретом и текстом.
    Управление:
        E / ENTER — следующая реплика / закрыть диалог
    """

    def __init__(self, game):
        """
        Инициализация состояния диалога.

        Аргументы:
            game: ссылка на главный объект Game
        """
        self.game = game

        # Корневая папка проекта
        self.root_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        # Список реплик диалога
        self.lines = []

        # Текущая реплика
        self.current_index = 0

        # Портреты говорящих
        self.portraits = {}

        # Шрифт
        font_path = os.path.join(self.root_dir, "assets", "menu", "Compilance-Sans.ttf")
        self.font = pygame.font.Font(font_path, 26)
        self.hint_font = pygame.font.Font(font_path, 18)

        # Текущая локация (чтобы вернуться после диалога)
        self.location_id = 1

    def start(self, dialog_file, location_id, portrait_paths):
        """
        Запускает диалог из JSON файла.

        Аргументы:
            dialog_file: путь к JSON файлу с репликами
            location_id: номер текущей локации
            portrait_paths: словарь {speaker: путь к PNG портрета}
        """
        self.current_index = 0
        self.location_id = location_id
        self.lines = []
        self.portraits = {}

        # Загружаем реплики из JSON
        try:
            with open(dialog_file, "r", encoding="utf-8") as f:
                self.lines = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки диалога {dialog_file}: {e}")
            self.lines = []
            return

        # Загружаем портреты
        for speaker, path in portrait_paths.items():
            try:
                img = pygame.image.load(path).convert_alpha()
                # Масштабируем портрет до 96x96
                self.portraits[speaker] = pygame.transform.scale(img, (96, 96))
            except Exception as e:
                print(f"Ошибка загрузки портрета {path}: {e}")

    def handle_events(self, events):
        """
        Обработка событий диалога.

        Аргументы:
            events: список событий Pygame
        """
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e or event.key == pygame.K_RETURN:
                    self.current_index += 1

                    # Диалог закончился — возвращаемся в exploring
                    if self.current_index >= len(self.lines):
                        self.game.change_state(GameState.EXPLORING)

    def update(self, dt):
        pass

    def draw(self, screen):
        """
        Отрисовка диалогового окна поверх карты.

        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
        # Сначала рисуем карту под диалогом
        exploring = self.game.states.get(GameState.EXPLORING)
        if exploring:
            exploring.draw_world(screen)

        if not self.lines or self.current_index >= len(self.lines):
            return

        line = self.lines[self.current_index]
        speaker = line.get("speaker", "")
        text = line.get("text", "")
        color = line.get("color", "white")

        w = screen.get_width()
        h = screen.get_height()

        # Фон диалогового окна
        box_rect = pygame.Rect(20, h - 160, w - 40, 140)
        pygame.draw.rect(screen, (0, 0, 0), box_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), box_rect, 2, border_radius=10)

        # Портрет справа
        portrait = self.portraits.get(speaker)
        if portrait:
            # Центрируем портрет по высоте диалогового окна
            portrait_x = w - 130
            portrait_y = h - 160 + (140 - 96) // 2  # центр окна по вертикали
            screen.blit(portrait, (portrait_x, portrait_y))

        # Цвет текста
        text_colors = {
            "white": (255, 255, 255),
            "green": (100, 255, 100),
            "red": (255, 100, 100),
            "yellow": (255, 255, 0),
            "gray": (180, 180, 180),
        }
        text_color = text_colors.get(color, (255, 255, 255))

        # Разбиваем текст на строки по ширине
        max_width = w - 200
        words = text.split()
        lines_to_draw = []
        current_line = ""

        for word in words:
            test = current_line + (" " if current_line else "") + word
            if self.font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines_to_draw.append(current_line)
                current_line = word
        if current_line:
            lines_to_draw.append(current_line)

        # Рисуем строки текста
        for i, l in enumerate(lines_to_draw):
            surf = self.font.render(l, True, text_color)
            screen.blit(surf, (40, h - 145 + i * 28))