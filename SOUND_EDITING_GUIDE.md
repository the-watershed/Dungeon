# Sound Editing Guide

Complete reference for editing sound effects and assigning triggers in the dungeon crawler game.

## Overview

The sound manager now provides **full editing capabilities** for all audio properties, including:
- Volume and weight adjustments
- Audio effects (pitch, distortion, filters)
- Timing controls (fade in/out, start/end times)
- Trigger assignments for game events

## Audio Effects Parameters

### Basic Properties
- **Volume** (0.0 - 2.0): Playback volume multiplier
  - 0.0 = silent
  - 1.0 = normal
  - 2.0 = double volume
  
- **Weight** (0.0 - 10.0): Selection probability for random variants
  - Higher weight = more likely to play

### Pitch & Distortion
- **Pitch Shift** (-12 to +12 semitones): Changes the tone
  - Negative values = lower pitch
  - Positive values = higher pitch
  - Use for variation or creature sounds
  
- **Distortion** (0.0 - 1.0): Adds grit/noise
  - 0.0 = clean audio
  - 1.0 = maximum distortion
  - **Note:** Only applied to WAV files

### Timing Controls
- **Fade In** (0-5 seconds): Gradual volume increase at start
- **Fade Out** (0-5 seconds): Gradual volume decrease at end
- **Start Time** (0-10 seconds): Offset where playback begins
- **End Time** (0-60 seconds): Cutoff point for playback (0 = play full file)

### Filters
- **Low-Pass Filter** (0-22000 Hz): Cuts high frequencies
  - 0 = filter disabled
  - Lower values = muffle/underwater effect
  - Typical: 4000-8000 Hz for dampened sound
  
- **High-Pass Filter** (0-5000 Hz): Cuts low frequencies
  - 0 = filter disabled
  - Higher values = tinny/radio effect
  - Typical: 200-500 Hz for thin sound
  
- **Reverb** (0.0 - 1.0): Room/echo effect
  - 0.0 = dry (no reverb)
  - 1.0 = maximum room effect
  - **Note:** Advanced DSP - may require external libraries

## Using the Effects Editor

### Opening the Editor
1. Launch the sound manager: `python sound_manager_ui.py`
2. Click on a sound asset to select it
3. Click on a variant row (right panel) to select it
4. Click the **"Edit Variant"** button

### Editor Interface
The effects editor shows:
- **Scrollable list** of all parameters organized by category
- **Sliders** for precise value adjustment
- **Real-time value display** showing current setting
- **Tooltips** explaining each parameter
- **Save/Cancel** buttons at the bottom

### Workflow
1. Adjust sliders to desired values
2. Values update in real-time
3. Click **Save** to apply changes
4. Click **Cancel** to discard changes

## Trigger System

### Available Triggers (170+ total)

#### Discovery & Exploration
- `finding_secret` - Secret discovered
- `discovering_treasure` - Treasure found
- `secret_door_revealed` - Hidden door opens
- `hidden_passage_found` - Secret passage discovered
- `map_revealed` - Map area uncovered
- `area_discovered` - New location found

#### Dungeon-Specific Events
- `puzzle_start` - Puzzle begins
- `puzzle_solved` - Puzzle completed
- `puzzle_failed` - Wrong puzzle solution
- `pressure_plate_step` - Floor plate pressed
- `statue_move` - Statue shifts position
- `rune_activate` - Magical rune triggers
- `glyph_trigger` - Glyph activates
- `wall_slide` - Secret wall moves
- `ceiling_collapse` - Ceiling falls
- `flooding_starts` - Water rushes in
- `darkness_spreads` - Light fades
- `curse_applied` - Curse effect
- `blessing_received` - Blessing effect

#### Traps & Hazards
- `trap_trigger` - Generic trap activation
- `trap_disarm` - Successful trap disarm
- `trap_detect` - Trap spotted
- `trap_failed_disarm` - Failed disarm attempt
- `spike_trap` - Spikes emerge
- `arrow_trap` - Arrow fires
- `poison_gas` - Gas releases
- `floor_collapse` - Floor gives way
- `pit_trap` - Pit opens
- `boulder_trap` - Rolling boulder
- `flame_jet` - Fire burst

#### Creatures & Monsters
- `rat_squeak` - Rat sound
- `bat_screech` - Bat cry
- `spider_hiss` - Spider noise
- `skeleton_rattle` - Skeleton bones
- `zombie_groan` - Zombie moan
- `ghost_wail` - Ghost scream
- `dragon_roar` - Dragon roar
- `slime_squelch` - Slime movement
- `wolf_howl` - Wolf cry
- `mimic_reveal` - Mimic transforms
- `golem_stomp` - Golem footstep
- `demon_laugh` - Demon cackle

#### Dungeon Atmosphere
- `dungeon_ambient` - General dungeon background
- `crypt_ambient` - Tomb atmosphere
- `cave_ambient` - Cave sounds
- `sewer_ambient` - Sewer ambience
- `tomb_ambient` - Burial chamber
- `catacomb_echo` - Echo in catacombs
- `distant_scream` - Far-off scream
- `ghostly_whisper` - Ethereal voice
- `ominous_chant` - Ritual chanting
- `dripping_blood` - Blood drips
- `bones_crunch` - Bones breaking
- `torch_sputter` - Torch flickering

#### Combat & Player
- `combat_hit` - Attack lands
- `player_damage` - Player hurt
- `enemy_spotted` - Enemy sees player
- `boss_encounter` - Boss fight begins
- And 100+ more...

### Assigning Triggers

1. Click on an asset to select it
2. Click **"Edit Asset"** button
3. In the metadata dialog, click **"Edit Triggers"**
4. Check all triggers that should play this sound
5. Click **OK** to save

### Using Triggers in Code

```python
from sound_library import SoundLibrary

# Initialize
library = SoundLibrary()

# Play sound for specific trigger
library.play_trigger_sound("puzzle_solved")
library.play_trigger_sound("finding_secret")
library.play_trigger_sound("trap_trigger")

# Get all assets with a trigger
assets = library.get_assets_by_trigger("boss_encounter")
```

## Best Practices

### Effect Combinations

**Creature Sounds:**
- Use pitch shift (-3 to +3) for variation
- Add slight distortion (0.1-0.3) for aggression
- Low-pass filter (4000-6000 Hz) for distant sounds

**Environmental:**
- High reverb (0.6-0.8) for caves/large rooms
- Low reverb (0.2-0.4) for tight corridors
- Fade in (0.5-2s) for ambient loops

**Combat:**
- Quick fade out (0.1-0.3s) for impact sounds
- No fade in for instant response
- Slight distortion (0.1-0.2) for weapon hits

**UI Sounds:**
- Clean (no distortion)
- Short duration (trim with start/end time)
- Mid-range volume (0.6-0.8)

### Trigger Assignment

- **Be specific:** Use `spike_trap` instead of generic `trap_trigger` when possible
- **Multiple triggers:** Assign multiple triggers to versatile sounds
- **Variants:** Create multiple variants with different effects for variety
- **Weight:** Adjust weight to control how often variants play

### Performance Tips

- **WAV files:** Best for effects processing (supports all features)
- **MP3 files:** Load from disk (limited effect support)
- **MIDI files:** For music (no effects applied)
- **Distortion:** Only applies to WAV format
- **Filters:** May require additional libraries for full support

## Technical Notes

### Audio Format Support
- **WAV:** Full effect support, buffer-based loading
- **MP3/OGG:** File-based loading, limited effect support
- **MIDI:** Music playback, no effects

### Effect Implementation Status
✅ **Fully Implemented:**
- Volume control
- Weight-based selection
- Fade in/out
- Start/end time trimming
- Distortion (WAV only)

⚠️ **Partial Implementation:**
- Pitch shift (data structure ready, DSP pending)
- Reverb (data structure ready, DSP pending)
- Filters (data structure ready, DSP pending)

💡 **Note:** Advanced effects (pitch, reverb, filters) require external libraries like `scipy` or `librosa` for full implementation.

## Keyboard Shortcuts

When the sound manager is open:
- **E** - Edit selected variant
- **A** - Add new asset
- **V** - Add variant to selected asset
- **Delete** - Remove selected asset/variant
- **Enter** - Preview selected sound
- **S** - Save changes
- **Esc** - Exit (auto-saves)

## Examples

### Creating a Trap Sound
1. Import WAV file of spike trap
2. Add variant with:
   - Volume: 0.9
   - Distortion: 0.15 (metallic edge)
   - Fade out: 0.2s (quick end)
3. Assign triggers: `trap_trigger`, `spike_trap`
4. Add second variant with pitch +2 for variation

### Creating Boss Music
1. Import MIDI or MP3 file
2. Set category to "music"
3. Adjust volume: 0.7 (not too loud)
4. Fade in: 3.0s (dramatic entrance)
5. Assign triggers: `boss_encounter`, `boss_phase_change`

### Creating Ambient Loop
1. Import ambient sound (MP3 or WAV)
2. Set category to "ambient"
3. Configure:
   - Volume: 0.4 (background)
   - Fade in: 2.0s (smooth start)
   - Reverb: 0.5 (spatial feel)
4. Assign trigger: `dungeon_ambient`, `cave_ambient`

## Troubleshooting

**Sound plays as static:**
- Check file format (MP3 needs file-based loading)
- Reduce distortion value
- Verify mixer initialization (44100 Hz recommended)

**No sound plays:**
- Check volume setting (ensure > 0.0)
- Verify trigger assignment
- Check asset category matches playback method

**Effects don't apply:**
- WAV format recommended for full effect support
- MP3/OGG have limited effect processing
- Some effects require additional libraries

**Slider values don't save:**
- Ensure you click **Save** button
- Don't close dialog with X button
- Check for error messages in console

## See Also

- `SOUND_TRIGGER_GUIDE.md` - Comprehensive trigger reference
- `SOUND_MANAGER_GUIDE.md` - Manager interface documentation
- `README.md` - Project overview
