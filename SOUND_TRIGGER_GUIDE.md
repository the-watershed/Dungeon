# Sound Trigger System Guide

## Overview

The Sound Trigger System allows you to assign game events (triggers) to sound assets, making it easy to play context-appropriate sounds in response to game events like "finding a secret", "opening a door", or "player taking damage".

## Features

### 🎯 Trigger Assignment
- Assign multiple triggers to each sound asset
- Choose from 30+ common game event triggers
- Add custom triggers for your specific game events
- View all assigned triggers in the asset details panel

### 🎮 Common Triggers

The system includes these pre-defined game event triggers:

#### Discovery & Exploration
- `finding_secret` - Player discovers a hidden area or secret
- `discovering_treasure` - Finding treasure or valuable items
- `unlocking_chest` - Opening a locked chest

#### Doors & Interaction
- `opening_door` - Door opening sound
- `closing_door` - Door closing sound
- `lever_pull` - Pulling a lever
- `button_press` - Pressing a button

#### Player Actions
- `player_footstep` - Footstep sounds
- `player_jump` - Jumping
- `player_land` - Landing after a jump
- `player_damage` - Taking damage
- `player_death` - Player death

#### Combat
- `enemy_spotted` - Enemy notices player
- `enemy_attack` - Enemy attacking
- `enemy_death` - Enemy defeated
- `combat_hit` - Successful hit
- `combat_miss` - Attack missed
- `combat_critical` - Critical hit

#### Items & Inventory
- `item_pickup` - Picking up an item
- `item_drop` - Dropping an item
- `item_equip` - Equipping an item
- `item_use` - Using/consuming an item

#### Magic & Abilities
- `spell_cast` - Casting a spell

#### Environment
- `trap_trigger` - Trap activated
- `water_splash` - Water interaction
- `fire_ignite` - Fire starting

#### UI & Menus
- `menu_open` - Menu opened
- `menu_close` - Menu closed
- `ui_click` - UI button click
- `ui_hover` - UI element hover

#### Game Flow
- `level_complete` - Level finished
- `game_over` - Game over screen

## Using Triggers in the UI

### Assigning Triggers to New Assets

1. Click **"Add Asset"** button
2. Select your sound file
3. Fill in basic metadata (name, type, category, tags)
4. A "Assign Triggers" dialog will appear
5. Check boxes for applicable game events
6. Or enter custom triggers in the text field (comma-separated)
7. Click **OK** to save

### Editing Triggers on Existing Assets

1. Select an asset from the list
2. Click the **"Edit"** button
3. After entering name/category/tags, the trigger dialog appears
4. Modify checkboxes or add/remove custom triggers
5. Click **OK** to save changes
6. The triggers list updates in the details panel

### Viewing Assigned Triggers

In the asset details panel, you'll see:
```
Triggers: finding_secret, discovering_treasure
```

If no triggers are assigned:
```
Triggers: —
```

## Using Triggers in Game Code

### Playing Sounds by Trigger

```python
from sound_library import get_sound_library

library = get_sound_library()

# When player finds a secret
library.play_trigger_sound("finding_secret")

# When player opens a door
library.play_trigger_sound("opening_door")

# When combat hit occurs
library.play_trigger_sound("combat_hit")
```

The `play_trigger_sound()` method will:
1. Find all assets with that trigger
2. Pick one randomly (if multiple exist)
3. Play it with appropriate method (sound vs. music)

### Finding Assets by Trigger

```python
# Get all sounds for a specific trigger
secret_sounds = library.get_assets_by_trigger("finding_secret")
print(f"Found {len(secret_sounds)} sounds for finding secrets")

for asset in secret_sounds:
    print(f"- {asset.name}")
```

### Multiple Sounds for One Trigger

You can assign the same trigger to multiple assets for variety:

**Example Setup:**
- `footstep_dirt_1` → triggers: `player_footstep`
- `footstep_dirt_2` → triggers: `player_footstep`
- `footstep_dirt_3` → triggers: `player_footstep`

When you call `library.play_trigger_sound("player_footstep")`, the system randomly picks one of the three variants, creating natural variation.

## Custom Triggers

### Adding Custom Triggers

You're not limited to the pre-defined triggers! Add your own:

1. In the trigger dialog, scroll to the bottom
2. Enter custom triggers in the text field: `dragon_roar, boss_phase_2, puzzle_solved`
3. Click **OK**

Custom triggers work exactly like built-in ones.

### Best Practices for Custom Triggers

- Use **snake_case** for consistency: `boss_encounter` not "Boss Encounter"
- Be **specific**: `wooden_door_open` vs. `door_open`
- Use **verbs** for actions: `explosion_occur`, `item_collect`
- Document your custom triggers in a separate file for team reference

## Workflow Examples

### Setting Up Discovery Sounds

**Goal:** Play exciting sounds when player finds secrets

1. Import 3 discovery sound effects
2. Name them: `discovery_1`, `discovery_2`, `discovery_3`
3. Set type to **effect**
4. Assign trigger: `finding_secret` to all three
5. In game code:
   ```python
   if player.discovered_secret():
       library.play_trigger_sound("finding_secret")
   ```

### Setting Up Footsteps

**Goal:** Different footstep sounds for different surfaces

1. Import footstep sounds
2. Create assets: `footstep_stone_1`, `footstep_wood_1`, `footstep_dirt_1`
3. Assign triggers:
   - Stone sounds → `player_footstep_stone`
   - Wood sounds → `player_footstep_wood`
   - Dirt sounds → `player_footstep_dirt`
4. In game code:
   ```python
   surface = player.get_current_surface()
   library.play_trigger_sound(f"player_footstep_{surface}")
   ```

### Setting Up Combat Sounds

**Goal:** Rich combat audio feedback

1. Create assets for:
   - `sword_hit_1`, `sword_hit_2` → `combat_hit`
   - `sword_miss_1` → `combat_miss`
   - `critical_impact` → `combat_critical`
   - `enemy_grunt_1`, `enemy_grunt_2` → `enemy_damage`
   
2. In combat system:
   ```python
   if attack.is_critical:
       library.play_trigger_sound("combat_critical")
   elif attack.hit:
       library.play_trigger_sound("combat_hit")
   else:
       library.play_trigger_sound("combat_miss")
   ```

## Tips & Best Practices

### Organization
- Use **triggers** for game events
- Use **tags** for sound characteristics ("wooden", "metal", "loud")
- Use **category** for asset organization ("combat", "ui", "ambient")

### Multiple Triggers per Asset
A single sound can have multiple triggers:
```
Asset: "wooden_creak"
Triggers: opening_door, closing_door, player_footstep_wood
```

This reuses sounds efficiently while maintaining context.

### Trigger Naming Conventions
- **Prefix with subject**: `player_jump`, `enemy_attack`
- **Use present participles**: `finding_secret` not `found_secret`
- **Be consistent**: If you use `player_footstep`, use `enemy_footstep` not `enemy_walking`

### Testing Triggers
1. Assign triggers in the sound manager
2. Preview sounds with the Preview button
3. Save the library
4. In game code, test with:
   ```python
   library.play_trigger_sound("your_trigger_name")
   ```

### Debugging
```python
# Check what sounds respond to a trigger
assets = library.get_assets_by_trigger("finding_secret")
if not assets:
    print("No sounds assigned to 'finding_secret' trigger!")
else:
    print(f"Found {len(assets)} sounds for this trigger")
```

## Data Storage

Triggers are stored in `sound_library.json`:

```json
{
  "name": "discovery_chime",
  "asset_type": "effect",
  "triggers": ["finding_secret", "discovering_treasure"],
  "variants": [...]
}
```

## Integration with Existing Systems

The trigger system is **backward compatible**:
- Existing assets without triggers work normally
- You can still play sounds by name: `library.play_sound("click_1")`
- Triggers are **optional** - use them where helpful

## Advanced Usage

### Conditional Trigger Selection

```python
# Play different sounds based on player health
if player.health < 20:
    library.play_trigger_sound("player_damage_critical")
else:
    library.play_trigger_sound("player_damage")
```

### Trigger Categories

Group related triggers:
```python
PLAYER_TRIGGERS = [
    "player_footstep",
    "player_jump",
    "player_land",
    "player_damage",
]

COMBAT_TRIGGERS = [
    "combat_hit",
    "combat_miss",
    "combat_critical",
]
```

### Random Trigger Pools

```python
# Play one of several related triggers
import random

discovery_triggers = ["finding_secret", "discovering_treasure", "unlocking_chest"]
trigger = random.choice(discovery_triggers)
library.play_trigger_sound(trigger)
```

## Troubleshooting

### Trigger Not Playing Sound
1. Check trigger spelling in both asset and code
2. Verify asset has the trigger assigned (check details panel)
3. Test with `get_assets_by_trigger("trigger_name")`
4. Ensure sound file exists and is valid

### Multiple Sounds Playing
If you have multiple assets with the same trigger, `play_trigger_sound()` picks ONE randomly. This is by design for variation.

To play all matching sounds:
```python
for asset in library.get_assets_by_trigger("explosion"):
    library.play_sound(asset.name)
```

### Trigger Not Saving
- Click the **Save** button or exit the UI (auto-saves)
- Check `sound_library.json` to verify triggers are persisted

---

**Version:** 2.0  
**Added:** 2025-10-09  
**Compatible with:** Sound Manager UI v2.0+
