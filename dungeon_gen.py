"""
Dungeon generation module.

Exports:
- Rect: simple rectangle helper
- TILE_FLOOR, TILE_WALL: tile identifiers
- Dungeon: grid container with carve helpers
- generate_dungeon(width, height, complexity, length, room_min, room_max, seed):
    Create and return a Dungeon with rooms and tunnels. Complexity adds extra
    connections for a more maze-like layout; length controls the number of
    attempted rooms (overall dungeon size/length).
"""
from __future__ import annotations

import random
from typing import List


class Rect:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        cx = (self.x1 + self.x2) // 2
        cy = (self.y1 + self.y2) // 2
        return cx, cy

    def intersect(self, other: "Rect") -> bool:
        return (self.x1 < other.x2 and self.x2 > other.x1 and
                self.y1 < other.y2 and self.y2 > other.y1)


TILE_FLOOR = 0
TILE_WALL = 1

# Material identifiers (render-agnostic)
MAT_COBBLE = 0   # stone floor / cobblestone
MAT_BRICK = 1    # brick wall
MAT_DIRT = 2     # dirt/earth (optional usage)
MAT_MOSS = 3     # mossy floor/stone
MAT_SAND = 4     # sand/sandstone
MAT_IRON = 5     # iron bars/metal
MAT_GRASS = 6    # grass
MAT_WATER = 7    # water
MAT_LAVA = 8     # lava
MAT_MARBLE = 9   # marble
MAT_WOOD = 10    # wood


class Dungeon:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        # Initialize all walls (tile types, not display chars)
        self.tiles: List[List[int]] = [[TILE_WALL for _ in range(h)] for _ in range(w)]
        # Materials grid, default to brick (matches initial walls)
        self.materials: List[List[int]] = [[MAT_BRICK for _ in range(h)] for _ in range(w)]
        self.rooms: List[Rect] = []

    def carve_room(self, room: Rect):
        for x in range(room.x1 + 1, room.x2 - 1):
            for y in range(room.y1 + 1, room.y2 - 1):
                if 0 <= x < self.w and 0 <= y < self.h:
                    self.tiles[x][y] = TILE_FLOOR
                    self.materials[x][y] = MAT_COBBLE

    def carve_h_tunnel(self, x1: int, x2: int, y: int):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.w and 0 <= y < self.h:
                self.tiles[x][y] = TILE_FLOOR
                self.materials[x][y] = MAT_COBBLE

    def carve_v_tunnel(self, y1: int, y2: int, x: int):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x < self.w and 0 <= y < self.h:
                self.tiles[x][y] = TILE_FLOOR
                self.materials[x][y] = MAT_COBBLE

    def generate(self, max_rooms: int, room_min: int, room_max: int):
        for _ in range(max_rooms):
            w = random.randint(room_min, room_max)
            h = random.randint(room_min, room_max)
            x = random.randint(1, max(1, self.w - w - 2))
            y = random.randint(1, max(1, self.h - h - 2))
            new_room = Rect(x, y, w, h)

            if any(new_room.intersect(other) for other in self.rooms):
                continue

            self.carve_room(new_room)
            if self.rooms:
                # connect to previous room with a corridor
                (prev_x, prev_y) = self.rooms[-1].center()
                (new_x, new_y) = new_room.center()
                if random.random() < 0.5:
                    self.carve_h_tunnel(prev_x, new_x, prev_y)
                    self.carve_v_tunnel(prev_y, new_y, new_x)
                else:
                    self.carve_v_tunnel(prev_y, new_y, prev_x)
                    self.carve_h_tunnel(prev_x, new_x, new_y)

            self.rooms.append(new_room)

    def is_wall(self, x: int, y: int) -> bool:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.tiles[x][y] == TILE_WALL
        return True

    def material_at(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.materials[x][y]
        return MAT_BRICK

    def stamp_prefab(self, px: int, py: int, cells: List[str], legend: dict):
        """Stamp a prefab at top-left (px,py). Legend maps chars to {tile, material}.
        tile: 'wall' | 'floor' | 'void'
        material: 'brick' | 'cobble' | 'dirt' (optional)
        """
        tile_map = {
            'wall': TILE_WALL,
            'floor': TILE_FLOOR,
        }
        mat_map = {
            'brick': MAT_BRICK,
            'cobble': MAT_COBBLE,
            'stone': MAT_COBBLE,
            'dirt': MAT_DIRT,
            'moss': MAT_MOSS,
            'sand': MAT_SAND,
            'iron': MAT_IRON,
            'grass': MAT_GRASS,
            'water': MAT_WATER,
            'lava': MAT_LAVA,
            'marble': MAT_MARBLE,
            'wood': MAT_WOOD,
        }
        h = len(cells)
        w = len(cells[0]) if h else 0
        for y in range(h):
            for x in range(w):
                ch = cells[y][x]
                entry = legend.get(ch)
                if not entry:
                    continue
                if entry.get('tile') == 'void':
                    continue
                dx, dy = px + x, py + y
                if not (0 <= dx < self.w and 0 <= dy < self.h):
                    continue
                tile_name = entry.get('tile') if isinstance(entry, dict) else 'floor'
                if not isinstance(tile_name, str):
                    tile_name = 'floor'
                mat_name = entry.get('material', 'cobble') if isinstance(entry, dict) else 'cobble'
                if not isinstance(mat_name, str):
                    mat_name = 'cobble'
                t = tile_map.get(tile_name, TILE_FLOOR)
                m = mat_map.get(mat_name, MAT_COBBLE)
                self.tiles[dx][dy] = t
                self.materials[dx][dy] = m


def generate_dungeon(
    width: int,
    height: int,
    complexity: float = 0.5,
    length: int = 25,
    room_min: int = 4,
    room_max: int = 9,
    seed: int | None = None,
) -> Dungeon:
    """Generate and return a Dungeon.

    Parameters
    - width, height: target dungeon size in tiles
    - complexity: 0..1, adds extra connections (corridors) between rooms
    - length: approximate number of rooms to attempt (overall size)
    - room_min, room_max: inclusive room size bounds
    - seed: optional seed for deterministic generation

    Returns
    - Dungeon instance with tiles and room list populated
    """
    rnd_state = None
    if seed is not None:
        rnd_state = random.getstate()
        random.seed(seed)
    try:
        d = Dungeon(width, height)
        max_rooms = max(1, int(length))
        d.generate(max_rooms=max_rooms, room_min=room_min, room_max=room_max)

        # Extra connections based on complexity: link random room pairs
        extra_links = max(0, int(complexity * max(0, len(d.rooms) - 1)))
        for _ in range(extra_links):
            if len(d.rooms) < 2:
                break
            a = random.choice(d.rooms)
            b = random.choice(d.rooms)
            if a is b:
                continue
            (ax, ay) = a.center()
            (bx, by) = b.center()
            if random.random() < 0.5:
                d.carve_h_tunnel(ax, bx, ay)
                d.carve_v_tunnel(ay, by, bx)
            else:
                d.carve_v_tunnel(ay, by, ax)
                d.carve_h_tunnel(ax, bx, by)

        return d
    finally:
        if rnd_state is not None:
            # Restore RNG state
            random.setstate(rnd_state)
