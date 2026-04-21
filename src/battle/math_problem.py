"""
src/battle/math_problem.py
Генерация математических примеров для боя.
Никаких зависимостей от pygame или игровой логики.
"""

import random

# Человекочитаемые имена атак
ATTACK_NAMES = {
    "add": "Сложение",
    "sub": "Вычитание",
    "mul": "Умножение",
    "div": "Деление",
}

_OP_MAP = {"add": "+", "sub": "-", "mul": "*", "div": "/"}


def make_problem(op: str) -> tuple[str, int]:
    """Случайный пример для оператора '+', '-', '*', '/'."""
    if op == "+":
        a, b = random.randint(1, 9), random.randint(1, 9)
        return f"{a} + {b} = ?", a + b
    elif op == "-":
        b = random.randint(1, 5)
        a = random.randint(b, b + 6)
        return f"{a} - {b} = ?", a - b
    elif op == "*":
        a, b = random.randint(2, 5), random.randint(2, 4)
        return f"{a} × {b} = ?", a * b
    else:  # "/"
        b = random.randint(2, 4)
        a = b * random.randint(2, 5)
        return f"{a} ÷ {b} = ?", a // b


def gen_tutorial_add_problem(y: int) -> tuple[str, int]:
    """
    Первый ход — обучение сложению.
    Показывает «Y + 1 = {y+1}», игрок должен ввести значение Y.
    """
    return f"Y + 1 = {y + 1}\nY = ?", y


def gen_tutorial_sub_problem(x: int, y: int) -> tuple[str, int]:
    """
    Обучение вычитанию (когда X достигает 7).
    Показывает «|X – Y| = |{x} – {y}| = ?».
    """
    return f"|X – Y| = |{x} – {y}| = ?", abs(x - y)

def gen_boss_add_problem(y: int, n_min: int, n_max: int) -> tuple[str, int]:
    """
    Атака босса: Сложение.
    Показывает «{y} + {n} = ?», игрок вводит сумму.
    """
    n = random.randint(n_min, n_max)
    return f"[Атака босса: Сложение]\n{y} + {n} = ?", y + n, n


def gen_boss_problem(attack_type: str) -> tuple[str, int]:
    """Случайный пример для обычной атаки босса."""
    op = _OP_MAP.get(attack_type, "+")
    text, ans = make_problem(op)
    return f"[Атака босса: {ATTACK_NAMES[attack_type]}]\n{text}", ans