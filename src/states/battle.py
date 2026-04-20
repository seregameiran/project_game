"""
Модуль states/battle.py
Состояние боя с боссом.
"""

import pygame
import sys
import os
import random
import math

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.core.audio_manager import SoundType, MusicTrack


# ---------------------------------------------------------------------------
# Константы параметров боссов
# ---------------------------------------------------------------------------

PLAYER_HP_START = {1: 80, 2: 100, 3: 120}
BOSS_HP_START = {1: 60, 2: 90, 3: 120}
BOSS_Y_START = {1: 5, 2: 8, 3: 12}
BOSS_ADD_N_MIN = {1: 2, 2: 3, 3: 4}
BOSS_ADD_N_MAX = {1: 6, 2: 7, 3: 8}

UNLOCK_X_SUB = 7
UNLOCK_X_MUL = 10
UNLOCK_X_DIV = 12

BOSS_ADD_INTERVAL = 2
BOSS_SUB_INTERVAL = 3
BOSS_MUL_INTERVAL = 4
BOSS_DIV_INTERVAL = 4


# ---------------------------------------------------------------------------
# Цвета
# ---------------------------------------------------------------------------
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (220, 50, 50)
COLOR_GREEN = (50, 200, 80)
COLOR_YELLOW = (240, 200, 40)
COLOR_GRAY = (120, 120, 120)
COLOR_DARK = (20, 20, 30)
COLOR_HP_RED = (200, 40, 40)
COLOR_HP_BG = (60, 20, 20)
COLOR_HP_GREEN = (40, 180, 60)
COLOR_HP_BOSS_BG = (20, 40, 60)
COLOR_HP_BOSS = (40, 140, 220)

ATTACK_NAMES = {
    "add": "Сложение",
    "sub": "Вычитание",
    "mul": "Умножение",
    "div": "Деление",
}

ATTACK_KEYS = {
    pygame.K_1: "add",
    pygame.K_2: "sub",
    pygame.K_3: "mul",
    pygame.K_4: "div",
}


class BattleState:
    """
    Состояние пошагового боя с боссом.
    """

    PHASE_PLAYER_CHOOSE = "player_choose"
    PHASE_PLAYER_ANSWER = "player_answer"
    PHASE_BOSS_ATTACK = "boss_attack"
    PHASE_BOSS_ANSWER = "boss_answer"
    PHASE_RESULT = "result"
    PHASE_UNLOCK_ANIM = "unlock_anim"
    PHASE_ESCAPE = "escape"  # Новая фаза для выхода

    def __init__(self, game):
        self.game = game

        self.root_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # --- Параметры боя ---
        self.boss_id = 1
        self.hp_player = 0
        self.hp_boss = 0
        self.x = 0
        self.y = 0
        self.turn_counter = 0

        # --- Флаги особых состояний ---
        self.mul_next_double = False
        self.div_next_half = False
        self._boss_next_mul2 = False

        # --- Разблокировка атак ---
        self.add_unlocked = False
        self.sub_unlocked = False
        self.mul_unlocked = False
        self.div_unlocked = False

        self._pending_unlock_attack = None
        self._unlock_stage = 0

        # --- Ввод ответа ---
        self.answer_buffer = ""
        self.correct_answer = 0
        self.problem_text = ""

        # --- Текущая атака ---
        self.pending_attack = None
        self._boss_attack = None

        # --- Сообщения ---
        self.error_msg = ""
        self.error_timer = 0.0
        self.result_msg = ""
        self.result_timer = 0.0
        self._unlock_msg = ""
        self._unlock_timer = 0.0

        # --- Фаза хода ---
        self.phase = self.PHASE_PLAYER_CHOOSE

        # --- Фаза выхода из боя ---
        self.escape_selected = 1  # 0 = Да, 1 = Нет

        # --- Спрайты и шрифты ---
        self._fonts_loaded = False
        self.font_big = None
        self.font_mid = None
        self.font_small = None
        self.font_hint = None
        self.boss_sprite = None
        self.player_sprite = None

        # --- Фон для боя ---
        self.battle_bg = None
        self._load_battle_bg()

    def _load_battle_bg(self):
        """Загружает фон для битвы."""
        bg_path = os.path.join(self.root_dir, "assets", "location3", "battle_bg.png")
        try:
            if os.path.exists(bg_path):
                img = pygame.image.load(bg_path).convert()
                self.battle_bg = pygame.transform.scale(img, (800, 608))
                print(f"Загружен фон битвы: {bg_path}")
            else:
                print(f"Фон битвы не найден: {bg_path}, использую заливку")
                self.battle_bg = None
        except Exception as e:
            print(f"Ошибка загрузки фона битвы: {e}")
            self.battle_bg = None

    # -----------------------------------------------------------------------
    # Вход в состояние боя
    # -----------------------------------------------------------------------

    def enter(self, boss_id: int, saved_x: int = 0):
        """
        Инициализирует бой с указанным боссом.
        """
        self.boss_id = int(boss_id)
        self.hp_player = PLAYER_HP_START.get(self.boss_id, 80)
        self.hp_boss = BOSS_HP_START.get(self.boss_id, 60)

        if self.boss_id == 1:
            self.x = 0
        else:
            self.x = max(1, saved_x // 2) if saved_x > 0 else 0

        self.y = BOSS_Y_START.get(self.boss_id, 5)
        self.turn_counter = 0

        self.mul_next_double = False
        self.div_next_half = False
        self._boss_next_mul2 = False

        # Разблокировка атак
        self.add_unlocked = False
        self.sub_unlocked = (self.x >= UNLOCK_X_SUB)
        self.mul_unlocked = (self.boss_id >= 2 and self.x >= UNLOCK_X_MUL)
        self.div_unlocked = (self.boss_id >= 3 and self.x >= UNLOCK_X_DIV)

        self._pending_unlock_attack = None
        self._unlock_stage = 0

        self.answer_buffer = ""
        self.correct_answer = 0
        self.problem_text = ""
        self.pending_attack = None
        self._boss_attack = None

        self.error_msg = ""
        self.error_timer = 0.0
        self.result_msg = ""
        self.result_timer = 0.0
        self._unlock_msg = ""
        self._unlock_timer = 0.0

        # Проверяем нужно ли открыть сложение
        if not self.add_unlocked:
            self._start_unlock_challenge("add")
            self.phase = self.PHASE_PLAYER_ANSWER
        else:
            self.phase = self.PHASE_PLAYER_CHOOSE

        self._load_assets()

        print(f"[BATTLE] Бой начат. Босс #{self.boss_id}, "
              f"HP_player={self.hp_player}, HP_boss={self.hp_boss}, "
              f"X={self.x}, Y={self.y}")

    def _load_assets(self):
        """Загружает шрифты и спрайты для боя."""
        if self._fonts_loaded:
            return

        font_path = os.path.join(self.root_dir, "assets", "menu", "Compilance-Sans.ttf")

        def load_font(size):
            try:
                return pygame.font.Font(font_path, size)
            except Exception:
                return pygame.font.SysFont("Arial", size)

        self.font_big = load_font(36)
        self.font_mid = load_font(26)
        self.font_small = load_font(20)
        self.font_hint = load_font(18)

        # Спрайт босса
        boss_names = {1: "NPC-3-Head", 2: "boss2", 3: "boss3"}
        boss_name = boss_names.get(self.boss_id, "boss1")
        boss_path = os.path.join(
            self.root_dir, "assets", f"location{self.boss_id + 2}", f"{boss_name}.png"
        )
        try:
            if os.path.exists(boss_path):
                img = pygame.image.load(boss_path).convert_alpha()
                self.boss_sprite = pygame.transform.scale(img, (80, 80))
            else:
                self.boss_sprite = None
        except Exception as e:
            print(f"Ошибка загрузки спрайта босса: {e}")
            self.boss_sprite = None

        # Спрайт игрока
        player_path = os.path.join(self.root_dir, "assets", "location3", "Billy-Head.png")
        try:
            if os.path.exists(player_path):
                img = pygame.image.load(player_path).convert_alpha()
                frame_w = img.get_width() // 4 if img.get_width() > img.get_height() else img.get_width()
                frame = img.subsurface(pygame.Rect(0, 0, frame_w, img.get_height()))
                self.player_sprite = pygame.transform.scale(frame, (80, 80))
            else:
                self.player_sprite = None
        except Exception as e:
            print(f"Ошибка загрузки спрайта игрока: {e}")
            self.player_sprite = None

        self._fonts_loaded = True

    # -----------------------------------------------------------------------
    # Генерация математических примеров
    # -----------------------------------------------------------------------

    def _gen_unlock_problem(self, attack_type: str):
        """Генерирует пример для разблокировки атаки."""
        problems = {
            "add": lambda: self._make_problem("+"),
            "sub": lambda: self._make_problem("-"),
            "mul": lambda: self._make_problem("*"),
            "div": lambda: self._make_problem("/"),
        }
        return problems.get(attack_type, lambda: self._make_problem("+"))()

    def _make_problem(self, op: str):
        """Создаёт простой пример с операцией op."""
        if op == "+":
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            return f"{a} + {b} = ?", a + b
        elif op == "-":
            b = random.randint(1, 5)
            a = random.randint(b, b + 6)
            return f"{a} - {b} = ?", a - b
        elif op == "*":
            a = random.randint(2, 5)
            b = random.randint(2, 4)
            return f"{a} × {b} = ?", a * b
        else:  # "/"
            b = random.randint(2, 4)
            a = b * random.randint(2, 5)
            return f"{a} ÷ {b} = ?", a // b

    def _gen_boss_problem(self, attack_type: str):
        """Генерирует пример для атаки босса."""
        return self._make_problem(
            {"add": "+", "sub": "-", "mul": "*", "div": "/"}.get(attack_type, "+")
        )

    # -----------------------------------------------------------------------
    # Старт этапов разблокировки
    # -----------------------------------------------------------------------

    def _start_unlock_challenge(self, attack_type: str):
        """Начинает процедуру разблокировки атаки."""
        self._pending_unlock_attack = attack_type
        self._unlock_stage = 1
        text, ans = self._gen_unlock_problem(attack_type)
        self.problem_text = f"[Разблокировка: {ATTACK_NAMES[attack_type]}]\n{text}"
        self.correct_answer = ans
        self.answer_buffer = ""
        self.error_msg = ""

    # -----------------------------------------------------------------------
    # Атаки игрока
    # -----------------------------------------------------------------------

    def _apply_player_attack(self, attack_type: str):
        """Применяет выбранную атаку игрока."""
        multiplier = 2 if self.mul_next_double else 1
        self.mul_next_double = False

        if attack_type == "add":
            gain = 1 * multiplier
            self.x += gain
            self.hp_boss -= self.x
            self.game.audio.play_sound(SoundType.BOSS_HIT)
            self._show_unlock_anim(f"+{gain} к уровню! HP босса -{self.x}")

        elif attack_type == "sub":
            dmg = 2 * multiplier
            self.y = max(0, self.y - dmg)
            self.hp_boss -= dmg
            self.game.audio.play_sound(SoundType.BOSS_HIT)
            self._show_unlock_anim(f"Y босса -{dmg}, HP босса -{dmg}")

        elif attack_type == "mul":
            self.mul_next_double = True
            self._show_unlock_anim("Следующая атака удвоена!")

        elif attack_type == "div":
            self.div_next_half = True
            self._show_unlock_anim("Следующий удар босса ослаблен!")

    # -----------------------------------------------------------------------
    # Атаки босса
    # -----------------------------------------------------------------------

    def _choose_boss_attack(self) -> str:
        """Босс выбирает атаку."""
        tc = self.turn_counter

        if self.boss_id >= 3 and tc % BOSS_DIV_INTERVAL == 0 and tc > 0:
            return "div"

        if self.boss_id >= 2 and tc % BOSS_MUL_INTERVAL == 0 and tc > 0:
            return "mul"

        if tc % BOSS_SUB_INTERVAL == 0 and tc > 0:
            return "sub"

        if tc % BOSS_ADD_INTERVAL == 0 and tc > 0:
            return "add"

        return "basic"

    def _apply_boss_attack_result(self, attack_type: str, correct: bool):
        """Применяет результат атаки босса."""
        n_min = BOSS_ADD_N_MIN.get(self.boss_id, 2)
        n_max = BOSS_ADD_N_MAX.get(self.boss_id, 6)
        n = random.randint(n_min, n_max)

        divisor = 2 if self.div_next_half else 1
        self.div_next_half = False

        if attack_type == "basic":
            dmg = max(1, self.y // divisor)
            self.hp_player -= dmg
            self.game.audio.play_sound(SoundType.DAMAGE)

        elif attack_type == "add":
            if correct:
                self.y += n
                self._show_unlock_anim(f"Босс: Y +{n}")
            else:
                self.y += n * 2
                self.game.audio.play_sound(SoundType.DAMAGE)
                self._show_unlock_anim(f"Ошибка! Босс: Y +{n * 2}")

        elif attack_type == "sub":
            if correct:
                self.x = max(0, self.x - 2)
                self._show_unlock_anim("Босс: X -2")
            else:
                self.x = max(0, self.x // 2)
                self.game.audio.play_sound(SoundType.DAMAGE)
                self._show_unlock_anim("Ошибка! Босс: X ÷ 2")

        elif attack_type == "mul":
            if correct:
                self._boss_next_mul2 = True
                self._show_unlock_anim("Босс: следующий удар x2!")
            else:
                self.x = max(0, int(self.x / 1.5))
                self.y = int(self.y * 2)
                self.game.audio.play_sound(SoundType.DAMAGE)
                self._show_unlock_anim("Ошибка! X ÷1.5, Y ×2")

        elif attack_type == "div":
            if correct:
                self.x = max(0, self.x // 2)
                self._show_unlock_anim("Босс: X ÷ 2")
            else:
                self.x = max(0, self.x // 2)
                self.y = int(self.y * 1.5)
                self.game.audio.play_sound(SoundType.DAMAGE)
                self._show_unlock_anim("Ошибка! X ÷2, Y ×1.5")

    # -----------------------------------------------------------------------
    # Разблокировка атак
    # -----------------------------------------------------------------------

    def _check_unlock_conditions(self):
        """Проверяет условия разблокировки."""
        if not self.sub_unlocked and self.x >= UNLOCK_X_SUB:
            self._start_unlock_challenge("sub")
            self.phase = self.PHASE_PLAYER_ANSWER

        elif (not self.mul_unlocked and self.boss_id >= 2
              and self.x >= UNLOCK_X_MUL):
            self._start_unlock_challenge("mul")
            self.phase = self.PHASE_PLAYER_ANSWER

        elif (not self.div_unlocked and self.boss_id >= 3
              and self.x >= UNLOCK_X_DIV):
            self._start_unlock_challenge("div")
            self.phase = self.PHASE_PLAYER_ANSWER

    def _resolve_unlock_answer(self, correct: bool):
        """Обрабатывает ответ игрока на пример разблокировки."""
        attack = self._pending_unlock_attack

        if correct:
            setattr(self, f"{attack}_unlocked", True)
            self._unlock_msg = f"Атака «{ATTACK_NAMES[attack]}» разблокирована!"
            self._unlock_timer = 2.5
            self._pending_unlock_attack = None
            self._unlock_stage = 0
            self.problem_text = ""
            self.answer_buffer = ""
            self.error_msg = ""
            self.game.audio.play_sound(SoundType.VICTORY)

            if self.hp_boss > 0 and self.hp_player > 0:
                self.phase = self.PHASE_PLAYER_CHOOSE
        else:
            if self._unlock_stage == 1:
                self._unlock_stage = 2
                self.error_msg = "Неверно! Попробуй ещё раз."
                self.error_timer = 2.0
                text, ans = self._gen_unlock_problem(attack)
                self.problem_text = f"[Разблокировка: {ATTACK_NAMES[attack]}]\n{text}"
                self.correct_answer = ans
                self.answer_buffer = ""
            else:
                self.error_msg = "Не удалось разблокировать атаку. Возврат..."
                self.error_timer = 2.0
                self._pending_unlock_attack = None
                self._unlock_stage = 0
                self.result_msg = ""
                self.result_timer = 2.5
                self.phase = self.PHASE_RESULT

    # -----------------------------------------------------------------------
    # Победа / Поражение
    # -----------------------------------------------------------------------

    def _check_battle_end(self):
        """Проверяет условия окончания боя."""
        if self.hp_boss <= 0:
            if self.boss_id == 3:
                self.result_msg = "Ты победил! Конец игры!"
                self.result_timer = 3.0
                self.phase = self.PHASE_RESULT
                self.game.audio.play_sound(SoundType.VICTORY)
                self.game.audio.play_music(MusicTrack.VICTORY)
                self._victory_goto_credits = True
            else:
                self.result_msg = f"Босс #{self.boss_id} повержен!"
                self.result_timer = 3.0
                self.phase = self.PHASE_RESULT
                self.game.audio.play_sound(SoundType.VICTORY)
                self.game.audio.play_music(MusicTrack.VICTORY)
                self._victory_goto_credits = False
            return True

        if self.hp_player <= 0:
            self.result_msg = "Wasted. Попробуй снова."
            self.result_timer = 3.0
            self.phase = self.PHASE_RESULT
            self.game.audio.play_sound(SoundType.DEFEAT)
            self._victory_goto_credits = False
            return True

        return False

    def _exit_battle(self, victory: bool):
        """Выходит из боя."""
        exploring = self.game.states.get(GameState.EXPLORING)

        if victory and self.boss_id == 3:
            credits_state = self.game.states.get(GameState.CREDITS)
            if credits_state:
                self.game.change_state(GameState.CREDITS)
            return

        if victory:
            location_id = self.boss_id + 2
            self.game.mark_boss_defeated(location_id)

            if exploring:
                exploring._saved_battle_x = max(1, self.x // 2)

            self.game.audio.play_music(MusicTrack.EXPLORING)
            self.game.change_state(GameState.EXPLORING)
        else:
            self.game.audio.play_music(MusicTrack.EXPLORING)
            self.game.change_state(GameState.EXPLORING)

    # -----------------------------------------------------------------------
    # Вспомогательные
    # -----------------------------------------------------------------------

    def _show_unlock_anim(self, msg: str):
        self._unlock_msg = msg
        self._unlock_timer = 2.0

    def _validate_answer(self) -> bool:
        """Проверяет введённый ответ."""
        try:
            return int(self.answer_buffer) == self.correct_answer
        except ValueError:
            return False

    def _is_attack_available(self, attack: str) -> bool:
        """Возвращает True, если атака доступна игроку."""
        return getattr(self, f"{attack}_unlocked", False)

    def _submit_answer(self):
        """Обрабатывает подтверждение ответа игрока."""
        correct = self._validate_answer()

        if self.phase == self.PHASE_PLAYER_ANSWER:
            self._resolve_unlock_answer(correct)

        elif self.phase == self.PHASE_BOSS_ANSWER:
            self._apply_boss_attack_result(self._boss_attack, correct)
            if not correct:
                self.error_msg = "Ошибка! Попробуй ещё раз."
                self.error_timer = 1.5
            self.answer_buffer = ""
            self.problem_text = ""
            self._boss_attack = None

            if not self._check_battle_end():
                self.phase = self.PHASE_PLAYER_CHOOSE

    def _do_boss_turn(self):
        """Выполняет ход босса."""
        boss_attack = self._choose_boss_attack()

        if boss_attack == "basic":
            divisor = 2 if self.div_next_half else 1
            self.div_next_half = False
            multiplier = 2 if getattr(self, "_boss_next_mul2", False) else 1
            self._boss_next_mul2 = False
            dmg = max(1, (self.y * multiplier) // divisor)
            self.hp_player -= dmg
            self.game.audio.play_sound(SoundType.DAMAGE)
            self._show_unlock_anim(f"Босс: базовый удар -{dmg} HP")
            self._check_battle_end()
        else:
            self._boss_attack = boss_attack
            text, ans = self._gen_boss_problem(boss_attack)
            self.problem_text = f"[Атака босса: {ATTACK_NAMES[boss_attack]}]\n{text}"
            self.correct_answer = ans
            self.answer_buffer = ""
            self.error_msg = ""
            self.phase = self.PHASE_BOSS_ANSWER

    # -----------------------------------------------------------------------
    # Обработка выхода из боя
    # -----------------------------------------------------------------------

    def _escape_battle(self):
        """Выход из боя в главное меню."""
        self.game.audio.play_sound(SoundType.UI_SELECT)
        self.game.change_state(GameState.EXPLORING)

    # -----------------------------------------------------------------------
    # Обработка событий
    # -----------------------------------------------------------------------

    def handle_events(self, events):
        """Обрабатывает события клавиатуры."""
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            # Выход по ESC
            if event.key == pygame.K_ESCAPE:
                self._escape_battle()
                return

            # --- Фаза выбора атаки ---
            if self.phase == self.PHASE_PLAYER_CHOOSE:
                attack = ATTACK_KEYS.get(event.key)
                if attack and self._is_attack_available(attack):
                    self.pending_attack = attack

                    if attack in ("add", "sub"):
                        self._apply_player_attack(attack)
                        self.turn_counter += 1
                        if not self._check_battle_end():
                            self._check_unlock_conditions()
                            if self.phase == self.PHASE_PLAYER_CHOOSE:
                                self._do_boss_turn()
                    elif attack == "mul":
                        self._apply_player_attack(attack)
                        self.turn_counter += 1
                        if not self._check_battle_end():
                            self._check_unlock_conditions()
                            if self.phase == self.PHASE_PLAYER_CHOOSE:
                                self._do_boss_turn()
                    elif attack == "div":
                        self._apply_player_attack(attack)
                        self.turn_counter += 1
                        if not self._check_battle_end():
                            self._check_unlock_conditions()
                            if self.phase == self.PHASE_PLAYER_CHOOSE:
                                self._do_boss_turn()

            # --- Фаза ввода ответа ---
            elif self.phase in (self.PHASE_PLAYER_ANSWER, self.PHASE_BOSS_ANSWER):
                if event.key == pygame.K_BACKSPACE:
                    self.answer_buffer = self.answer_buffer[:-1]

                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    if self.answer_buffer:
                        self._submit_answer()

                elif event.unicode.isdigit():
                    if len(self.answer_buffer) < 3:
                        self.answer_buffer += event.unicode

    # -----------------------------------------------------------------------
    # Обновление
    # -----------------------------------------------------------------------

    def update(self, dt: float):
        """Обновляет таймеры сообщений."""
        if self.error_timer > 0:
            self.error_timer -= dt
            if self.error_timer <= 0:
                self.error_msg = ""

        if self._unlock_timer > 0:
            self._unlock_timer -= dt
            if self._unlock_timer <= 0:
                self._unlock_msg = ""

        if self.phase == self.PHASE_RESULT and self.result_timer > 0:
            self.result_timer -= dt
            if self.result_timer <= 0:
                victory = self.hp_boss <= 0
                self._exit_battle(victory)

    # -----------------------------------------------------------------------
    # Отрисовка
    # -----------------------------------------------------------------------

    def draw(self, screen: pygame.Surface):
        """
        Рисует экран боя.
        """
        if not self._fonts_loaded:
            self._load_assets()

        W, H = screen.get_width(), screen.get_height()

        # --- ФОН БОЯ ---
        if self.battle_bg:
            screen.blit(self.battle_bg, (0, 0))
        else:
            # Градиентный фон
            for i in range(H):
                color_value = 18 + int(i / H * 30)
                pygame.draw.line(screen, (color_value, color_value, color_value + 20), (0, i), (W, i))


        # ========== ИЗМЕНЕНИЕ 1: Правильное расположение прямоугольников ==========
        # Прямоугольник БОССА (справа ВВЕРХУ)
        boss_box = pygame.Rect(W - 260, 20, 260, 140)
        pygame.draw.rect(screen, (0, 0, 0), boss_box, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), boss_box, 2, border_radius=10)

        # Прямоугольник ИГРОКА (слева ВНИЗУ)
        player_box = pygame.Rect(20, 20, 260, 140)
        pygame.draw.rect(screen, (0, 0, 0), player_box, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), player_box, 2, border_radius=10)

        # ========== ИЗМЕНЕНИЕ 2: Имена над прямоугольниками ==========
        # Имя босса (над верхним прямоугольником)
        boss_names = {1: "Внучка", 2: "Отец", 3: "Бабушка"}
        boss_name = boss_names.get(self.boss_id, "Босс")
        name_surf = self.font_mid.render(boss_name, True, COLOR_YELLOW)
        screen.blit(name_surf, (boss_box.x + boss_box.width // 2 - name_surf.get_width() // 2, boss_box.y - 25))

        # Имя игрока (над нижним прямоугольником)
        player_name_surf = self.font_mid.render("Билли", True, COLOR_YELLOW)
        screen.blit(player_name_surf,
                    (player_box.x + player_box.width // 2 - player_name_surf.get_width() // 2, player_box.y - 25))

        # --- Спрайты ---
        # Спрайт босса (справа в прямоугольнике)
        if self.boss_sprite:
            bx = boss_box.x + boss_box.width - self.boss_sprite.get_width() - 20
            by = boss_box.y + (140 - self.boss_sprite.get_height()) // 2
            screen.blit(self.boss_sprite, (bx, by))

        # Спрайт игрока (слева в прямоугольнике)
        if self.player_sprite:
            px = player_box.x + 20
            py = player_box.y + (140 - self.player_sprite.get_height()) // 2
            screen.blit(self.player_sprite, (px, py))

        # ========== ИЗМЕНЕНИЕ 3: HP и уровни БОССА (в верхнем прямоугольнике) ==========
        # HP бар босса
        boss_hp_bar_x = boss_box.x + 20
        boss_hp_bar_y = boss_box.y + 40
        self._draw_hp_bar(
            screen, x=boss_hp_bar_x, y=boss_hp_bar_y, w=100, h=18,
            hp=self.hp_boss, max_hp=BOSS_HP_START.get(self.boss_id, 60),
            label="", color=COLOR_HP_BOSS, bg=COLOR_HP_BOSS_BG
        )
        # Текст HP босса
        boss_hp_text = self.font_small.render(f"HP: {max(0, self.hp_boss)}/{BOSS_HP_START.get(self.boss_id, 60)}",
                                              True, COLOR_WHITE)
        screen.blit(boss_hp_text, (boss_hp_bar_x, boss_hp_bar_y - 18))

        # Уровень Y босса
        y_surf = self.font_mid.render(f"Уровень Y: {self.y}", True, (100, 180, 255))
        screen.blit(y_surf, (boss_box.x + 20, boss_box.y + 70))

        # ========== ИЗМЕНЕНИЕ 4: HP и уровни ИГРОКА (в нижнем прямоугольнике) ==========
        # HP бар игрока
        hp_bar_x = player_box.x + 120
        hp_bar_y = player_box.y + 40
        self._draw_hp_bar(
            screen, x=hp_bar_x, y=hp_bar_y, w=100, h=18,
            hp=self.hp_player, max_hp=PLAYER_HP_START.get(self.boss_id, 80),
            label="", color=COLOR_HP_GREEN, bg=COLOR_HP_BG
        )
        # Текст HP игрока
        hp_text = self.font_small.render(f"HP: {max(0, self.hp_player)}/{PLAYER_HP_START.get(self.boss_id, 80)}",
                                         True, COLOR_WHITE)
        screen.blit(hp_text, (hp_bar_x, hp_bar_y - 18))

        # Уровень X игрока
        x_surf = self.font_mid.render(f"Уровень X: {self.x}", True, COLOR_YELLOW)
        screen.blit(x_surf, (player_box.x + 120, player_box.y + 70))

        # --- Пример (по центру экрана) ---
        if self.problem_text:
            self._draw_problem(screen, W, H)
        else:
            # Если нет примера, показываем текущую фазу
            if self.phase == self.PHASE_PLAYER_CHOOSE:
                phase_text = self.font_mid.render("Выбери атаку!", True, COLOR_YELLOW)
                screen.blit(phase_text, (W // 2 - phase_text.get_width() // 2, H // 2 - 30))
        info_box = pygame.Rect(20, H - 180, W - 40, 160)
        pygame.draw.rect(screen, (0, 0, 0), info_box, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), info_box, 2, border_radius=10)

        # --- Иконки атак (внутри нижнего блока) ---
        self._draw_attack_icons(screen, W, H, info_box)

        # --- Подсказка выхода (внутри нижнего блока) ---
        escape_hint = self.font_hint.render("ESC - выйти из боя", True, COLOR_GRAY)
        screen.blit(escape_hint, (info_box.x + info_box.width - escape_hint.get_width() - 20,
                                  info_box.y + info_box.height - 30))

        # --- Сообщение разблокировки (внутри нижнего блока) ---
        if self._unlock_msg:
            surf = self.font_mid.render(self._unlock_msg, True, COLOR_GREEN)
            screen.blit(surf, (info_box.x + info_box.width // 2 - surf.get_width() // 2,
                               info_box.y + 15))

        # --- Сообщение ошибки (внутри нижнего блока) ---
        if self.error_msg:
            surf = self.font_mid.render(self.error_msg, True, COLOR_RED)
            screen.blit(surf, (info_box.x + info_box.width // 2 - surf.get_width() // 2,
                               info_box.y + 50))

        # --- Финальное сообщение ---
        if self.phase == self.PHASE_RESULT and self.result_msg:
            self._draw_result_overlay(screen, W, H)

    def _draw_hp_bar(self, screen, x, y, w, h, hp, max_hp, label, color, bg):
        """Рисует полоску HP."""
        pygame.draw.rect(screen, bg, (x, y, w, h), border_radius=4)
        fill_w = int(w * max(0, hp) / max(1, max_hp))
        pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
        pygame.draw.rect(screen, (80, 80, 80), (x, y, w, h), 1, border_radius=4)
        # Убираем отрисовку label, так как текст HP рисуется отдельно

    def _draw_attack_icons(self, screen, W, H, info_box):
        """Рисует иконки доступных атак внутри нижнего блока."""
        attacks = [
            ("1", "add", "Сложение"),
            ("2", "sub", "Вычитание"),
            ("3", "mul", "Умножение"),
            ("4", "div", "Деление"),
        ]
        total = len([a for a in attacks if self._is_attack_available(a[1])])
        if total == 0:
            return

        slot_w = 110
        start_x = info_box.x + info_box.width // 2 - (total * slot_w) // 2
        drawn = 0

        for key, att, name in attacks:
            if not self._is_attack_available(att):
                continue
            sx = start_x + drawn * slot_w
            sy = info_box.y + info_box.height - 50

            # Фон иконки
            color = (50, 50, 80) if self.phase == self.PHASE_PLAYER_CHOOSE else (30, 30, 50)
            pygame.draw.rect(screen, color, (sx, sy, 100, 40), border_radius=6)
            pygame.draw.rect(screen, (80, 80, 120), (sx, sy, 100, 40), 1, border_radius=6)

            # Текст
            key_surf = self.font_hint.render(f"[{key}]", True, COLOR_YELLOW)
            name_surf = self.font_hint.render(name, True, COLOR_WHITE)
            screen.blit(key_surf, (sx + 8, sy + 6))
            screen.blit(name_surf, (sx + 8, sy + 22))
            drawn += 1

    def _draw_problem(self, screen, W, H):
        """Рисует блок математического примера по центру экрана."""
        box_w, box_h = 420, 120
        box_x = W // 2 - box_w // 2
        box_y = H // 2 - box_h // 2

        s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        s.fill((10, 10, 30, 230))
        screen.blit(s, (box_x, box_y))
        pygame.draw.rect(screen, (80, 80, 160), (box_x, box_y, box_w, box_h), 2, border_radius=8)

        lines = self.problem_text.split("\n")
        for i, line in enumerate(lines):
            color = COLOR_YELLOW if i == 0 else COLOR_WHITE
            surf = self.font_mid.render(line, True, color)
            screen.blit(surf, (box_x + 20, box_y + 15 + i * 30))

        # Поле ввода
        buf_text = self.answer_buffer + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " ")
        buf_surf = self.font_big.render(buf_text, True, COLOR_WHITE)
        inp_x = box_x + box_w // 2 - buf_surf.get_width() // 2
        inp_y = box_y + box_h - 50
        pygame.draw.line(screen, (100, 100, 200),
                         (box_x + 20, inp_y + 36),
                         (box_x + box_w - 20, inp_y + 36), 2)
        screen.blit(buf_surf, (inp_x, inp_y))
        # Убираем подсказку - она теперь в нижнем блоке

    def _draw_result_overlay(self, screen, W, H):
        """Рисует финальный экран поверх всего."""
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        victory = self.hp_boss <= 0
        color = COLOR_GREEN if victory else COLOR_RED
        surf = self.font_big.render(self.result_msg, True, color)
        screen.blit(surf, (W // 2 - surf.get_width() // 2, H // 2 - 30))

        sub = self.font_small.render("Возврат через секунду...", True, COLOR_GRAY)
        screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + 20))