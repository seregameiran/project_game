"""
Модуль core/game.py
Главный класс игры.
"""

import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game_state import GameState
from src.states.exploring_dialogue import ExploringDialogueState
from src.states.transition_location import TransitionLocationState
from src.core.audio_manager import AudioManager, MusicTrack, SoundType
from src.states.battle import BattleState


class Game:
    """
    Главный класс игры.
    """

    # Константы для управления состояниями
    STATE_MUSIC_MAP = {
        GameState.MAIN_MENU: MusicTrack.MAIN_MENU,
        GameState.EXPLORING: MusicTrack.EXPLORING,
        GameState.BATTLE: MusicTrack.BATTLE,
        GameState.CREDITS: MusicTrack.CREDITS,
    }

    def __init__(self, screen, virtual_screen, screen_width, screen_height):
        """
        Инициализация игры.
        """
        self.screen = screen
        self.virtual_screen = virtual_screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MAIN_MENU
        self.show_fps = False
        # Локации, в которых босс уже побеждён
        self.defeated_boss_locations = set()

        # Вычисляем масштаб
        self._update_scale()

        # Инициализация состояний игры
        from src.states.main_menu import MainMenuState
        from src.states.exploring import ExploringState
        from src.states.pause_menu import PauseMenuState

        self.states = {
            GameState.MAIN_MENU: MainMenuState(self),
            GameState.EXPLORING: ExploringState(self),
            GameState.DIALOGUE: ExploringDialogueState(self),
            GameState.PAUSE: PauseMenuState(self),
            GameState.TRANSITION_LOCATION: TransitionLocationState(self),
            GameState.BATTLE: BattleState(self),
        }

        self.current_state = self.states[self.state]

        # Инициализация аудио
        self.audio = AudioManager(enabled=True, music_volume=0.5, sfx_volume=0.7)
        self.audio.play_music(MusicTrack.MAIN_MENU)

    def _update_scale(self):
        """Вычисляет масштаб для отображения виртуального экрана."""
        virtual_w = self.virtual_screen.get_width()
        virtual_h = self.virtual_screen.get_height()

        scale_x = self.screen_width / virtual_w
        scale_y = self.screen_height / virtual_h
        self.scale = min(scale_x, scale_y)

        self.scaled_w = int(virtual_w * self.scale)
        self.scaled_h = int(virtual_h * self.scale)

        self.offset_x = (self.screen_width - self.scaled_w) // 2
        self.offset_y = (self.screen_height - self.scaled_h) // 2

    def _get_music_for_state(self, state):
        """Возвращает музыкальный трек для состояния."""
        return self.STATE_MUSIC_MAP.get(state)

    def change_state(self, new_state):
        """Переключает игру в новое состояние."""
        if new_state not in self.states:
            print(f"Ошибка: состояние {new_state} не найдено")
            return False

        music_track = self._get_music_for_state(new_state)
        if music_track:
            self.audio.play_music(music_track)
        
        old_state = self.state
        self.state = new_state
        self.current_state = self.states[new_state]

        print(f"Переход из {old_state} в {new_state}")
        return True

    def handle_global_events(self, events):
        """Обрабатывает глобальные события."""
        for event in events:
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                # Ctrl+D - отладка
                if event.key == pygame.K_d and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    print(f"\n--- ОТЛАДКА ---")
                    print(f"Состояние: {self.state}")
                    print(f"FPS: {self.clock.get_fps():.2f}")
                    print(f"Доступные состояния: {list(self.states.keys())}")
                    print(f"---------------\n")
                
                # Ctrl+F - показать FPS
                elif event.key == pygame.K_f and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.show_fps = not self.show_fps
                    print(f"FPS отображение: {'Вкл' if self.show_fps else 'Выкл'}")
                
                # Ctrl+M - отключить звук
                elif event.key == pygame.K_m and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.audio.toggle_mute()
                    print(f"Звук: {'Выкл' if not self.audio.enabled else 'Вкл'}")
        
        return True

    def run(self):
        """Запускает главный игровой цикл."""
        frame_count = 0
        fps_timer = 0.0
        
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.033)
            
            events = pygame.event.get()
            
            if not self.handle_global_events(events):
                self.running = False
                break
            
            if self.current_state:
                self.current_state.handle_events(events)
            
            if self.current_state:
                self.current_state.update(dt)
            
            self.virtual_screen.fill((0, 0, 0))
            
            if self.current_state:
                self.current_state.draw(self.virtual_screen)
            
            self.screen.fill((0, 0, 0))
            scaled = pygame.transform.scale(
                self.virtual_screen,
                (self.scaled_w, self.scaled_h)
            )
            self.screen.blit(scaled, (self.offset_x, self.offset_y))
            
            pygame.display.flip()
            
            frame_count += 1
            fps_timer += dt
            if fps_timer >= 1.0 and self.show_fps:
                pygame.display.set_caption(f"Billy's Adventure - FPS: {frame_count}")
                frame_count = 0
                fps_timer = 0.0
        
        pygame.quit()
        sys.exit()

    # Добавьте этот метод в класс Game (в файл src/core/game.py)

    def reset_game(self):
        """
        Полный сброс состояния игры для начала новой игры.
        """
        print("Сброс игры...")
        self.defeated_boss_locations.clear()

        # Сбрасываем состояние исследования (перезагружаем первую локацию)
        exploring_state = self.states.get(GameState.EXPLORING)
        if exploring_state:
            exploring_state.load_location(1)

        # Сбрасываем состояние диалога
        dialogue_state = self.states.get(GameState.DIALOGUE)
        if dialogue_state:
            dialogue_state.lines = []
            dialogue_state.current_index = 0
            dialogue_state.displayed_chars = 0
            dialogue_state.text_done = False

        # Сбрасываем состояние перехода
        transition_state = self.states.get(GameState.TRANSITION_LOCATION)
        if transition_state:
            transition_state.transition_data = None
            transition_state.selected = 1
            transition_state.appear_progress = 0.0

        print("Игра сброшена до начального состояния")

    def mark_boss_defeated(self, location_id: int):
        """Помечает босса локации как побеждённого."""
        self.defeated_boss_locations.add(int(location_id))

    def is_boss_defeated(self, location_id: int) -> bool:
        """Проверяет, побеждён ли босс в указанной локации."""
        return int(location_id) in self.defeated_boss_locations