"""
src/states/battle.py
Состояние боя — тонкий клей между BattleSystem, BattleHUD и game.

Отвечает только за:
  - создание BattleSystem и BattleHUD
  - проброс событий клавиатуры в BattleSystem
  - вызовы audio при смене состояния
  - переходы в другие состояния игры
"""

import os
import pygame

from src.game_state import GameState
from src.core.audio_manager import SoundType, MusicTrack
from src.battle.battle_system import BattleSystem, Phase
from src.ui.hud import BattleHUD

# pygame-константы для атак (здесь, а не в BattleSystem — там нет pygame)
ATTACK_KEYS = {
    pygame.K_1: "add",
    pygame.K_2: "sub",
    pygame.K_3: "mul",
    pygame.K_4: "div",
}


class BattleState:
    """
    Игровое состояние «Бой».
    Интерфейс: enter(boss_id, saved_x), handle_events(events),
               update(dt), draw(screen).
    """

    def __init__(self, game):
        self.game = game

        root_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.hud = BattleHUD(root_dir)
        self.sys: BattleSystem | None = None

    # -----------------------------------------------------------------------
    # Вход в состояние
    # -----------------------------------------------------------------------

    def enter(self, boss_id: int, saved_x: int = 0):
        self.sys = BattleSystem(boss_id=boss_id, saved_x=saved_x)
        self.sys.enter()
        self.hud.load(boss_id)

        print(f"[BATTLE] Бой начат. Босс #{boss_id}, "
              f"HP_player = {self.sys.hp_player}, HP_boss = {self.sys.hp_boss}, "
              f"X = {self.sys.x}, Y = {self.sys.y}")

    # -----------------------------------------------------------------------
    # Обработка событий
    # -----------------------------------------------------------------------

    def handle_events(self, events):
        if not self.sys:
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            key = event.key

            # ESC — сразу выходим в exploring
            if key == pygame.K_ESCAPE:
                self.game.audio.play_sound(SoundType.UI_SELECT)
                self.game.change_state(GameState.EXPLORING)
                return

            phase = self.sys.phase

            # Выбор атаки
            if phase == Phase.PLAYER_CHOOSE:
                attack = ATTACK_KEYS.get(key)
                if attack:
                    prev_x = self.sys.x
                    applied = self.sys.on_attack_key(attack)
                    if applied and attack in ("add", "sub"):
                        # звук удара только для атакующих действий
                        self.game.audio.play_sound(SoundType.BOSS_HIT)

            # Ввод ответа
            elif phase in (Phase.PLAYER_ANSWER, Phase.BOSS_ANSWER):
                if event.unicode.isdigit():
                    self.sys.on_digit(event.unicode)
                elif key == pygame.K_BACKSPACE:
                    self.sys.on_backspace()
                elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.sys.answer_buffer:
                        self.sys.on_confirm()

    # -----------------------------------------------------------------------
    # Обновление
    # -----------------------------------------------------------------------

    def update(self, dt: float):
        if not self.sys:
            return

        self.sys.update(dt)

        # Проверяем окончание таймера финального сообщения
        if self.sys.phase == Phase.RESULT and self.sys.result_timer <= 0:
            self._exit_battle()

    # -----------------------------------------------------------------------
    # Отрисовка
    # -----------------------------------------------------------------------

    def draw(self, screen: pygame.Surface):
        if not self.sys:
            return
        self.hud.draw(screen, self.sys)

    # -----------------------------------------------------------------------
    # Выход из боя
    # -----------------------------------------------------------------------

    def _exit_battle(self):
        sys = self.sys

        if sys.victory:
            new_x = sys.finalize_victory()

            if sys.boss_id == 3:
                # Финальный босс → титры
                self.game.audio.play_sound(SoundType.VICTORY)
                self.game.change_state(GameState.CREDITS)
                return

            # Победа над боссом 1 или 2
            self.game.mark_boss_defeated(sys.boss_id + 2)  # location_id

            exploring = self.game.states.get(GameState.EXPLORING)
            if exploring:
                exploring._saved_battle_x = new_x

            self.game.audio.play_sound(SoundType.VICTORY)
            self.game.audio.play_music(MusicTrack.EXPLORING)
            self.game.change_state(GameState.EXPLORING)

        else:
            # Поражение — возврат на локацию, бой начнётся заново
            self.game.audio.play_sound(SoundType.DEFEAT)
            self.game.audio.play_music(MusicTrack.EXPLORING)
            self.game.change_state(GameState.EXPLORING)