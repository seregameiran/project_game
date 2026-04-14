"""
Модуль core/audio_manager.py
Менеджер звуков и музыки для игры.

Отвечает за:
    - Воспроизведение фоновой музыки для разных состояний
    - Воспроизведение звуковых эффектов (UI, взаимодействие)
    - Управление громкостью
    - Плавные переходы между треками
"""

import pygame
import os
from enum import Enum


class SoundType(Enum):
    """Типы звуковых эффектов."""
    UI_HOVER = "ui_hover"  # Наведение на пункт меню
    UI_SELECT = "ui_select"  # Выбор пункта меню
    UI_BACK = "ui_back"  # Возврат/отмена
    INTERACT = "interact"  # Взаимодействие с NPC/объектом
    TRANSITION = "transition"  # Переход между локациями
    DAMAGE = "damage"  # Получение урона
    HEAL = "heal"  # Лечение
    ATTACK = "attack"  # Атака игрока
    BOSS_HIT = "boss_hit"  # Удар по боссу
    VICTORY = "victory"  # Победа над боссом
    DEFEAT = "defeat"  # Поражение
    DIALOG = "dialog" #диалог


class MusicTrack(Enum):
    """Типы музыкальных треков."""
    MAIN_MENU = "main_menu"
    EXPLORING = "exploring"
    BATTLE = "battle"
    BOSS_BATTLE = "boss_battle"
    VICTORY = "victory"
    CREDITS = "credits"


class AudioManager:
    """
    Менеджер звуков и музыки.

    Особенности:
        - Фоновая музыка зацикливается с плавным затуханием при смене трека
        - Звуковые эффекты могут накладываться друг на друга
        - Поддержка регулировки громкости
        - Кэширование звуков для быстрого доступа
    """

    def __init__(self, enabled=True, music_volume=0.5, sfx_volume=0.7):
        """
        Инициализация аудио менеджера.

        Аргументы:
            enabled: включен ли звук
            music_volume: громкость музыки (0.0 - 1.0)
            sfx_volume: громкость звуковых эффектов (0.0 - 1.0)
        """
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.enabled = enabled
        self.music_volume = max(0.0, min(1.0, music_volume))
        self.sfx_volume = max(0.0, min(1.0, sfx_volume))

        # Кэш звуковых эффектов
        self.sounds = {}

        # Текущий играющий трек
        self.current_music = None

        # Путь к корневой папке проекта (где находится папка src)
        self.project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        # Путь к папке assets
        self.assets_dir = os.path.join(self.project_root, "assets")

        print(f"Путь к проекту: {self.project_root}")
        print(f"Путь к assets: {self.assets_dir}")

        # Загружаем звуки
        self._load_sounds()

    def _load_sounds(self):
        """Загружает все звуковые эффекты в кэш."""
        # Путь к папке со звуками эффектов
        sounds_dir = os.path.join(self.assets_dir, "sounds")

        # Создаём папку если её нет
        os.makedirs(sounds_dir, exist_ok=True)

        print(f"Загрузка звуков из: {sounds_dir}")

        # Определяем пути к звуковым файлам
        sound_files = {
            SoundType.UI_HOVER: "ui_hover.mp3",
            SoundType.UI_SELECT: "ui_select.mp3",
            SoundType.UI_BACK: "ui_back.mp3",
            SoundType.INTERACT: "interact.mp3",
            SoundType.TRANSITION: "transition.mp3",
            SoundType.DAMAGE: "damage.wav",
            SoundType.HEAL: "heal.wav",
            SoundType.ATTACK: "attack.wav",
            SoundType.BOSS_HIT: "boss_hit.wav",
            SoundType.VICTORY: "victory.wav",
            SoundType.DEFEAT: "defeat.wav",
            SoundType.DIALOG: "dialog.mp3",
        }

        # Загружаем звуки
        for sound_type, filename in sound_files.items():
            filepath = os.path.join(sounds_dir, filename)
            if os.path.exists(filepath):
                try:
                    sound = pygame.mixer.Sound(filepath)
                    sound.set_volume(self.sfx_volume)
                    self.sounds[sound_type] = sound
                    print(f"Загружен звук: {filename}")
                except Exception as e:
                    print(f"Ошибка загрузки звука {filename}: {e}")
            else:
                print(f"Предупреждение: звуковой файл не найден - {filepath}")

    def _get_music_path(self, track):
        """
        Возвращает путь к музыкальному файлу.

        Поддерживает разные папки для разных типов музыки:
            - menu/sounds/forest.mp3 для главного меню
            - music/ для остальных треков
        """


        # Для остальных треков используем папку music
        music_dir = os.path.join(self.assets_dir, "music")
        os.makedirs(music_dir, exist_ok=True)

        music_files = {
            MusicTrack.EXPLORING: "exploring.mp3",
            MusicTrack.BATTLE: "battle.ogg",
            MusicTrack.BOSS_BATTLE: "boss_battle.ogg",
            MusicTrack.VICTORY: "victory.ogg",
            MusicTrack.CREDITS: "credits.ogg",
            MusicTrack.MAIN_MENU: "main_menu.mp3",
        }

        filename = music_files.get(track)
        if filename:
            return os.path.join(music_dir, filename)
        return None

    def play_sound(self, sound_type):
        """
        Воспроизводит звуковой эффект.

        Аргументы:
            sound_type: тип звука из перечисления SoundType
        """
        if not self.enabled:
            return

        sound = self.sounds.get(sound_type)
        if sound:
            try:
                sound.play()
            except Exception as e:
                print(f"Ошибка воспроизведения звука {sound_type}: {e}")

    def play_music(self, track, fade_in_ms=1000, loop=True):
        """
        Воспроизводит фоновую музыку с плавным затуханием.

        Аргументы:
            track: музыкальный трек из перечисления MusicTrack
            fade_in_ms: время плавного появления в миллисекундах
            loop: зацикливать ли трек
        """
        if not self.enabled:
            return

        # Если эта же музыка уже играет, ничего не делаем
        if self.current_music == track:
            return

        music_path = self._get_music_path(track)
        if not music_path or not os.path.exists(music_path):
            print(f"Предупреждение: музыкальный файл не найден - {music_path}")
            return

        try:
            # Плавно затухаем текущую музыку
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(500)

            # Загружаем и запускаем новую
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade_in_ms)

            self.current_music = track
            print(f"Запущена музыка: {track.value} - {music_path}")

        except Exception as e:
            print(f"Ошибка воспроизведения музыки {track.value}: {e}")

    def stop_music(self, fade_out_ms=500):
        """
        Останавливает фоновую музыку с затуханием.

        Аргументы:
            fade_out_ms: время затухания в миллисекундах
        """
        if not self.enabled:
            return

        try:
            pygame.mixer.music.fadeout(fade_out_ms)
            self.current_music = None
        except Exception as e:
            print(f"Ошибка остановки музыки: {e}")

    def stop_sound(self, sound_type):
        """
        Останавливает воспроизведение звукового эффекта.

        Аргументы:
            sound_type: тип звука из перечисления SoundType
        """
        if not self.enabled:
            return

        sound = self.sounds.get(sound_type)
        if sound:
            try:
                sound.stop()
            except Exception as e:
                print(f"Ошибка остановки звука {sound_type}: {e}")

    def set_music_volume(self, volume):
        """
        Устанавливает громкость музыки.

        Аргументы:
            volume: громкость от 0.0 до 1.0
        """
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume):
        """
        Устанавливает громкость звуковых эффектов.

        Аргументы:
            volume: громкость от 0.0 до 1.0
        """
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)

    def toggle_mute(self):
        """Включает/выключает звук."""
        self.enabled = not self.enabled
        if not self.enabled:
            pygame.mixer.music.set_volume(0)
        else:
            pygame.mixer.music.set_volume(self.music_volume)

    def update(self, dt):
        """
        Обновление аудио менеджера (вызывается каждый кадр).
        """
        pass  # Пока ничего не нужно, оставлено для будущего расширения