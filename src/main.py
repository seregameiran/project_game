import pygame
import pytmx
from pytmx.util_pygame import load_pygame

class TiledMapRenderer:
    """Класс для загрузки и отрисовки TMX карты"""
    
    def __init__(self, filename, zoom=1.5):
        self.tmx_data = load_pygame(filename)
        self.zoom = zoom
        
        self.original_tile_width = self.tmx_data.tilewidth
        self.original_tile_height = self.tmx_data.tileheight
        
        self.tilewidth = int(self.original_tile_width * zoom)
        self.tileheight = int(self.original_tile_height * zoom)
        
        self.orientation = getattr(self.tmx_data, 'orientation', 'orthogonal')
        print(f"📐 Ориентация карты: {self.orientation}")
        print(f"🔍 Zoom: {zoom}")
        
        if self.orientation == 'isometric':
            self.width = (self.tmx_data.width + self.tmx_data.height) * self.tilewidth // 2
            self.height = (self.tmx_data.height + self.tmx_data.width) * self.tileheight // 2
        else:
            self.width = self.tmx_data.width * self.tilewidth
            self.height = self.tmx_data.height * self.tileheight
        
        self.map_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.collision_rects = []
        
        self.render_map()
        self._load_collisions()
    
    def render_map(self):
        if self.tmx_data.background_color:
            self.map_surface.fill(pygame.Color(self.tmx_data.background_color))
        else:
            self.map_surface.fill((0, 0, 0, 0))
        
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                self._render_tile_layer(layer)
            elif isinstance(layer, pytmx.TiledObjectGroup):
                self._render_object_layer(layer)
            elif isinstance(layer, pytmx.TiledImageLayer):
                if layer.image:
                    scaled = pygame.transform.scale(layer.image, 
                        (int(layer.image.get_width() * self.zoom), 
                         int(layer.image.get_height() * self.zoom)))
                    self.map_surface.blit(scaled, (0, 0))
    
    def _render_tile_layer(self, layer):
        for x, y, image in layer.tiles():
            if image:
                scaled_image = pygame.transform.scale(image, (self.tilewidth, self.tileheight))
                
                if self.orientation == 'isometric':
                    screen_x = (x - y) * (self.tilewidth // 2)
                    screen_y = (x + y) * (self.tileheight // 2)
                    self.map_surface.blit(scaled_image, (screen_x, screen_y))
                else:
                    self.map_surface.blit(scaled_image, (x * self.tilewidth, y * self.tileheight))
    
    def _render_object_layer(self, layer):
        """Отрисовка слоя объектов - пропускаем объекты игрока"""
        for obj in layer:
            obj_type = getattr(obj, 'type', '')
            if obj_type == 'player' or obj_type == 'Player':
                continue
            
            if obj.image:
                scaled_w = int(obj.width * self.zoom) if obj.width > 0 else obj.image.get_width()
                scaled_h = int(obj.height * self.zoom) if obj.height > 0 else obj.image.get_height()
                scaled_image = pygame.transform.scale(obj.image, (scaled_w, scaled_h))
                
                if self.orientation == 'isometric':
                    render_x, render_y = self._world_to_screen(obj.x * self.zoom, obj.y * self.zoom)
                    self.map_surface.blit(scaled_image, (render_x, render_y))
                else:
                    self.map_surface.blit(scaled_image, (obj.x * self.zoom, obj.y * self.zoom))
    
    def _world_to_screen(self, world_x, world_y):
        if self.orientation == 'isometric':
            screen_x = (world_x - world_y) / self.original_tile_width * (self.tilewidth // 2)
            screen_y = (world_x + world_y) / self.original_tile_height * (self.tileheight // 2)
            return int(screen_x), int(screen_y)
        return world_x, world_y
    
    def _load_collisions(self):
        print("\n🔍 ЗАГРУЗКА КОЛЛИЗИЙ:")
        
        for layer in self.tmx_data.layers:
            if isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    is_collision = False
                    
                    if obj.properties.get('collision', False):
                        is_collision = True
                    elif obj.properties.get('solid', False):
                        is_collision = True
                    elif hasattr(obj, 'type') and obj.type in ['collision', 'wall', 'block', 'solid']:
                        is_collision = True
                    
                    if is_collision:
                        scaled_x = obj.x * self.zoom
                        scaled_y = obj.y * self.zoom
                        scaled_w = obj.width * self.zoom if obj.width > 0 else self.tilewidth
                        scaled_h = obj.height * self.zoom if obj.height > 0 else self.tileheight
                        
                        if self.orientation == 'isometric':
                            screen_x, screen_y = self._world_to_screen(scaled_x, scaled_y)
                            rect = pygame.Rect(screen_x, screen_y, scaled_w, scaled_h)
                        else:
                            rect = pygame.Rect(scaled_x, scaled_y, scaled_w, scaled_h)
                        
                        self.collision_rects.append(rect)
                        print(f"  ✅ Коллизия добавлена: {obj.name if obj.name else 'объект'}")
        
        print(f"🟢 Всего коллизий: {len(self.collision_rects)}")
    
    def check_collision(self, rect):
        for collision_rect in self.collision_rects:
            if rect.colliderect(collision_rect):
                return True
        return False
    
    def draw(self, screen, camera_x=0, camera_y=0):
        screen.blit(self.map_surface, (-camera_x, -camera_y))
    
    def draw_collisions_debug(self, screen, camera_x=0, camera_y=0):
        for rect in self.collision_rects:
            debug_rect = pygame.Rect(rect.x - camera_x, rect.y - camera_y, rect.width, rect.height)
            pygame.draw.rect(screen, (255, 0, 0, 180), debug_rect, 3)
            s = pygame.Surface((rect.width, rect.height))
            s.set_alpha(80)
            s.fill((255, 0, 0))
            screen.blit(s, (rect.x - camera_x, rect.y - camera_y))


class AnimatedPlayer:
    """Класс анимированного игрока с анимацией дыхания (idle)"""
    
    def __init__(self, x, y, sprite_path, scale=1.5):
        self.sprite_sheet = pygame.image.load(sprite_path).convert_alpha()
        
        sheet_width = self.sprite_sheet.get_width()
        sheet_height = self.sprite_sheet.get_height()
        
        print(f"📏 Размер PNG: {sheet_width} x {sheet_height}")
        
        # Для 16 кадров в строке: 512 / 16 = 32 пикселя на кадр
        self.frame_width = sheet_width // 16
        self.frame_height = sheet_height
        
        print(f"📏 Размер одного кадра: {self.frame_width} x {self.frame_height}")
        
        self.scale = scale
        self.scaled_width = int(self.frame_width * scale)
        self.scaled_height = int(self.frame_height * scale)
        
        self.rect = pygame.Rect(x, y, self.scaled_width - 10, self.scaled_height - 10)
        self.rect.center = (x, y)
        
        # Загружаем все 16 кадров
        all_frames = self._load_all_frames()
        print(f"📊 Всего загружено кадров: {len(all_frames)}")
        
        # Распределение кадров: 2 idle + 2 walk на каждое направление
        if len(all_frames) >= 16:
            self.idle_animations = {
                'down': all_frames[0:2],
                'left': all_frames[8:10],
                'right': all_frames[4:6],
                'up': all_frames[12:14]
            }
            self.walk_animations = {
                'down': all_frames[2:4],
                'left': all_frames[9:12],
                'right': all_frames[5:8],
                'up': all_frames[14:16]
            }
        else:
            frames_per_dir = len(all_frames) // 4
            half_frames = frames_per_dir // 2 if frames_per_dir > 1 else 1
            self.idle_animations = {
                'down': all_frames[0:half_frames],
                'left': all_frames[frames_per_dir:frames_per_dir + half_frames],
                'right': all_frames[frames_per_dir*2:frames_per_dir*2 + half_frames],
                'up': all_frames[frames_per_dir*3:frames_per_dir*3 + half_frames]
            }
            self.walk_animations = {
                'down': all_frames[half_frames:frames_per_dir],
                'left': all_frames[frames_per_dir + half_frames:frames_per_dir*2],
                'right': all_frames[frames_per_dir*2 + half_frames:frames_per_dir*3],
                'up': all_frames[frames_per_dir*3 + half_frames:frames_per_dir*4]
            }
        
        print(f"✅ Загружено анимаций:")
        for direction in self.idle_animations:
            print(f"   {direction} - idle: {len(self.idle_animations[direction])} кадров, walk: {len(self.walk_animations[direction])} кадров")
        
        self.direction = 'down'
        self.current_frame = 0
        self.animation_timer = 0
        self.is_moving = False
        self.speed = 4
        
        self.walk_animation_speed = 0.15
        self.idle_animation_speed = 0.08
    
    def _load_all_frames(self):
        """Вырезает все кадры из горизонтального спрайтлиста"""
        frames = []
        num_frames = self.sprite_sheet.get_width() // self.frame_width
        
        for i in range(num_frames):
            try:
                frame = self.sprite_sheet.subsurface(
                    pygame.Rect(i * self.frame_width, 0, self.frame_width, self.frame_height)
                )
                scaled_frame = pygame.transform.scale(frame, (self.scaled_width, self.scaled_height))
                frames.append(scaled_frame)
            except Exception as e:
                print(f"⚠️ Ошибка вырезания кадра {i}: {e}")
        
        return frames
    
    def update(self, keys, collision_callback):
        dx = 0
        dy = 0
        was_moving = self.is_moving
        self.is_moving = False
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -self.speed
            self.direction = 'left'
            self.is_moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = self.speed
            self.direction = 'right'
            self.is_moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -self.speed
            self.direction = 'up'
            self.is_moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = self.speed
            self.direction = 'down'
            self.is_moving = True
        
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
        
        if dx != 0:
            new_rect = self.rect.copy()
            new_rect.x += dx
            if not collision_callback(new_rect):
                self.rect.x += dx
        
        if dy != 0:
            new_rect = self.rect.copy()
            new_rect.y += dy
            if not collision_callback(new_rect):
                self.rect.y += dy
        
        # Сброс кадра при остановке
        if was_moving and not self.is_moving:
            self.current_frame = 0
            self.animation_timer = 0
        
        self._update_animation()
    
    def _update_animation(self):
        if self.is_moving:
            frames = self.walk_animations[self.direction]
            speed = self.walk_animation_speed
        else:
            frames = self.idle_animations[self.direction]
            speed = self.idle_animation_speed
        
        if not frames or len(frames) == 0:
            return
        
        self.animation_timer += speed
        if self.animation_timer >= 1:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % len(frames)
        
        # Убеждаемся, что current_frame не выходит за пределы
        if self.current_frame >= len(frames):
            self.current_frame = 0
    
    def get_current_frame(self):
        if self.is_moving:
            frames = self.walk_animations[self.direction]
        else:
            frames = self.idle_animations[self.direction]
        
        if not frames or len(frames) == 0:
            return None
        
        # Защита от выхода за пределы
        if self.current_frame >= len(frames):
            self.current_frame = 0
        
        return frames[self.current_frame]
    
    def get_animation_length(self):
        if self.is_moving:
            return len(self.walk_animations[self.direction])
        else:
            return len(self.idle_animations[self.direction])
    
    def draw(self, screen, camera_x, camera_y):
        frame = self.get_current_frame()
        if not frame:
            return
        
        screen_x = self.rect.x - camera_x - (self.scaled_width - self.rect.width) // 2
        screen_y = self.rect.y - camera_y - (self.scaled_height - self.rect.height) // 2
        screen.blit(frame, (screen_x, screen_y))
    
    def get_center(self):
        return self.rect.center


class Camera:
    def __init__(self, map_width, map_height, screen_width, screen_height):
        self.map_width = map_width
        self.map_height = map_height
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.x = 0
        self.y = 0
    
    def follow(self, target_rect):
        target_x = target_rect.centerx - self.screen_width // 2
        target_y = target_rect.centery - self.screen_height // 2
        self.x = target_x
        self.y = target_y
        self.x = max(0, min(self.x, self.map_width - self.screen_width))
        self.y = max(0, min(self.y, self.map_height - self.screen_height))


def main():
    pygame.init()
    
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Isometric Map - Animated Player (16 frames)")
    clock = pygame.time.Clock()
    
    # ПУТИ К ФАЙЛАМ (ИЗМЕНИТЕ ПОД СЕБЯ)
    tmx_file_path = "D:/project_game/assets/map/tmx/location1.tmx"
    player_sprite_path = "D:/project_game/assets/character/sprite/Billy.png"
    
    ZOOM = 1.5
    PLAYER_SCALE = 1.5
    
    try:
        map_renderer = TiledMapRenderer(tmx_file_path, zoom=ZOOM)
        print(f"✅ Карта загружена!")
    except Exception as e:
        print(f"❌ Ошибка загрузки карты: {e}")
        return
    
    start_x = map_renderer.width // 2
    start_y = map_renderer.height // 2
    
    try:
        player = AnimatedPlayer(start_x, start_y, player_sprite_path, scale=PLAYER_SCALE)
        print(f"✅ Персонаж загружен!")
    except Exception as e:
        print(f"❌ Ошибка загрузки персонажа: {e}")
        return
    
    camera = Camera(map_renderer.width, map_renderer.height, SCREEN_WIDTH, SCREEN_HEIGHT)
    show_debug = True
    font = pygame.font.Font(None, 24)
    small_font = pygame.font.Font(None, 18)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F1:
                    show_debug = not show_debug
                elif event.key == pygame.K_r:
                    player.rect.center = (map_renderer.width // 2, map_renderer.height // 2)
        
        keys = pygame.key.get_pressed()
        player.update(keys, map_renderer.check_collision)
        camera.follow(player.rect)
        
        screen.fill((30, 30, 40))
        map_renderer.draw(screen, int(camera.x), int(camera.y))
        
        if show_debug:
            map_renderer.draw_collisions_debug(screen, int(camera.x), int(camera.y))
        
        player.draw(screen, int(camera.x), int(camera.y))
        
        # ИСПРАВЛЕННАЯ СТРОКА - убрано обращение к animations
        info_texts = [
            f"Позиция: ({player.rect.x}, {player.rect.y})",
            f"Направление: {player.direction}",
            f"Кадр: {player.current_frame + 1}/{player.get_animation_length()}",
            f"Движется: {player.is_moving}",
            f"Коллизий: {len(map_renderer.collision_rects)}",
            "",
            "WASD/Стрелки - движение",
            "F1 - Показать/скрыть коллизии",
            "R - Сброс позиции",
            "ESC - Выход"
        ]
        
        y_offset = 10
        for text in info_texts:
            if text:
                text_surface = small_font.render(text, True, (255, 255, 255))
                screen.blit(text_surface, (10, y_offset))
                y_offset += 22
        
        fps = int(clock.get_fps())
        fps_text = font.render(f"FPS: {fps}", True, (255, 255, 0))
        screen.blit(fps_text, (SCREEN_WIDTH - 100, 10))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()


if __name__ == "__main__":
    main()