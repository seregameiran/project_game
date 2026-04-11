"""
Модуль entities/player.py
Класс игрока с анимацией из спрайт-листа.

Содержит два класса:
    - AnimatedPlayer: полноценный игрок с анимацией из Billy.png
    - Player: упрощённая версия (красный квадрат) для отладки
"""

import pygame


class AnimatedPlayer:
    """
    Класс анимированного игрока на основе спрайт-листа Billy.png.

    Спрайт-лист: 512x64 пикселей, 16 кадров по 32x64 каждый,
    все кадры расположены в один ряд.

    Структура анимаций:
        Кадры 0-1   — idle вниз   (персонаж дышит, смотрит на игрока)
        Кадры 1-3   — ходьба вниз
        Кадры 4-5   — idle вправо
        Кадры 5-7   — ходьба вправо
        Кадры 8-9   — idle влево
        Кадры 9-11  — ходьба влево
        Кадры 12-13 — idle вверх
        Кадры 13-15 — ходьба вверх

    Хитбокс:
        Нижняя треть спрайта (ноги персонажа).
        Спрайт отрисовывается над хитбоксом, выровненный по нижнему краю.

    Управление:
        W / стрелка вверх    — движение вверх
        S / стрелка вниз     — движение вниз
        A / стрелка влево    — движение влево
        D / стрелка вправо   — движение вправо
    """

    # Размеры одного кадра в оригинальном спрайт-листе (пикселей)
    FRAME_WIDTH  = 32
    FRAME_HEIGHT = 64

    # Общее количество кадров в спрайт-листе
    FRAME_COUNT = 16

    # Анимации: имя -> (первый кадр, последний кадр включительно)
    ANIMATIONS = {
        "idle_down":  (0,  1),
        "walk_down":  (1,  3),
        "idle_right": (4,  5),
        "walk_right": (5,  7),
        "idle_left":  (8,  9),
        "walk_left":  (9,  11),
        "idle_up":    (12, 13),
        "walk_up":    (13, 15),
    }

    # Длительность одного кадра анимации (секунд)
    FRAME_DURATION = 0.15

    def __init__(self, x, y, sprite_path, scale=1.5):
        """
        Инициализация анимированного игрока.

        Загружает спрайт-лист, нарезает кадры, создаёт хитбокс.

        Аргументы:
            x: начальная X координата хитбокса в пикселях (мировые координаты)
            y: начальная Y координата хитбокса в пикселях (мировые координаты)
            sprite_path: путь к файлу спрайт-листа Billy.png
            scale: масштаб спрайта относительно оригинала (по умолчанию 1.5)
        """
        self.scale = scale
        self.speed = 4

        # Размеры спрайта с учётом масштаба
        w = int(self.FRAME_WIDTH  * scale)
        h = int(self.FRAME_HEIGHT * scale)

        # Хитбокс — нижняя треть спрайта (область ног)
        # Это позволяет персонажу визуально "стоять" на препятствиях
        hitbox_h = h // 3
        self.rect = pygame.Rect(x, y, w, hitbox_h)

        # Загружаем спрайт-лист и нарезаем кадры
        sheet = pygame.image.load(sprite_path).convert_alpha()
        self.frames = []
        for i in range(self.FRAME_COUNT):
            frame = sheet.subsurface(
                pygame.Rect(i * self.FRAME_WIDTH, 0, self.FRAME_WIDTH, self.FRAME_HEIGHT)
            )
            frame = pygame.transform.scale(frame, (w, h))
            self.frames.append(frame)

        # Текущее название анимации (ключ из словаря ANIMATIONS)
        self.current_anim = "idle_down"

        # Таймер для переключения кадров (секунд)
        self.anim_timer = 0.0

        # Индекс текущего кадра внутри анимации (0, 1, 2...)
        self.frame_index = 0

    def _set_animation(self, name):
        """
        Переключает текущую анимацию.

        Если анимация уже активна — ничего не делает (не сбрасывает кадр).
        При смене анимации сбрасывает таймер и индекс кадра на начало.

        Аргументы:
            name: название анимации (ключ из словаря ANIMATIONS)
        """
        if self.current_anim != name:
            self.current_anim = name
            self.frame_index  = 0
            self.anim_timer   = 0.0

    def update(self, keys, collision_callback, map_bounds=None):
        """
        Обновляет логику игрока: движение, коллизии, выбор анимации.

        Движение раздельное по осям — это позволяет скользить вдоль стен.
        Анимация выбирается по направлению движения. При остановке
        автоматически переключается на idle того же направления.

        Аргументы:
            keys: словарь нажатых клавиш от pygame.key.get_pressed()
            collision_callback: функция(rect) -> bool, True если есть коллизия
            map_bounds: pygame.Rect с границами карты; если None — не ограничивает
        """
        dx = 0
        dy = 0

        # Считываем нажатые клавиши
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx =  self.speed
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy = -self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy =  self.speed

        moving = dx != 0 or dy != 0

        # Выбираем анимацию по направлению движения
        if moving:
            if   dy > 0: self._set_animation("walk_down")
            elif dy < 0: self._set_animation("walk_up")
            elif dx > 0: self._set_animation("walk_right")
            elif dx < 0: self._set_animation("walk_left")
        else:
            # При остановке — idle того же направления
            self._set_animation(self.current_anim.replace("walk_", "idle_"))

        # Движение по X с проверкой коллизий
        if dx != 0:
            self.rect.x += dx
            if collision_callback(self.rect):
                self.rect.x -= dx

        # Движение по Y с проверкой коллизий
        if dy != 0:
            self.rect.y += dy
            if collision_callback(self.rect):
                self.rect.y -= dy

        # Ограничение границами карты
        if map_bounds is not None:
            self.rect.x = max(map_bounds.left,
                min(self.rect.x, map_bounds.right  - self.rect.width))
            self.rect.y = max(map_bounds.top,
                min(self.rect.y, map_bounds.bottom - self.rect.height))

    def update_animation(self, dt):
        """
        Обновляет таймер анимации и переключает кадры.

        Вызывать каждый кадр после update(), передавая delta time.

        Аргументы:
            dt: время прошедшее с прошлого кадра (секунд)
        """
        self.anim_timer += dt

        if self.anim_timer >= self.FRAME_DURATION:
            self.anim_timer = 0.0

            # Длина текущей анимации в кадрах
            start, end = self.ANIMATIONS[self.current_anim]
            anim_len = end - start + 1

            # Переходим к следующему кадру (по кругу)
            self.frame_index = (self.frame_index + 1) % anim_len

    def _current_frame(self):
        """
        Возвращает поверхность текущего кадра анимации.

        Возвращает:
            pygame.Surface — текущий кадр с учётом анимации и масштаба
        """
        start, _ = self.ANIMATIONS[self.current_anim]
        return self.frames[start + self.frame_index]

    def draw(self, screen, camera_x, camera_y):
        """
        Отрисовывает спрайт игрока на экране.

        Спрайт выравнивается по нижнему краю хитбокса и центрируется по X.
        Это создаёт ощущение что персонаж стоит ногами на поверхности.

        Аргументы:
            screen: поверхность Pygame для отрисовки
            camera_x: X координата левого верхнего угла камеры
            camera_y: Y координата левого верхнего угла камеры
        """
        frame = self._current_frame()

        # Выравниваем спрайт по центру хитбокса (X) и по нижнему краю (Y)
        sprite_x = self.rect.centerx - frame.get_width()  // 2 - camera_x
        sprite_y = self.rect.bottom  - frame.get_height()      - camera_y

        screen.blit(frame, (sprite_x, sprite_y))


class Player:
    """
    Упрощённая версия игрока без анимации — красный квадрат.

    Используется для отладки или как заглушка когда
    спрайт-лист недоступен.

    Управление:
        W / стрелка вверх    — движение вверх
        S / стрелка вниз     — движение вниз
        A / стрелка влево    — движение влево
        D / стрелка вправо   — движение вправо
    """

    def __init__(self, x, y):
        """
        Инициализация игрока.

        Аргументы:
            x: начальная X координата в пикселях (мировые координаты)
            y: начальная Y координата в пикселях (мировые координаты)
        """
        self.rect  = pygame.Rect(x, y, 32, 32)
        self.speed = 4

    def update(self, keys, collision_callback, map_bounds=None):
        """
        Обновляет логику игрока: движение и коллизии.

        Аргументы:
            keys: словарь нажатых клавиш от pygame.key.get_pressed()
            collision_callback: функция(rect) -> bool, True если есть коллизия
            map_bounds: pygame.Rect с границами карты; если None — не ограничивает
        """
        dx = 0
        dy = 0

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx =  self.speed
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy = -self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy =  self.speed

        # Движение по X с проверкой коллизий
        if dx != 0:
            self.rect.x += dx
            if collision_callback(self.rect):
                self.rect.x -= dx

        # Движение по Y с проверкой коллизий
        if dy != 0:
            self.rect.y += dy
            if collision_callback(self.rect):
                self.rect.y -= dy

        # Ограничение границами карты
        if map_bounds is not None:
            self.rect.x = max(map_bounds.left,
                min(self.rect.x, map_bounds.right  - self.rect.width))
            self.rect.y = max(map_bounds.top,
                min(self.rect.y, map_bounds.bottom - self.rect.height))

    def update_animation(self, dt):
        """
        Заглушка для совместимости с AnimatedPlayer.

        Аргументы:
            dt: время прошедшее с прошлого кадра (секунд), не используется
        """
        pass

    def draw(self, screen, camera_x, camera_y):
        """
        Отрисовывает красный квадрат на экране.

        Аргументы:
            screen: поверхность Pygame для отрисовки
            camera_x: X координата левого верхнего угла камеры
            camera_y: Y координата левого верхнего угла камеры
        """
        pygame.draw.rect(screen, (255, 0, 0),
            (self.rect.x - camera_x, self.rect.y - camera_y, 32, 32))