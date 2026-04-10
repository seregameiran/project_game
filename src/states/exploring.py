"""
Модуль states/exploring.py
Состояние исследования карты.

Загружает TMX карту, отображает её, управляет игроком и камерой.
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.world.map_renderer import TiledMapRenderer
from src.world.camera import Camera
from src.entities.player import AnimatedPlayer


class ExploringState:
    """
    Состояние исследования карты.
    
    Отвечает за:
        - Загрузку и отрисовку карты
        - Управление игроком
        - Камеру, следующую за игроком
        - Коллизии с препятствиями
        - Взаимодействие с NPC и боссами (пока заглушки)
    """
    
    def __init__(self, game):
        """
        Инициализация состояния карты.
        
        Аргументы:
            game: ссылка на главный объект Game
        """
        self.game = game
        self.screen = game.screen
        
        # Параметры карты (пока для первой локации)
        self.current_location = 1
        self.map_renderer = None
        self.player = None
        self.camera = None
        
        # Флаг отладки (показывать коллизии)
        self.show_debug = False
        
        # Загружаем первую карту
        self.load_location(1)
    
    def load_location(self, location_id):
        """
        Загружает карту по номеру локации.
        
        Аргументы:
            location_id: номер локации (1-5)
        """
        # Путь к TMX файлу
        tmx_path = f"assets/location{location_id}/location{location_id}.tmx"
        
        try:
            self.map_renderer = TiledMapRenderer(tmx_path, zoom=1.5)
            print(f"Загружена локация {location_id}: {self.map_renderer.width}x{self.map_renderer.height}")
            
            # Создаём игрока в центре карты
            start_x = self.map_renderer.width // 2
            start_y = self.map_renderer.height // 2
            self.player = AnimatedPlayer(start_x, start_y, "assets/character/sprite/Billy.png", scale=1.5)
            
            # Создаём камеру
            self.camera = Camera(
                self.map_renderer.width,
                self.map_renderer.height,
                self.screen.get_width(),
                self.screen.get_height()
            )
            
        except Exception as e:
            print(f"Ошибка загрузки локации {location_id}: {e}")
    
    def handle_events(self, events):
        """
        Обработка событий в состоянии карты.
        
        Аргументы:
            events: список событий Pygame
        """
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Пауза (пока заглушка)
                    print("Пауза (будет реализовано позже)")
                elif event.key == pygame.K_F1:
                    # Включить/выключить отладку коллизий
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_e:
                    # Проверка взаимодействия с NPC/боссом
                    self.check_interaction()
    
    def check_interaction(self):
        """Проверяет, есть ли рядом NPC или босс для взаимодействия."""
        # TODO: реализовать проверку по объектам на карте
        # Пока просто заглушка
        print("Взаимодействие (будет реализовано позже)")
    
    def update(self, dt):
        """
        Обновление логики состояния карты.
        
        Аргументы:
            dt: время между кадрами (delta time)
        """
        if self.player is None or self.camera is None:
            return
        
        # Получаем нажатые клавиши
        keys = pygame.key.get_pressed()
        
        # Обновляем игрока (движение + коллизии)
        self.player.update(keys, self.map_renderer.check_collision)
        
        # Обновляем камеру
        self.camera.follow(self.player.rect)
    
    def draw(self, screen):
        """
        Отрисовка состояния карты.
        
        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
        if self.map_renderer is None:
            # Если карта не загружена, показываем ошибку
            screen.fill((0, 0, 0))
            font = pygame.font.Font(None, 36)
            text = font.render("Ошибка загрузки карты", True, (255, 0, 0))
            screen.blit(text, (screen.get_width() // 2 - 150, screen.get_height() // 2))
            return
        
        # Рисуем карту
        self.map_renderer.draw(screen, int(self.camera.x), int(self.camera.y))
        
        # Рисуем коллизии для отладки (если включено)
        if self.show_debug:
            self.map_renderer.draw_collisions_debug(screen, int(self.camera.x), int(self.camera.y))
        
        # Рисуем игрока
        self.player.draw(screen, int(self.camera.x), int(self.camera.y))
        
        # Отладочная информация
        font = pygame.font.Font(None, 24)
        info_text = font.render(
            f"Позиция: ({self.player.rect.x}, {self.player.rect.y})  "
            f"Камера: ({int(self.camera.x)}, {int(self.camera.y)})  "
            f"Коллизий: {len(self.map_renderer.collision_rects)}  "
            f"F1: отладка",
            True,
            (255, 255, 255)
        )
        screen.blit(info_text, (10, 10))