# Equipment & Paperdoll System

## Overview
The inventory system now includes a **paperdoll** (character equipment display) showing all equipped items on your character, along with an improved 3-panel layout for better organization.

## Screen Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  INVENTORY & EQUIPMENT: Character Name                                  │
│  Gold: 50gp | Weight: 45.2 lbs | Items: 12                             │
│  [Context-sensitive help text based on current mode]                    │
├──────────────────────────────┬────────────────────────────────────────────┤
│                              │                                            │
│   INVENTORY (Left Panel)     │    EQUIPPED (Right Panel - Paperdoll)      │
│   - Scrollable item list     │    - 13 equipment slots                    │
│   - 8 main slots             │    - Head, Neck, Body                      │
│   - Container contents       │    - Wrists (L/R), Hands                   │
│                              │    - Rings (L/R), Legs, Feet               │
│                              │    - Trinket, Main Hand, Off-Hand          │
│                              │                                            │
│                              │                                            │
│                              │                                            │
├──────────────────────────────┴────────────────────────────────────────────┤
│ ─────────────────────────────────────────────────────────────────────── │
│  INFO PANEL (8 lines at bottom)                                          │
│  - Selected item details (name, category, weight, value, stats)          │
│  - Equipped item details when viewing paperdoll                          │
│  - Prompts for equip/use disambiguation                                  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Equipment Slots (13 total)

### Character Paperdoll Slots:
1. **Head** - Helms, helmets
2. **Neck** - Amulets, necklaces
3. **Body** - Armor (leather, chain, plate, etc.)
4. **Left Wrist** - Bracers, wrist bands
5. **Right Wrist** - Bracers, wrist bands
6. **Hands** - Gloves, gauntlets
7. **Left Ring** - Rings
8. **Right Ring** - Rings
9. **Legs** - Greaves, leg armor
10. **Feet** - Boots
11. **Trinket** - Lucky charms, holy symbols, misc magical items
12. **Main Hand** - Primary weapon
13. **Off-Hand** - Shield, secondary weapon

## Navigation & Controls

### Basic Controls
- **I** - Open/close inventory screen
- **ESC** - Back/close (cascading: prompt → paperdoll → container → inventory → game)
- **UP/DOWN** or **W/S** - Navigate lists
- **TAB** - Toggle between inventory list and paperdoll navigation

### Inventory List Mode (Default)
- **UP/DOWN** - Select different inventory slots
- **ENTER** - Equip item (if equippable) OR open container (if container)
- **1-8** - Quick jump to slot number
- **LEFT** - Close container (when viewing container contents)
- **TAB** - Switch to paperdoll navigation

### Paperdoll Mode (After pressing TAB)
- **UP/DOWN** - Select different equipment slots
- **ENTER** - Unequip selected item (moves to inventory)
- **TAB** - Return to inventory list navigation
- **ESC** - Return to inventory list navigation

### Container View Mode
- **UP/DOWN** - Navigate container contents
- **ENTER** - Equip/use selected item
- **LEFT** or **ESC** - Return to main inventory
- **TAB** - View equipped items

## Equipping Items

### Automatic Equipping
1. Navigate to an equippable item in inventory
2. Press **ENTER**
3. Item is automatically equipped to its designated slot
4. If that slot already has an item, they swap places

### Example: Equipping a Sword
```
Before:
Inventory Slot 3: Long Sword
Main Hand: Dagger

After pressing ENTER on Long Sword:
Inventory Slot 3: Dagger
Main Hand: Long Sword
```

### Special Cases

#### Rings and Wrists
Items that can go on left OR right wrist/ring will automatically find an empty slot. If both are full, it defaults to the left slot (swapping).

#### Equip or Use Disambiguation
Some items (like magical jewelry or holy symbols) can be both equipped AND used from inventory. When you press ENTER on these items:
```
Item: Ring of Fire Resistance
This item can be equipped or used.
Press E to Equip, U to Use, or ESC to Cancel.
```

## Unequipping Items

1. Press **TAB** to enter paperdoll mode
2. Use **UP/DOWN** to select the equipped slot
3. Press **ENTER** to unequip
4. Item moves to first available inventory slot
5. If inventory is full, item cannot be unequipped (warning displayed)

## Item Properties

### Equippable Items
All equippable items have these properties:
- `equippable: true` - Can be worn
- `equipment_slot` - Which slot it uses (head, neck, body, wrist, hands, ring, legs, feet, trinket, main_hand, off_hand)

### Usable Items
Items like potions have:
- `usable_from_inventory: true` - Can be used without equipping

### Dual-Purpose Items
Some items have both properties and will prompt for your choice.

## Equipment Examples by Slot

### Head
- Leather Helm (AC -1)
- Iron Helm (AC -1)

### Neck
- Amulet
- Various necklaces and charms

### Body
- Leather Armor (AC 8)
- Chain Mail (AC 5)
- Plate Mail (AC 3)
- All armor types (studded leather, ring mail, scale mail, splint mail)

### Wrists (can equip 2)
- Bracers

### Hands
- Leather Gloves
- Gauntlets (AC -1)

### Rings (can equip 2)
- Ring of Protection (AC -1)
- Silver Ring
- Any magical rings

### Legs
- Leather Greaves
- Iron Greaves (AC -1)

### Feet
- Leather Boots
- Iron Boots

### Trinket
- Lucky Charm
- Holy Symbol
- Miscellaneous magical items

### Main Hand
- All weapons: swords, axes, hammers, bows, etc.
- Damage and speed stats apply

### Off-Hand
- Shields (AC -1)
- Secondary weapons (future feature)

## Weight & AC Calculations

### Total Weight
The info line shows total weight including:
- All items in inventory (8 main slots + container contents)
- All equipped items on paperdoll
- Weight reductions from containers apply

### Total AC Bonus
All equipped items with AC modifiers contribute to your overall armor class. The CharacterEquipment class automatically calculates total AC bonus from:
- Body armor (AC 3-8)
- Shields (AC -1)
- Helms, gauntlets, greaves (AC -1 each)
- Magical items with AC bonuses

## Scrolling

### When Do Lists Scroll?
- Inventory list scrolls when container contents exceed visible space
- Maximum visible rows = screen height - header (4 lines) - info panel (8 lines) - borders
- Auto-scroll keeps selected item visible

### Scroll Indicators
- **▲** appears at top when more items above
- **▼** appears at bottom when more items below

## Tips & Strategies

### Organization
- Keep frequently equipped items in main inventory slots (1-8)
- Store alternate equipment in containers
- Use TAB to quickly check what you're wearing

### Combat Preparation
1. Open inventory (I)
2. Press TAB to view equipped items
3. Verify weapon in Main Hand
4. Verify armor in Body slot
5. Check for shield in Off-Hand
6. Press ESC to return to game

### Equipment Swapping
To quickly swap weapons:
1. Press I to open inventory
2. Navigate to new weapon
3. Press ENTER - automatically swaps with current weapon
4. Press ESC to close

### Weight Management
- Equipped items count toward total weight
- Heavy armor significantly impacts movement
- Consider unequipping heavy items when not in combat

## Context-Sensitive Help

The help text at the top of the screen changes based on your current mode:

**Normal Inventory Mode:**
```
UP/DOWN: Navigate | ENTER: Equip/Open | TAB: View Equipment | ESC: Close
```

**Paperdoll Mode:**
```
TAB: Navigate Equipment | ENTER: Unequip | ESC/TAB: Back
```

**Container View Mode:**
```
UP/DOWN: Navigate | LEFT/ESC: Back | TAB: View Equipment
```

**Equip/Use Prompt:**
```
E: Equip | U: Use | ESC: Cancel
```

## Advanced Features

### Nested Containers (Future)
Currently, containers inside containers are not supported, but the system is designed to accommodate this in future updates.

### Two-Weapon Fighting (Future)
Currently, only shields can be equipped in the off-hand. Future updates may allow weapons in both hands.

### Item Usage
Pressing U on usable items (like potions) will consume them. This is a placeholder for future expansion with various item effects.

## Technical Details

### Classes
- `InventoryItem` - Represents any item with all properties
- `CharacterInventory` - Manages 8 inventory slots and containers
- `CharacterEquipment` - Manages 13 equipment slots (paperdoll)

### State Variables
- `inventory_open` - Is inventory screen visible
- `inventory_main_slot` - Selected slot (0-7)
- `inventory_viewing_container` - Viewing container contents
- `inventory_container_slot` - Selected slot within container
- `inventory_scroll_offset` - Current scroll position
- `inventory_viewing_paperdoll` - Navigating paperdoll (TAB mode)
- `inventory_paperdoll_slot` - Selected equipment slot (0-12)
- `inventory_prompt_mode` - Currently showing prompt ('equip_or_use')
- `inventory_prompt_item` - Item being prompted about

### Equipment Slot Order (for TAB navigation)
1. head → 2. neck → 3. body → 4. left_wrist → 5. right_wrist → 6. hands → 7. left_ring → 8. right_ring → 9. legs → 10. feet → 11. trinket → 12. main_hand → 13. off_hand

## Troubleshooting

### "Inventory full! Cannot unequip"
- Your 8 inventory slots are all occupied
- Free up space by opening containers or dropping items
- Consider storing items in backpack first

### Item Won't Equip
- Check if item is marked as equippable
- Verify equipment slot is correct
- Some items may have class/race restrictions (future feature)

### Can't Open Container
- Make sure ENTER is pressed while container is highlighted
- Container must be in main inventory (not inside another container yet)
- Press LEFT or ESC to return if accidentally opened

## Future Enhancements

Planned features:
- [ ] Drag-and-drop item movement
- [ ] Equipment comparison tooltips
- [ ] Set bonuses for matching armor pieces
- [ ] Weapon proficiency restrictions
- [ ] Class-specific equipment limitations
- [ ] Magical item identification
- [ ] Cursed items (can't unequip)
- [ ] Item durability and repair
- [ ] Equipment customization/enchantment

---

**Last Updated:** October 4, 2025
**Compatible with:** Main game version with slot-based inventory system
