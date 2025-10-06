# Container Navigation Flow

## Visual Guide to the New Container System

### Main Inventory View (Default)
```
═══════════════════════════════════════════════════════════════════════════
                    INVENTORY: Adventurer (8 Slots)
Gold: 50gp | Total Weight: 35.2 lbs | Total Items: 12
UP/DOWN: Navigate | ENTER: Open Container | ESC: Close
───────────────────────────────────────────────────────────────────────────
LEFT PANEL:                              RIGHT PANEL:
=== MAIN INVENTORY (8 SLOTS) ===        === ITEM DETAILS ===

> [1] Long Sword (4.0lb)                Name: Long Sword
  [2] Leather Armor (15.0lb)            Category: Weapons
  [3] Backpack [3/10 slots]             Size: medium
  [4] Belt Pouch [2/2 slots]            Weight: 4.0 lbs
  [5] Healing Potion (0.5lb)            Value: 15 gp
  [6] <empty>                            Damage: 1d8
  [7] <empty>
  [8] <empty>
═══════════════════════════════════════════════════════════════════════════
```

**Actions:**
- **UP/DOWN**: Select different main slots
- **ENTER** on slot 3: Opens the Backpack (see below)
- **1-8**: Jump to specific slot
- **ESC**: Close inventory

---

### Container View (After Pressing ENTER on Backpack)
```
═══════════════════════════════════════════════════════════════════════════
                    INVENTORY: Adventurer (8 Slots)
Gold: 50gp | Total Weight: 35.2 lbs | Total Items: 12
UP/DOWN: Navigate | ESC or LEFT: Back to main inventory
───────────────────────────────────────────────────────────────────────────
LEFT PANEL:                              RIGHT PANEL:
=== BACKPACK ===                         === ITEM DETAILS ===
Capacity: 3/10 slots
Max Item Size: large                     Name: Rope (50ft)
Weight Reduction: 15%                    Category: Gear
─────────────────────────────────────    Size: medium
> [1] Rope (50ft) (8.0lb)               Weight: 8.0 lbs
  [2] Rations (7 days) (7.0lb)          Value: 1 gp
  [3] Torches (6) (6.0lb)
  [4] <empty>
  [5] <empty>
  [6] <empty>
  [7] <empty>
  [8] <empty>
  [9] <empty>
  [10] <empty>
═══════════════════════════════════════════════════════════════════════════
```

**Actions:**
- **UP/DOWN**: Select different slots within the backpack
- **LEFT Arrow**: Return to main 8-slot view
- **ESC**: Return to main 8-slot view (first press), close inventory (second press)
- **1-8**: Jump to main slot (returns to main view)

---

## Navigation Summary

### Opening a Container
1. In main view, navigate to a container slot (e.g., Backpack in slot 3)
2. Press **ENTER**
3. Left panel **replaces** 8-slot view with container contents
4. All container slots are visible (empty and filled)

### Closing a Container
**Option 1:** Press **LEFT Arrow**
- Immediately returns to main 8-slot view

**Option 2:** Press **ESC**
- First press: Returns to main 8-slot view
- Second press: Closes entire inventory

### Benefits of This System
✅ **Focus**: Full attention on container contents when opened
✅ **Clarity**: All container slots visible at once
✅ **Efficiency**: LEFT arrow for quick back navigation
✅ **Consistency**: Same layout whether viewing main slots or container
✅ **Space**: More room to display container information

---

## Example Workflow: Finding a Potion in a Backpack

1. **Press I** → Inventory opens showing 8 main slots
2. **Navigate to slot 3** → Backpack is highlighted
3. **Press ENTER** → Left panel now shows all 10 backpack slots
4. **Navigate with UP/DOWN** → Find your healing potion in slot 7
5. **Press LEFT** → Return to main 8-slot view
6. **Press ESC** → Close inventory

---

## Multi-Level Containers (Future Feature)

The system supports containers within containers:

```
Main Inventory → Backpack [10 slots] → Small Pouch [3 slots]
     (8 slots)         Slot 5              Slot 2
```

**Navigation:**
- Slot 5 of Backpack contains a Small Pouch
- Press ENTER on the pouch → View pouch contents
- Press LEFT → Back to Backpack
- Press LEFT again → Back to Main Inventory

---

## Tips & Tricks

### Quick Container Access
- Remember which slot your backpack is in (e.g., slot 3)
- Press **3** from anywhere to highlight it
- Press **ENTER** to dive in

### Visual Scanning
- Empty slots appear dimmer (easier to spot open space)
- Filled slots show weight for quick comparison
- Container header shows capacity at a glance

### Weight Management
- Open your backpack to see effective weights
- Items in backpack weigh less (15% reduction shown in header)
- Total weight updates automatically

### Organization Strategy
- Keep frequently-used items in main slots (1-8)
- Store bulk supplies in your backpack
- Use small pouches for tiny items (potions, gems)
