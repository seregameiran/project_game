"""
Третий босс: Бабушка (Андреева Людмила Петровна)
Локация 5. Операции: базовая, сложение, вычитание, умножение, деление.

Механика:
- Сложение и вычитание работают сразу (перенесены с первых боссов)
- Умножение работает сразу (перенесено со второго босса)
- При X >= 12: обучающий пример на деление X ÷ Y = ?
  * Правильно → атака «Деление» разблокирована, X не уменьшается
  * Неправильно → ещё одна попытка; снова неправильно → смерть
- После разблокировки деление используется раз в 4-5 ходов
"""

import random


# Типы атак — строковые константы
ATTACK_TUTORIAL_DIV = "tutorial_div"  # обучение делению (при X >= 12)
ATTACK_BASIC        = "basic"         # базовый удар: HP_player -= Y
ATTACK_ADD          = "add"           # сложение: Y += N или Y += N*2
ATTACK_SUB          = "sub"           # вычитание: X -= 2 или X //= 2
ATTACK_MUL          = "mul"           # умножение: след. удар босса ×2
ATTACK_DIV          = "div"           # деление: X //= 2 или X //= 2, Y *= 1.5


class Boss3:
    """Третий босс: Бабушка."""

    BOSS_ID  = 3
    NAME     = "Бабушка"
    HP_START = 100
    Y_START  = 6   # сразу открыт

    # Диапазон N для атаки сложения
    N_MIN = 4
    N_MAX = 8

    def __init__(self):
        self.hp         = self.HP_START
        self.y          = self.Y_START
        self.y_revealed = True   # Y сразу виден

        # Флаг обучения делению
        self.division_taught = False

        # Флаг: следующий базовый удар босса удваивается
        self._next_basic_doubled = False

        # Счётчики ходов между атаками
        self._turns_since_add = 0
        self._turns_since_sub = 0
        self._turns_since_mul = 0
        self._turns_since_div = 0

        # Случайные пороги для вычитания (3-4 хода) и умножения (4-5 ходов)
        self._sub_threshold = random.randint(3, 4)
        self._mul_threshold = random.randint(4, 5)
        self._div_threshold = random.randint(4, 5)

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
        # Обучение делению — первый раз когда X достигает 12
        if player_x >= 12 and not self.division_taught:
            return ATTACK_TUTORIAL_DIV

        # Обычные ходы
        self._turns_since_add += 1
        self._turns_since_sub += 1

        # Деление раз в 4-5 ходов (только после разблокировки)
        if self.division_taught:
            self._turns_since_div += 1
            if self._turns_since_div >= self._div_threshold:
                self._turns_since_div = 0
                self._div_threshold = random.randint(4, 5)
                return ATTACK_DIV

        # Умножение раз в 4-5 ходов
        self._turns_since_mul += 1
        if self._turns_since_mul >= self._mul_threshold:
            self._turns_since_mul = 0
            self._mul_threshold = random.randint(4, 5)
            return ATTACK_MUL

        # Вычитание раз в 3-4 хода
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
        if attack == ATTACK_TUTORIAL_DIV:
            # Игрок видит «X ÷ Y = ?» и должен ввести частное
            ans = player_x // self.y if self.y != 0 else 0
            return f"X ÷ Y = {player_x} ÷ {self.y} = ?", ans

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

        if attack == ATTACK_DIV:
            # Пример на деление: X ÷ Y = ?
            ans = player_x // self.y if self.y != 0 else 0
            return f"X ÷ Y = {player_x} ÷ {self.y} = ?", ans

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
        if attack == ATTACK_TUTORIAL_DIV:
            self.division_taught = True
            player.div_unlocked = True
            # X не уменьшается при правильном обучающем ответе
            return "Ты понял! Атака «Деление» разблокирована."

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

        if attack == ATTACK_DIV:
            # Правильно: X = X ÷ 2
            player.x = max(0, player.x // 2)
            return f"X уменьшился вдвое → X = {player.x}"

        return ""

    def apply_wrong(self, attack: str, player) -> str:
        """
        Применяет штраф при НЕПРАВИЛЬНОМ ответе.
        Возвращает "DEATH" для обучающих атак (2-я ошибка).
        """
        if attack == ATTACK_TUTORIAL_DIV:
            return "DEATH"

        if attack == ATTACK_ADD:
            self.y += self._pending_n * 2
            return f"Ошибка! Y вырос на {self._pending_n * 2} → Y = {self.y}"

        if attack == ATTACK_SUB:
            old_x = player.x
            player.x = player.x // 2
            return f"Ошибка! X = {old_x} // 2 → X = {player.x}"

        if attack == ATTACK_MUL:
            # Ошибка: X ÷ 1.5, Y × 2
            old_x = player.x
            player.x = max(0, int(player.x / 1.5))
            self.y = int(self.y * 2)
            return f"Ошибка! X = {old_x} ÷ 1.5 → {player.x}, Y × 2 → Y = {self.y}"

        if attack == ATTACK_DIV:
            # Ошибка: X = X ÷ 2, Y = Y × 1.5
            player.x = max(0, player.x // 2)
            self.y = int(self.y * 1.5)
            return f"Ошибка! X ÷ 2 = {player.x}, Y × 1.5 = {self.y}"

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