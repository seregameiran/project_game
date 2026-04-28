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
    Поддерживает:
        - обычные линейные реплики
        - варианты ответа через поле options у текущей реплики

    Управление:
        E / ENTER — следующая реплика / подтвердить выбор
        ↑ / ↓ или W / S — выбрать вариант ответа
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

        # Текущая локация
        self.location_id = 1

        # Анимация печати текста
        self.displayed_chars = 0
        self.text_speed = 30
        self.text_timer = 0.0
        self.text_done = False

        # Кто сейчас говорит
        self.current_speaker = ""
        # Если это диалог босса, после полного завершения пометим победу
        self.pending_boss_location = None

        # Состояние выбора ответа
        self.awaiting_choice = False
        self.selected_option = 0
        self.choice_options = []

        # Действие, которое нужно выполнить после показа response-ветки
        self.post_dialog_action = None

        # Контекст для возврата к меню выбора после показа response-ветки
        self.return_choice_context = None

    def _reset_text_animation(self):
        """Сбрасывает анимацию печати текста для новой реплики."""
        self.displayed_chars = 0
        self.text_timer = 0.0
        self.text_done = False

    def _load_portraits(self, portrait_paths):
        """Загружает портреты говорящих."""
        for speaker, path in portrait_paths.items():
            try:
                img = pygame.image.load(path).convert_alpha()
                self.portraits[speaker] = pygame.transform.scale(img, (96, 96))
            except Exception as e:
                print(f"Ошибка загрузки портрета {path}: {e}")

    def start(self, dialog_file, location_id, portrait_paths, is_boss_dialog=False):
        """
        Запускает диалог из JSON файла.

        Аргументы:
            dialog_file: путь к JSON файлу с репликами
            location_id: номер текущей локации
            portrait_paths: словарь {speaker: путь к PNG портрета}
            is_boss_dialog: True если это диалог с боссом (после него начнётся бой)
        """
        self.current_index = 0
        self.location_id = location_id
        self.pending_boss_location = int(location_id) if is_boss_dialog else None
        self.lines = []
        self.portraits = {}
        self.current_speaker = ""

        self.awaiting_choice = False
        self.selected_option = 0
        self.choice_options = []
        self.post_dialog_action = None
        self.return_choice_context = None

        self._reset_text_animation()

        # Если босс уже побеждён — показываем короткий диалог вместо полного
        if is_boss_dialog and self.game.is_boss_defeated(int(location_id)):
            self.pending_boss_location = None  # бой не запускать
            self.lines = self._make_defeated_dialog(dialog_file)
            self._load_portraits(portrait_paths)
            return

        # Загружаем реплики из JSON
        try:
            with open(dialog_file, "r", encoding="utf-8") as f:
                self.lines = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки диалога {dialog_file}: {e}")
            self.lines = []
            return

        self._load_portraits(portrait_paths)


    def _perform_dialog_action(self, action):
        """
        Выполняет действие, выбранное игроком в диалоге.

        Поддерживаемые действия:
            - start_battle
            - decline_battle
            - return_to_choice_menu
        """
        self.game.audio.stop_sound(SoundType.DIALOG)
        self.game.audio.stop_sound(SoundType.DIALOG_BILLY)

        if action == "start_battle":
            if self.pending_boss_location is not None:
                boss_id = int(self.pending_boss_location) - 2
                self.pending_boss_location = None

                battle = self.game.states.get(GameState.BATTLE)
                if battle:
                    exploring = self.game.states.get(GameState.EXPLORING)
                    saved_x = getattr(exploring, "_saved_battle_x", 0)
                    battle.enter(boss_id, saved_x)
                    self.game.change_state(GameState.BATTLE)
                else:
                    self.game.change_state(GameState.EXPLORING)
            else:
                self.game.change_state(GameState.EXPLORING)
            return

        if action == "decline_battle":
            self.pending_boss_location = None
            self.game.change_state(GameState.EXPLORING)
            return

        # Обычный финал диалога без специальных действий
        if self.pending_boss_location is not None:
            boss_id = int(self.pending_boss_location) - 2
            self.pending_boss_location = None

            battle = self.game.states.get(GameState.BATTLE)
            if battle:
                exploring = self.game.states.get(GameState.EXPLORING)
                saved_x = getattr(exploring, "_saved_battle_x", 0)
                battle.enter(boss_id, saved_x)
                self.game.change_state(GameState.BATTLE)
            else:
                self.game.change_state(GameState.EXPLORING)
        else:
            self.game.change_state(GameState.EXPLORING)

    def _finish_dialogue(self):
        """Завершает текущий диалог с учётом отложенного действия."""
        self.game.audio.stop_sound(SoundType.DIALOG)
        self.game.audio.stop_sound(SoundType.DIALOG_BILLY)

        if self.post_dialog_action == "return_to_choice_menu" and self.return_choice_context:
            context = self.return_choice_context
            self.return_choice_context = None
            self.post_dialog_action = None

            self.lines = context["lines"]
            self.current_index = context["current_index"]
            self.awaiting_choice = True
            self.selected_option = 0
            self.choice_options = context["choice_options"]

            current_line = self.lines[self.current_index]
            self.current_speaker = current_line.get("speaker", "")
            self.displayed_chars = len(current_line.get("text", ""))
            self.text_timer = 0.0
            self.text_done = True
            return

        if self.post_dialog_action is not None:
            action = self.post_dialog_action
            self.post_dialog_action = None
            self._perform_dialog_action(action)
            return

        self._perform_dialog_action(None)

    @staticmethod
    def _make_defeated_dialog(dialog_file: str) -> list:
        """Загружает диалог побеждённого босса из JSON рядом с основным диалогом."""
        # boss-1.json → boss-1-defeated.json
        base, ext = os.path.splitext(dialog_file)
        defeated_file = f"{base}-defeated{ext}"

        try:
            with open(defeated_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки defeated-диалога {defeated_file}: {e}")
            # Фоллбэк если файл не найден
            return [{"speaker": "npc", "text": "Экзамен уже сдан.", "color": "red"}]
        

    def _confirm_selected_option(self):
        """Подтверждает выбранный вариант ответа."""
        if not self.choice_options:
            return

        choice = self.choice_options[self.selected_option]
        action = choice.get("action")
        response = choice.get("response") or []

        self.awaiting_choice = False
        self.selected_option = 0
        self.choice_options = []

        if response:
            if action == "return_to_choice_menu":
                self.return_choice_context = {
                    "lines": self.lines,
                    "current_index": self.current_index,
                    "choice_options": list(choice.get("options", []) for choice in []),
                }
                self.return_choice_context["choice_options"] = self.lines[self.current_index].get("options") or []

            self.lines = response
            self.current_index = 0
            self.post_dialog_action = action
            self._reset_text_animation()
        else:
            self.post_dialog_action = None
            self._perform_dialog_action(action)

    def handle_events(self, events):
        """
        Обработка событий диалога.

        Аргументы:
            events: список событий Pygame
        """
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            char = event.unicode.lower() if event.unicode else ""

            # Выход по ESC
            if event.key == pygame.K_ESCAPE:
                self.game.audio.stop_sound(SoundType.DIALOG)
                self.game.audio.stop_sound(SoundType.DIALOG_BILLY)
                self.awaiting_choice = False
                self.selected_option = 0
                self.choice_options = []
                self.post_dialog_action = None
                self.pending_boss_location = None
                self.game.change_state(GameState.EXPLORING)
                return

            # Если открыт выбор ответа — обрабатываем его отдельно
            if self.awaiting_choice:
                if event.key in (pygame.K_UP, pygame.K_w) or char == "ц":
                    self.selected_option = max(0, self.selected_option - 1)
                    return

                if event.key in (pygame.K_DOWN, pygame.K_s) or char == "ы":
                    self.selected_option = min(len(self.choice_options) - 1, self.selected_option + 1)
                    return

                if event.key == pygame.K_e or event.key == pygame.K_RETURN or char == "у":
                    self._confirm_selected_option()
                    return

                continue

            # Далее по E или Enter
            if event.key == pygame.K_e or event.key == pygame.K_RETURN or char == "у":
                if not self.text_done:
                    # Показываем весь текст сразу
                    self.text_done = True
                    if self.lines and self.current_index < len(self.lines):
                        self.displayed_chars = len(self.lines[self.current_index].get("text", ""))
                        current_line = self.lines[self.current_index]
                        options = current_line.get("options") or []
                        if options:
                            self.awaiting_choice = True
                            self.selected_option = 0
                            self.choice_options = options
                            self.game.audio.stop_sound(SoundType.DIALOG)
                            self.game.audio.stop_sound(SoundType.DIALOG_BILLY)
                    return

                if not self.lines or self.current_index >= len(self.lines):
                    return

                current_line = self.lines[self.current_index]
                options = current_line.get("options") or []

                # Если у текущей реплики есть варианты — переходим в режим выбора
                if options:
                    self.awaiting_choice = True
                    self.selected_option = 0
                    self.choice_options = options
                    self.game.audio.stop_sound(SoundType.DIALOG)
                    self.game.audio.stop_sound(SoundType.DIALOG_BILLY)
                    return

                # Переходим к следующей реплике
                self.current_index += 1
                self._reset_text_animation()

                if self.current_index >= len(self.lines):
                    self._finish_dialogue()

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

        if self.awaiting_choice:
            self.game.audio.stop_sound(SoundType.DIALOG)
            self.game.audio.stop_sound(SoundType.DIALOG_BILLY)
            return

        if not self.text_done:
            self.text_timer += dt
            chars_to_show = int(self.text_timer * self.text_speed)

            if chars_to_show > self.displayed_chars:
                # Воспроизводим звук для NPC
                if speaker != "billy" and chars_to_show < len(current_text):
                    self.game.audio.play_sound(SoundType.DIALOG)
                # Воспроизводим звук для Billy
                if speaker == "billy" and chars_to_show < len(current_text):
                    self.game.audio.play_sound(SoundType.DIALOG_BILLY)

                self.displayed_chars = min(chars_to_show, len(current_text))

            if self.displayed_chars >= len(current_text):
                self.text_done = True
                # Останавливаем звук диалога после завершения реплики
                if speaker != "billy":
                    self.game.audio.stop_sound(SoundType.DIALOG)
                if speaker == "billy":
                    self.game.audio.stop_sound(SoundType.DIALOG_BILLY)

                options = current_line.get("options") or []
                if options and not self.awaiting_choice:
                    self.awaiting_choice = True
                    self.selected_option = 0
                    self.choice_options = options
        else:
            self.game.audio.stop_sound(SoundType.DIALOG)
            self.game.audio.stop_sound(SoundType.DIALOG_BILLY)

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
        hint_surf = self.hint_font.render(hint_text, True, (255, 255, 0))
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
        if self.awaiting_choice:
            partial_text = text

        words = partial_text.split()
        lines_to_draw = []
        current_line_text = ""

        for word in words:
            test = current_line_text + (" " if current_line_text else "") + word
            if self.font.size(test)[0] <= max_width:
                current_line_text = test
            else:
                if current_line_text:
                    lines_to_draw.append(current_line_text)
                current_line_text = word
        if current_line_text:
            lines_to_draw.append(current_line_text)

        # Рисуем строки текста
        for i, rendered_line in enumerate(lines_to_draw):
            surf = self.font.render(rendered_line, True, text_color)
            screen.blit(surf, (40, h - 145 + i * 28))

        # Если открыт выбор — рисуем варианты ответа столбиком
        if self.awaiting_choice and self.choice_options:
            option_line_height = 24
            options_y = h - 145 + len(lines_to_draw) * 24 + 4

            for i, option in enumerate(self.choice_options):
                option_text = option.get("text", "")
                option_color = (255, 255, 0) if i == self.selected_option else (180, 180, 180)
                prefix = "► " if i == self.selected_option else "  "
                option_surf = self.font.render(prefix + option_text, True, option_color)
                screen.blit(option_surf, (40, options_y + i * option_line_height))

            controls_text = "W/S или ↑/↓ выбрать, E или Enter подтвердить"
            controls_surf = self.hint_font.render(controls_text, True, (180, 220, 255))
            controls_rect = controls_surf.get_rect(bottomright=(w - 30, h - 18))
            screen.blit(controls_surf, controls_rect)
