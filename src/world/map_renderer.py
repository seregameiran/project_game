"""
Модуль world/map_renderer.py
Рендерер карты из TMX файла.
"""
import os

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
        self.collision_polygons = []
        self.transitions = []
        self.npcs = []

        self._render_map()
        self._load_collisions()
        self._load_transitions()
        self._load_npcs()

        # Список анимированных тайлов для обновления каждый кадр
        self.animated_tiles = []
        self.anim_timer = 0.0

        self._find_animated_tiles()

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
                # В TMX тайлы могут быть больше базового tilewidth/tileheight (например ковёр 64x64 при сетке 32x32).
                # Поэтому масштабируем по фактическому размеру изображения и выравниваем по "низу" тайла,
                # иначе появляются артефакты (в т.ч. чёрные пиксели на прозрачности) и съезжает позиция.
                if self.zoom != 1.0:
                    sw = max(1, int(image.get_width() * self.zoom))
                    sh = max(1, int(image.get_height() * self.zoom))
                    image = pygame.transform.scale(image, (sw, sh))

                dest_x = x * self.tilewidth
                dest_y = y * self.tileheight + (self.tileheight - image.get_height())
                self.map_surface.blit(image, (dest_x, dest_y))

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

    @staticmethod
    def _clip_collider_to_tile_local(lx, ly, lw, lh, tw, th):
        """
        Обрезает ось-ориентированный бокс коллизии границами тайла (0..tw, 0..th).

        В Tiled полигоны иногда выходят за край тайла; AABB тогда тоже «висит» ниже
        или правее картинки, и после масштаба на объекте коллизия визуально съезжает
        (типично для ямы Hole на локации 3).
        """
        ix1 = max(0.0, lx)
        iy1 = max(0.0, ly)
        ix2 = min(float(tw), lx + lw)
        iy2 = min(float(th), ly + lh)
        w = ix2 - ix1
        h = iy2 - iy1
        if w <= 0 or h <= 0:
            return None
        return (ix1, iy1, w, h)

    def _flags_for_internal_gid(self, internal_gid):
        """Флаги отражения/поворота тайла для внутреннего gid (pytmx)."""
        if not internal_gid:
            return None
        for _tiled_gid, variants in self.tmx_data.gidmap.items():
            for igid, flags in variants:
                if igid == internal_gid:
                    return flags
        return None

    @staticmethod
    def _transform_local_aabb_for_tile_flags(lx, ly, lw, lh, tw, th, flags):
        """
        Зеркалирует локальный AABB коллизии так же, как текстура тайла в Tiled.
        Без этого отражённый по горизонтали тайл-объект (например пальма) получает
        коллизию с неотражённого тайла — она визуально «съезжает».
        """
        if flags is None:
            return lx, ly, lw, lh
        if getattr(flags, "flipped_horizontally", False):
            lx = tw - lx - lw
        if getattr(flags, "flipped_vertically", False):
            ly = th - ly - lh
        # flipped_diagonally: сложный случай (поворот + отражение); на картах
        # проекта не используется для коллизий пальмы — при необходимости
        # расширить отдельно.
        return lx, ly, lw, lh

    def _load_collisions(self):
        self.collision_rects = []
        self.collision_polygons = []

        # Шаг 1: словарь gid -> список фигур
        # - rect: (local_x, local_y, w, h)
        # - poly: [(x1,y1), (x2,y2), ...] в локальных координатах тайла
        collider_map = {}

        for gid, colliders in self.tmx_data.get_tile_colliders():
            tileset = self.tmx_data.get_tileset_from_gid(gid)
            tw, th = tileset.tilewidth, tileset.tileheight
            shapes = []
            for obj in colliders:
                if hasattr(obj, 'points') and obj.points:
                    # Важно: используем полигон как есть (контур из TMX),
                    # а не AABB, иначе ямы/фигуры превращаются в "квадраты".
                    pts = []
                    for p in obj.points:
                        pts.append((float(getattr(p, "x", p[0])), float(getattr(p, "y", p[1]))))
                    shapes.append({"type": "poly", "points": pts, "tw": tw, "th": th})
                else:
                    lx, ly, lw, lh = obj.x, obj.y, obj.width, obj.height
                    clipped = self._clip_collider_to_tile_local(lx, ly, lw, lh, tw, th)
                    if clipped is not None:
                        shapes.append({"type": "rect", "rect": clipped})
            if shapes:
                collider_map[gid] = shapes

        # Шаг 2: тайловые слои
        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for tx, ty, gid in layer:
                if not gid or gid not in collider_map:
                    continue
                tileset = self.tmx_data.get_tileset_from_gid(gid)
                tw, th = tileset.tilewidth, tileset.tileheight
                flags = self._flags_for_internal_gid(gid)
                world_x = tx * self.orig_tilewidth
                world_y = ty * self.orig_tileheight
                for shape in collider_map[gid]:
                    if shape["type"] == "rect":
                        lx, ly, lw, lh = shape["rect"]
                        lx, ly, lw, lh = self._transform_local_aabb_for_tile_flags(
                            lx, ly, lw, lh, tw, th, flags)
                        self.collision_rects.append(pygame.Rect(
                            int((world_x + lx) * self.zoom),
                            int((world_y + ly) * self.zoom),
                            int(lw * self.zoom),
                            int(lh * self.zoom)
                        ))
                    else:
                        pts = shape["points"]
                        pts = self._transform_local_poly_for_tile_flags(pts, tw, th, flags)
                        self.collision_polygons.append([
                            (float(world_x + x) * self.zoom, float(world_y + y) * self.zoom)
                            for (x, y) in pts
                        ])

        # Шаг 3: объектные слои — только тайл-объекты, у которых в тайлсете заданы фигуры
        # коллизии (collider_map). Остальные объекты коллизий не получают.
        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            for obj in layer:
                if not obj.gid or obj.gid not in collider_map:
                    continue

                tileset = self.tmx_data.get_tileset_from_gid(obj.gid)
                orig_w = tileset.tilewidth
                orig_h = tileset.tileheight
                flags = self._flags_for_internal_gid(obj.gid)

                scale_x = (obj.width / orig_w) if obj.width else 1.0
                scale_y = (obj.height / orig_h) if obj.height else 1.0

                # pytmx уже нормализует y — используем как есть
                world_x = obj.x
                world_y = obj.y

                for shape in collider_map[obj.gid]:
                    if shape["type"] == "rect":
                        lx, ly, lw, lh = shape["rect"]
                        lx, ly, lw, lh = self._transform_local_aabb_for_tile_flags(
                            lx, ly, lw, lh, orig_w, orig_h, flags)
                        self.collision_rects.append(pygame.Rect(
                            int((world_x + lx * scale_x) * self.zoom),
                            int((world_y + ly * scale_y) * self.zoom),
                            int(lw * scale_x * self.zoom),
                            int(lh * scale_y * self.zoom)
                        ))
                    else:
                        pts = shape["points"]
                        pts = self._transform_local_poly_for_tile_flags(pts, orig_w, orig_h, flags)
                        self.collision_polygons.append([
                            (float(world_x + x * scale_x) * self.zoom, float(world_y + y * scale_y) * self.zoom)
                            for (x, y) in pts
                        ])

    @staticmethod
    def _transform_local_poly_for_tile_flags(points, tw, th, flags):
        """Зеркалит локальные точки полигона так же, как текстура тайла в Tiled."""
        if flags is None:
            return points
        out = []
        for (x, y) in points:
            if getattr(flags, "flipped_horizontally", False):
                x = tw - x
            if getattr(flags, "flipped_vertically", False):
                y = th - y
            out.append((x, y))
        return out

    @staticmethod
    def _point_in_poly(px, py, poly):
        """Ray casting: True если точка внутри полигона."""
        inside = False
        n = len(poly)
        if n < 3:
            return False
        x1, y1 = poly[0]
        for i in range(1, n + 1):
            x2, y2 = poly[i % n]
            if ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / ((y2 - y1) or 1e-9) + x1):
                inside = not inside
            x1, y1 = x2, y2
        return inside

    @staticmethod
    def _segments_intersect(a, b, c, d):
        """Пересечение отрезков AB и CD."""
        def orient(p, q, r):
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

        def on_seg(p, q, r):
            return (min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and
                    min(p[1], r[1]) <= q[1] <= max(p[1], r[1]))

        o1 = orient(a, b, c)
        o2 = orient(a, b, d)
        o3 = orient(c, d, a)
        o4 = orient(c, d, b)

        if (o1 == 0 and on_seg(a, c, b)) or (o2 == 0 and on_seg(a, d, b)) or (o3 == 0 and on_seg(c, a, d)) or (o4 == 0 and on_seg(c, b, d)):
            return True
        return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)

    @classmethod
    def _poly_intersects_rect(cls, poly, rect: pygame.Rect):
        """True если полигон пересекает прямоугольник rect."""
        # Быстрый AABB pre-check
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        if not rect.colliderect(pygame.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))):
            return False

        # 1) любой угол rect внутри poly
        corners = (rect.topleft, rect.topright, rect.bottomright, rect.bottomleft)
        for (cx, cy) in corners:
            if cls._point_in_poly(cx, cy, poly):
                return True

        # 2) любая вершина poly внутри rect
        for (x, y) in poly:
            if rect.collidepoint(x, y):
                return True

        # 3) пересечение ребер
        rx1, ry1 = rect.topleft
        rx2, ry2 = rect.topright
        rx3, ry3 = rect.bottomright
        rx4, ry4 = rect.bottomleft
        rect_edges = (((rx1, ry1), (rx2, ry2)),
                      ((rx2, ry2), (rx3, ry3)),
                      ((rx3, ry3), (rx4, ry4)),
                      ((rx4, ry4), (rx1, ry1)))
        n = len(poly)
        for i in range(n):
            a = poly[i]
            b = poly[(i + 1) % n]
            for (c, d) in rect_edges:
                if cls._segments_intersect(a, b, c, d):
                    return True

        return False

    # ------------------------------------------------------------------ #
    #  ПЕРЕХОДЫ МЕЖДУ ЛОКАЦИЯМИ                                           #
    # ------------------------------------------------------------------ #

    def _load_transitions(self):
        self.transitions = []

        # Корневая папка проекта
        root_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

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
                "tmx_path": os.path.join(root_dir, props["transition"]),
                "spawn_x": float(props.get("spawnX", 0)),
                "spawn_y": float(props.get("spawnY", 0)),
                "requires_boss": bool(props.get("requiresBoss", False)),
            })

    # ------------------------------------------------------------------ #
    #  NPC                                                                 #
    # ------------------------------------------------------------------ #

    def _load_npcs(self):
        self.npcs = []

        # Корневая папка проекта
        root_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            for obj in layer:
                if not obj.name or not (obj.name.startswith("npc") or obj.name.startswith("boss")):
                    continue
                self.npcs.append({
                    "rect": pygame.Rect(
                        int(obj.x * self.zoom),
                        int(obj.y * self.zoom),
                        int(obj.width * self.zoom),
                        int(obj.height * self.zoom)
                    ),
                    "name": obj.name,
                    "dialog_file": os.path.join(root_dir, obj.properties.get("dialogFile", "")),
                })

    # ------------------------------------------------------------------ #
    #  ОТРИСОВКА И УТИЛИТЫ                                                #
    # ------------------------------------------------------------------ #

    def draw(self, screen, camera_x=0, camera_y=0):
        screen.blit(self.map_surface, (-camera_x, -camera_y))

    def draw_collisions_debug(self, screen, camera_x=0, camera_y=0):
        """Красный — коллизии-rect, жёлтый — коллизии-poly, голубой — переходы, зелёный — NPC."""
        for rect in self.collision_rects:
            pygame.draw.rect(screen, (255, 0, 0),
                (rect.x - camera_x, rect.y - camera_y, rect.width, rect.height), 2)
        for poly in self.collision_polygons:
            if len(poly) >= 2:
                pts = [(x - camera_x, y - camera_y) for (x, y) in poly]
                pygame.draw.polygon(screen, (255, 255, 0), pts, 2)
        for t in self.transitions:
            r = t["rect"]
            pygame.draw.rect(screen, (0, 255, 255),
                (r.x - camera_x, r.y - camera_y, r.width, r.height), 2)
        for npc in self.npcs:
            r = npc["rect"]
            pygame.draw.rect(screen, (0, 255, 0),
                (r.x - camera_x, r.y - camera_y, r.width, r.height), 2)

    def check_collision(self, rect):
        if any(rect.colliderect(r) for r in self.collision_rects):
            return True
        for poly in self.collision_polygons:
            if self._poly_intersects_rect(poly, rect):
                return True
        return False

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

    def _find_animated_tiles(self):
        """Находит все анимированные тайлы на карте (tile layers + object layers)."""
        self.animated_tiles = []

        # 1) Анимированные тайлы на обычных тайловых слоях
        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, gid in layer:
                if not gid:
                    continue
                tile_data = self.tmx_data.get_tile_properties_by_gid(gid)
                if tile_data and "frames" in tile_data:
                    self.animated_tiles.append({
                        "kind": "tile",
                        "x": x * self.tilewidth,
                        "y": y * self.tileheight,
                        "draw_w": self.tilewidth,
                        "draw_h": self.tileheight,
                        "frames": tile_data["frames"],
                        "current_frame": 0,
                        "timer": 0.0,
                    })

        # 2) Анимированные tile-объекты на object слоях (например аквариум на location4)
        for layer in self.tmx_data.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue

            for obj in layer:
                if not getattr(obj, "gid", None):
                    continue

                tile_data = self.tmx_data.get_tile_properties_by_gid(obj.gid)
                if tile_data and "frames" in tile_data:
                    draw_w = int((obj.width if obj.width else self.orig_tilewidth) * self.zoom)
                    draw_h = int((obj.height if obj.height else self.orig_tileheight) * self.zoom)
                    self.animated_tiles.append({
                        "kind": "object",
                        "x": int(obj.x * self.zoom),
                        "y": int(obj.y * self.zoom),
                        "draw_w": draw_w,
                        "draw_h": draw_h,
                        "frames": tile_data["frames"],
                        "current_frame": 0,
                        "timer": 0.0,
                    })

    def update(self, dt):
        """Обновляет анимацию тайлов."""
        for tile in self.animated_tiles:
            if not tile["frames"]:
                continue

            tile["timer"] += dt * 1000  # в миллисекунды

            # Защита от выхода за пределы
            if tile["current_frame"] >= len(tile["frames"]):
                tile["current_frame"] = 0

            current = tile["frames"][tile["current_frame"]]

            if tile["timer"] >= current.duration:
                tile["timer"] = 0.0
                tile["current_frame"] = (
                                                tile["current_frame"] + 1
                                        ) % len(tile["frames"])

                # Перерисовываем этот тайл на map_surface
                frame_gid = current.gid
                image = self.tmx_data.get_tile_image_by_gid(frame_gid)
                if image:
                    image = pygame.transform.scale(
                        image, (tile["draw_w"], tile["draw_h"])
                    )
                    # Для тайлового слоя очищаем ячейку перед перерисовкой кадра.
                    # Для object-слоя обычно достаточно просто перерисовать кадр.
                    if tile.get("kind") == "tile":
                        self.map_surface.fill(
                            (0, 0, 0, 0),
                            (tile["x"], tile["y"], tile["draw_w"], tile["draw_h"])
                        )
                    self.map_surface.blit(image, (tile["x"], tile["y"]))