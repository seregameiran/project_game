"""
src/ui/hud.py
BattleHUD — отрисовка экрана боя.
Весь pygame-код рендеринга живёт здесь.
Не знает ничего об игровой логике — только читает поля BattleSystem.
"""

import os
import pygame

from battle.battle_system import (
    Phase,
    PLAYER_HP_START,
    BOSS_HP_START,
)

# ---------------------------------------------------------------------------
# Цвета (из оригинального battle.py)
# ---------------------------------------------------------------------------

COLOR_WHITE     = (255, 255, 255)
COLOR_BLACK     = (0,   0,   0)
COLOR_RED       = (220, 50,  50)
COLOR_GREEN     = (50,  200, 80)
COLOR_YELLOW    = (240, 200, 40)
COLOR_GRAY      = (120, 120, 120)
COLOR_HP_RED    = (200, 40,  40)
COLOR_HP_BG     = (60,  20,  20)
COLOR_HP_GREEN  = (40,  180, 60)
COLOR_HP_BOSS_BG = (20, 40,  60)
COLOR_HP_BOSS   = (40,  140, 220)

# Имена боссов для отображения
BOSS_DISPLAY_NAMES = {1: "Внучка", 2: "Отец", 3: "Бабушка"}

# Пути к спрайтам по boss_id
BOSS_SPRITE_NAMES = {
    1: ("location3", "NPC-3-Head.png"),
    2: ("location4", "Boss-2-Head.png"),
    3: ("location5", "Boss-3-Head.png"),
}


class BattleHUD:
    """
    Отвечает за весь рендеринг экрана боя.
    Создаётся один раз в BattleState, переиспользуется между боями.
    """

    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self._loaded  = False

        self.font_big   = None
        self.font_mid   = None
        self.font_small = None
        self.font_hint  = None

        self.battle_bg     = None
        self.boss_sprite   = None
        self.player_sprite = None
        self._loaded_boss_id = None   # чтобы перегружать спрайт при смене босса

    # -----------------------------------------------------------------------
    # Загрузка ресурсов
    # -----------------------------------------------------------------------

    def load(self, boss_id: int):
        """
        Загружает шрифты и спрайты для указанного boss_id.
        Шрифты грузятся один раз, спрайт босса — при смене boss_id.
        """
        if not self._loaded:
            self._load_fonts()
            self._load_battle_bg()
            self._load_player_sprite()
            self._loaded = True

        if self._loaded_boss_id != boss_id:
            self._load_boss_sprite(boss_id)
            self._loaded_boss_id = boss_id

    def _load_fonts(self):
        font_path = os.path.join(self.root_dir, "assets", "menu", "Compilance-Sans.ttf")

        def f(size):
            try:
                return pygame.font.Font(font_path, size)
            except Exception:
                return pygame.font.SysFont("Arial", size)

        self.font_big   = f(36)
        self.font_mid   = f(26)
        self.font_small = f(20)
        self.font_hint  = f(18)

    def _load_battle_bg(self):
        path = os.path.join(self.root_dir, "assets", "location3", "battle_bg.png")
        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert()
                self.battle_bg = pygame.transform.scale(img, (800, 608))
        except Exception as e:
            print(f"[HUD] Не удалось загрузить фон боя: {e}")

    def _load_player_sprite(self):
        path = os.path.join(self.root_dir, "assets", "location3", "Billy-Head.png")
        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                # Billy-Head — спрайтлист 4 кадра, берём первый
                frame_w = img.get_width() // 4 if img.get_width() > img.get_height() else img.get_width()
                frame = img.subsurface(pygame.Rect(0, 0, frame_w, img.get_height()))
                self.player_sprite = pygame.transform.scale(frame, (80, 80))
        except Exception as e:
            print(f"[HUD] Не удалось загрузить спрайт игрока: {e}")

    def _load_boss_sprite(self, boss_id: int):
        self.boss_sprite = None
        loc, name = BOSS_SPRITE_NAMES.get(boss_id, ("location3", "Boss-1.png"))
        path = os.path.join(self.root_dir, "assets", loc, name)
        try:
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                self.boss_sprite = pygame.transform.scale(img, (80, 80))
        except Exception as e:
            print(f"[HUD] Не удалось загрузить спрайт босса {boss_id}: {e}")

    # -----------------------------------------------------------------------
    # Главный метод отрисовки
    # -----------------------------------------------------------------------

    def draw(self, screen: pygame.Surface, sys: "BattleSystem"):
        """
        Рисует весь экран боя.
        sys — объект BattleSystem с актуальными данными.
        """
        W, H = screen.get_width(), screen.get_height()

        # Фон
        if self.battle_bg:
            screen.blit(self.battle_bg, (0, 0))
        else:
            for i in range(H):
                v = 18 + int(i / H * 30)
                pygame.draw.line(screen, (v, v, v + 20), (0, i), (W, i))

        # Прямоугольник босса — справа сверху
        boss_box = pygame.Rect(W - 260, 20, 260, 140)
        pygame.draw.rect(screen, COLOR_BLACK, boss_box, border_radius=10)
        pygame.draw.rect(screen, COLOR_WHITE, boss_box, 2, border_radius=10)

        # Прямоугольник игрока — слева сверху
        player_box = pygame.Rect(20, 20, 260, 140)
        pygame.draw.rect(screen, COLOR_BLACK, player_box, border_radius=10)
        pygame.draw.rect(screen, COLOR_WHITE, player_box, 2, border_radius=10)

        # Имена над прямоугольниками
        boss_name = BOSS_DISPLAY_NAMES.get(sys.boss_id, "Босс")
        self._blit_centered(screen, self.font_mid, boss_name, COLOR_YELLOW,
                            boss_box.centerx, boss_box.y - 22)
        self._blit_centered(screen, self.font_mid, "Билли", COLOR_YELLOW,
                            player_box.centerx, player_box.y - 22)

        # Спрайты
        if self.boss_sprite:
            bx = boss_box.right - self.boss_sprite.get_width() - 20
            by = boss_box.y + (140 - self.boss_sprite.get_height()) // 2
            screen.blit(self.boss_sprite, (bx, by))

        if self.player_sprite:
            px = player_box.x + 20
            py = player_box.y + (140 - self.player_sprite.get_height()) // 2
            screen.blit(self.player_sprite, (px, py))

        # HP и параметры босса
        bx = boss_box.x + 20
        by = boss_box.y + 40
        self._draw_hp_bar(screen, bx, by, 100, 18,
                          sys.hp_boss, BOSS_HP_START.get(sys.boss_id, 60),
                          COLOR_HP_BOSS, COLOR_HP_BOSS_BG)
        hp_txt = self.font_small.render(
            f"HP: {max(0, sys.hp_boss)}/{BOSS_HP_START.get(sys.boss_id, 60)}",
            True, COLOR_WHITE)
        screen.blit(hp_txt, (bx, by - 18))
        y_label = f"Урон Y: {sys.y}" if sys.y_revealed else "Урон Y: ?"
        y_txt = self.font_mid.render(y_label, True, (100, 180, 255))
        screen.blit(y_txt, (boss_box.x + 20, boss_box.y + 70))

        # HP и параметры игрока
        px2 = player_box.x + 120
        py2 = player_box.y + 40
        self._draw_hp_bar(screen, px2, py2, 100, 18,
                          sys.hp_player, PLAYER_HP_START.get(sys.boss_id, 80),
                          COLOR_HP_GREEN, COLOR_HP_BG)
        hp_txt2 = self.font_small.render(
            f"HP: {max(0, sys.hp_player)}/{PLAYER_HP_START.get(sys.boss_id, 80)}",
            True, COLOR_WHITE)
        screen.blit(hp_txt2, (px2, py2 - 18))
        x_txt = self.font_mid.render(f"Урон X: {sys.x}", True, COLOR_YELLOW)
        screen.blit(x_txt, (player_box.x + 120, player_box.y + 70))

        # Центральная зона: пример или подсказка выбора
        if sys.problem_text:
            self._draw_problem(screen, W, H, sys)
        elif sys.phase == Phase.PLAYER_CHOOSE:
            t = self.font_mid.render("Выбери атаку!", True, COLOR_YELLOW)
            screen.blit(t, (W // 2 - t.get_width() // 2, H // 2 - 30))

        # Нижняя панель
        info_box = pygame.Rect(20, H - 180, W - 40, 160)
        pygame.draw.rect(screen, COLOR_BLACK, info_box, border_radius=10)
        pygame.draw.rect(screen, COLOR_WHITE, info_box, 2, border_radius=10)

        self._draw_attack_icons(screen, sys, info_box)

        # Подсказка ESC
        esc = self.font_hint.render("ESC — выйти из боя", True, COLOR_GRAY)
        screen.blit(esc, (info_box.right - esc.get_width() - 20,
                          info_box.bottom - 28))

        # Сообщение фидбека (зелёное)
        if sys.feedback_msg:
            s = self.font_mid.render(sys.feedback_msg, True, COLOR_GREEN)
            screen.blit(s, (info_box.centerx - s.get_width() // 2, info_box.y + 15))

        # Сообщение ошибки (красное)
        if sys.error_msg:
            s = self.font_mid.render(sys.error_msg, True, COLOR_RED)
            screen.blit(s, (info_box.centerx - s.get_width() // 2, info_box.y + 50))

        # Финальный оверлей
        if sys.phase == Phase.RESULT and sys.result_msg:
            self._draw_result_overlay(screen, W, H, sys)

    # -----------------------------------------------------------------------
    # Части UI
    # -----------------------------------------------------------------------

    def _draw_hp_bar(self, screen, x, y, w, h, hp, max_hp, color, bg):
        pygame.draw.rect(screen, bg, (x, y, w, h), border_radius=4)
        fill_w = int(w * max(0, hp) / max(1, max_hp))
        pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=4)
        pygame.draw.rect(screen, (80, 80, 80), (x, y, w, h), 1, border_radius=4)

    def _draw_attack_icons(self, screen, sys: "BattleSystem",
                           info_box: pygame.Rect):
        slots = [
            ("1", "add", "Сложение"),
            ("2", "sub", "Вычитание"),
            ("3", "mul", "Умножение"),
            ("4", "div", "Деление"),
        ]
        available = [s for s in slots if sys._is_unlocked(s[1])]
        if not available:
            return

        slot_w  = 110
        start_x = info_box.centerx - (len(available) * slot_w) // 2
        sy      = info_box.bottom - 50

        for i, (key, att, name) in enumerate(available):
            sx    = start_x + i * slot_w
            active = sys.phase == Phase.PLAYER_CHOOSE
            bg    = (50, 50, 80) if active else (30, 30, 50)
            pygame.draw.rect(screen, bg,        (sx, sy, 100, 40), border_radius=6)
            pygame.draw.rect(screen, (80,80,120),(sx, sy, 100, 40), 1, border_radius=6)

            k = self.font_hint.render(f"[{key}]", True, COLOR_YELLOW)
            n = self.font_hint.render(name,        True, COLOR_WHITE)
            screen.blit(k, (sx + 8, sy + 6))
            screen.blit(n, (sx + 8, sy + 22))

    def _draw_problem(self, screen, W, H, sys: "BattleSystem"):
        box_w, box_h = 420, 120
        box_x = W // 2 - box_w // 2
        box_y = H // 2 - box_h // 2

        s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        s.fill((10, 10, 30, 230))
        screen.blit(s, (box_x, box_y))
        pygame.draw.rect(screen, (80, 80, 160),
                         (box_x, box_y, box_w, box_h), 2, border_radius=8)

        for i, line in enumerate(sys.problem_text.split("\n")):
            color = COLOR_YELLOW if i == 0 else COLOR_WHITE
            surf  = self.font_mid.render(line, True, color)
            screen.blit(surf, (box_x + 20, box_y + 15 + i * 30))

        # Мигающий курсор
        cursor   = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        buf_surf = self.font_big.render(sys.answer_buffer + cursor, True, COLOR_WHITE)
        inp_x    = box_x + box_w // 2 - buf_surf.get_width() // 2
        inp_y    = box_y + box_h - 50
        pygame.draw.line(screen, (100, 100, 200),
                         (box_x + 20,       inp_y + 36),
                         (box_x + box_w - 20, inp_y + 36), 2)
        screen.blit(buf_surf, (inp_x, inp_y))

    def _draw_result_overlay(self, screen, W, H, sys: "BattleSystem"):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        color = COLOR_GREEN if sys.victory else COLOR_RED
        main  = self.font_big.render(sys.result_msg, True, color)
        sub   = self.font_small.render("Возврат через секунду...", True, COLOR_GRAY)
        screen.blit(main, (W // 2 - main.get_width() // 2, H // 2 - 30))
        screen.blit(sub,  (W // 2 - sub.get_width()  // 2, H // 2 + 20))

    # -----------------------------------------------------------------------
    # Утилита
    # -----------------------------------------------------------------------

    @staticmethod
    def _blit_centered(screen, font, text, color, cx, y):
        surf = font.render(text, True, color)
        screen.blit(surf, (cx - surf.get_width() // 2, y))