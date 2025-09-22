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


class Dungeon:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        # Initialize all walls (tile types, not display chars)
        self.tiles: List[List[int]] = [[TILE_WALL for _ in range(h)] for _ in range(w)]
        self.rooms: List[Rect] = []

    def carve_room(self, room: Rect):
        for x in range(room.x1 + 1, room.x2 - 1):
            for y in range(room.y1 + 1, room.y2 - 1):
                if 0 <= x < self.w and 0 <= y < self.h:
                    self.tiles[x][y] = TILE_FLOOR

    def carve_h_tunnel(self, x1: int, x2: int, y: int):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.w and 0 <= y < self.h:
                self.tiles[x][y] = TILE_FLOOR

    def carve_v_tunnel(self, y1: int, y2: int, x: int):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x < self.w and 0 <= y < self.h:
                self.tiles[x][y] = TILE_FLOOR

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
        if seed is not None:
            # Restore RNG state
            random.setstate(rnd_state)
