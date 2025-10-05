# Character Creator Integration Guide

## Overview
The character creator is now fully integrated into the main dungeon game as a Pygame popup window.

## How to Use

### At Startup
1. Run the main game: `python main.py`
2. **Character creator launches automatically** at startup
3. Choose to create a new character or load an existing one
4. Complete the character creation process (or select a saved character)
5. The dungeon game starts with your character loaded

### In-Game (Optional)
- Press `Escape` or `Q` to open the main menu
- Select "Character Creator" to create/load a different character
- The character creator popup will open

### Character Creation Flow
1. **Welcome Screen** - Introduction to the character creation process
2. **Load/Create Choice** - Option to load existing character or create new
3. **Choose Race** - Select from 7 AD&D races (Human, Elf, Dwarf, etc.)
4. **Roll Abilities** - 4d6 drop lowest for each stat (STR, DEX, CON, INT, WIS, CHA)
5. **Choose Class** - Select from 8 classes (Fighter, Mage, Cleric, Thief, etc.)
6. **Choose Alignment** - Pick from 9 alignments (Lawful Good to Chaotic Evil)
7. **Purchase Equipment** - Buy weapons, armor, gear with starting gold
8. **Name Character** - Enter your character's name
9. **Review & Save** - Review final stats and save to file

### Controls
- **Arrow Keys** / **W/S**: Navigate menus
- **Enter**: Select option / Confirm
- **Escape**: Go back / Cancel
- **Type**: Enter text when prompted

## Character Stats Display

Once a character is created or loaded, their stats appear in the game's status panel:
- Character Name
- Race and Class
- Hit Points (Current/Max)
- Armor Class (AC) and THAC0
- Ability Scores (STR, DEX, CON, INT, WIS, CHA)
- Gold Pieces

## Save Files

Characters are automatically saved to the `saves/` directory as JSON files:
- Location: `saves/<CharacterName>.json`
- Format: JSON with all character data
- Loading: Available from the character creator startup screen

## Features

### Races (7 total)
- **Human**: Versatile, no modifiers
- **Elf**: +1 DEX, -1 CON, Infravision, Secret door detection
- **Dwarf**: +1 CON, -1 CHA, Infravision, Magic resistance
- **Halfling**: -1 STR, +1 DEX, Stealth bonus
- **Half-Elf**: Balanced, Infravision, Charm resistance
- **Gnome**: +1 CON, Infravision, Illusion magic
- **Half-Orc**: +1 STR, +1 CON, -2 INT, -2 CHA, Infravision

### Classes (8 total)
- **Fighter**: HD d10, High HP, Best combat
- **Mage**: HD d4, Spellcasting, Low HP
- **Cleric**: HD d8, Divine magic, Medium combat
- **Thief**: HD d6, Skills, Backstab
- **Ranger**: HD d10, Tracking, Dual-wield
- **Paladin**: HD d10, Holy powers, Strict alignment
- **Druid**: HD d8, Nature magic
- **Bard**: HD d6, Music, Jack-of-all-trades

### Equipment Categories
- **Weapons**: 16+ weapon types (swords, axes, bows, etc.)
- **Armor**: 8 armor types (leather to plate mail, shields)
- **Gear**: 12+ adventuring items (rope, torches, thieves' tools, etc.)
- **Potions**: Healing potions, antidotes

### Equipment Properties
- **Cost**: Price in gold pieces
- **Weight**: Encumbrance tracking
- **Damage**: Weapon damage dice (e.g., 1d8)
- **AC**: Armor class for armor pieces

## Game Integration

The character creator returns a `Character` object with these attributes:
- `name`: Character name
- `race`: Race name
- `char_class`: Class name
- `level`: Character level (starts at 1)
- `xp`: Experience points
- `strength, dexterity, constitution, intelligence, wisdom, charisma`: Ability scores
- `max_hp, current_hp`: Hit points
- `armor_class`: AC (lower is better in AD&D)
- `thac0`: To Hit AC 0 (attack bonus)
- `alignment`: Character alignment
- `gold`: Gold pieces
- `equipment`: List of equipment names
- `weight_carried`: Total encumbrance
- `racial_abilities`: List of special racial abilities

## Technical Details

### Files
- `char_gui.py`: Pygame character creator (standalone)
- `main.py`: Main game with integration code
- `saves/`: Directory for character JSON files

### Integration Points
1. Menu system in main.py calls `run_character_creator()`
2. Returns `Character` object or `None` if cancelled
3. Character stats displayed in status panel
4. Character data available as `player_character` variable

### Window Specifications
- Size: 1000x600 pixels (exactly matches game window)
- Background: Dark parchment color (74, 71, 65)
- Text: Light parchment color (245, 237, 215)
- Highlights: Gold color (200, 170, 120)
- Font: System font at 18pt (titles at 24pt)

## Future Enhancements
- Combat integration (use character stats for attacks/defense)
- Equipment effects (weapons deal damage, armor protects)
- HP tracking during gameplay
- Experience and leveling system
- Character inventory management
- Spell selection for magic users
- Racial ability activation
- Multi-classing support

## Troubleshooting

### Character creator won't open
- Ensure `char_gui.py` is in the game directory
- Check that Pygame is installed
- Verify `saves/` directory exists (created automatically)

### Stats not displaying
- Ensure a character was created/loaded successfully
- Check for success message in game log
- Verify character file exists in `saves/` directory

### Equipment not showing effects
- Equipment tracking is implemented
- Combat/protection effects pending future update
- Weight and gold are tracked and displayed
