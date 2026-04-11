"""
Модуль world/map_renderer.py
Рендерер карты из TMX файла.
"""

import pygame
import pytmx
from pytmx.util_pygame import load_pygame


class TiledMapRenderer:

    def __init__(self, filename, zoom=1.0):
        self.zoom = zoom
        self.tmx_data = load_pygame(filename)
        self.orientation = getattr(self.tmx_data, 'orientation', 'orthogonal')

        self.orig_tilewidth = self.tmx_data.tilewidth
        self.orig_tileheight = self.tmx_data.tileheight
        self.tilewidth = int(self.orig_tilewidth * zoom)
        self.tileheight = int(self.orig_tileheight * zoom)

        self.width = self.tmx_data.width * self.tilewidth
        self.height = self.tmx_data.height * self.tileheight

        self.map_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        self.collision_rects = []
        self.transitions = []
        self.npcs = []

        self._render_map()
        self._load_collisions()
        self._load_transitions()
        self._load_npcs()

        print(f"Карта: {self.width}x{self.height} | "
              f"коллизий: {len(self.collision_rects)} | "
              f"переходов: {len(self.transitions)} | "
              f"NPC: {len(self.npcs)}")

    # ------------------------------------------------------------------ #
    #  РЕНДЕР                                                              #
    # ------------------------------------------------------------------ #

    def _render_map(self):
        if self.tmx_data.background_color:
            self.map_surface.fill(pygame.Color(self.tmx_data.background_color))
        else:
            self.map_surface.fill((0, 0, 0, 0))

        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                self._render_tile_layer(layer)
            elif isinstance(layer, pytmx.TiledObjectGroup):
                self._render_object_layer(layer)

    def _render_tile_layer(self, layer):
        for x, y, image in layer.tiles():
            if image:
                if self.zoom != 1.0:
                    image = pygame.transform.scale(image, (self.tilewidth, self.tileheight))
                self.map_surface.blit(image, (x * self.tilewidth, y * self.tileheight))

    def _render_object_layer(self, layer):
        if layer.name in ("Transition",):
            return

        for obj in layer:
            if obj.image:
                img = obj.image
                if obj.width and obj.height:
                    img = pygame.transform.scale(
                        img,
                        (int(obj.width * self.zoom), int(obj.height * self.zoom))
                    )
                self.map_surface.blit(
                    img,
                    (int(obj.x * self.zoom), int(obj.y * self.zoom))
                )

    # ------------------------------------------------------------------ #
    #  КОЛЛИЗИИ                                                            #
    # ------------------------------------------------------------------ #

    def _load_collisions(self):
        self.collision_rects = []

        # Шаг 1: словарь gid -> список фигур (local_x, local_y, w, h)
        collider_map = {}

        for gid, colliders in self.tmx_data.get_tile_colliders():
            shapes = []
            for obj in colliders:
                if hasattr(obj, 'points') and obj.points:
                    xs = [p[0] + obj.x for p in obj.points]
                    ys = [p[1] + obj.y for p in obj.points]
                    shapes.append((
                        min(xs), min(ys),
                        max(xs) - min(xs),
                        max(ys) - min(ys)
                    ))
                else:
                    shapes.append((obj.x, obj.y, obj.width, obj.height))
            collider_map[gid] = shapes

        # Шаг 2: тайловые слои
        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for tx, ty, gid in layer:
                if not gid or gid not in collider_map:
                    continue
                world_x = tx * self.orig_tilewidth
                world_y = ty * self.orig_tileheight
                for (lx, ly, lw, lh) in collider_map[gid]:
                    self.collision_rects.append(pygame.Rect(
                        int((world_x + lx) * self.zoom),
                        int((world_y + ly) * self.zoom),
                        int(lw * self.zoom),
                        int(lh * self.zoom)
                    ))

        # Шаг 3: объектные слои
        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            for obj in layer:
                if not obj.gid or obj.gid not in collider_map:
                    continue

                tileset = self.tmx_data.get_tileset_from_gid(obj.gid)
                orig_w = tileset.tilewidth
                orig_h = tileset.tileheight

                scale_x = (obj.width / orig_w) if obj.width else 1.0
                scale_y = (obj.height / orig_h) if obj.height else 1.0

                # pytmx уже нормализует y — используем как есть
                world_x = obj.x
                world_y = obj.y

                for (lx, ly, lw, lh) in collider_map[obj.gid]:
                    self.collision_rects.append(pygame.Rect(
                        int((world_x + lx * scale_x) * self.zoom),
                        int((world_y + ly * scale_y) * self.zoom),
                        int(lw * scale_x * self.zoom),
                        int(lh * scale_y * self.zoom)
                    ))

    # ------------------------------------------------------------------ #
    #  ПЕРЕХОДЫ МЕЖДУ ЛОКАЦИЯМИ                                           #
    # ------------------------------------------------------------------ #

    def _load_transitions(self):
        self.transitions = []
        try:
            layer = self.tmx_data.get_layer_by_name("Transition")
        except ValueError:
            return

        for obj in layer:
            props = obj.properties
            if "transition" not in props:
                continue
            self.transitions.append({
                "rect": pygame.Rect(
                    int(obj.x * self.zoom),
                    int(obj.y * self.zoom),
                    int(obj.width * self.zoom),
                    int(obj.height * self.zoom)
                ),
                "tmx_path": props["transition"],
                "spawn_x": float(props.get("spawnX", 0)),
                "spawn_y": float(props.get("spawnY", 0)),
            })

    # ------------------------------------------------------------------ #
    #  NPC                                                                 #
    # ------------------------------------------------------------------ #

    def _load_npcs(self):
        self.npcs = []
        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            for obj in layer:
                if not obj.name or not obj.name.startswith("npc"):
                    continue
                self.npcs.append({
                    "rect": pygame.Rect(
                        int(obj.x * self.zoom),
                        int(obj.y * self.zoom),
                        int(obj.width * self.zoom),
                        int(obj.height * self.zoom)
                    ),
                    "name": obj.name,
                    "dialog_file": obj.properties.get("dialogFile", None),
                })

    # ------------------------------------------------------------------ #
    #  ОТРИСОВКА И УТИЛИТЫ                                                #
    # ------------------------------------------------------------------ #

    def draw(self, screen, camera_x=0, camera_y=0):
        screen.blit(self.map_surface, (-camera_x, -camera_y))

    def draw_collisions_debug(self, screen, camera_x=0, camera_y=0):
        """Красный — коллизии, голубой — переходы, зелёный — NPC."""
        for rect in self.collision_rects:
            pygame.draw.rect(screen, (255, 0, 0),
                (rect.x - camera_x, rect.y - camera_y, rect.width, rect.height), 2)
        for t in self.transitions:
            r = t["rect"]
            pygame.draw.rect(screen, (0, 255, 255),
                (r.x - camera_x, r.y - camera_y, r.width, r.height), 2)
        for npc in self.npcs:
            r = npc["rect"]
            pygame.draw.rect(screen, (0, 255, 0),
                (r.x - camera_x, r.y - camera_y, r.width, r.height), 2)

    def check_collision(self, rect):
        return any(rect.colliderect(r) for r in self.collision_rects)

    def check_transition(self, rect):
        """Возвращает данные перехода если игрок вошёл в зону, иначе None."""
        for t in self.transitions:
            if rect.colliderect(t["rect"]):
                return t
        return None

    def check_npc_interaction(self, rect, radius=48):
        """Возвращает ближайшего NPC в радиусе от rect, иначе None."""
        for npc in self.npcs:
            if rect.inflate(radius * 2, radius * 2).colliderect(npc["rect"]):
                return npc
        return None