"""
Ядро боевой системы — чистая логика без pygame.
Управляет фазами боя, очерёдностью ходов и состоянием участников.

Фазы боя (BattlePhase):
  TUTORIAL_SHOW  — показываем обучающий пример
  TUTORIAL_INPUT — ожидаем ввод ответа (с флагом retry)
  PLAYER_TURN    — игрок выбирает атаку (1-4)
  BOSS_SHOW      — показываем пример босса (или просто текст удара)
  BOSS_INPUT     — ожидаем ввод ответа на пример босса
  RESULT_SHOW    — кратко показываем результат хода
  VICTORY        — победа
  DEFEAT         — поражение
"""

from dataclasses import dataclass, field


# -----------------------------------------------------------------------
# Фазы боя
# -----------------------------------------------------------------------

class BattlePhase:
    TUTORIAL_SHOW  = "tutorial_show"
    TUTORIAL_INPUT = "tutorial_input"
    PLAYER_TURN    = "player_turn"
    BOSS_SHOW      = "boss_show"
    BOSS_INPUT     = "boss_input"
    RESULT_SHOW    = "result_show"
    VICTORY        = "victory"
    DEFEAT         = "defeat"


# -----------------------------------------------------------------------
# Данные игрока во время боя
# -----------------------------------------------------------------------

@dataclass
class PlayerState:
    hp:            int  = 50
    x:             int  = 0   # текущий урон игрока
    add_unlocked:  bool = False
    sub_unlocked:  bool = False
    mul_unlocked:  bool = False
    div_unlocked:  bool = False

    # Буфф от атаки «Умножение» (для боссов 2-3, здесь не используется)
    multiply_buff: bool = False

    def available_attacks(self) -> list[tuple[int, str]]:
        """Возвращает список (номер_клавиши, название) доступных атак."""
        result = []
        if self.add_unlocked:
            result.append((1, "Сложение"))
        if self.sub_unlocked:
            result.append((2, "Вычитание"))
        if self.mul_unlocked:
            result.append((3, "Умножение"))
        if self.div_unlocked:
            result.append((4, "Деление"))
        return result

    def is_dead(self) -> bool:
        return self.hp <= 0


# -----------------------------------------------------------------------
# Основной класс боевой системы
# -----------------------------------------------------------------------

class BattleSystem:
    """
    Управляет одним боем с конкретным боссом.

    Использование:
        player = PlayerState(hp=50, x=0)
        boss   = Boss1()
        battle = BattleSystem(boss, player)
        battle.start()          # → phase = TUTORIAL_SHOW

    На каждом «экране» состояние battle.phase говорит,
    что должно рисоваться. Когда игрок что-то нажал —
    вызываем нужный метод (submit_answer, choose_attack и т.д.)
    и снова смотрим на phase.
    """

    # Сколько секунд показывать RESULT_SHOW перед следующим ходом
    RESULT_SHOW_DURATION = 1.8

    def __init__(self, boss, player: PlayerState):
        self.boss   = boss
        self.player = player

        self.phase: str = BattlePhase.PLAYER_TURN

        # Текущая атака босса
        self._boss_attack:    str = ""
        self._boss_problem:   str = ""
        self._boss_answer:    int = 0
        self._boss_retry:     bool = False   # True = уже дана одна попытка

        # Результат хода для отображения
        self.result_text: str = ""
        self._result_timer: float = 0.0

        # Текущий вводимый ответ (строка цифр)
        self.input_buffer: str = ""

        # Сообщение об ошибке (для UI)
        self.error_text: str = ""

    # ------------------------------------------------------------------
    # Запуск боя
    # ------------------------------------------------------------------

    def start(self):
        """Вызвать один раз при входе в состояние Battle."""
        self._begin_boss_turn()

    # ------------------------------------------------------------------
    # Ход игрока
    # ------------------------------------------------------------------

    def choose_attack(self, attack_num: int) -> bool:
        """
        Игрок нажал клавишу 1-4.
        Возвращает True если атака применена, False если недоступна.
        """
        if self.phase != BattlePhase.PLAYER_TURN:
            return False

        attacks = {k: v for k, v in self.player.available_attacks()}
        # available_attacks() даёт (номер, название), делаем dict номер→название
        avail = {k: v for k, v in self.player.available_attacks()}

        if attack_num not in avail:
            return False

        self._apply_player_attack(attack_num)
        return True

    def _apply_player_attack(self, attack_num: int):
        """Применяет атаку игрока и проверяет победу."""
        p, b = self.player, self.boss
        buff = p.multiply_buff
        p.multiply_buff = False  # баф одноразовый

        if attack_num == 1:   # Сложение
            delta = (p.x + 1) * 2 if buff else p.x + 1
            p.x  = p.x + 1 if not buff else (p.x + 1) * 2
            # При сложении X сначала увеличивается, потом наносится урон
            # Из доки: X = X+1, HP_boss -= X (нового X)
            # Поэтому если buff: X = (X+1)*2
            if not buff:
                p.x += 0   # уже обновлен выше, просто для ясности
            b.take_damage(p.x)
            self.result_text = f"Сложение! X = {p.x}, урон боссу: -{p.x}"

        elif attack_num == 2:  # Вычитание
            if buff:
                b.y   = max(0, b.y - 4)
                b.take_damage(4)
                self.result_text = f"Вычитание ×2! Y = {b.y}, урон боссу: -4"
            else:
                b.y   = max(0, b.y - 2)
                b.take_damage(2)
                self.result_text = f"Вычитание! Y = {b.y}, урон боссу: -2"

        elif attack_num == 3:  # Умножение (бафф на след. атаку)
            p.multiply_buff = True
            self.result_text = "Умножение! Следующая атака удвоена."

        elif attack_num == 4:  # Деление (защита от след. удара)
            b._halve_next_hit = True
            self.result_text = "Деление! Следующий удар босса ÷ 2."

        self._transition_after_player(attack_num)

    def _transition_after_player(self, attack_num: int):
        """После атаки игрока — проверяем победу, потом ход босса."""
        if self.boss.is_dead():
            self.phase = BattlePhase.VICTORY
            return
        self._show_result_then(lambda: self._begin_boss_turn())

    # ------------------------------------------------------------------
    # Ход босса
    # ------------------------------------------------------------------

    def _begin_boss_turn(self):
        attack = self.boss.choose_attack(self.player.x)
        self._boss_attack = attack
        self._boss_retry  = False

        if attack == "basic":
            # Базовый удар без ввода
            self._boss_problem = ""
            self._boss_answer  = 0
            self.phase = BattlePhase.BOSS_SHOW
        else:
            problem, answer = self.boss.make_problem(attack, self.player.x)
            self._boss_problem = problem
            self._boss_answer  = answer
            self.input_buffer  = ""
            self.error_text    = ""
            self.phase = BattlePhase.BOSS_SHOW

    def confirm_boss_show(self):
        """
        Вызывается когда игрок нажал Enter/пробел чтобы «увидел» удар босса.
        Переходит к вводу ответа или сразу применяет базовый удар.
        """
        if self.phase != BattlePhase.BOSS_SHOW:
            return

        if self._boss_attack == "basic":
            self._apply_boss_basic()
        else:
            self.phase = BattlePhase.BOSS_INPUT

    def _apply_boss_basic(self):
        effect = self.boss.apply_basic(self.player)
        self.result_text = effect
        self._check_defeat_or_continue()

    def submit_answer(self) -> bool:
        """
        Игрок нажал Enter при вводе ответа на пример босса.
        Возвращает True если ответ принят (независимо от правильности).
        """
        if self.phase not in (BattlePhase.BOSS_INPUT, BattlePhase.TUTORIAL_INPUT):
            return False
        if not self.input_buffer:
            return False

        try:
            given = int(self.input_buffer)
        except ValueError:
            self.error_text = "Введи число!"
            return False

        self.input_buffer = ""
        self.error_text   = ""

        is_tutorial = self._boss_attack in ("tutorial_add", "tutorial_sub")
        correct     = (given == self._boss_answer)

        if correct:
            effect = self.boss.apply_correct(self._boss_attack, self.player)
            self.result_text = effect
            self._check_defeat_or_continue()
        else:
            if is_tutorial and not self._boss_retry:
                # Первая ошибка в обучении — даём ещё одну попытку
                self._boss_retry = True
                self.error_text  = "Неправильно! Попробуй ещё раз."
                # Остаёмся в фазе ввода
            else:
                effect = self.boss.apply_wrong(self._boss_attack, self.player)
                if effect == "DEATH":
                    self.phase = BattlePhase.DEFEAT
                else:
                    self.result_text = effect
                    self._check_defeat_or_continue()
        return True

    def add_char(self, ch: str):
        """Добавить цифру в буфер ввода (вызывать при нажатии цифры)."""
        if len(self.input_buffer) < 6 and ch.isdigit():
            self.input_buffer += ch

    def backspace(self):
        """Удалить последний символ из буфера."""
        self.input_buffer = self.input_buffer[:-1]

    # ------------------------------------------------------------------
    # Вспомогательные переходы
    # ------------------------------------------------------------------

    def _check_defeat_or_continue(self):
        if self.player.is_dead():
            self.phase = BattlePhase.DEFEAT
        elif self.boss.is_dead():
            self.phase = BattlePhase.VICTORY
        else:
            self._show_result_then(lambda: self._go_player_turn())

    def _go_player_turn(self):
        self.phase = BattlePhase.PLAYER_TURN

    def _show_result_then(self, callback):
        """Устанавливает фазу RESULT_SHOW и запоминает callback."""
        self.phase             = BattlePhase.RESULT_SHOW
        self._result_timer     = self.RESULT_SHOW_DURATION
        self._result_callback  = callback

    def update(self, dt: float):
        """
        Вызывать каждый кадр с delta-time в секундах.
        Нужно только для автоматического перехода из RESULT_SHOW.
        """
        if self.phase == BattlePhase.RESULT_SHOW:
            self._result_timer -= dt
            if self._result_timer <= 0:
                self._result_callback()

    # ------------------------------------------------------------------
    # Итог боя
    # ------------------------------------------------------------------

    def finalize_victory(self) -> int:
        """
        Вызвать при победе. Сбрасывает X игрока по правилам.
        Возвращает новый X.
        """
        self.player.x = max(1, self.player.x // 2)
        return self.player.x