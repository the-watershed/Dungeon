# ASCII Dungeon Crawler

A top-down, grid-based dungeon crawler rendered with ASCII characters.

- `#` walls
- space ` ` floor
- `@` player
- Per-tile lighting using field-of-view (shadowcasting) with brightness falloff
- WASD movement, `Q` or `Esc` to quit

Two renderers are supported:
- Pygame windowed mode (default): 1600x1200 window, 80x40 character grid
- Terminal mode (legacy): ANSI-based (not default anymore)

## Run (Pygame window)

Install dependency:

```powershell
pip install -r .\requirements.txt
```

Start the game:

```powershell
python .\main.py
```

## Settings

Customize ASCII characters in `settings.json`:

```json
{
  "floor": " ",
  "wall": "#",
  "player": "@",
  "dark": " ",
  "hud_text": true
}
```

- floor: character used for traversable tiles (often a single space)
- wall: character for walls
- player: character for the player avatar
- dark: character for tiles outside light radius (space for full darkness)
- hud_text: toggle HUD text at the bottom of the window

## Minimap

A fog-of-war minimap is rendered as a pixel grid (not characters) for clarity.
Configure via `settings.json`:

```json
"minimap": {
  "enabled": true,
  "tile": 4,
  "margin": 8,
  "position": "top-right"  // top-left | top-right | bottom-left | bottom-right
}
```

- Visible tiles: bright gray, walls slightly brighter
- Explored (not currently visible): dark gray
- Unseen: black
- Player: red square

## Notes

- Grid size is fixed to 80x40 in windowed mode (each cell is 20x30 pixels).
- Lighting radius is 3 tiles; tweak `LIGHT_RADIUS` in `main.py`.
- Generation uses simple rooms and corridors.
- If you need the terminal renderer, call `run_terminal()` from `main()` manually.
