"""
Модуль core/game.py
Отвечает за главный игровой цикл и управление состояниями игры.
"""

import pygame
import sys
import os
from src.states.exploring_dialogue import ExploringDialogueState

#Корневая папка проекта в путь поиска
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

#Импортируем от корня проекта
from src.game_state import GameState


class Game:
    """
    Главный класс игры.
    Управляет состояниями (меню, карта, бой) и главным циклом.
    """
    
    def __init__(self, screen):
        """
        Инициализация игры.
        
        Аргументы:
            screen: поверхность Pygame для отрисовки
        """
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MAIN_MENU
        
        from src.states.main_menu import MainMenuState
        from src.states.exploring import ExploringState
        
        self.states = {
            GameState.MAIN_MENU: MainMenuState(self),
            GameState.EXPLORING: ExploringState(self),
            GameState.DIALOGUE: ExploringDialogueState(self),
        }
        
        self.current_state = self.states[self.state]
    
    def change_state(self, new_state):
        if new_state in self.states:
            self.state = new_state
            self.current_state = self.states[new_state]
            print(f"Переход: {new_state}")
    
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
            
            self.current_state.handle_events(events)
            self.current_state.update(dt)
            self.current_state.draw(self.screen)
            
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()