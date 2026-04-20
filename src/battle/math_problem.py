"""
Вспомогательный модуль для генерации математических примеров.
Используется как утилита — вся основная логика генерации
живёт в самих классах боссов (boss-1.py и т.д.).

Здесь — общие хелперы, которые могут пригодиться в разных местах.
"""

import random
import math


def make_addition_problem(y: int, n: int) -> tuple[str, int]:
    """Y + N = ?, ответ = Y + N."""
    return f"{y} + {n} = ?", y + n


def make_subtraction_problem(x: int, y: int) -> tuple[str, int]:
    """
    |X – Y| = ?
    Используется и для учебного примера, и для обычного.
    """
    ans = abs(x - y)
    return f"|{x} – {y}| = ?", ans


def make_multiplication_problem(x: int, y: int) -> tuple[str, int]:
    """X × Y = ?"""
    return f"{x} × {y} = ?", x * y


def make_division_problem(x: int, y: int) -> tuple[str, int]:
    """
    X ÷ Y = ? (округление вниз)
    Защита от деления на 0.
    """
    if y == 0:
        return f"{x} ÷ 1 = ?", x
    return f"{x} ÷ {y} = ?", x // y


def random_n(n_min: int, n_max: int) -> int:
    """Случайное N в диапазоне [n_min, n_max]."""
    return random.randint(n_min, n_max)


def floor_div2(x: int, minimum: int = 0) -> int:
    """x // 2, не меньше minimum."""
    return max(minimum, x // 2)


def ceil_div(x: float, d: float) -> int:
    """Деление с округлением вверх (для x / 1.5 и т.п.)."""
    return math.ceil(x / d)