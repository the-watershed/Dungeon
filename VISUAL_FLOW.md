# Visual Startup Flow Guide

## New Game Launch Sequence

```
┌─────────────────────────────────────────────────────────┐
│  STEP 1: Launch Game                                    │
│  Command: python main.py                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  CHARACTER CREATOR WINDOW OPENS                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  AD&D 2nd Edition Character Creator               │  │
│  │                                                   │  │
│  │  Welcome to the AD&D 2nd Edition Character       │  │
│  │  Creator!                                         │  │
│  │                                                   │  │
│  │  This wizard will guide you through creating a   │  │
│  │  new character...                                 │  │
│  │                                                   │  │
│  │  Press any key to continue...                     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  CHARACTER SELECTION                                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Character Selection                              │  │
│  │                                                   │  │
│  │  ► 1. Create New Character                        │  │
│  │    2. Gandalf                                     │  │
│  │    3. Thorin                                      │  │
│  │    4. Legolas                                     │  │
│  │                                                   │  │
│  │  Use UP/DOWN arrows to navigate, Enter to        │  │
│  │  select, Escape to cancel                         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↓
              ┌─────────┴─────────┐
              │                   │
         NEW CHARACTER        LOAD EXISTING
              │                   │
              ↓                   ↓
┌──────────────────────┐  ┌──────────────────────┐
│  8-Step Creation     │  │  Character Loaded    │
│  1. Race             │  │  ┌────────────────┐  │
│  2. Abilities        │  │  │ Gandalf        │  │
│  3. Class            │  │  │ Human Mage     │  │
│  4. Alignment        │  │  │ Level 1        │  │
│  5. Equipment        │  │  │ HP: 4          │  │
│  6. Name             │  │  └────────────────┘  │
│  7. Review           │  └──────────────────────┘
│  8. Save             │
└──────────────────────┘
              │                   │
              └─────────┬─────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  CHARACTER CREATOR WINDOW CLOSES                        │
│  Terminal Output:                                       │
│  > Welcome, Gandalf! Starting your adventure...         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  DUNGEON GENERATES                                      │
│  - Creating rooms and corridors                         │
│  - Placing doors                                        │
│  - Calculating light levels                             │
│  - Building FOV system                                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  GAME WINDOW OPENS                                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ╔════STATUS════╗ ┊ ############################# │  │
│  │ ║ Gandalf      ║ ┊ #                       #     │  │
│  │ ║ Human Mage   ║ ┊ #   @                   #     │  │
│  │ ║ HP:4/4       ║ ┊ #                       +     │  │
│  │ ║ AC:10 T0:20  ║ ┊ #                       #     │  │
│  │ ║ S10 D14 C12  ║ ┊ ############################# │  │
│  │ ║ I16 W13 Ch11 ║ ┊                               │  │
│  │ ║ Gold:35gp    ║ ┊                               │  │
│  │ ║ Explored:0%  ║ ┊                               │  │
│  │ ╚══════════════╝ ┊                               │  │
│  │                                                   │  │
│  │  Message Log:                                     │  │
│  │  > Welcome, Gandalf the Human Mage!               │  │
│  │  > HP: 4/4, AC: 10                                │  │
│  └───────────────────────────────────────────────────┘  │
│  GAME READY - START EXPLORING!                          │
└─────────────────────────────────────────────────────────┘
```

## Alternative Flow: Cancel Character Creation

```
┌─────────────────────────────────────────────────────────┐
│  CHARACTER SELECTION                                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Character Selection                              │  │
│  │                                                   │  │
│  │  ► 1. Create New Character                        │  │
│  │    2. Gandalf                                     │  │
│  │                                                   │  │
│  │  User presses: ESC                                │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  CHARACTER CREATOR WINDOW CLOSES                        │
│  Terminal Output:                                       │
│  > Character creation cancelled. Exiting game.          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  GAME EXITS                                             │
│  - No dungeon generated                                 │
│  - No game window opened                                │
│  - Clean exit to command prompt                         │
└─────────────────────────────────────────────────────────┘
```

## In-Game Character Creator Access

```
┌─────────────────────────────────────────────────────────┐
│  PLAYING GAME                                           │
│  User presses: ESC or Q                                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  MENU OPENS (Overlay on Game)                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │  ╔════════════════════════════════════════════╗   │  │
│  │  ║                                            ║   │  │
│  │  ║         🎲 ADVENTURER'S MENU 🎲            ║   │  │
│  │  ║                                            ║   │  │
│  │  ║  ► Character Creator                       ║   │  │
│  │  ║    Settings                                ║   │  │
│  │  ║    Save                                    ║   │  │
│  │  ║    Load                                    ║   │  │
│  │  ║    Quit                                    ║   │  │
│  │  ║                                            ║   │  │
│  │  ╚════════════════════════════════════════════╝   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        ↓
             Select "Character Creator"
                        ↓
┌─────────────────────────────────────────────────────────┐
│  CHARACTER CREATOR OPENS AGAIN                          │
│  - Can create new character                             │
│  - Can load different character                         │
│  - New character replaces current one                   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  RETURN TO GAME                                         │
│  - Updated character stats in status panel              │
│  - Welcome message for new character                    │
│  - Continue adventuring                                 │
└─────────────────────────────────────────────────────────┘
```

## Character Creation Steps Detail

```
STEP 1: CHOOSE RACE
┌─────────────────────────────────────┐
│ ► Human     - No modifiers          │
│   Elf       - +1 DEX, -1 CON       │
│   Dwarf     - +1 CON, -1 CHA       │
│   Halfling  - -1 STR, +1 DEX       │
│   Half-Elf  - Balanced              │
│   Gnome     - +1 CON                │
│   Half-Orc  - +1 STR, +1 CON, -2.. │
└─────────────────────────────────────┘

STEP 2: ROLL ABILITIES
┌─────────────────────────────────────┐
│ Your ability scores:                │
│ >>> Strength:     14                │
│ >>> Dexterity:    16                │
│ >>> Constitution: 12                │
│ >>> Intelligence: 15                │
│ >>> Wisdom:       13                │
│ >>> Charisma:     11                │
└─────────────────────────────────────┘

STEP 3: CHOOSE CLASS
┌─────────────────────────────────────┐
│ ► Fighter   - HD: d10, Gold: 5d4   │
│   Mage      - HD: d4, Gold: 1d4    │
│   Cleric    - HD: d8, Gold: 3d6    │
│   Thief     - HD: d6, Gold: 2d6    │
│   Ranger    - HD: d10, Gold: 5d4   │
│   Paladin   - HD: d10, Gold: 5d4   │
│   Druid     - HD: d8, Gold: 3d6    │
│   Bard      - HD: d6, Gold: 3d6    │
└─────────────────────────────────────┘

STEP 4: CHOOSE ALIGNMENT
┌─────────────────────────────────────┐
│ ► Lawful Good    - Crusader         │
│   Neutral Good   - Benefactor       │
│   Chaotic Good   - Rebel            │
│   Lawful Neutral - Judge            │
│   True Neutral   - Balanced         │
│   Chaotic Neutral- Free spirit      │
│   Lawful Evil    - Dominator        │
│   Neutral Evil   - Malefactor       │
│   Chaotic Evil   - Destroyer        │
└─────────────────────────────────────┘

STEP 5: PURCHASE EQUIPMENT
┌─────────────────────────────────────┐
│ Gold: 150 gp  Weight: 0 lbs         │
│                                     │
│ ► Weapons                           │
│   Armor                             │
│   Gear                              │
│   Potions                           │
│   Finish Shopping                   │
└─────────────────────────────────────┘

STEP 6: NAME CHARACTER
┌─────────────────────────────────────┐
│ Enter your character's name:        │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Gandalf|                        │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Press Enter to confirm              │
└─────────────────────────────────────┘

STEP 7: REVIEW CHARACTER
┌─────────────────────────────────────┐
│ === CHARACTER COMPLETE ===          │
│                                     │
│ Name: Gandalf                       │
│ Race: Human                         │
│ Class: Mage                         │
│ Alignment: Neutral Good             │
│                                     │
│ Ability Scores:                     │
│   STR: 10  DEX: 14  CON: 12        │
│   INT: 16  WIS: 13  CHA: 11        │
│                                     │
│ Hit Points: 4/4                     │
│ Armor Class: 10                     │
│ THAC0: 20                           │
│ Gold: 35 gp                         │
│                                     │
│ Equipment (5 items):                │
│   • Dagger                          │
│   • Spellbook                       │
│   • Backpack                        │
│   • Waterskin                       │
│   • Rations (7 days)                │
└─────────────────────────────────────┘

STEP 8: AUTO-SAVE
┌─────────────────────────────────────┐
│ Character saved successfully!       │
│ File: saves/Gandalf.json            │
└─────────────────────────────────────┘
```

## Key User Interactions

### Navigation Controls
- **↑ / W** - Move selection up
- **↓ / S** - Move selection down
- **Enter** - Select / Confirm
- **Escape** - Cancel / Go back
- **Type** - Enter text (when prompted)

### Visual Feedback
- **►** - Current selection (highlighted in gold)
- **>>>** - Important values (highlighted in gold)
- **|** - Text cursor (when typing)
- **Box borders** - Active input areas

### Status Indicators
- **Gold color** - Selected items, important values
- **Dim color** - Help text, instructions
- **White color** - Normal text
- **Red color** - Errors (not enough gold, etc.)

## Summary

The new startup flow ensures:
1. **Character creation is mandatory** - Can't play without a character
2. **Character selection is first** - Choice to create or load before dungeon generates
3. **Clean exit on cancel** - No empty game window if player changes mind
4. **Smooth transition** - Character creator → Dungeon generation → Game start
5. **In-game flexibility** - Can still create/switch characters via menu

The experience is now streamlined: **Character first, then adventure!** 🎲⚔️
