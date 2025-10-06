# Inventory System

## Overview
The inventory system provides a comprehensive view of your character's equipment with detailed information and flexible sorting options.

## How to Access
- **Press `I`** while in the game to open your inventory
- **Press `ESC`** to close the inventory and return to the game

## Features

### Item Information Displayed
Each item shows the following properties (when applicable):
- **Item Name** - The name of the item
- **Type** - Category (Weapons, Armor, Gear, Potions)
- **Value** - Cost in gold pieces (gp)
- **Weight** - Weight in pounds (lbs)
- **Damage** - Weapon damage dice (e.g., 1d8)
- **AC** - Armor Class modifier (negative is better)
- **Speed** - Speed factor for weapons

### Navigation
- **UP Arrow** - Move selection up
- **DOWN Arrow** - Move selection down
- The list automatically scrolls to keep the selected item visible

### Sorting Options
You can sort the inventory by any column using either number keys or letter keys:

| Sort By | Number Key | Letter Key | Description |
|---------|-----------|------------|-------------|
| Type | `1` | `T` | Sort by item category |
| Weight | `2` | `W` | Sort by weight (heaviest first) |
| Value | `3` | `V` | Sort by cost (most expensive first) |
| Damage | `4` | `G` | Sort by weapon damage |
| AC | `5` | `C` | Sort by Armor Class modifier |
| Speed | `6` | `R` | Sort by speed factor |
| Name | `7` | `N` | Sort alphabetically by name |

When you change the sort order, the selection resets to the first item and the scroll position resets to the top.

### Character Information
The top of the inventory screen displays:
- Character name
- Total gold
- Total weight carried
- Number of items in inventory

### Selected Item Details
At the bottom of the screen, you'll see detailed information about the currently selected item, including all applicable properties.

## Tips
- Use the inventory to quickly assess your combat capabilities
- Sort by weight to manage encumbrance
- Sort by value to identify valuable items
- Sort by AC or damage to optimize your loadout
- The inventory reflects equipment purchased during character creation

## Technical Notes
- The inventory system automatically parses equipment from `char_gui.py`'s EQUIPMENT database
- Items are displayed with full AD&D 2nd Edition stats
- Unknown items (not in the database) are shown with available information
- The inventory uses the same parchment background and font as the main game
