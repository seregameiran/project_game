"""
Второй босс: Отец (Андреев Андрей Андреевич)
Локация 4. Операции: базовая, сложение, вычитание, умножение.

Механика:
- Сложение и вычитание работают сразу (перенесены с первого босса)
- При X >= 10: обучающий пример на умножение X × Y = ?
  * Правильно → атака «Умножение» разблокирована, X не уменьшается
  * Неправильно → ещё одна попытка; снова неправильно → смерть
- После разблокировки умножение используется раз в 4–5 ходов
"""

import random


# Типы атак — строковые константы
ATTACK_TUTORIAL_MUL = "tutorial_mul"  # обучение умножению (при X >= 10)
ATTACK_BASIC        = "basic"         # базовый удар: HP_player -= Y
ATTACK_ADD          = "add"           # сложение: Y += N или Y += N*2
ATTACK_SUB          = "sub"           # вычитание: X -= 2 или X //= 2
ATTACK_MUL          = "mul"           # умножение: след. удар босса ×2


class Boss2:
    """Второй босс: Отец."""

    BOSS_ID  = 2
    NAME     = "Отец"
    HP_START = 70
    Y_START  = 4   # сразу открыт (не скрыт как у первого босса)

    # Диапазон N для атаки сложения
    N_MIN = 3
    N_MAX = 7

    def __init__(self):
        self.hp         = self.HP_START
        self.y          = self.Y_START
        self.y_revealed = True   # Y сразу виден

        # Флаг обучения умножению
        self.multiplication_taught = False

        # Флаг: следующий базовый удар босса удваивается
        self._next_basic_doubled = False

        # Счётчики ходов между атаками
        self._turns_since_add = 0
        self._turns_since_sub = 0
        self._turns_since_mul = 0

        # Случайный порог для вычитания (3–4 хода)
        self._sub_threshold = random.randint(3, 4)
        # Случайный порог для умножения (4–5 ходов)
        self._mul_threshold = random.randint(4, 5)

        # N текущей атаки сложения
        self._pending_n = 0

    # ------------------------------------------------------------------
    # Выбор атаки
    # ------------------------------------------------------------------

    def choose_attack(self, player_x: int) -> str:
        """
        Возвращает тип следующей атаки босса.
        player_x — текущий урон игрока.
        """
        # Обучение умножению — первый раз когда X достиг 10
        if player_x >= 10 and not self.multiplication_taught:
            return ATTACK_TUTORIAL_MUL

        # Обычные ходы
        self._turns_since_add += 1
        self._turns_since_sub += 1

        # Умножение раз в 4–5 ходов (только после разблокировки)
        if self.multiplication_taught:
            self._turns_since_mul += 1
            if self._turns_since_mul >= self._mul_threshold:
                self._turns_since_mul = 0
                self._mul_threshold = random.randint(4, 5)
                return ATTACK_MUL

        # Вычитание раз в 3–4 хода
        if self._turns_since_sub >= self._sub_threshold:
            self._turns_since_sub = 0
            self._sub_threshold = random.randint(3, 4)
            return ATTACK_SUB

        # Сложение раз в 2 хода
        if self._turns_since_add >= 2:
            self._turns_since_add = 0
            return ATTACK_ADD

        return ATTACK_BASIC

    # ------------------------------------------------------------------
    # Генерация примеров
    # ------------------------------------------------------------------

    def make_problem(self, attack: str, player_x: int) -> tuple[str, int]:
        """
        Возвращает (текст_примера, правильный_ответ).
        Вызывать ПЕРЕД apply_correct/apply_wrong.
        """
        if attack == ATTACK_TUTORIAL_MUL:
            # Игрок видит «X × Y = ?» и должен ввести произведение
            ans = player_x * self.y
            return f"X × Y = {player_x} × {self.y} = ?", ans

        if attack == ATTACK_ADD:
            self._pending_n = random.randint(self.N_MIN, self.N_MAX)
            ans = self.y + self._pending_n
            return f"Y + {self._pending_n} = ?", ans

        if attack == ATTACK_SUB:
            ans = abs(player_x - self.y)
            return f"|X – Y| = |{player_x} – {self.y}| = ?", ans

        if attack == ATTACK_MUL:
            # Пример на умножение: X × Y = ?
            ans = player_x * self.y
            return f"X × Y = {player_x} × {self.y} = ?", ans

        # BASIC не требует ввода
        return "", 0

    # ------------------------------------------------------------------
    # Применение результата атаки
    # ------------------------------------------------------------------

    def apply_correct(self, attack: str, player) -> str:
        """
        Применяет эффект при ПРАВИЛЬНОМ ответе.
        player — объект PlayerState из battle_system.
        """
        if attack == ATTACK_TUTORIAL_MUL:
            self.multiplication_taught = True
            player.mul_unlocked        = True
            # X не уменьшается при правильном обучающем ответе
            return "Ты понял! Атака «Умножение» разблокирована."

        if attack == ATTACK_BASIC:
            dmg = self.y * 2 if self._next_basic_doubled else self.y
            self._next_basic_doubled = False
            player.hp -= dmg
            return f"Базовый удар: -{dmg} HP"

        if attack == ATTACK_ADD:
            self.y += self._pending_n
            return f"Y вырос на {self._pending_n} → Y = {self.y}"

        if attack == ATTACK_SUB:
            player.x = max(0, player.x - 2)
            return f"X уменьшился на 2 → X = {player.x}"

        if attack == ATTACK_MUL:
            # Правильно: следующий базовый удар удваивается
            self._next_basic_doubled = True
            return "Следующий базовый удар босса будет удвоен!"

        return ""

    def apply_wrong(self, attack: str, player) -> str:
        """
        Применяет штраф при НЕПРАВИЛЬНОМ ответе.
        Возвращает "DEATH" для обучающих атак (2-я ошибка).
        """
        if attack == ATTACK_TUTORIAL_MUL:
            return "DEATH"

        if attack == ATTACK_ADD:
            self.y += self._pending_n * 2
            return f"Ошибка! Y вырос на {self._pending_n * 2} → Y = {self.y}"

        if attack == ATTACK_SUB:
            old_x    = player.x
            player.x = player.x // 2
            return f"Ошибка! X = {old_x} // 2 → X = {player.x}"

        if attack == ATTACK_MUL:
            # Ошибка: X ÷ 1.5 (округление вверх), Y × 2
            import math
            old_x    = player.x
            player.x = max(0, math.ceil(player.x / 1.5))
            self.y   = int(self.y * 2)
            return f"Ошибка! X = {old_x} ÷ 1.5 → {player.x}, Y × 2 → Y = {self.y}"

        return ""

    def apply_basic(self, player) -> str:
        """Наносит базовый удар (без примера)."""
        dmg = self.y * 2 if self._next_basic_doubled else self.y
        self._next_basic_doubled = False
        player.hp -= dmg
        return f"Базовый удар: -{dmg} HP"

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    def is_dead(self) -> bool:
        return self.hp <= 0

    def take_damage(self, dmg: int):
        self.hp = max(0, self.hp - dmg)