"""
Состояние BATTLE — рендеринг и обработка ввода.
Вся чистая логика живёт в BattleSystem / Boss*.
Этот файл только рисует и передаёт события.

Виртуальный экран: 800 × 608 пикселей.
Ассеты: assets/location3/ (для первого босса).
"""

import os
import pygame

# Импорт логики боя
from battle.battle_system import BattleSystem, BattlePhase, PlayerState

# Импорт первого босса
import importlib
_boss1_module = importlib.import_module("bosses.boss1")
Boss1 = _boss1_module.Boss1


# -----------------------------------------------------------------------
# Вспомогательные функции загрузки ресурсов
# -----------------------------------------------------------------------

def _asset(location_folder: str, filename: str) -> str:
    """Формирует путь к файлу в папке assets/<location_folder>/."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "assets", location_folder, filename)


def _load_image(path: str, scale=None) -> pygame.Surface:
    try:
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.scale(img, scale)
        return img
    except Exception:
        surf = pygame.Surface(scale or (64, 64), pygame.SRCALPHA)
        surf.fill((200, 50, 200, 180))
        return surf


def _load_font(path: str, size: int) -> pygame.font.Font:
    try:
        return pygame.font.Font(path, size)
    except Exception:
        return pygame.font.Font(None, size)


# -----------------------------------------------------------------------
# Константы UI
# -----------------------------------------------------------------------

VSCREEN_W = 800
VSCREEN_H = 608

C_WHITE    = (255, 255, 255)
C_BLACK    = (0,   0,   0)
C_RED      = (220, 50,  50)
C_GREEN    = (80,  200, 80)
C_YELLOW   = (255, 230, 50)
C_GRAY     = (150, 150, 150)
C_DARK     = (20,  20,  20)
C_ORANGE   = (255, 160, 0)
C_HP_GREEN = (60,  190, 60)
C_HP_RED   = (190, 40,  40)
C_HP_BG    = (60,  20,  20)

HP_BAR_W   = 200
HP_BAR_H   = 18
PLAYER_HP_X = 20
PLAYER_HP_Y = 20
BOSS_HP_X   = VSCREEN_W - HP_BAR_W - 20
BOSS_HP_Y   = 20

ATTACK_PANEL_Y = VSCREEN_H - 100
PROBLEM_Y = VSCREEN_H // 2 - 60


# -----------------------------------------------------------------------
# Главный класс состояния
# -----------------------------------------------------------------------

class BattleState:
    """
    Игровое состояние «Бой».
    Интерфейс совместим с game.py.
    """

    ASSET_FOLDER = "location3"

    def __init__(self, game):
        """Инициализация состояния боя."""
        self.game = game
        self._loaded = False
        self._battle: BattleSystem | None = None

        # Спрайты / изображения
        self._bg = None
        self._fight_win = None
        self._billy_head = None
        self._boss_img = None
        self._pointer = None

        # Шрифты
        self._font_big = None
        self._font_med = None
        self._font_small = None

        # Анимация текста результата
        self._result_alpha = 255

        # Мигание курсора ввода
        self._cursor_timer = 0.0
        self._cursor_vis = True

    # ------------------------------------------------------------------
    # Загрузка
    # ------------------------------------------------------------------

    def _load_assets(self):
        if self._loaded:
            return

        folder = self.ASSET_FOLDER
        font_path = _asset(folder, "Compilance-Sans.ttf")

        self._bg = _load_image(_asset(folder, "battle_bg.png"),
                               (VSCREEN_W, VSCREEN_H))
        self._fight_win = _load_image(_asset(folder, "Fight-Window.png"))
        self._billy_head = _load_image(_asset(folder, "Billy-Head.png"), (80, 80))
        self._boss_img = _load_image(_asset(folder, "Boss-1.png"), (160, 200))
        self._pointer = _load_image(_asset(folder, "Pointer.png"), (20, 20))

        self._font_big = _load_font(font_path, 28)
        self._font_med = _load_font(font_path, 20)
        self._font_small = _load_font(font_path, 15)

        self._loaded = True

    # ------------------------------------------------------------------
    # Жизненный цикл состояния
    # ------------------------------------------------------------------

    def start_battle(self, boss_id: int = 1, saved_x: int = 0):
        """Запускает бой с указанным боссом."""
        self._load_assets()

        # Загружаем босса по ID
        if boss_id == 1:
            from bosses.boss1 import Boss1
            boss = Boss1()
        elif boss_id == 2:
            from bosses.boss2 import Boss2
            boss = Boss2()
        elif boss_id == 3:
            from bosses.boss3 import Boss3
            boss = Boss3()
        else:
            from bosses.boss1 import Boss1
            boss = Boss1()

        player = PlayerState(hp=50, x=saved_x)
        self._battle = BattleSystem(boss, player)
        self._battle.start()

        if self.game.audio:
            self.game.audio.stop_music()

    def handle_events(self, events):
        """Обработка событий (вызывается из game.py)."""
        if not self._battle:
            return

        b = self._battle
        phase = b.phase

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            self._handle_key(event.key, event.unicode)

    def _handle_key(self, key: int, unicode_char: str):
        b = self._battle
        phase = b.phase

        if phase == BattlePhase.BOSS_SHOW:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                b.confirm_boss_show()
            return

        if phase in (BattlePhase.BOSS_INPUT, BattlePhase.TUTORIAL_INPUT):
            if unicode_char.isdigit():
                b.add_char(unicode_char)
            elif key == pygame.K_BACKSPACE:
                b.backspace()
            elif key == pygame.K_RETURN:
                b.submit_answer()
            return

        if phase == BattlePhase.PLAYER_TURN:
            attack_map = {
                pygame.K_1: 1, pygame.K_KP1: 1,
                pygame.K_2: 2, pygame.K_KP2: 2,
                pygame.K_3: 3, pygame.K_KP3: 3,
                pygame.K_4: 4, pygame.K_KP4: 4,
            }
            if key in attack_map:
                b.choose_attack(attack_map[key])
            return

        if phase == BattlePhase.VICTORY:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                b.finalize_victory()
                self._on_victory()
            return

        if phase == BattlePhase.DEFEAT:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._on_defeat()
            return

    def update(self, dt: float):
        """Обновление логики (вызывается из game.py)."""
        if not self._battle:
            return

        self._battle.update(dt)

        # Мигание курсора
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_vis = not self._cursor_vis

    def draw(self, screen: pygame.Surface):
        """Отрисовка (вызывается из game.py)."""
        if not self._battle:
            return

        b = self._battle
        p, boss = b.player, b.boss

        screen.blit(self._bg, (0, 0))

        # Спрайт босса
        boss_x = VSCREEN_W - 200
        boss_y = VSCREEN_H // 2 - 180
        screen.blit(self._boss_img, (boss_x, boss_y))

        # HP-бары
        self._draw_hp_bar(screen, PLAYER_HP_X, PLAYER_HP_Y,
                          p.hp, 50, "Билли", show_x=True, x_val=p.x)
        self._draw_hp_bar(screen, BOSS_HP_X, BOSS_HP_Y,
                          boss.hp, boss.HP_START, "Внучка",
                          show_y=True, y_val=boss.y, y_hidden=not boss.y_revealed)

        # Нижняя панель атак
        self._draw_attack_panel(screen, p)

        phase = b.phase

        if phase == BattlePhase.BOSS_SHOW:
            self._draw_boss_attack_announcement(screen, b)
        elif phase in (BattlePhase.BOSS_INPUT, BattlePhase.TUTORIAL_INPUT):
            self._draw_input_zone(screen, b)
        elif phase == BattlePhase.RESULT_SHOW:
            self._draw_result(screen, b)
        elif phase == BattlePhase.PLAYER_TURN:
            self._draw_player_prompt(screen)
        elif phase == BattlePhase.VICTORY:
            self._draw_overlay(screen, "Победа!", C_GREEN,
                               "Нажми Enter чтобы продолжить")
        elif phase == BattlePhase.DEFEAT:
            self._draw_overlay(screen, "Wasted...", C_RED,
                               "Нажми Enter чтобы начать заново")

    # ------------------------------------------------------------------
    # Переходы после боя
    # ------------------------------------------------------------------

    def _on_victory(self):
        """Победа над боссом."""
        if self._battle:
            self.game.player_battle_x = self._battle.player.x
        # Переход обратно на карту
        self.game.change_state(GameState.EXPLORING)

    def _on_defeat(self):
        """Поражение — возврат на карту."""
        self.game.change_state(GameState.EXPLORING)

    # ------------------------------------------------------------------
    # UI методы (оставлены без изменений, только убран параметр game)
    # ------------------------------------------------------------------

    def _draw_hp_bar(self, screen, x, y, hp, max_hp,
                     name, show_x=False, x_val=0,
                     show_y=False, y_val=0, y_hidden=False):
        name_surf = self._font_small.render(name, True, C_WHITE)
        screen.blit(name_surf, (x, y))
        y += 18

        pygame.draw.rect(screen, C_HP_BG, (x, y, HP_BAR_W, HP_BAR_H), border_radius=4)

        fill_w = max(0, int(HP_BAR_W * hp / max(1, max_hp)))
        color = C_HP_GREEN if hp > max_hp * 0.3 else C_HP_RED
        if fill_w > 0:
            pygame.draw.rect(screen, color, (x, y, fill_w, HP_BAR_H), border_radius=4)

        hp_text = self._font_small.render(f"{max(0, hp)} / {max_hp}", True, C_WHITE)
        screen.blit(hp_text, (x + HP_BAR_W // 2 - hp_text.get_width() // 2, y + 1))
        y += HP_BAR_H + 4

        if show_x:
            xt = self._font_small.render(f"X (урон) = {x_val}", True, C_YELLOW)
            screen.blit(xt, (x, y))
        if show_y:
            label = "Y = ?" if y_hidden else f"Y (урон) = {y_val}"
            yt = self._font_small.render(label, True, C_ORANGE)
            screen.blit(yt, (x, y))

    def _draw_attack_panel(self, screen, player: PlayerState):
        panel_rect = pygame.Rect(0, ATTACK_PANEL_Y - 10, VSCREEN_W, 110)
        panel_surf = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 160))
        screen.blit(panel_surf, panel_rect.topleft)

        attacks_info = {
            1: ("1 — Сложение",  player.add_unlocked),
            2: ("2 — Вычитание", player.sub_unlocked),
            3: ("3 — Умножение", player.mul_unlocked),
            4: ("4 — Деление",   player.div_unlocked),
        }

        slot_w = VSCREEN_W // 4
        for idx, (label, unlocked) in attacks_info.items():
            sx = (idx - 1) * slot_w
            sy = ATTACK_PANEL_Y

            if unlocked:
                color = C_WHITE
                bg = (40, 80, 40, 180)
            else:
                color = C_GRAY
                bg = (20, 20, 20, 100)

            bg_surf = pygame.Surface((slot_w - 4, 60), pygame.SRCALPHA)
            bg_surf.fill(bg)
            screen.blit(bg_surf, (sx + 2, sy))

            txt = self._font_small.render(label, True, color)
            screen.blit(txt, (sx + slot_w // 2 - txt.get_width() // 2, sy + 20))

    def _draw_boss_attack_announcement(self, screen, b: BattleSystem):
        attack_names = {
            "tutorial_add": "Обучение: Сложение",
            "tutorial_sub": "Обучение: Вычитание",
            "basic": "Базовый удар!",
            "add": "Атака: Сложение",
            "sub": "Атака: Вычитание",
        }
        name = attack_names.get(b._boss_attack, b._boss_attack)

        box_rect = pygame.Rect(100, PROBLEM_Y - 20, 600, 150)
        self._draw_box(screen, box_rect)

        title = self._font_big.render(f"Внучка: {name}", True, C_ORANGE)
        screen.blit(title, (VSCREEN_W // 2 - title.get_width() // 2, PROBLEM_Y))

        if b._boss_attack == "basic":
            dmg_text = self._font_med.render(f"Базовый урон: -{b.boss.y}", True, C_RED)
            screen.blit(dmg_text, (VSCREEN_W // 2 - dmg_text.get_width() // 2, PROBLEM_Y + 40))
        elif b._boss_problem:
            for i, line in enumerate(b._boss_problem.split("\n")):
                ls = self._font_med.render(line, True, C_WHITE)
                screen.blit(ls, (VSCREEN_W // 2 - ls.get_width() // 2, PROBLEM_Y + 40 + i * 26))

        hint = self._font_small.render("Нажми Enter чтобы продолжить", True, C_GRAY)
        screen.blit(hint, (VSCREEN_W // 2 - hint.get_width() // 2, PROBLEM_Y + 120))

    def _draw_input_zone(self, screen, b: BattleSystem):
        box_rect = pygame.Rect(100, PROBLEM_Y - 20, 600, 180)
        self._draw_box(screen, box_rect)

        for i, line in enumerate(b._boss_problem.split("\n")):
            ls = self._font_big.render(line, True, C_WHITE)
            screen.blit(ls, (VSCREEN_W // 2 - ls.get_width() // 2, PROBLEM_Y + i * 34))

        inp_y = PROBLEM_Y + 80
        cursor = "|" if self._cursor_vis else " "
        inp_str = b.input_buffer + cursor
        inp_surf = self._font_big.render(inp_str, True, C_YELLOW)
        inp_x = VSCREEN_W // 2 - inp_surf.get_width() // 2
        pygame.draw.rect(screen, (40, 40, 60),
                         (inp_x - 10, inp_y - 4, inp_surf.get_width() + 20, 36),
                         border_radius=4)
        screen.blit(inp_surf, (inp_x, inp_y))

        if b.error_text:
            err = self._font_med.render(b.error_text, True, C_RED)
            screen.blit(err, (VSCREEN_W // 2 - err.get_width() // 2, PROBLEM_Y + 130))

        hint = self._font_small.render("Введи ответ, нажми Enter", True, C_GRAY)
        screen.blit(hint, (VSCREEN_W // 2 - hint.get_width() // 2, PROBLEM_Y + 155))

    def _draw_result(self, screen, b: BattleSystem):
        if not b.result_text:
            return
        box_rect = pygame.Rect(150, PROBLEM_Y, 500, 80)
        self._draw_box(screen, box_rect, alpha=180)

        txt = self._font_med.render(b.result_text, True, C_WHITE)
        screen.blit(txt, (VSCREEN_W // 2 - txt.get_width() // 2, PROBLEM_Y + 25))

    def _draw_player_prompt(self, screen):
        hint = self._font_med.render("Твой ход — выбери атаку (1-4)", True, C_WHITE)
        screen.blit(hint, (VSCREEN_W // 2 - hint.get_width() // 2, PROBLEM_Y + 30))

    def _draw_overlay(self, screen, title: str, title_color, subtitle: str):
        ov = pygame.Surface((VSCREEN_W, VSCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        screen.blit(ov, (0, 0))

        ts = self._font_big.render(title, True, title_color)
        sub = self._font_med.render(subtitle, True, C_WHITE)

        cy = VSCREEN_H // 2
        screen.blit(ts, (VSCREEN_W // 2 - ts.get_width() // 2, cy - 30))
        screen.blit(sub, (VSCREEN_W // 2 - sub.get_width() // 2, cy + 20))

    @staticmethod
    def _draw_box(screen, rect: pygame.Rect, alpha=200):
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        surf.fill((10, 10, 30, alpha))
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, C_GRAY, rect, 1, border_radius=6)