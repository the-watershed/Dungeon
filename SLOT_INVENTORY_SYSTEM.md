# Slot-Based Inventory System

## Overview
The game now features a sophisticated slot-based inventory system with containers, size restrictions, and weight reduction mechanics. Characters have 8 base inventory slots, and containers (backpacks, bags, pouches) can be placed in slots to expand storage capacity.

## Core Mechanics

### 8 Base Slots
- Every character has exactly **8 inventory slots**
- Each slot can hold one item OR one container
- Slots are numbered 1-8 for easy reference
- Empty slots are clearly marked

### Containers
Containers are special items that provide additional storage:

#### Container Types & Capacities

**Pouches & Small Bags:**
- **Belt Pouch**: 2 slots, small items only
- **Small Sack**: 3 slots, small items only  
- **Large Sack**: 5 slots, small/medium items

**Backpacks:**
- **Small Backpack**: 6 slots, up to medium items, 10% weight reduction
- **Backpack** (standard): 10 slots, all sizes, 15% weight reduction
- **Large Backpack**: 12 slots, all sizes, 20% weight reduction

**Specialty Containers:**
- **Rucksack**: 8 slots, all sizes, 10% weight reduction
- **Haversack**: 14 slots, all sizes, 25% weight reduction

**Magic Containers** (rare/expensive):
- **Bag of Holding (Minor)**: 15 slots, all sizes, 50% weight reduction (500gp)
- **Bag of Holding**: 20 slots, all sizes, 75% weight reduction (2500gp)

### Item Sizes
All items have a size category that determines what containers can hold them:

- **Small**: Potions, daggers, tools, flasks, holy symbols
- **Medium**: Most weapons, shields, ropes, rations, spellbooks
- **Large**: Two-handed weapons, armor, tents, bedrolls

**Size Restrictions:**
- Pouches can only hold small items
- Sacks can hold small or medium items
- Backpacks and larger containers can hold any size

### Weight System

#### Base Weight
- Each item has a base weight in pounds
- Container weight includes the container itself plus contents

#### Weight Reduction
- Backpacks and better containers reduce the weight of items inside them
- Reduction percentages: 10% (small backpack) to 75% (Bag of Holding)
- Formula: `Effective Weight = Container Weight + (Contents Weight × (1 - Reduction%))`

#### Example:
- Large Backpack (3 lbs) with 20% reduction
- Contains: Chain Mail (40 lbs) + Rations (7 lbs) = 47 lbs of contents
- Reduced contents: 47 × 0.8 = 37.6 lbs
- Total effective weight: 3 + 37.6 = 40.6 lbs (vs 50 lbs without backpack!)

### Auto-Fill Logic
When picking up items:
1. **First**: Fill empty main slots (1-8)
2. **Then**: Automatically place items in containers if they fit
3. Check size restrictions (item must fit container's max size)
4. Check available space in containers

## User Interface

### Main Inventory Screen
Press **`I`** to open inventory

**Main View (Default):**
**Left Panel: 8 Main Slots**
- Shows all 8 base inventory slots
- Selected slot is highlighted with `>`
- Empty slots show `<empty>`
- Items show name and weight
- Containers show name and capacity (e.g., `[5/10 slots]`)

**Right Panel: Item Details**
- Shows detailed information about the selected item
- For containers: shows capacity, size restrictions, weight reduction

**Container View (After Pressing ENTER on a container):**
**Left Panel: Container Contents**
- Replaces the 8-slot view with the container's contents
- Shows ALL slots in the container (empty and filled)
- Container header shows name, capacity, and properties
- Navigate with UP/DOWN
- Press LEFT or ESC to return to main 8-slot view

**Right Panel: Item Details**
- Shows details of the selected item inside the container

### Navigation Controls

**Main Slot Navigation (8 Slots View):**
- **UP/DOWN**: Navigate through the 8 main slots
- **1-8 keys**: Jump directly to slot number
- **ENTER**: Open selected container (replaces main view with container contents)
- **ESC**: Close inventory

**Container View (Inside a Container):**
- **UP/DOWN**: Navigate items inside container
- **LEFT Arrow**: Close container and return to main 8-slot view
- **ESC**: Close container and return to main 8-slot view (first press), or close inventory (second press)
- **1-8 keys**: Still available for quick slot reference

### Visual Indicators
- **`>`**: Currently selected item
- **`[X/Y slots]`**: Container capacity (X used, Y total)
- Weight displayed in pounds (lb)
- Empty slots clearly marked
- Container contents shown in detail panel

## Item Management

### Current Features (Implemented)
- ✅ View all 8 slots
- ✅ Navigate main inventory
- ✅ Open and view container contents
- ✅ See item stats and container info
- ✅ Automatic weight calculation with reductions
- ✅ Size restriction enforcement
- ✅ Auto-fill when picking up items

### Future Features (Planned)
- Move items between slots
- Move items into/out of containers
- Drop items
- Equip/unequip items
- Stack similar items
- Quick-use for potions
- Container organization tools

## Technical Details

### Data Structures

**InventoryItem Class:**
```python
- name: str
- category: str  
- size: str  # small, medium, large
- weight: float
- cost: int
- is_container: bool
- slots: int  # if container
- max_item_size: str  # if container
- weight_reduction: float  # 0.0 to 1.0
- contents: List[InventoryItem]  # if container
```

**CharacterInventory Class:**
```python
- slots: List[Optional[InventoryItem]]  # Always 8 slots
- get_total_weight()  # Calculates with reductions
- get_item_count()  # Includes container contents
- add_item_auto(item)  # Smart placement logic
```

### Container Methods
- `can_fit_item(item)`: Checks size and space
- `add_item(item)`: Adds to first empty slot
- `remove_item(index)`: Removes and returns item
- `get_effective_weight()`: Recursive weight calc
- `get_container_info()`: Capacity string

## Examples

### Starting Character (No Backpack)
**Slots 1-8:**
1. Long Sword (4 lbs)
2. Leather Armor (15 lbs)
3. Rations (7 lbs)
4. Rope (8 lbs)
5. Torches (6 lbs)
6. Waterskin (4 lbs)
7. Healing Potion (0.5 lbs)
8. `<empty>`

**Total Weight**: 44.5 lbs

### Character with Backpack
**Slots 1-8:**
1. Long Sword (4 lbs)
2. Leather Armor (15 lbs)
3. **Backpack** [7/10 slots] (effective: 18.85 lbs)
   - Rations (7 lbs)
   - Rope (8 lbs)
   - Torches (6 lbs)
   - Waterskin (4 lbs)
   - Healing Potion (0.5 lbs)
   - Belt Pouch [2/2 slots]
     - Thieves' Tools (1 lb)
     - Holy Symbol (0.5 lb)
4-8. `<empty>`

**Total Weight**: 37.85 lbs (vs 44.5 without backpack!)

### Advanced: Multiple Containers
**Slots 1-8:**
1. Bastard Sword
2. Chain Mail
3. Shield
4. Large Backpack [10/12 slots] (20% reduction)
   - Bedroll, Tent, Rope, etc.
5. Belt Pouch [2/2] (potions)
6. Large Sack [4/5] (food/water)
7. `<empty>`
8. `<empty>`

## Tips & Strategies

1. **Prioritize Backpacks**: Get the best backpack you can afford early
2. **Organize by Size**: Put large items in main slots if no backpack
3. **Nested Containers**: Small pouches can go inside backpacks
4. **Weight Management**: Use containers with high weight reduction for heavy items
5. **Quick Access**: Keep frequently used items (potions, tools) in main slots or small pouches
6. **Size Planning**: Know what fits where - don't buy a pouch for your sword!
7. **Magic Bags**: Bags of Holding are expensive but worth it for encumbrance

## Migration from Old System
Characters with the old list-based inventory will automatically convert:
- First 8 items go into main slots
- Remaining items attempt to go into any backpack present
- If no backpack or still overflow, items remain in conversion queue

## Future Expansion Ideas
- Quivers (arrow-specific containers)
- Spell component pouches
- Lockboxes (secure containers)
- Containers with special properties (fire resistance, preservation)
- Container crafting/upgrading
- Slot-specific equipment (belt, back, hands)
