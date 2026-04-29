"""
src/battle/battle_system.py
Чистая логика пошагового боя — без pygame, без ссылок на game.

Отличия от старой версии (исправлено по документу):
  - HP игрока/босса и Y откорректированы под доку
  - Туториал сложения: фиксированный пример «Y+1=3», ответ=Y, после успеха X=2
  - Туториал вычитания: пример «|X–Y|=?», X не уменьшается при успехе
  - Y скрыт до конца туториала сложения (флаг y_revealed)
  - Интервал вычитания босса: случайный 3–4 хода
"""

import random
from .math_problem import (
    ATTACK_NAMES,
    gen_tutorial_add_problem,
    gen_tutorial_sub_problem,
    gen_boss_problem,
)

# ---------------------------------------------------------------------------
# Константы параметров боссов (строго по документу)
# ---------------------------------------------------------------------------

PLAYER_HP_START = {1: 50,  2: 60,  3: 70}
BOSS_HP_START   = {1: 50,  2: 70,  3: 100}
BOSS_Y_START    = {1: 2,   2: 4,   3: 6}
BOSS_N_MIN      = {1: 2,   2: 3,   3: 4}
BOSS_N_MAX      = {1: 6,   2: 7,   3: 8}

# X-порог для разблокировки атак
UNLOCK_X_SUB = 7
UNLOCK_X_MUL = 10
UNLOCK_X_DIV = 12

# Интервалы атак босса (в ходах)
BOSS_ADD_INTERVAL = 2       # раз в 2 хода
BOSS_SUB_INTERVAL_MIN = 3   # раз в 3–4 хода (случайно)
BOSS_SUB_INTERVAL_MAX = 4
BOSS_MUL_INTERVAL = 4
BOSS_DIV_INTERVAL = 4


# ---------------------------------------------------------------------------
# Фазы боя
# ---------------------------------------------------------------------------

class Phase:
    PLAYER_CHOOSE = "player_choose"   # игрок выбирает атаку (1–4)
    PLAYER_ANSWER = "player_answer"   # игрок вводит ответ на туториал
    BOSS_ANSWER   = "boss_answer"     # игрок вводит ответ на атаку босса
    BOSS_DELAY    = "boss_delay"      # задержка перед ходом босса
    RESULT        = "result"          # финальная заставка победы / поражения


# ---------------------------------------------------------------------------
# Основной класс
# ---------------------------------------------------------------------------

class BattleSystem:
    """
    Вся логика боя. Не знает ничего о pygame и audio.
    BattleState читает публичные поля и вызывает методы on_*.
    """

    def __init__(self, boss_id: int, saved_x: int = 0):
        self.boss_id  = int(boss_id)
        self.saved_x  = saved_x

        # Игровые параметры
        self.hp_player    = 0
        self.hp_boss      = 0
        self.x            = 0   # урон игрока
        self.y            = 0   # урон босса
        self.y_revealed   = False  # Y скрыт до конца туториала сложения
        self.turn_counter = 0

        # Баффы
        self.mul_next_double = False   # следующая атака игрока ×2
        self.div_next_half   = False   # следующий удар босса ÷2
        self._boss_next_mul2 = False   # следующий базовый удар босса ×2

        # Разблокировки атак игрока
        self.add_unlocked = False
        self.sub_unlocked = False
        self.mul_unlocked = False
        self.div_unlocked = False

        # Разблокировка: внутреннее состояние
        self._pending_unlock = None   # "add" / "sub" / "mul" / "div"
        self._unlock_stage   = 0      # 1 = первая попытка, 2 = последняя

        # Пример и ввод
        self.problem_text   = ""
        self.correct_answer = 0
        self.answer_buffer  = ""

        # Текущая атака босса и выбранный N для атаки сложением
        self._boss_attack = None
        self._boss_n      = 0   # N, выбранный при генерации примера сложения

        # Счётчики интервалов атак босса
        self._turns_since_add = 0
        self._turns_since_sub = 0
        self._turns_since_mul = 0
        self._turns_since_div = 0
        # Текущий случайный порог для вычитания босса
        self._sub_threshold = random.randint(BOSS_SUB_INTERVAL_MIN, BOSS_SUB_INTERVAL_MAX)

        # Сообщения для UI
        self.feedback_msg   = ""
        self.feedback_timer = 0.0
        self.error_msg      = ""
        self.error_timer    = 0.0
        self.result_msg     = ""
        self.result_timer   = 0.0

        self.phase   = Phase.PLAYER_CHOOSE
        self.victory = False

        # Лог боя — последние записи
        self.battle_log: list[str] = []
        self.MAX_LOG = 10  # сколько строк хранить

        # Задержка перед ходом босса
        self._boss_delay_timer = 0.0
        BOSS_DELAY_SECONDS = 1.0
    # -----------------------------------------------------------------------
    # Инициализация
    # -----------------------------------------------------------------------

    def enter(self):
        """Инициализирует бой. Вызывать один раз при входе в состояние."""
        self.hp_player = PLAYER_HP_START.get(self.boss_id, 50)
        self.hp_boss   = BOSS_HP_START.get(self.boss_id, 50)
        self.y         = BOSS_Y_START.get(self.boss_id, 2)

        # Первый босс всегда начинает с X=0.
        # Остальные — с сохранённым X ÷ 2 (минимум 1).
        self.x = 0 if self.boss_id == 1 else max(1, self.saved_x // 2)

        # Y скрыт до завершения первого туториала
        self.y_revealed = (self.boss_id != 1)

        self.turn_counter    = 0
        self.mul_next_double = False
        self.div_next_half   = False
        self._boss_next_mul2 = False

        self._turns_since_add = 0
        self._turns_since_sub = 0
        self._turns_since_mul = 0
        self._turns_since_div = 0
        self._sub_threshold = random.randint(BOSS_SUB_INTERVAL_MIN, BOSS_SUB_INTERVAL_MAX)

        # Разблокировки: у первого босса всё с нуля.
        # У последующих — сохранённый X мог уже превысить пороги.
        self.add_unlocked = False
        self.sub_unlocked = (self.x >= UNLOCK_X_SUB)
        self.mul_unlocked = (self.boss_id >= 2 and self.x >= UNLOCK_X_MUL)
        self.div_unlocked = (self.boss_id >= 3 and self.x >= UNLOCK_X_DIV)

        self._pending_unlock = None
        self._unlock_stage   = 0
        self.answer_buffer   = ""
        self.problem_text    = ""
        self._boss_attack    = None
        self._boss_n         = 0

        self.feedback_msg   = ""
        self.feedback_timer = 0.0
        self.error_msg      = ""
        self.error_timer    = 0.0
        self.result_msg     = ""
        self.result_timer   = 0.0
        self.victory        = False

        # Первый ход: туториал сложения (если ещё не открыто)
        if not self.add_unlocked:
            self._start_unlock("add")
            self.phase = Phase.PLAYER_ANSWER
        else:
            self.phase = Phase.PLAYER_CHOOSE

    # -----------------------------------------------------------------------
    # Обновление таймеров
    # -----------------------------------------------------------------------

    def update(self, dt: float):
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            if self.feedback_timer <= 0:
                self.feedback_msg = ""

        if self.error_timer > 0:
            self.error_timer -= dt
            if self.error_timer <= 0:
                self.error_msg = ""

        # BattleState сам смотрит на result_timer <= 0 и делает переход
        if self.phase == Phase.RESULT and self.result_timer > 0:
            self.result_timer -= dt

        # Задержка перед ходом босса
        if self.phase == Phase.BOSS_DELAY:
            self._boss_delay_timer -= dt
            if self._boss_delay_timer <= 0:
                self.phase = Phase.PLAYER_CHOOSE
                self._do_boss_turn()

    # -----------------------------------------------------------------------
    # записи в лог
    # -----------------------------------------------------------------------

    def _log(self, msg: str):
        """Добавляет запись в лог боя."""
        self.battle_log.append(msg)
        if len(self.battle_log) > self.MAX_LOG:
            self.battle_log.pop(0)

    # -----------------------------------------------------------------------
    # Ввод: атака игрока (клавиши 1–4)
    # -----------------------------------------------------------------------

    def on_attack_key(self, attack_type: str) -> bool:
        """Возвращает True если атака применена."""
        if self.phase != Phase.PLAYER_CHOOSE:
            return False
        if not self._is_unlocked(attack_type):
            return False

        self._apply_player_attack(attack_type)
        self.turn_counter += 1

        if not self._check_end():
            self._check_unlock_conditions()
            if self.phase == Phase.PLAYER_CHOOSE:
                # Запускаем задержку вместо мгновенного хода босса
                self.phase = Phase.BOSS_DELAY
                self._boss_delay_timer = 1.0
        return True

    # -----------------------------------------------------------------------
    # Ввод: ответ на пример
    # -----------------------------------------------------------------------

    def on_digit(self, ch: str):
        if self.phase in (Phase.PLAYER_ANSWER, Phase.BOSS_ANSWER):
            if len(self.answer_buffer) < 4 and ch.isdigit():
                self.answer_buffer += ch

    def on_backspace(self):
        self.answer_buffer = self.answer_buffer[:-1]

    def on_confirm(self) -> bool:
        if self.phase not in (Phase.PLAYER_ANSWER, Phase.BOSS_ANSWER):
            return False
        if not self.answer_buffer:
            return False

        correct = self._validate()
        if self.phase == Phase.PLAYER_ANSWER:
            self._resolve_unlock(correct)
        else:
            self._resolve_boss_answer(correct)
        return True

    # -----------------------------------------------------------------------
    # Атаки игрока
    # -----------------------------------------------------------------------

    def _apply_player_attack(self, attack_type: str):
        mult = 2 if self.mul_next_double else 1
        self.mul_next_double = False

        if attack_type == "add":
            # X = X + 1 (×2 если бафф), HP босса -= новый X
            self.x += 1 * mult
            self.hp_boss -= self.x
            msg = f"Билли: Сложение +{mult*1} X, урон {self.x}"
            self._feedback(msg)
            self._log(msg)

        elif attack_type == "sub":
            # Y = Y – 2 (×2 если бафф), HP босса -= 2 (×2 если бафф)
            dmg = 2 * mult
            self.y = max(0, self.y - dmg)
            self.hp_boss -= dmg
            msg = f"Билли: Вычитание Y-{dmg}, урон {dmg}"
            self._feedback(msg)
            self._log(msg)

        elif attack_type == "mul":
            # Бафф: следующая атака ×2
            self.mul_next_double = True
            msg = "Билли: Умножение — след. атака ×2"
            self._feedback(msg)
            self._log(msg)

        elif attack_type == "div":
            # Бафф: следующий удар босса ÷2
            self.div_next_half = True
            msg = "Билли: Деление — след. удар босса ÷2"
            self._feedback(msg)
            self._log(msg)

    # -----------------------------------------------------------------------
    # Ход босса
    # -----------------------------------------------------------------------

    def _do_boss_turn(self):
        attack = self._choose_boss_attack()

        if attack == "basic":
            divisor = 2 if self.div_next_half else 1
            self.div_next_half   = False
            mult = 2 if self._boss_next_mul2 else 1
            self._boss_next_mul2 = False
            dmg = max(1, (self.y * mult) // divisor)
            self.hp_player -= dmg
            msg = f"Босс: базовый удар -{dmg} HP"
            self._feedback(msg)
            self._log(msg)
            self._check_end()
        else:
            self._boss_attack = attack

            if attack == "add":
                # Пример вида «Y + N = ?» с реальным текущим Y
                n = random.randint(
                    BOSS_N_MIN.get(self.boss_id, 2),
                    BOSS_N_MAX.get(self.boss_id, 6),
                )
                self._boss_n        = n
                self.problem_text   = f"[Атака босса: Сложение]\n{self.y} + {n} = ?"
                self.correct_answer = self.y + n
            else:
                self._boss_n = 0
                text, ans = gen_boss_problem(attack)
                self.problem_text   = text
                self.correct_answer = ans

            self.answer_buffer = ""
            self.error_msg     = ""
            self.phase = Phase.BOSS_ANSWER

    def _choose_boss_attack(self) -> str:
        """
        Выбирает тип атаки босса на основе счётчиков ходов.
        Вычитание: случайный порог 3–4 хода.
        Остальные: фиксированные интервалы.
        """
        # Деление (только босс 3)
        if self.boss_id >= 3:
            self._turns_since_div += 1
            if self._turns_since_div >= BOSS_DIV_INTERVAL:
                self._turns_since_div = 0
                return "div"

        # Умножение (только босс 2+)
        if self.boss_id >= 2:
            self._turns_since_mul += 1
            if self._turns_since_mul >= BOSS_MUL_INTERVAL:
                self._turns_since_mul = 0
                return "mul"

        # Вычитание (случайный интервал 3–4)
        if self.sub_unlocked:  # появляется только после разблокировки у игрока
            self._turns_since_sub += 1
            if self._turns_since_sub >= self._sub_threshold:
                self._turns_since_sub = 0
                self._sub_threshold = random.randint(
                    BOSS_SUB_INTERVAL_MIN, BOSS_SUB_INTERVAL_MAX
                )
                return "sub"

        # Сложение (каждые 2 хода)
        self._turns_since_add += 1
        if self._turns_since_add >= BOSS_ADD_INTERVAL:
            self._turns_since_add = 0
            return "add"

        return "basic"

    def _resolve_boss_answer(self, correct: bool):
        self._apply_boss_effect(self._boss_attack, correct)
        if not correct:
            self._set_error("Ошибка!")
        self.answer_buffer = ""
        self.problem_text  = ""
        self._boss_attack  = None
        if not self._check_end():
            self.phase = Phase.PLAYER_CHOOSE

    def _apply_boss_effect(self, attack: str, correct: bool):
        if attack == "add":
            # N уже был выбран при генерации примера и показан игроку
            n = self._boss_n
            delta = n if correct else n * 2
            self.y += delta
            msg = f"Босс: Y+{delta} → Y={self.y}" + ("" if correct else " (ошибка!)")
            self._feedback(msg)
            self._log(msg)

        elif attack == "sub":
            # Правильно: X -= 2; Ошибка: X = X // 2
            if correct:
                self.x = max(0, self.x - 2)
                msg = f"Босс: X-2 → X={self.x}"
            else:
                self.x = max(0, self.x // 2)
                msg = f"Босс: X÷2 → X={self.x} (ошибка!)"
            self._feedback(msg)
            self._log(msg)

        elif attack == "mul":
            # Правильно: следующий удар босса ×2
            # Ошибка: X = X ÷ 1.5 (вверх), Y = Y × 2
            if correct:
                self._boss_next_mul2 = True
                msg = "Босс: след. удар ×2!"
            else:
                self.x = max(0, int(self.x / 1.5))
                self.y = int(self.y * 2)
                msg = f"Босс: X÷2={self.x}, Y×1.5={self.y} (ошибка!)"
            self._feedback(msg)
            self._log(msg)

        elif attack == "div":
            # Правильно: X = X ÷ 2
            # Ошибка: X = X ÷ 2, Y = Y × 1.5 (вниз)
            if correct:
                self.x = max(0, self.x // 2)
                self._feedback(f"Босс: X ÷ 2 → X = {self.x}")
            else:
                self.x = max(0, self.x // 2)
                self.y = int(self.y * 1.5)
                self._feedback(f"Ошибка! X ÷ 2 = {self.x}, Y × 1.5 = {self.y}")

    # -----------------------------------------------------------------------
    # Разблокировка атак (туториалы)
    # -----------------------------------------------------------------------

    def _start_unlock(self, attack_type: str):
        """Запускает туториал для указанной атаки."""
        self._pending_unlock = attack_type
        self._unlock_stage   = 1
        self.answer_buffer   = ""
        self.error_msg       = ""

        if attack_type == "add":
            # Фиксированный пример: «Y + 1 = {y+1}», ответ = Y
            text, ans = gen_tutorial_add_problem(self.y)
            self.problem_text   = f"[Обучение: Сложение]\n{text}"
            self.correct_answer = ans

        elif attack_type == "sub":
            # Пример с текущими значениями: «|X – Y| = ?»
            text, ans = gen_tutorial_sub_problem(self.x, self.y)
            self.problem_text   = f"[Обучение: Вычитание]\n{text}"
            self.correct_answer = ans

        else:
            # Умножение и деление — случайные примеры (боссы 2–3)
            from .math_problem import make_problem, _OP_MAP
            op = _OP_MAP.get(attack_type, "+")
            text, ans = make_problem(op)
            self.problem_text   = f"[Обучение: {ATTACK_NAMES[attack_type]}]\n{text}"
            self.correct_answer = ans

    def _check_unlock_conditions(self):
        """Проверяет, нужно ли показать туториал для новой атаки."""
        if not self.sub_unlocked and self.x >= UNLOCK_X_SUB:
            self._start_unlock("sub")
            self.phase = Phase.PLAYER_ANSWER

        elif not self.mul_unlocked and self.boss_id >= 2 and self.x >= UNLOCK_X_MUL:
            self._start_unlock("mul")
            self.phase = Phase.PLAYER_ANSWER

        elif not self.div_unlocked and self.boss_id >= 3 and self.x >= UNLOCK_X_DIV:
            self._start_unlock("div")
            self.phase = Phase.PLAYER_ANSWER

    def _resolve_unlock(self, correct: bool):
        """Обрабатывает ответ на туториал."""
        attack = self._pending_unlock

        if correct:
            setattr(self, f"{attack}_unlocked", True)

            # Особые эффекты туториала сложения:
            # после успеха Y раскрывается, X становится 2
            if attack == "add":
                self.y_revealed = True
                self.x = 2
                self._feedback(
                    f"Атака «{ATTACK_NAMES[attack]}» разблокирована! X = 2, Y = {self.y}"
                )
            else:
                # Туториал вычитания: X не уменьшается
                self._feedback(f"Атака «{ATTACK_NAMES[attack]}» разблокирована!")

            self._pending_unlock = None
            self._unlock_stage   = 0
            self.problem_text    = ""
            self.answer_buffer   = ""
            self.error_msg       = ""

            if self.hp_boss > 0 and self.hp_player > 0:
                self.phase = Phase.PLAYER_CHOOSE

        else:
            if self._unlock_stage == 1:
                # Первая ошибка: ещё одна попытка
                self._unlock_stage = 2
                self._set_error("Неверно! Попробуй ещё раз.")
                # Перегенерируем туториал (те же правила)
                self._regenerate_unlock_problem(attack)
            else:
                # Вторая ошибка → смерть, бой заново
                self.hp_player       = 0
                self._pending_unlock = None
                self._unlock_stage   = 0
                self._check_end()

    def _regenerate_unlock_problem(self, attack_type: str):
        """Перегенерирует задачу туториала для второй попытки."""
        self.answer_buffer = ""

        if attack_type == "add":
            text, ans = gen_tutorial_add_problem(self.y)
            self.problem_text   = f"[Обучение: Сложение]\n{text}"
            self.correct_answer = ans

        elif attack_type == "sub":
            text, ans = gen_tutorial_sub_problem(self.x, self.y)
            self.problem_text   = f"[Обучение: Вычитание]\n{text}"
            self.correct_answer = ans

        else:
            from .math_problem import make_problem, _OP_MAP
            op = _OP_MAP.get(attack_type, "+")
            text, ans = make_problem(op)
            self.problem_text   = f"[Обучение: {ATTACK_NAMES[attack_type]}]\n{text}"
            self.correct_answer = ans

    # -----------------------------------------------------------------------
    # Победа / поражение
    # -----------------------------------------------------------------------

    def _check_end(self) -> bool:
        if self.hp_boss <= 0:
            self.victory    = True
            names = {1: "Внучка повержена!", 2: "Отец повержен!", 3: "Бабушка повержена!"}
            self.result_msg   = names.get(self.boss_id, "Победа!")
            self.result_timer = 3.0
            self.phase        = Phase.RESULT
            return True

        if self.hp_player <= 0:
            self.victory      = False
            self.result_msg   = "Wasted. Попробуй снова."
            self.result_timer = 3.0
            self.phase        = Phase.RESULT
            return True

        return False

    def finalize_victory(self) -> int:
        """Сбрасывает X после победы (÷2, минимум 1). Возвращает новый X."""
        self.x = max(1, self.x // 2)
        return self.x

    # -----------------------------------------------------------------------
    # Вспомогательные
    # -----------------------------------------------------------------------

    def _is_unlocked(self, attack: str) -> bool:
        return getattr(self, f"{attack}_unlocked", False)

    def _validate(self) -> bool:
        try:
            return int(self.answer_buffer) == self.correct_answer
        except ValueError:
            return False

    def _feedback(self, msg: str):
        self.feedback_msg   = msg
        self.feedback_timer = 2.5

    def _set_error(self, msg: str):
        self.error_msg   = msg
        self.error_timer = 2.5