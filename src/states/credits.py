"""
src/states/credits.py
Состояние показа титров после победы над финальным боссом.
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.core.audio_manager import SoundType, MusicTrack


class CreditsState:
    """
    Состояние показа титров.

    Титры прокручиваются снизу вверх с заданной скоростью.
    Пользователь может нажать ENTER/ESC для пропуска и возврата в главное меню.
    """

    # Константы анимации
    SCROLL_SPEED = 35
    FAST_SCROLL_SPEED = 200
    FONT_SIZE_TITLE = 48
    FONT_SIZE_HEADER = 36
    FONT_SIZE_NAME = 28
    FONT_SIZE_ROLE = 22
    FONT_SIZE_THANKS = 24
    FONT_SIZE_HINT = 20

    SPACING_AFTER_TITLE = 80
    SPACING_BEFORE_SECTION = 60
    SPACING_BETWEEN_ENTRIES = 40
    SPACING_NAME_ROLE = 8

    COLOR_WHITE = (255, 255, 255)
    COLOR_YELLOW = (255, 255, 0)
    COLOR_GRAY = (180, 180, 180)
    COLOR_BLUE = (100, 150, 255)
    COLOR_GREEN = (100, 255, 100)

    def __init__(self, game):
        """
        Инициализация состояния титров.
        """
        self.game = game
        self.screen = game.virtual_screen

        # Параметры анимации
        self.scroll_y = self.screen.get_height()
        self.scroll_speed = self.SCROLL_SPEED
        self.fast_scroll = False
        self.fast_scroll_timer = 0.0

        # Шрифты (инициализируем сразу)
        self._load_fonts()

        # Загружаем фон
        self.background = None
        self._load_background()

        # Генерируем текст титров (после загрузки шрифтов)
        self.credits_surface = None
        self.credits_height = 0
        self._generate_credits_surface()

        # Флаг завершения
        self.finished = False

    def _load_background(self):
        """Загружает фоновое изображение для титров."""
        root_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        bg_paths = [
            os.path.join(root_dir, "assets", "menu", "image.png"),
            os.path.join(root_dir, "assets", "location5", "battle_bg.png"),
        ]

        for path in bg_paths:
            if os.path.exists(path):
                try:
                    bg = pygame.image.load(path)
                    self.background = pygame.transform.scale(
                        bg,
                        (self.screen.get_width(), self.screen.get_height())
                    )
                    break
                except Exception as e:
                    print(f"Ошибка загрузки фона титров: {e}")

        if self.background is None:
            self.background = pygame.Surface((
                self.screen.get_width(),
                self.screen.get_height()
            ))
            self.background.fill((0, 0, 0))

    def _load_fonts(self):
        """Загружает шрифты для титров."""
        root_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        font_path = os.path.join(root_dir, "assets", "menu", "Compilance-Sans.ttf")

        def get_font(size):
            try:
                return pygame.font.Font(font_path, size)
            except Exception:
                return pygame.font.SysFont("Arial", size)

        self.font_title = get_font(self.FONT_SIZE_TITLE)
        self.font_header = get_font(self.FONT_SIZE_HEADER)
        self.font_name = get_font(self.FONT_SIZE_NAME)
        self.font_role = get_font(self.FONT_SIZE_ROLE)
        self.font_thanks = get_font(self.FONT_SIZE_THANKS)
        self.font_hint = get_font(self.FONT_SIZE_HINT)

    def _generate_credits_surface(self):
        """
        Генерирует поверхность со всем текстом титров.
        """
        screen_w = self.screen.get_width()

        # Проверяем, что шрифты загружены
        if not hasattr(self, 'font_title') or not self.font_title:
            print("[CREDITS] Ошибка: шрифты не загружены")
            return

        lines = []
        y_offset = 0

        # ========== ЗАГОЛОВОК "ПОБЕДА!" ==========
        victory_text = self.font_title.render("ПОБЕДА!", True, self.COLOR_YELLOW)
        lines.append((victory_text, y_offset))
        y_offset += victory_text.get_height() + self.SPACING_AFTER_TITLE

        # ========== ПОЗДРАВЛЕНИЕ ==========
        congrats_lines = [
            "Поздравляем с прохождением игры!",
            "Ты доказал преподавателям,",
            "что разбираешься в математике лучше них!"
        ]
        for line in congrats_lines:
            text = self.font_thanks.render(line, True, self.COLOR_WHITE)
            lines.append((text, y_offset))
            y_offset += text.get_height() + 10
        y_offset += self.SPACING_BEFORE_SECTION

        # ========== РАЗРАБОТЧИКИ ==========
        header = self.font_header.render("РАЗРАБОТЧИКИ", True, self.COLOR_BLUE)
        lines.append((header, y_offset))
        y_offset += header.get_height() + self.SPACING_BETWEEN_ENTRIES

        developers = [
            ("Мейран Сергей Игоревич", "Team Lead / Battle System"),
            ("Симаков Даниил Дмитриевич", "Map & Level Design"),
            ("Антропов Сергей Михайлович", "UI / HUD Developer"),
            ("Крутик Максим Александрович", "Audio & Animation"),
        ]

        for name, role in developers:
            name_surf = self.font_name.render(name, True, self.COLOR_YELLOW)
            role_surf = self.font_role.render(role, True, self.COLOR_GRAY)

            lines.append((name_surf, y_offset))
            y_offset += name_surf.get_height() + self.SPACING_NAME_ROLE
            lines.append((role_surf, y_offset))
            y_offset += role_surf.get_height() + self.SPACING_BETWEEN_ENTRIES

        y_offset += self.SPACING_BEFORE_SECTION // 2

        # ========== БЛАГОДАРНОСТИ ==========
        thanks_header = self.font_header.render("БЛАГОДАРНОСТИ", True, self.COLOR_BLUE)
        lines.append((thanks_header, y_offset))
        y_offset += thanks_header.get_height() + self.SPACING_BETWEEN_ENTRIES

        thanks_lines = [
            "Дальневосточному федеральному университету",
            "Департаменту программной инженерии и ИИ",
            "Руководителю практики за ценные советы",
            "Всем преподавателям-боссам за интересные задачи",
            "",
            "Спасибо за игру!"
        ]

        for line in thanks_lines:
            if line:
                text = self.font_thanks.render(line, True, self.COLOR_GREEN)
            else:
                text = self.font_thanks.render(" ", True, self.COLOR_GREEN)
            lines.append((text, y_offset))
            y_offset += text.get_height() + 12

        y_offset += self.SPACING_BEFORE_SECTION

        # ========== КОНЕЦ ==========
        end_text = self.font_header.render("THE END", True, self.COLOR_YELLOW)
        lines.append((end_text, y_offset))
        y_offset += end_text.get_height() + 100

        # Пустое пространство внизу
        empty = self.font_hint.render(" ", True, self.COLOR_WHITE)
        lines.append((empty, y_offset))
        y_offset += 200

        # Создаём поверхность
        self.credits_height = y_offset
        self.credits_surface = pygame.Surface((screen_w, self.credits_height), pygame.SRCALPHA)

        for surf, y_pos in lines:
            x = screen_w // 2 - surf.get_width() // 2
            self.credits_surface.blit(surf, (x, y_pos))

    def enter(self):
        """Вход в состояние титров."""
        self.scroll_y = self.screen.get_height()
        self.scroll_speed = self.SCROLL_SPEED
        self.fast_scroll = False
        self.fast_scroll_timer = 0.0
        self.finished = False

        # Перегенерируем поверхность титров при каждом входе
        self._generate_credits_surface()

        # Запускаем музыку для титров
        self.game.audio.play_music(MusicTrack.CREDITS)

        print("[CREDITS] Титры начаты")

    def handle_events(self, events):
        """Обработка событий в титрах."""
        for event in events:
            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    self.game.audio.play_sound(SoundType.UI_SELECT)
                    self._exit_to_main_menu()
                    return

                if not self.fast_scroll:
                    self.fast_scroll = True
                    self.scroll_speed = self.FAST_SCROLL_SPEED
                    self.fast_scroll_timer = 0.5

    def _exit_to_main_menu(self):
        """Выход в главное меню."""
        if not self.finished:
            self.finished = True
            self.game.reset_game()
            self.game.change_state(GameState.MAIN_MENU)

    def update(self, dt):
        """Обновление анимации прокрутки титров."""
        if self.fast_scroll:
            self.fast_scroll_timer -= dt
            if self.fast_scroll_timer <= 0:
                self.fast_scroll = False
                self.scroll_speed = self.SCROLL_SPEED

        self.scroll_y -= self.scroll_speed * dt

        if self.scroll_y + self.credits_height < 0:
            self._exit_to_main_menu()

    def draw(self, screen):
        """Отрисовка титров."""
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((0, 0, 0))

        # Затемнение фона
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Титры
        if self.credits_surface:
            screen.blit(self.credits_surface, (0, int(self.scroll_y)))

        # Подсказка
        hint_text = "Нажми ENTER или ESC для выхода в главное меню"
        if self.fast_scroll:
            hint_text += " (ускоренная прокрутка)"

        hint_surf = self.font_hint.render(hint_text, True, self.COLOR_GRAY)
        hint_rect = hint_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() - 30))

        hint_bg = pygame.Surface((hint_surf.get_width() + 20, hint_surf.get_height() + 10), pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 200))
        screen.blit(hint_bg, (hint_rect.x - 10, hint_rect.y - 5))
        screen.blit(hint_surf, hint_rect)