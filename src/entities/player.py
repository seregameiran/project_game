"""
Модуль entities/player.py
Классы игрока.

Отвечают за создание, управление и отрисовку игрока на карте.
"""

import pygame


class AnimatedPlayer:
    """
    Класс анимированного игрока (временная версия — красный квадрат).
    
    В будущем будет заменён на полноценного анимированного персонажа
    с использованием спрайт-листа Billy.png.
    
    Управление:
        - W/A/S/D или стрелки для движения
        - Коллизии с препятствиями
    
    TODO: Реализовать анимацию движения из спрайт-листа.
    """
    
    def __init__(self, x, y, sprite_path, scale=1.5):
        """
        Инициализация анимированного игрока.
        
        Аргументы:
            x: начальная X координата в пикселях
            y: начальная Y координата в пикселях
            sprite_path: путь к файлу спрайт-листа (пока не используется)
            scale: масштаб спрайта (пока не используется)
        """
        # Прямоугольник игрока (позиция и размер)
        self.rect = pygame.Rect(x, y, 32, 32)
        
        # Скорость движения (пикселей в кадр при 60 FPS)
        self.speed = 4
    
    def update(self, keys, collision_callback):
        """
        Обновление логики игрока: движение и проверка коллизий.
        
        Аргументы:
            keys: список нажатых клавиш от pygame.key.get_pressed()
            collision_callback: функция проверки коллизий, принимает rect и возвращает bool
        """
        dx = 0  # изменение по X
        dy = 0  # изменение по Y
        
        # Обработка нажатий клавиш
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = self.speed
        
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
    
    def draw(self, screen, camera_x, camera_y):
        """
        Отрисовка игрока на экране.
        
        Аргументы:
            screen: поверхность Pygame для рисования
            camera_x: X координата левого верхнего угла камеры
            camera_y: Y координата левого верхнего угла камеры
        """
        # Рисуем красный квадрат (временная заглушка)
        # Координаты корректируются с учётом камеры
        pygame.draw.rect(
            screen,
            (255, 0, 0),  # красный цвет
            (self.rect.x - camera_x, self.rect.y - camera_y, 32, 32)
        )


class Player:
    """
    Класс игрока (простая версия — красный квадрат).
    
    Альтернативная версия без параметров sprite_path и scale.
    Используется, когда анимация не требуется.
    
    Управление:
        - W/A/S/D или стрелки для движения
        - Коллизии с препятствиями
    """
    
    def __init__(self, x, y):
        """
        Инициализация игрока.
        
        Аргументы:
            x: начальная X координата в пикселях
            y: начальная Y координата в пикселях
        """
        # Прямоугольник игрока (позиция и размер)
        self.rect = pygame.Rect(x, y, 32, 32)
        
        # Скорость движения (пикселей в кадр при 60 FPS)
        self.speed = 4
    
    def update(self, keys, collision_callback):
        """
        Обновление логики игрока: движение и проверка коллизий.
        
        Аргументы:
            keys: список нажатых клавиш от pygame.key.get_pressed()
            collision_callback: функция проверки коллизий, принимает rect и возвращает bool
        """
        dx = 0  # изменение по X
        dy = 0  # изменение по Y
        
        # Обработка нажатий клавиш
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = self.speed
        
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
    
    def draw(self, screen, camera_x, camera_y):
        """
        Отрисовка игрока на экране.
        
        Аргументы:
            screen: поверхность Pygame для рисования
            camera_x: X координата левого верхнего угла камеры
            camera_y: Y координата левого верхнего угла камеры
        """
        # Рисуем красный квадрат
        # Координаты корректируются с учётом камеры
        pygame.draw.rect(
            screen,
            (255, 0, 0),  # красный цвет
            (self.rect.x - camera_x, self.rect.y - camera_y, 32, 32)
        )