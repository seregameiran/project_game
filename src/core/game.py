"""
Модуль core/game.py
Главный класс игры.

Использует паттерн виртуального экрана:
    - Вся игра рисуется на virtual_screen (800x608)
    - virtual_screen масштабируется на реальный экран через pygame.transform.scale
    - Логика, коллизии, камера — всё работает в координатах 800x608
    - Зум карты фиксирован (1.5) и не зависит от разрешения монитора
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.states.exploring_dialogue import ExploringDialogueState


class Game:
    """
    Главный класс игры.

    Хранит виртуальный экран (800x608) и реальный экран монитора.
    Каждый кадр:
        1. Рисует текущее состояние на virtual_screen
        2. Масштабирует virtual_screen на реальный экран
        3. Показывает результат через pygame.display.flip()

    Благодаря этому вся игровая логика работает в фиксированных
    координатах 800x608 независимо от разрешения монитора.
    """

    def __init__(self, screen, virtual_screen, screen_width, screen_height):
        """
        Инициализация игры.

        Аргументы:
            screen:         реальная поверхность экрана монитора
            virtual_screen: виртуальная поверхность 800x608 для отрисовки игры
            screen_width:   реальная ширина экрана в пикселях
            screen_height:  реальная высота экрана в пикселях
        """
        self.screen         = screen
        self.virtual_screen = virtual_screen
        self.screen_width   = screen_width
        self.screen_height  = screen_height
        self.clock          = pygame.time.Clock()
        self.running        = True
        self.state          = GameState.MAIN_MENU

        # Вычисляем масштаб и отступы для центрирования виртуального экрана
        # на реальном с сохранением пропорций
        self._update_scale()

        from src.states.main_menu import MainMenuState
        from src.states.exploring import ExploringState

        self.states = {
            GameState.MAIN_MENU: MainMenuState(self),
            GameState.EXPLORING: ExploringState(self),
            GameState.DIALOGUE:  ExploringDialogueState(self),
        }

        self.current_state = self.states[self.state]

    def _update_scale(self):
        """
        Вычисляет масштаб и отступы для отображения виртуального экрана
        на реальном с сохранением пропорций (letterbox/pillarbox).

        Результат:
            self.scale:    коэффициент масштабирования
            self.offset_x: отступ слева (для центрирования по горизонтали)
            self.offset_y: отступ сверху (для центрирования по вертикали)
            self.scaled_w: ширина масштабированного изображения
            self.scaled_h: высота масштабированного изображения
        """
        virtual_w = self.virtual_screen.get_width()
        virtual_h = self.virtual_screen.get_height()

        # Берём минимальный масштаб чтобы изображение влезло целиком
        scale_x = self.screen_width  / virtual_w
        scale_y = self.screen_height / virtual_h
        self.scale = min(scale_x, scale_y)

        # Размер масштабированного изображения
        self.scaled_w = int(virtual_w * self.scale)
        self.scaled_h = int(virtual_h * self.scale)

        # Отступы для центрирования (чёрные полосы по краям если нужно)
        self.offset_x = (self.screen_width  - self.scaled_w) // 2
        self.offset_y = (self.screen_height - self.scaled_h) // 2

    def change_state(self, new_state):
        """
        Переключает игру в новое состояние.

        Аргументы:
            new_state: новое состояние из перечисления GameState
        """
        if new_state in self.states:
            self.state         = new_state
            self.current_state = self.states[new_state]
            print(f"Переход в состояние: {new_state}")
        else:
            print(f"Предупреждение: состояние {new_state} не найдено")

    def run(self):
        """
        Запускает главный игровой цикл.

        Каждый кадр:
            1. Считает delta time
            2. Обрабатывает глобальные события (выход)
            3. Передаёт события текущему состоянию
            4. Обновляет логику текущего состояния
            5. Рисует состояние на virtual_screen
            6. Масштабирует virtual_screen на реальный экран
            7. Показывает кадр
        """
        while self.running:
            dt = self.clock.tick(60) / 1000.0

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            self.current_state.handle_events(events)
            self.current_state.update(dt)

            # Рисуем игру на виртуальный экран
            self.current_state.draw(self.virtual_screen)

            # Масштабируем виртуальный экран на реальный
            self.screen.fill((0, 0, 0))  # чёрные полосы по краям
            scaled = pygame.transform.scale(
                self.virtual_screen,
                (self.scaled_w, self.scaled_h)
            )
            self.screen.blit(scaled, (self.offset_x, self.offset_y))

            pygame.display.flip()

        pygame.quit()
        sys.exit()