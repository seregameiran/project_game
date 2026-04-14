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

from src.core.audio_manager import SoundType


class ExploringDialogueState:
    """
    Состояние диалога с NPC.

    Показывает диалоговое окно с портретом и текстом.
    Управление:
        E / ENTER — следующая реплика / закрыть диалог
        ESC — выйти из диалога и вернуться в исследование карты
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

        # Шрифты
        font_path = os.path.join(self.root_dir, "assets", "menu", "Compilance-Sans.ttf")
        self.font = pygame.font.Font(font_path, 26)       # основной текст диалога
        self.hint_font = pygame.font.Font(font_path, 24)  # подсказка (увеличенный)

        # Текущая локация (чтобы вернуться после диалога)
        self.location_id = 1

        # Анимация печати текста
        self.displayed_chars = 0
        self.text_speed = 30
        self.text_timer = 0.0
        self.text_done = False

        # Кто сейчас говорит (для звука)
        self.current_speaker = ""

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

        self.displayed_chars = 0
        self.text_speed = 30
        self.text_timer = 0.0
        self.text_done = False

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
                # Выход по ESC
                if event.key == pygame.K_ESCAPE:
                    self.game.audio.stop_sound(SoundType.DIALOG)
                    self.game.change_state(GameState.EXPLORING)
                    return

                # Далее по E или Enter
                if event.key == pygame.K_e or event.key == pygame.K_RETURN or event.unicode.lower() == "у":
                    if not self.text_done:
                        # Показываем весь текст сразу
                        self.text_done = True
                        if self.lines and self.current_index < len(self.lines):
                            self.displayed_chars = len(self.lines[self.current_index].get("text", ""))
                    else:
                        # Переходим к следующей реплике
                        self.current_index += 1
                        self.displayed_chars = 0
                        self.text_timer = 0.0
                        self.text_done = False


                        if self.current_index >= len(self.lines):
                            self.game.change_state(GameState.EXPLORING)

    def update(self, dt):
        """Обновляет анимацию печати текста и воспроизводит звуки."""
        if not self.lines or self.current_index >= len(self.lines):
            return

        current_line = self.lines[self.current_index]
        current_text = current_line.get("text", "")
        speaker = current_line.get("speaker", "")

        # Обновляем текущего говорящего
        if speaker != self.current_speaker:
            self.current_speaker = speaker

        if not self.text_done:
            self.text_timer += dt
            chars_to_show = int(self.text_timer * self.text_speed)

            if chars_to_show > self.displayed_chars:
                # Воспроизводим звук для NPC
                if speaker != "billy" and chars_to_show < len(current_text):
                    self.game.audio.play_sound(SoundType.DIALOG)

                self.displayed_chars = min(chars_to_show, len(current_text))

            if self.displayed_chars >= len(current_text):
                self.text_done = True
                # Останавливаем звук диалога после завершения реплики NPC
                if speaker != "billy":
                    self.game.audio.stop_sound(SoundType.DIALOG)
        else:
            self.game.audio.stop_sound(SoundType.DIALOG)

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
            portrait_x = w - 130
            portrait_y = h - 160 + (140 - 96) // 2
            screen.blit(portrait, (portrait_x, portrait_y))

        # --- ПОДСКАЗКА "Нажмите ESC, чтобы выйти" (левый верхний угол окна) ---
        hint_text = "Нажмите ESC, чтобы выйти"
        hint_surf = self.hint_font.render(hint_text, True, (255, 255, 0))  # жёлтый цвет
        hint_rect = hint_surf.get_rect(topright=(w - 10, 10))
        screen.blit(hint_surf, hint_rect)

        # Цвет текста
        text_colors = {
            "white": (255, 255, 255),
            "green": (100, 255, 100),
            "red": (255, 100, 100),
            "yellow": (255, 255, 0),
            "gray": (180, 180, 180),
        }
        text_color = text_colors.get(color, (255, 255, 255))

        # Разбиваем текст на строки
        max_width = w - 200
        partial_text = text[:self.displayed_chars]
        words = partial_text.split()
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