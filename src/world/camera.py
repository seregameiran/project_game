"""
Модуль world/camera.py
Камера для 2D игры.

Отвечает за позиционирование камеры на карте и её следование за игроком.
"""


class Camera:
    """
    Класс камеры, который определяет, какая часть карты видна на экране.
    
    Камера всегда следует за игроком, оставаясь в центре экрана,
    но не выходит за границы карты.
    """
    
    def __init__(self, map_width, map_height, screen_width, screen_height):
        """
        Инициализация камеры.
        
        Аргументы:
            map_width: общая ширина карты в пикселях
            map_height: общая высота карты в пикселях
            screen_width: ширина игрового окна в пикселях
            screen_height: высота игрового окна в пикселях
        """
        self.map_width = map_width          # ширина всей карты
        self.map_height = map_height        # высота всей карты
        self.screen_width = screen_width    # ширина экрана
        self.screen_height = screen_height  # высота экрана
        self.x = 0                          # X координата левого верхнего угла камеры
        self.y = 0                          # Y координата левого верхнего угла камеры
    
    def follow(self, target_rect):
        """
        Устанавливает камеру так, чтобы она следовала за целью (обычно игроком).
        
        Цель (игрок) всегда находится в центре экрана, если это возможно.
        Камера не выходит за границы карты.
        
        Аргументы:
            target_rect: прямоугольник (pygame.Rect) цели, за которой следит камера
                         (обычно player.rect)
        """
        # Вычисляем позицию камеры так, чтобы цель была в центре экрана
        target_x = target_rect.centerx - self.screen_width // 2
        target_y = target_rect.centery - self.screen_height // 2
        
        # Устанавливаем новую позицию камеры
        self.x = target_x
        self.y = target_y
        
        # Ограничиваем камеру границами карты (не даём уйти за край)
        self.x = max(0, min(self.x, self.map_width - self.screen_width))
        self.y = max(0, min(self.y, self.map_height - self.screen_height))