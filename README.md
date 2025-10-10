# ASCII Dungeon Crawler

A top-down, grid-based dungeon crawler with AD&D 2nd Edition character creation.

## Features
- ASCII art rendering with lighting and shadows
- Field-of-view (shadowcasting) with brightness falloff
- **AD&D 2nd Edition Character Creator** - Full character creation with races, classes, equipment
- Procedurally generated dungeons with rooms and corridors
- Door system at room entrances
- Save/Load game system
- Character stats tracking and display

## Game Elements
- `#` walls
- space ` ` floor
- `@` player
- `+` doors
- WASD movement, `Q` or `Esc` for menu

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

## Character Creator

**The character creator launches automatically when you start the game!** You can create a new character or load an existing one before entering the dungeon.

You can also access it in-game by pressing `Esc` or `Q` to open the menu and selecting "Character Creator".

**Character Creation Process:**
1. Choose race (Human, Elf, Dwarf, Halfling, Half-Elf, Gnome, Half-Orc)
2. Roll ability scores (4d6 drop lowest)
3. Choose class (Fighter, Mage, Cleric, Thief, Ranger, Paladin, Druid, Bard)
4. Choose alignment (9 alignments from Lawful Good to Chaotic Evil)
5. Purchase equipment with starting gold
6. Name your character
7. Review and save

**Character Stats Displayed:**
- Name, Race, Class
- HP (Hit Points)
- AC (Armor Class) and THAC0 (attack bonus)
- Six ability scores (STR, DEX, CON, INT, WIS, CHA)
- Gold

Characters are saved to `saves/<name>.json` and can be loaded later.

For more details, see [CHARACTER_INTEGRATION.md](CHARACTER_INTEGRATION.md)
- Unseen: black
- Player: red square

## Sound Manager

**NEW:** Complete mouse-driven sound library manager with trigger system!

### Features
- **Mouse-Navigable UI**: Click to select assets, edit metadata, manage sounds
- **Import/Export**: Full support for MP3, WAV, and MIDI files
- **Trigger System**: Assign game events to sounds (e.g., "finding_secret", "combat_hit")
- **High-Quality Playback**: Fixed MP3 playback (44.1kHz, no static)
- **Variant Management**: Multiple sound files per asset for randomization

### Run Sound Manager
```powershell
python sound_manager_ui.py
```

### Documentation
- **[SOUND_MANAGER_GUIDE.md](SOUND_MANAGER_GUIDE.md)** - Complete UI guide
- **[SOUND_TRIGGER_GUIDE.md](SOUND_TRIGGER_GUIDE.md)** - Trigger system documentation

### Using Sounds in Game Code
```python
from sound_library import get_sound_library

library = get_sound_library()

# Play by name
library.play_sound("click_1")

# Play by trigger event
library.play_trigger_sound("finding_secret")
```

### Common Triggers
The system includes 32 built-in triggers like:
- `finding_secret`, `discovering_treasure`
- `opening_door`, `closing_door`
- `player_footstep`, `player_jump`, `player_damage`
- `combat_hit`, `combat_miss`, `combat_critical`
- `enemy_attack`, `enemy_death`
- `item_pickup`, `spell_cast`
- `ui_click`, `menu_open`

Plus custom triggers for your specific game events!

## Notes

- Grid size is fixed to 80x40 in windowed mode (each cell is 20x30 pixels).
- Lighting radius is 3 tiles; tweak `LIGHT_RADIUS` in `main.py`.
- Generation uses simple rooms and corridors.
- If you need the terminal renderer, call `run_terminal()` from `main()` manually.
- **Sound playback fixed**: MP3s now play correctly at 44.1kHz (no static)
