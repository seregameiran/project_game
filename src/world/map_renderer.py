"""
Модуль world/map_renderer.py
Рендерер карты из TMX файла с поддержкой изометрической проекции и масштаба.
"""

import pygame
import pytmx
from pytmx.util_pygame import load_pygame


class TiledMapRenderer:
    """Класс для загрузки и отрисовки TMX карты с поддержкой изометрической проекции"""
    
    def __init__(self, filename, zoom=1.0):
        self.zoom = zoom
        
        # Загружаем карту из TMX файла
        self.tmx_data = load_pygame(filename)
        
        # Определяем ориентацию карты
        self.orientation = getattr(self.tmx_data, 'orientation', 'orthogonal')
        print(f"📐 Ориентация карты: {self.orientation}")
        
        # Размеры карты в пикселях (оригинальные)
        self.orig_tilewidth = self.tmx_data.tilewidth
        self.orig_tileheight = self.tmx_data.tileheight
        
        # Размеры с учётом зума
        self.tilewidth = int(self.orig_tilewidth * zoom)
        self.tileheight = int(self.orig_tileheight * zoom)
        
        if self.orientation == 'isometric':
            # Для изометрической карты размеры рассчитываются иначе
            self.width = (self.tmx_data.width + self.tmx_data.height) * self.tilewidth // 2
            self.height = (self.tmx_data.height + self.tmx_data.width) * self.tileheight // 2
        else:
            self.width = self.tmx_data.width * self.tilewidth
            self.height = self.tmx_data.height * self.tileheight
        
        # Создаем поверхность для всей карты
        self.map_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Список коллизий
        self.collision_rects = []
        
        # Рендерим карту один раз при создании
        self._render_map()
        self._load_collisions()
        
        print(f"📏 Размер карты: {self.width}x{self.height}")
    
    def _render_map(self):
        """Рендерит всю карту на внутреннюю поверхность"""
        
        # Заливаем фон
        if self.tmx_data.background_color:
            self.map_surface.fill(pygame.Color(self.tmx_data.background_color))
        else:
            self.map_surface.fill((0, 0, 0, 0))
        
        # Отрисовываем все видимые слои
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                self._render_tile_layer(layer)
            elif isinstance(layer, pytmx.TiledObjectGroup):
                self._render_object_layer(layer)
            elif isinstance(layer, pytmx.TiledImageLayer):
                if layer.image:
                    img = layer.image
                    if self.zoom != 1.0:
                        img = pygame.transform.scale(img, (int(img.get_width() * self.zoom), int(img.get_height() * self.zoom)))
                    self.map_surface.blit(img, (0, 0))
    
    def _render_tile_layer(self, layer):
        """Отрисовка тайлового слоя с поддержкой изометрической проекции"""
        for x, y, image in layer.tiles():
            if image:
                if self.zoom != 1.0:
                    image = pygame.transform.scale(image, (self.tilewidth, self.tileheight))
                
                if self.orientation == 'isometric':
                    # Для изометрической карты тайлы рисуются со смещением
                    screen_x = (x - y) * (self.tilewidth // 2)
                    screen_y = (x + y) * (self.tileheight // 2)
                    self.map_surface.blit(image, (screen_x, screen_y))
                else:
                    # Для ортогональной карты
                    self.map_surface.blit(image, (x * self.tilewidth, y * self.tileheight))
    
    def _render_object_layer(self, layer):
        """Отрисовка слоя объектов с поддержкой изометрической проекции"""
        for obj in layer:
            if obj.image:
                # Получаем правильные координаты для отрисовки
                render_x, render_y = self._get_render_position(obj.x, obj.y)
                
                img = obj.image
                if self.zoom != 1.0:
                    img = pygame.transform.scale(img, (int(img.get_width() * self.zoom), int(img.get_height() * self.zoom)))
                
                # Масштабируем изображение под размер объекта, если нужно
                if obj.width > 0 and obj.height > 0:
                    img = pygame.transform.scale(img, (int(obj.width * self.zoom), int(obj.height * self.zoom)))
                
                self.map_surface.blit(img, (render_x, render_y))
    
    def _get_render_position(self, x, y):
        """
        Преобразует координаты из Tiled в экранные координаты
        с учётом изометрической проекции и масштаба.
        """
        if self.orientation == 'isometric':
            # В изометрической проекции позиция объекта преобразуется
            screen_x = (x - y) * (self.tilewidth // 2) / (self.orig_tilewidth / 2) if self.orig_tilewidth > 0 else x
            screen_y = (x + y) * (self.tileheight // 2) / (self.orig_tileheight / 2) if self.orig_tileheight > 0 else y
            
            return int(screen_x), int(screen_y)
        else:
            # Для ортогональной карты используем координаты как есть с учётом зума
            return int(x * self.zoom), int(y * self.zoom)
    
    def _load_collisions(self):
        """Загружает коллизии из слоя collision"""
        self.collision_rects = []
        
        for obj in self.tmx_data.objects:
            # Проверяем, является ли объект коллизией
            is_collision = False
            
            if obj.properties.get('collision', False):
                is_collision = True
            elif obj.properties.get('solid', False):
                is_collision = True
            elif hasattr(obj, 'type') and obj.type in ['collision', 'wall', 'block']:
                is_collision = True
            
            if is_collision:
                render_x, render_y = self._get_render_position(obj.x, obj.y)
                rect = pygame.Rect(render_x, render_y, obj.width * self.zoom, obj.height * self.zoom)
                self.collision_rects.append(rect)
        
        print(f"🟢 Загружено коллизий: {len(self.collision_rects)}")
    
    def draw(self, screen, camera_x=0, camera_y=0):
        """Отрисовывает карту на экране с поддержкой камеры"""
        screen.blit(self.map_surface, (-camera_x, -camera_y))
    
    def draw_collisions_debug(self, screen, camera_x=0, camera_y=0):
        """Рисует коллизии для отладки"""
        for rect in self.collision_rects:
            debug_rect = pygame.Rect(
                rect.x - camera_x,
                rect.y - camera_y,
                rect.width,
                rect.height
            )
            pygame.draw.rect(screen, (255, 0, 0), debug_rect, 2)
    
    def check_collision(self, rect):
        """Проверяет пересечение с коллизиями"""
        for collision_rect in self.collision_rects:
            if rect.colliderect(collision_rect):
                return True
        return False