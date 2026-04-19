"""
Модуль states/battle.py
Состояние боя с боссом.

Содержит класс BattleState, который реализует:
    - Пошаговую боевую систему с математическими атаками
    - Параметры игрока: HP_player, X (урон игрока)
    - Параметры босса: HP_boss, Y (урон босса)
    - 4 типа атак: сложение, вычитание, умножение, деление
    - Генерацию математических примеров от босса
    - Разблокировку атак по мере роста X
    - Экран поражения и победы

Управление в бою:
    1/2/3/4  — выбор атаки
    0-9      — ввод ответа на пример
    ENTER    — подтвердить ответ
    BACKSPACE — удалить последний символ ввода

Порядок хода:
    1. Игрок выбирает атаку клавишей 1-4
    2. Если атака требует примера — вводит ответ
    3. Применяется эффект атаки игрока
    4. Босс случайно выбирает свою атаку
    5. Если атака босса не базовая — появляется пример
    6. Игрок вводит ответ
    7. Применяется эффект атаки босса
    8. Проверка победы / поражения
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

# Стартовое HP игрока в зависимости от номера босса (boss_id = 1..3)
PLAYER_HP_START = {1: 80, 2: 100, 3: 120}

# Стартовое HP боссов
BOSS_HP_START = {1: 60, 2: 90, 3: 120}

# Стартовый урон Y босса
BOSS_Y_START = {1: 5, 2: 8, 3: 12}

# Диапазон n для сложения босса: n ∈ [n_min, n_max]
BOSS_ADD_N_MIN = {1: 2, 2: 3, 3: 4}
BOSS_ADD_N_MAX = {1: 6, 2: 7, 3: 8}

# Пороги разблокировки атак игрока
UNLOCK_X_SUB = 7    # вычитание: X >= 7
UNLOCK_X_MUL = 10   # умножение: X >= 10
UNLOCK_X_DIV = 12   # деление:   X >= 12

# Каждые сколько ходов босс использует особую атаку
BOSS_ADD_INTERVAL  = 2   # сложение раз в 2 хода
BOSS_SUB_INTERVAL  = 3   # вычитание раз в 3-4 хода
BOSS_MUL_INTERVAL  = 4   # умножение раз в 4-5 ходов
BOSS_DIV_INTERVAL  = 4   # деление раз в 4-5 ходов


# ---------------------------------------------------------------------------
# Цвета (для fallback-шрифтов; основной стиль — через ресурсы)
# ---------------------------------------------------------------------------
COLOR_WHITE   = (255, 255, 255)
COLOR_BLACK   = (0,   0,   0)
COLOR_RED     = (220, 50,  50)
COLOR_GREEN   = (50,  200, 80)
COLOR_YELLOW  = (240, 200, 40)
COLOR_GRAY    = (120, 120, 120)
COLOR_DARK    = (20,  20,  30)
COLOR_PANEL   = (15,  15,  25, 200)   # полупрозрачный тёмный фон
COLOR_HP_RED  = (200, 40,  40)
COLOR_HP_BG   = (60,  20,  20)
COLOR_HP_GREEN = (40, 180, 60)
COLOR_HP_BOSS_BG = (20, 40, 60)
COLOR_HP_BOSS  = (40, 140, 220)

# Имена атак для отображения
ATTACK_NAMES = {
    "add": "Сложение",
    "sub": "Вычитание",
    "mul": "Умножение",
    "div": "Деление",
}

# Клавиши выбора атак
ATTACK_KEYS = {
    pygame.K_1: "add",
    pygame.K_2: "sub",
    pygame.K_3: "mul",
    pygame.K_4: "div",
}


class BattleState:
    """
    Состояние пошагового боя с боссом.

    Хранит и обновляет все параметры боя согласно спецификации.
    Управляет отображением UI боя: полоски HP, атаки, примеры, ввод.
    По завершению боя передаёт управление обратно в ExploringState
    через game.change_state(GameState.EXPLORING) или в CREDITS.

    Атрибуты:
        game           — ссылка на главный объект Game
        boss_id        — номер текущего босса (1, 2 или 3)
        hp_player      — текущее HP игрока
        hp_boss        — текущее HP босса
        x              — текущий урон игрока
        y              — текущий урон босса
        turn_counter   — счётчик ходов
        phase          — текущая фаза хода (см. константы PHASE_*)
        pending_attack — выбранная атака игрока ("add"/"sub"/"mul"/"div")
        mul_next_double— флаг: следующая атака игрока удвоена (после умножения)
        div_next_half  — флаг: следующая атака босса ослаблена вдвое (после деления)
        answer_buffer  — строка вводимого ответа
        correct_answer — правильный ответ на текущий пример
        problem_text   — текст отображаемого примера
        error_msg      — текст ошибки (пустая строка = нет ошибки)
        error_timer    — время отображения ошибки
        result_msg     — финальное сообщение (победа / поражение)
        result_timer   — задержка перед выходом из боя
        add_unlocked   — доступна ли атака "Сложение"
        sub_unlocked   — доступна ли атака "Вычитание"
        mul_unlocked   — доступна ли атака "Умножение"
        div_unlocked   — доступна ли атака "Деление"
    """

    # Фазы хода
    PHASE_PLAYER_CHOOSE  = "player_choose"   # игрок выбирает атаку
    PHASE_PLAYER_ANSWER  = "player_answer"   # игрок вводит ответ на пример (если нужно)
    PHASE_BOSS_ATTACK    = "boss_attack"     # ход босса (базовая атака)
    PHASE_BOSS_ANSWER    = "boss_answer"     # игрок отвечает на пример босса
    PHASE_RESULT         = "result"          # отображение победы / поражения
    PHASE_UNLOCK_ANIM    = "unlock_anim"     # краткая анимация разблокировки

    def __init__(self, game):
        """
        Инициализация состояния боя.

        Аргументы:
            game: ссылка на главный объект Game
        """
        self.game = game

        # Корневая директория проекта (для загрузки ресурсов)
        self.root_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # --- Параметры боя (заполняются в enter()) ---
        self.boss_id      = 1
        self.hp_player    = 0
        self.hp_boss      = 0
        self.x            = 0     # урон игрока
        self.y            = 0     # урон босса
        self.turn_counter = 0

        # --- Флаги особых состояний ---
        self.mul_next_double = False  # следующая атака сложение/вычитание x2
        self.div_next_half   = False  # следующий удар босса делится на 2

        # --- Разблокировка атак ---
        self.add_unlocked = False
        self.sub_unlocked = False
        self.mul_unlocked = False
        self.div_unlocked = False

        # --- Очередь разблокировки (пример для открытия атаки) ---
        self._pending_unlock_attack = None  # "add"/"sub"/"mul"/"div"
        self._unlock_stage = 0             # 0=не начато, 1=пример выдан, 2=первая ошибка

        # --- Ввод ответа ---
        self.answer_buffer  = ""
        self.correct_answer = 0
        self.problem_text   = ""

        # --- Текущая атака ---
        self.pending_attack  = None   # выбранная атака игрока
        self._boss_attack    = None   # выбранная атака босса

        # --- Сообщения ---
        self.error_msg   = ""
        self.error_timer = 0.0
        self.result_msg  = ""
        self.result_timer = 0.0
        self._unlock_msg  = ""
        self._unlock_timer = 0.0

        # --- Фаза хода ---
        self.phase = self.PHASE_PLAYER_CHOOSE

        # --- Спрайты и шрифты (загружаются при enter()) ---
        self._fonts_loaded = False
        self.font_big    = None
        self.font_mid    = None
        self.font_small  = None
        self.font_hint   = None
        self.boss_sprite  = None
        self.player_sprite = None

        # --- Фоновая поверхность ---
        self.bg_surface = None

    # -----------------------------------------------------------------------
    # Вход в состояние боя
    # -----------------------------------------------------------------------

    def enter(self, boss_id: int, saved_x: int = 0):
        """
        Инициализирует бой с указанным боссом.

        Вызывается из ExploringState перед game.change_state(GameState.BATTLE).

        Аргументы:
            boss_id  — номер босса (1, 2, 3); берётся как current_location - 2
            saved_x  — сохранённый урон игрока (после победы над предыдущим боссом)
        """
        self.boss_id      = int(boss_id)
        self.hp_player    = PLAYER_HP_START.get(self.boss_id, 80)
        self.hp_boss      = BOSS_HP_START.get(self.boss_id, 60)
        # X: для первого босса = 0, для следующих = saved_x / 2 (минимум 1)
        if self.boss_id == 1:
            self.x = 0
        else:
            self.x = max(1, saved_x // 2) if saved_x > 0 else 0
        self.y            = BOSS_Y_START.get(self.boss_id, 5)
        self.turn_counter = 0

        self.mul_next_double = False
        self.div_next_half   = False

        # Разблокировка атак — сложение открывается после первого примера
        self.add_unlocked = False
        self.sub_unlocked = (self.x >= UNLOCK_X_SUB)
        self.mul_unlocked = (self.boss_id >= 2 and self.x >= UNLOCK_X_MUL)
        self.div_unlocked = (self.boss_id >= 3 and self.x >= UNLOCK_X_DIV)

        self._pending_unlock_attack = None
        self._unlock_stage = 0

        self.answer_buffer  = ""
        self.correct_answer = 0
        self.problem_text   = ""
        self.pending_attack = None
        self._boss_attack   = None

        self.error_msg    = ""
        self.error_timer  = 0.0
        self.result_msg   = ""
        self.result_timer = 0.0
        self._unlock_msg  = ""
        self._unlock_timer = 0.0

        # В самом начале — проверяем нужно ли открыть сложение
        if not self.add_unlocked:
            # Выдаём пример на сложение для разблокировки
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

        self.font_big   = load_font(36)
        self.font_mid   = load_font(26)
        self.font_small = load_font(20)
        self.font_hint  = load_font(18)

        # Спрайт босса
        boss_names = {1: "boss1", 2: "boss2", 3: "boss3"}
        boss_name = boss_names.get(self.boss_id, "boss1")
        boss_path = os.path.join(
            self.root_dir, "assets", f"location{self.boss_id + 2}", f"{boss_name}.png"
        )
        try:
            img = pygame.image.load(boss_path).convert_alpha()
            self.boss_sprite = pygame.transform.scale(img, (120, 120))
        except Exception:
            self.boss_sprite = None

        # Спрайт игрока (Билли)
        player_path = os.path.join(self.root_dir, "assets", "location1", "Billy.png")
        try:
            img = pygame.image.load(player_path).convert_alpha()
            # Берём первый кадр из спрайт-листа (предполагаем горизонтальный)
            frame_w = img.get_width() // 4 if img.get_width() > img.get_height() else img.get_width()
            frame = img.subsurface(pygame.Rect(0, 0, frame_w, img.get_height()))
            self.player_sprite = pygame.transform.scale(frame, (80, 80))
        except Exception:
            self.player_sprite = None

        self._fonts_loaded = True

    # -----------------------------------------------------------------------
    # Генерация математических примеров
    # -----------------------------------------------------------------------

    def _gen_unlock_problem(self, attack_type: str):
        """
        Генерирует пример для разблокировки атаки.

        Возвращает (problem_text, correct_answer).
        """
        problems = {
            "add": lambda: self._make_problem("+"),
            "sub": lambda: self._make_problem("-"),
            "mul": lambda: self._make_problem("*"),
            "div": lambda: self._make_problem("/"),
        }
        return problems.get(attack_type, lambda: self._make_problem("+"))()

    def _make_problem(self, op: str):
        """Создаёт простой пример с операцией op. Ответ — целое положительное."""
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
        """
        Начинает процедуру разблокировки атаки: генерирует пример.
        """
        self._pending_unlock_attack = attack_type
        self._unlock_stage = 1
        text, ans = self._gen_unlock_problem(attack_type)
        self.problem_text   = f"[Разблокировка: {ATTACK_NAMES[attack_type]}]\n{text}"
        self.correct_answer = ans
        self.answer_buffer  = ""
        self.error_msg      = ""

    # -----------------------------------------------------------------------
    # Атаки игрока
    # -----------------------------------------------------------------------

    def _apply_player_attack(self, attack_type: str):
        """
        Применяет выбранную атаку игрока согласно спецификации.

        add:  X = X + 1; HP_boss -= X  (сложение увеличивает урон)
        sub:  Y -= 2; HP_boss -= 2     (вычитание бьёт напрямую)
        mul:  устанавливает флаг удвоения следующей атаки
        div:  устанавливает флаг ослабления следующего удара босса
        """
        multiplier = 2 if self.mul_next_double else 1
        self.mul_next_double = False  # сбрасываем флаг

        if attack_type == "add":
            gain = 1 * multiplier
            self.x += gain
            self.hp_boss -= self.x
            self.game.audio.play_sound(SoundType.BOSS_HIT)
            self._show_unlock_anim(f"+{gain} к урону! HP босса -{self.x}")

        elif attack_type == "sub":
            dmg = 2 * multiplier
            self.y = max(0, self.y - dmg)
            self.hp_boss -= dmg
            self.game.audio.play_sound(SoundType.BOSS_HIT)
            self._show_unlock_anim(f"Y bosса -{dmg}, HP bosса -{dmg}")

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
        """
        Босс выбирает атаку на основе счётчика ходов и доступных атак.

        Возвращает строку: "basic" / "add" / "sub" / "mul" / "div"
        """
        tc = self.turn_counter

        # Деление — только у 3-го босса, раз в 4-5 ходов
        if self.boss_id >= 3 and tc % BOSS_DIV_INTERVAL == 0 and tc > 0:
            return "div"

        # Умножение — у 2-го и 3-го, раз в 4-5 ходов
        if self.boss_id >= 2 and tc % BOSS_MUL_INTERVAL == 0 and tc > 0:
            return "mul"

        # Вычитание — у всех боссов, раз в 3-4 хода
        if tc % BOSS_SUB_INTERVAL == 0 and tc > 0:
            return "sub"

        # Сложение — у всех, раз в 2 хода
        if tc % BOSS_ADD_INTERVAL == 0 and tc > 0:
            return "add"

        return "basic"

    def _apply_boss_attack_result(self, attack_type: str, correct: bool):
        """
        Применяет результат атаки босса.

        correct=True  — игрок ответил правильно → стандартный эффект
        correct=False — ошибка → штрафной эффект
        """
        n_min = BOSS_ADD_N_MIN.get(self.boss_id, 2)
        n_max = BOSS_ADD_N_MAX.get(self.boss_id, 6)
        n     = random.randint(n_min, n_max)

        # Применяем ослабление от деления игрока (div_next_half)
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
                # Следующий базовый удар x2 (сохраняем флаг)
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
                self.y  = int(self.y * 1.5)
                self.game.audio.play_sound(SoundType.DAMAGE)
                self._show_unlock_anim("Ошибка! X ÷2, Y ×1.5")

    # -----------------------------------------------------------------------
    # Разблокировка атак
    # -----------------------------------------------------------------------

    def _check_unlock_conditions(self):
        """
        Проверяет, не пора ли начать разблокировку следующей атаки.
        Вызывается после каждого хода игрока.
        """
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
        """
        Обрабатывает ответ игрока на пример разблокировки.
        """
        attack = self._pending_unlock_attack

        if correct:
            # Разблокируем атаку
            setattr(self, f"{attack}_unlocked", True)
            self._unlock_msg   = f"Атака «{ATTACK_NAMES[attack]}» разблокирована!"
            self._unlock_timer = 2.5
            self._pending_unlock_attack = None
            self._unlock_stage = 0
            self.problem_text  = ""
            self.answer_buffer = ""
            self.error_msg     = ""
            self.game.audio.play_sound(SoundType.VICTORY)

            # Переходим к ходу игрока (если здоровья больше 0)
            if self.hp_boss > 0 and self.hp_player > 0:
                self.phase = self.PHASE_PLAYER_CHOOSE
        else:
            if self._unlock_stage == 1:
                # Первая ошибка — ещё одна попытка
                self._unlock_stage = 2
                self.error_msg   = "Неверно! Попробуй ещё раз."
                self.error_timer = 2.0
                # Перегенерируем пример (можно оставить тот же)
                text, ans = self._gen_unlock_problem(attack)
                self.problem_text   = f"[Разблокировка: {ATTACK_NAMES[attack]}]\n{text}"
                self.correct_answer = ans
                self.answer_buffer  = ""
            else:
                # Вторая ошибка — возврат в исследование
                self.error_msg   = "Не удалось разблокировать атаку. Возврат..."
                self.error_timer = 2.0
                self._pending_unlock_attack = None
                self._unlock_stage = 0
                # Задержка перед выходом
                self.result_msg   = ""
                self.result_timer = 2.5
                self.phase        = self.PHASE_RESULT

    # -----------------------------------------------------------------------
    # Победа / Поражение
    # -----------------------------------------------------------------------

    def _check_battle_end(self):
        """Проверяет условия окончания боя."""
        if self.hp_boss <= 0:
            # Победа
            if self.boss_id == 3:
                # Победа над финальным боссом → CREDITS
                self.result_msg   = "Ты победил! Конец игры!"
                self.result_timer = 3.0
                self.phase        = self.PHASE_RESULT
                self.game.audio.play_sound(SoundType.VICTORY)
                self.game.audio.play_music(MusicTrack.VICTORY)
                self._victory_goto_credits = True
            else:
                self.result_msg   = f"Босс #{self.boss_id} повержен!"
                self.result_timer = 3.0
                self.phase        = self.PHASE_RESULT
                self.game.audio.play_sound(SoundType.VICTORY)
                self.game.audio.play_music(MusicTrack.VICTORY)
                self._victory_goto_credits = False
            return True

        if self.hp_player <= 0:
            # Поражение
            self.result_msg   = "Wasted. Попробуй снова."
            self.result_timer = 3.0
            self.phase        = self.PHASE_RESULT
            self.game.audio.play_sound(SoundType.DEFEAT)
            self._victory_goto_credits = False
            return True

        return False

    def _exit_battle(self, victory: bool):
        """
        Выходит из боя обратно в исследование или в CREDITS.
        """
        exploring = self.game.states.get(GameState.EXPLORING)

        if victory and self.boss_id == 3:
            # Финальная победа
            credits_state = self.game.states.get(GameState.CREDITS)
            if credits_state:
                self.game.change_state(GameState.CREDITS)
            return

        if victory:
            # Отмечаем победу над боссом
            location_id = self.boss_id + 2
            self.game.mark_boss_defeated(location_id)

            # Передаём сохранённый X в ExploringState для следующего боя
            if exploring:
                exploring._saved_battle_x = max(1, self.x // 2)

            self.game.audio.play_music(MusicTrack.EXPLORING)
            self.game.change_state(GameState.EXPLORING)
        else:
            # Поражение — перезапускаем текущую локацию
            self.game.audio.play_music(MusicTrack.EXPLORING)
            self.game.change_state(GameState.EXPLORING)

    # -----------------------------------------------------------------------
    # Вспомогательные
    # -----------------------------------------------------------------------

    def _show_unlock_anim(self, msg: str):
        self._unlock_msg   = msg
        self._unlock_timer = 2.0

    def _validate_answer(self) -> bool:
        """Проверяет введённый ответ. Возвращает True если верно."""
        try:
            return int(self.answer_buffer) == self.correct_answer
        except ValueError:
            return False

    # -----------------------------------------------------------------------
    # Обработка событий
    # -----------------------------------------------------------------------

    def handle_events(self, events):
        """
        Обрабатывает события клавиатуры.

        В фазе PLAYER_CHOOSE: 1-4 выбирают атаку.
        В фазе PLAYER_ANSWER / BOSS_ANSWER: цифры вводят ответ, ENTER подтверждает.
        """
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            # --- Фаза выбора атаки ---
            if self.phase == self.PHASE_PLAYER_CHOOSE:
                attack = ATTACK_KEYS.get(event.key)
                if attack and self._is_attack_available(attack):
                    self.pending_attack = attack

                    # Атаки сложение и вычитание просто применяются
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

            # --- Фаза ввода ответа (разблокировка или атака босса) ---
            elif self.phase in (self.PHASE_PLAYER_ANSWER, self.PHASE_BOSS_ANSWER):
                if event.key == pygame.K_BACKSPACE:
                    self.answer_buffer = self.answer_buffer[:-1]

                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    if self.answer_buffer:
                        self._submit_answer()

                elif event.unicode.isdigit():
                    if len(self.answer_buffer) < 3:  # ограничиваем 3 цифрами
                        self.answer_buffer += event.unicode

    def _is_attack_available(self, attack: str) -> bool:
        """Возвращает True, если атака доступна игроку."""
        return getattr(self, f"{attack}_unlocked", False)

    def _submit_answer(self):
        """Обрабатывает подтверждение ответа игрока."""
        correct = self._validate_answer()

        if self.phase == self.PHASE_PLAYER_ANSWER:
            # Это ответ на разблокировку
            self._resolve_unlock_answer(correct)

        elif self.phase == self.PHASE_BOSS_ANSWER:
            # Это ответ на атаку босса
            self._apply_boss_attack_result(self._boss_attack, correct)
            if not correct:
                self.error_msg   = "Ошибка! Попробуй ещё раз."
                self.error_timer = 1.5
            self.answer_buffer = ""
            self.problem_text  = ""
            self._boss_attack  = None

            if not self._check_battle_end():
                self.phase = self.PHASE_PLAYER_CHOOSE

    def _do_boss_turn(self):
        """Выполняет ход босса."""
        boss_attack = self._choose_boss_attack()

        if boss_attack == "basic":
            # Применяем ослабление от div_next_half, если есть
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
            # Особая атака — требует ответа игрока
            self._boss_attack = boss_attack
            text, ans = self._gen_boss_problem(boss_attack)
            self.problem_text   = f"[Атака босса: {ATTACK_NAMES[boss_attack]}]\n{text}"
            self.correct_answer = ans
            self.answer_buffer  = ""
            self.error_msg      = ""
            self.phase          = self.PHASE_BOSS_ANSWER

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
                # Время вышло — выходим из боя
                victory = self.hp_boss <= 0
                self._exit_battle(victory)

    # -----------------------------------------------------------------------
    # Отрисовка
    # -----------------------------------------------------------------------

    def draw(self, screen: pygame.Surface):
        """
        Рисует экран боя.

        Структура экрана (800x608):
            Верх-лево:  HP и урон игрока
            Верх-право: HP и урон босса (над спрайтом)
            Центр:      спрайты игрока и босса
            Низ-центр:  математический пример и поле ввода
            Низ-полоса: иконки доступных атак (1-Слож, 2-Выч, 3-Умн, 4-Дел)
            Центр-поверх: сообщения об ошибке / разблокировке / итоге
        """
        if not self._fonts_loaded:
            self._load_assets()

        W, H = screen.get_width(), screen.get_height()  # 800, 608

        # --- Фон ---
        screen.fill((18, 18, 28))

        # --- Декоративная линия разделения арены ---
        pygame.draw.line(screen, (40, 40, 60), (0, H // 2), (W, H // 2), 1)

        # --- Спрайты ---
        # Игрок — слева снизу
        if self.player_sprite:
            px = 80
            py = H // 2 - 20
            screen.blit(self.player_sprite, (px, py))

        # Босс — справа
        if self.boss_sprite:
            bx = W - 200
            by = H // 2 - 60
            screen.blit(self.boss_sprite, (bx, by))

        # --- HP-бары ---
        self._draw_hp_bar(
            screen, x=20, y=20, w=220, h=18,
            hp=self.hp_player, max_hp=PLAYER_HP_START.get(self.boss_id, 80),
            label="HP Игрока", color=COLOR_HP_GREEN, bg=COLOR_HP_BG
        )
        # X под HP игрока
        x_surf = self.font_small.render(f"Урон X: {self.x}", True, COLOR_YELLOW)
        screen.blit(x_surf, (20, 44))

        self._draw_hp_bar(
            screen, x=W - 240, y=20, w=220, h=18,
            hp=self.hp_boss, max_hp=BOSS_HP_START.get(self.boss_id, 60),
            label="HP Босса", color=COLOR_HP_BOSS, bg=COLOR_HP_BOSS_BG
        )
        # Y над боссом
        y_surf = self.font_small.render(f"Урон Y: {self.y}", True, (100, 180, 255))
        screen.blit(y_surf, (W - 240, 44))

        # --- Иконки атак (нижняя полоса) ---
        self._draw_attack_icons(screen, W, H)

        # --- Пример и поле ввода ---
        if self.problem_text:
            self._draw_problem(screen, W, H)

        # --- Подсказка фазы ---
        if self.phase == self.PHASE_PLAYER_CHOOSE:
            hint = self.font_hint.render("Выбери атаку: 1-Слож  2-Выч  3-Умн  4-Дел",
                                         True, COLOR_GRAY)
            screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 80))

        # --- Сообщение разблокировки / эффекта ---
        if self._unlock_msg:
            surf = self.font_mid.render(self._unlock_msg, True, COLOR_GREEN)
            screen.blit(surf, (W // 2 - surf.get_width() // 2, H // 2 - 80))

        # --- Сообщение ошибки ---
        if self.error_msg:
            surf = self.font_mid.render(self.error_msg, True, COLOR_RED)
            screen.blit(surf, (W // 2 - surf.get_width() // 2, H // 2 - 50))

        # --- Финальное сообщение ---
        if self.phase == self.PHASE_RESULT and self.result_msg:
            self._draw_result_overlay(screen, W, H)

    def _draw_hp_bar(self, screen, x, y, w, h, hp, max_hp, label, color, bg):
        """Рисует полоску HP с подписью."""
        pygame.draw.rect(screen, bg, (x, y, w, h), border_radius=4)
        fill_w = int(w * max(0, hp) / max(1, max_hp))
        pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
        pygame.draw.rect(screen, (80, 80, 80), (x, y, w, h), 1, border_radius=4)
        label_surf = self.font_hint.render(f"{label}: {max(0, hp)}/{max_hp}", True, COLOR_WHITE)
        screen.blit(label_surf, (x, y - 18))

    def _draw_attack_icons(self, screen, W, H):
        """Рисует иконки доступных атак у нижнего края."""
        attacks = [
            ("1", "add", "Сложение"),
            ("2", "sub", "Вычитание"),
            ("3", "mul", "Умножение"),
            ("4", "div", "Деление"),
        ]
        total = len([a for a in attacks if self._is_attack_available(a[1])])
        slot_w = 120
        start_x = W // 2 - (total * slot_w) // 2
        drawn = 0
        for key, att, name in attacks:
            if not self._is_attack_available(att):
                continue
            sx = start_x + drawn * slot_w
            sy = H - 55
            # Фон иконки
            color = (50, 50, 80) if self.phase == self.PHASE_PLAYER_CHOOSE else (30, 30, 50)
            pygame.draw.rect(screen, color, (sx, sy, 110, 44), border_radius=6)
            pygame.draw.rect(screen, (80, 80, 120), (sx, sy, 110, 44), 1, border_radius=6)
            key_surf  = self.font_hint.render(f"[{key}]", True, COLOR_YELLOW)
            name_surf = self.font_hint.render(name, True, COLOR_WHITE)
            screen.blit(key_surf,  (sx + 8,  sy + 6))
            screen.blit(name_surf, (sx + 8,  sy + 24))
            drawn += 1

    def _draw_problem(self, screen, W, H):
        """Рисует блок математического примера и поле ввода."""
        # Фон блока
        box_w, box_h = 420, 120
        box_x = W // 2 - box_w // 2
        box_y = H // 2 + 20

        s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        s.fill((10, 10, 30, 210))
        screen.blit(s, (box_x, box_y))
        pygame.draw.rect(screen, (80, 80, 160), (box_x, box_y, box_w, box_h), 1, border_radius=8)

        # Текст примера (может содержать \n)
        lines = self.problem_text.split("\n")
        for i, line in enumerate(lines):
            color = COLOR_YELLOW if i == 0 else COLOR_WHITE
            surf = self.font_mid.render(line, True, color)
            screen.blit(surf, (box_x + 14, box_y + 10 + i * 30))

        # Поле ввода
        buf_text = self.answer_buffer + ("_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " ")
        buf_surf = self.font_big.render(buf_text, True, COLOR_WHITE)
        inp_x = box_x + box_w // 2 - buf_surf.get_width() // 2
        inp_y = box_y + box_h - 46
        pygame.draw.line(screen, (100, 100, 200),
                         (box_x + 20, inp_y + 36),
                         (box_x + box_w - 20, inp_y + 36), 1)
        screen.blit(buf_surf, (inp_x, inp_y))

        # Подсказка
        hint = self.font_hint.render("Цифры → ответ   ENTER → подтвердить   BACKSPACE → стереть",
                                     True, COLOR_GRAY)
        screen.blit(hint, (W // 2 - hint.get_width() // 2, box_y + box_h + 6))

    def _draw_result_overlay(self, screen, W, H):
        """Рисует финальный экран поверх всего."""
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        victory = self.hp_boss <= 0
        color   = COLOR_GREEN if victory else COLOR_RED
        surf    = self.font_big.render(self.result_msg, True, color)
        screen.blit(surf, (W // 2 - surf.get_width() // 2, H // 2 - 30))

        sub = self.font_small.render("Возврат через секунду...", True, COLOR_GRAY)
        screen.blit(sub, (W // 2 - sub.get_width() // 2, H // 2 + 20))