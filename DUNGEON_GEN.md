# Dungeon Generation Module

This project exposes a small, reusable dungeon generation module in `dungeon_gen.py`.

## API

Exports:
- `Rect`: simple rectangle helper with `.center()` and `.intersect(other)`.
- `TILE_FLOOR`, `TILE_WALL`: integer tile identifiers (0 = floor, 1 = wall).
- `Dungeon`: grid container with:
  - `w`, `h`: width/height in tiles
  - `tiles[w][h]`: 2D list of tile integers
  - `rooms`: list of `Rect`
  - `is_wall(x, y) -> bool`
- `generate_dungeon(width, height, complexity=0.5, length=25, room_min=4, room_max=9, seed=None) -> Dungeon`
  - Creates and returns a populated `Dungeon`.
  - `complexity` [0..1]: adds extra connections between rooms (corridors)
  - `length`: approximate number of rooms to attempt
  - `room_min`/`room_max`: inclusive room size bounds
  - `seed`: set for deterministic generation

## Usage

Minimal example:

```python
from dungeon_gen import generate_dungeon, TILE_WALL

w, h = 80, 45
d = generate_dungeon(w, h, complexity=0.5, length=25, room_min=4, room_max=9)

# Iterate tiles
for y in range(d.h):
    for x in range(d.w):
        if d.tiles[x][y] == TILE_WALL:
            ...  # draw wall
        else:
            ...  # draw floor
```

Deterministic generation (tests, repro):

```python
seeded = generate_dungeon(50, 30, complexity=0.25, length=18, seed=1234)
```

## Integration in this project

`main.py` now imports and uses the module:

```python
from dungeon_gen import Dungeon, Rect, TILE_WALL, TILE_FLOOR, generate_dungeon

# ...
# Window mode
map_w, grid_h = 64, 36
level = generate_dungeon(map_w, grid_h, complexity=0.5, length=25, room_min=4, room_max=9)
```

The save/load helpers encode tiles using `TILE_WALL` and `TILE_FLOOR`, so other consumers can interoperate easily.

## Notes
- The generator creates non-overlapping rectangular rooms connected by corridors, with optional extra connections.
- Tile indices are `tiles[x][y]` (x-major), matching how rendering expects them in `main.py`.
- For larger maps, consider increasing `length` and `room_max`.