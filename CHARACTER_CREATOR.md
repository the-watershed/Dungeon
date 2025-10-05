# AD&D 2nd Edition Character Creator

A complete character creation system for Advanced Dungeons & Dragons 2nd Edition, fully integrated with the dungeon crawler game.

## Features

### Full 8-Step Character Creation Process

1. **Roll Ability Scores** - Choose from 4 different methods:
   - Method I: Roll 3d6 for each ability in order
   - Method II: Roll 3d6 twelve times, choose best six
   - Method III: Roll 3d6 six times per stat, choose highest
   - Method IV: Roll 2d6+6 for each stat

2. **Choose Race** - 7 playable races with unique modifiers:
   - Human - Versatile, can be any class
   - Elf - Dexterous, skilled with bows and swords
   - Dwarf - Hardy, resistant to magic
   - Halfling - Stealthy, good with thrown weapons
   - Half-Elf - Balanced, charm resistant
   - Gnome - Intelligent, skilled with magic
   - Half-Orc - Strong, tough

3. **Choose Class** - Based on race compatibility:
   - Fighter - High HP, excellent combat
   - Mage - Powerful spells, low HP
   - Cleric - Divine magic, good combat
   - Thief - Stealth, backstab, skills
   - Ranger - Wilderness warrior
   - Paladin - Holy warrior
   - Druid - Nature magic
   - Bard - Jack of all trades
   - Multi-class options for non-humans

4. **Roll Hit Points** - Roll your class hit die + Constitution modifier

5. **Choose Alignment** - 9 alignments from Lawful Good to Chaotic Evil

6. **Roll Starting Gold** - Based on your class

7. **Buy Equipment** - Shop from 50+ items:
   - **Weapons** (25+): Swords, axes, bows, crossbows, daggers, etc.
   - **Armor** (11): Leather to Plate Mail, shields
   - **Adventuring Gear** (20+): Rope, torches, lanterns, backpacks, tools
   - **Supplies**: Rations, waterskins, potions, spell components
   
8. **Final Details** - Name, age, height, weight

## Equipment Catalog

The character creator includes 50+ items useful in dungeons:

### Weapons
- Melee: Daggers, swords, axes, maces, flails, spears
- Ranged: Bows, crossbows, slings, darts
- Ammunition: Arrows, bolts, stones

### Armor & Shields
- Light: Leather, Studded Leather
- Medium: Ring Mail, Scale Mail, Chain Mail
- Heavy: Splint Mail, Banded Mail, Plate Mail
- Shields: Small, Medium, Large

### Adventuring Gear
- Light Sources: Torches, lanterns, candles, oil
- Climbing: Rope (hemp/silk), grappling hooks, pitons
- Camping: Tents, bedrolls, blankets
- Tools: Thieves' tools, crowbars, hammers, mirrors
- Containers: Backpacks, pouches, sacks, scroll cases
- Religious: Holy symbols, holy water
- Magical: Spell component pouches, spellbooks
- Supplies: Rations, waterskins, healing potions

## Running the Character Creator

### Standalone Mode
```bash
python char.py
```

### From Main Game Menu
1. Run the main dungeon game: `python main.py`
2. Press `Escape` or `Q` to open the menu
3. Select "Character Creator"
4. The character creator will launch in a new window

## Interactive Features

- **Manual Dice Rolling**: Press Enter to roll each die
- **Animated ASCII Art**: Typewriter effects and special formatting
- **Shopping System**: Browse equipment by category, see what you can afford
- **Character Sheet Display**: View complete character stats
- **Save/Load System**: Save characters to JSON files for later use

## Character Save Files

Characters are saved in the `saves/` directory as JSON files with the following information:
- All ability scores
- Race, class, alignment
- Hit points and combat stats
- Equipment inventory
- Gold remaining
- Physical characteristics

Save files are compatible with the main dungeon game for future integration.

## Integration with Dungeon Game

The character creator is designed to work alongside the main dungeon crawler. Future integration will allow:
- Loading created characters into the dungeon
- Using character stats for combat and skill checks
- Equipment management during gameplay
- Character progression and leveling

## Example Character Creation Session

1. Choose ability score method (e.g., Method IV for higher scores)
2. Roll your six ability scores
3. Select your race (e.g., Human Fighter)
4. Racial modifiers are applied automatically
5. Choose your class from available options
6. Roll hit points (e.g., 1d10 + CON modifier)
7. Choose alignment (e.g., Lawful Good)
8. Roll starting gold (e.g., 5d4 × 10 gp)
9. Buy equipment with your gold:
   - Long Sword (15 gp)
   - Chain Mail (150 gp)
   - Shield (10 gp)
   - Backpack (2 gp)
   - Rope (2 gp)
   - Torches (0.10 gp)
   - Rations (5 gp)
10. Enter name, age, height, weight
11. Review character sheet
12. Save your character

## Tips

- **For Fighters**: Prioritize strength and constitution, buy the best armor you can afford
- **For Mages**: Focus on intelligence, buy spellbook and component pouch
- **For Clerics**: Wisdom is key, don't forget your holy symbol
- **For Thieves**: Dexterity matters, buy thieves' tools and light armor
- **For Rangers**: Balance strength/dexterity/wisdom, get a good bow
- **For Paladins**: Need high strength and charisma, expensive armor requirements

## Technical Details

- Written in Python 3
- Uses standard library only (no external dependencies)
- JSON-based save system
- Cross-platform compatible
- Terminal/console-based with ASCII art

## Future Enhancements

Planned features for future versions:
- Spell selection for spellcasters
- Skill point allocation (for skills/thief abilities)
- Random character generator
- Character import into main game with full stat integration
- Experience and leveling system
- Equipment weight tracking and encumbrance
- Character portraits and descriptions

---

**Enjoy creating your AD&D 2nd Edition characters!**

*May your adventures be legendary!*
