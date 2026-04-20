"""
Первый босс: Внучка (Андреева Анастасия Андреевна)
Локация 3. Операции: базовая, сложение, вычитание.

Механика:
- Первый ход: обучающий пример Y + 1 = 3 → игрок угадывает Y
  * Правильно → атака «Сложение» разблокирована, X = 2
  * Неправильно → ещё одна попытка; снова неправильно → смерть
- При X >= 7: обучающий пример на вычитание |X – Y| = ?
  * Правильно → атака «Вычитание» разблокирована, X не уменьшается
  * Неправильно → ещё одна попытка; снова неправильно → смерть
"""

import random


# Типы атак — строковые константы для ясности
ATTACK_TUTORIAL_ADD = "tutorial_add"  # обучение сложению (первый ход)
ATTACK_TUTORIAL_SUB = "tutorial_sub"  # обучение вычитанию (при X >= 7)
ATTACK_BASIC        = "basic"         # базовый удар: HP_player -= Y
ATTACK_ADD          = "add"           # сложение: Y += N или Y += N*2
ATTACK_SUB          = "sub"           # вычитание: X -= 2 или X //= 2


class Boss1:
    """Первый босс: Внучка."""

    BOSS_ID  = 1
    NAME     = "Внучка"
    HP_START = 50
    Y_START  = 2   # скрыт до конца первого хода

    # Диапазон N для атаки сложения
    N_MIN = 2
    N_MAX = 6

    def __init__(self):
        self.hp         = self.HP_START
        self.y          = self.Y_START
        self.y_revealed = False   # Y скрыт до первого обучающего примера

        # Флаги обучения
        self.addition_taught    = False
        self.subtraction_taught = False

        # Счётчики ходов между атаками
        self._turns_since_add = 0
        self._turns_since_sub = 0

        # N текущей атаки сложения (сохраняем чтобы применить в apply_*)
        self._pending_n = 0

    # ------------------------------------------------------------------
    # Выбор атаки
    # ------------------------------------------------------------------

    def choose_attack(self, player_x: int) -> str:
        """
        Возвращает тип следующей атаки босса.
        player_x — текущий урон игрока.
        """
        # Обучение сложению — только самый первый ход
        if not self.addition_taught:
            return ATTACK_TUTORIAL_ADD

        # Обучение вычитанию — первый раз когда X достиг 7
        if player_x >= 7 and not self.subtraction_taught:
            return ATTACK_TUTORIAL_SUB

        # Обычные ходы
        self._turns_since_add += 1
        self._turns_since_sub += 1

        # Вычитание раз в 3-4 хода (только после разблокировки)
        if self.subtraction_taught and self._turns_since_sub >= random.randint(3, 4):
            self._turns_since_sub = 0
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
        if attack == ATTACK_TUTORIAL_ADD:
            # Игрок видит «Y + 1 = 3» и должен ввести значение Y
            return f"Y + 1 = {self.y + 1}\nY = ?", self.y

        if attack == ATTACK_TUTORIAL_SUB:
            # Игрок видит «|X – Y| = ?»
            ans = abs(player_x - self.y)
            return f"|X – Y| = |{player_x} – {self.y}| = ?", ans

        if attack == ATTACK_ADD:
            self._pending_n = random.randint(self.N_MIN, self.N_MAX)
            ans = self.y + self._pending_n
            return f"Y + {self._pending_n} = ?", ans

        if attack == ATTACK_SUB:
            ans = abs(player_x - self.y)
            return f"|X – Y| = |{player_x} – {self.y}| = ?", ans

        # BASIC не требует ввода
        return "", 0

    # ------------------------------------------------------------------
    # Применение результата атаки
    # ------------------------------------------------------------------

    def apply_correct(self, attack: str, player) -> str:
        """
        Применяет эффект при ПРАВИЛЬНОМ ответе.
        Возвращает строку с описанием эффекта для UI.
        player — объект PlayerState из battle_system.
        """
        if attack == ATTACK_TUTORIAL_ADD:
            self.addition_taught = True
            self.y_revealed      = True
            player.add_unlocked  = True
            player.x             = 2   # бонус первого урока
            return "Ты понял! Атака «Сложение» разблокирована. X = 2"

        if attack == ATTACK_TUTORIAL_SUB:
            self.subtraction_taught = True
            player.sub_unlocked     = True
            # X не уменьшается при правильном обучающем ответе
            return "Ты понял! Атака «Вычитание» разблокирована."

        if attack == ATTACK_BASIC:
            player.hp -= self.y
            return f"Базовый удар: -{self.y} HP"

        if attack == ATTACK_ADD:
            self.y += self._pending_n
            return f"Y вырос на {self._pending_n} → Y = {self.y}"

        if attack == ATTACK_SUB:
            player.x = max(0, player.x - 2)
            return f"X уменьшился на 2 → X = {player.x}"

        return ""

    def apply_wrong(self, attack: str, player) -> str:
        """
        Применяет штраф при НЕПРАВИЛЬНОМ ответе.
        Возвращает "DEATH" для обучающих атак (2-я ошибка).
        """
        if attack in (ATTACK_TUTORIAL_ADD, ATTACK_TUTORIAL_SUB):
            # Сигнал: игрок умирает, бой начинается заново
            return "DEATH"

        if attack == ATTACK_ADD:
            self.y += self._pending_n * 2
            return f"Ошибка! Y вырос на {self._pending_n * 2} → Y = {self.y}"

        if attack == ATTACK_SUB:
            old_x   = player.x
            player.x = player.x // 2
            return f"Ошибка! X = {old_x} // 2 → X = {player.x}"

        return ""

    def apply_basic(self, player) -> str:
        """Наносит базовый удар (без примера)."""
        player.hp -= self.y
        return f"Базовый удар: -{self.y} HP"

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    def is_dead(self) -> bool:
        return self.hp <= 0

    def take_damage(self, dmg: int):
        self.hp = max(0, self.hp - dmg)