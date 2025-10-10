# Sound Manager UI - User Guide

## Overview

The Dungeon Sound Library Manager is a complete mouse-driven GUI for managing all sound assets in your game. It provides full control over sound metadata, variants, and supports importing/exporting MP3, WAV, and MIDI files.

## Features

### 🎯 Mouse-Driven Interface
- **Click to select** assets from the list
- **Click buttons** for all operations (no keyboard required)
- **Hover highlighting** for better navigation
- **Click variant rows** to edit individual sound variants

### 🎵 Asset Management
- **Add Assets**: Import new sound files with full metadata
- **Edit Assets**: Modify name, category, tags, description, loop, and stream settings
- **Delete Assets**: Remove unwanted sounds from the library
- **Preview**: Play sounds directly in the UI (Enter key or Preview button)

### 🎼 Variant Management
- **Add Variants**: Attach multiple sound files to a single asset for randomization
- **Edit Variants**: Adjust volume and weight for each variant
- **Delete Variants**: Remove specific variants while keeping the asset
- **Click-to-select**: Click any variant row to select it for editing

### 📥 Import/Export
- **Import**: Add new variants from external MP3, WAV, or MID files
- **Export**: Save any asset/variant to disk in its original format
- **Supported Formats**: MP3, WAV, MIDI (.mid)
- **Preserves Quality**: Exports maintain original audio encoding

### 🏷️ Metadata Editing
- **Asset Name**: Rename assets (with duplicate checking)
- **Category**: Organize sounds by category
- **Tags**: Add searchable tags for filtering
- **Triggers**: Assign game event triggers (e.g., "finding_secret", "combat_hit")
- **Description**: Document usage notes
- **Loop**: Mark sounds that should loop
- **Stream**: Enable streaming for large music files

### 🎯 Trigger System
- **Assign Triggers**: Link sounds to game events (30+ common triggers included)
- **Custom Triggers**: Add your own event names
- **Multiple Triggers**: One sound can respond to multiple events
- **Play by Trigger**: Game code can play sounds by trigger name
- **See**: SOUND_TRIGGER_GUIDE.md for complete trigger documentation

### 🔍 Filtering
- **Filter by Type**: All, Effect, Ambient, Music, Procedural
- **Keyboard Navigation**: Use arrow keys or [ ] to cycle filters

## Controls

### Mouse Controls
| Action | Method |
|--------|--------|
| Select asset | Click asset row in left panel |
| Select variant | Click variant row in details panel |
| Add asset | Click "Add Asset" button |
| Edit asset | Click "Edit" button (or press E) |
| Delete asset | Click "Delete" button (or press Delete) |
| Add variant | Click "Add Variant" button (or press V) |
| Import variant | Click "Import" button |
| Export asset | Click "Export" button |
| Preview sound | Click "Preview" button (or press Enter) |
| Save changes | Click "Save" button (or press S) |

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| Up/Down or W/S | Navigate asset list |
| Left/Right or [ ] | Cycle asset type filter |
| Enter | Preview selected sound |
| Space | Toggle music playback |
| A | Add new asset |
| V | Add variant to selected asset |
| E | Edit asset metadata |
| Delete | Delete selected asset |
| S | Save changes |
| Esc | Exit (auto-saves) |

## Workflow Examples

### Adding a New Sound Effect
1. Click **"Add Asset"** button
2. Browse and select your sound file (MP3, WAV, or MID)
3. Enter a unique asset name
4. Choose asset type (effect, ambient, music, procedural)
5. Enter category (e.g., "ui", "combat", "ambient")
6. Add tags (comma-separated)
7. Set volume and weight
8. Choose loop behavior
9. Asset is added to the library

### Editing Sound Metadata
1. Click on an asset in the list to select it
2. Click the **"Edit"** button
3. Modify asset name, category, tags, description
4. Adjust loop and stream settings
5. Click through the dialogs to save changes
6. Click **"Save"** to persist to disk

### Managing Variants
1. Select an asset from the list
2. Click a variant row in the details panel to select it
3. Click **"Edit Variant"** to adjust volume/weight
4. Click **"Delete Variant"** to remove it
5. Click **"Add Variant"** to attach additional sound files

### Exporting Sounds
1. Select an asset from the list
2. (Optional) Click a specific variant to export that one
3. Click the **"Export"** button
4. Choose save location and filename
5. File is saved in its original format (MP3, WAV, or MID)

### Importing Variants
1. Select an existing asset
2. Click **"Import"** or **"Add Variant"**
3. Browse for a sound file (MP3, WAV, MID)
4. Set volume and weight for the new variant
5. Variant is added to the asset

## File Formats

### Supported Input Formats
- **MP3**: Compressed audio (music, effects)
- **WAV**: Uncompressed audio (effects, short sounds)
- **MIDI (.mid)**: Music sequences (smaller file size)
- **OGG**: Compressed audio (effects, music)

### Export Formats
- **MP3**: Exports maintain original MP3 encoding
- **WAV**: Exports maintain original WAV format
- **MIDI**: Exports maintain original MIDI data

## Tips & Best Practices

### Asset Organization
- Use **categories** to group sounds: "ui", "combat", "ambient", "music"
- Add **tags** for easy searching: "click", "explosion", "footstep"
- Use **descriptions** to document usage: "Player melee hit sound for sword attacks"

### Variants
- Use **multiple variants** for variety (e.g., 5 different footstep sounds)
- Adjust **weight** to control frequency (higher = more common)
- Adjust **volume** per-variant for consistent loudness
- Keep **at least one variant** per asset (can't delete the last one)

### Performance
- Enable **stream** for large music files (reduces memory usage)
- Keep **loop** enabled for ambient and music tracks
- Use **MP3** for music (smaller files)
- Use **WAV** for short effects (better quality, instant playback)

### Workflow
- **Preview** sounds before saving to verify they're correct
- **Save often** to avoid losing changes
- Use **Import** to add variants from external sources
- Use **Export** to back up sounds or share with team

## Data Storage

### Files Created
- `sound_library.json`: Metadata manifest (human-readable)
- `sounds.snd`: Packed binary archive (contains all audio data)
- `resources/sounds/`: Individual sound files (imported assets)

### Auto-Save
The UI automatically saves when you exit (Esc or close window).
You can also manually save anytime with the **Save** button or **S** key.

## Troubleshooting

### "Asset already exists" Error
- Asset names must be unique
- Rename the asset when editing if needed

### "Cannot delete last variant"
- Each asset must have at least one variant
- Delete the entire asset instead if needed

### Preview Not Playing
- Check that pygame mixer is initialized
- Verify the sound file exists in resources/sounds/
- Music assets require pressing Space or clicking Preview

### Export Failed
- Ensure variant data is accessible
- Check that storage key exists in archive
- Verify write permissions for target directory

## Advanced Features

### Storage Keys
Each variant has an internal `storage_key` used in the binary archive.
These are automatically managed by the library.

### Procedural Assets
The "procedural" asset type is for generated sounds (not file-based).
These are handled programmatically in code, not via the UI.

### Weight-Based Randomization
When an asset has multiple variants, the library chooses one randomly
based on weight. Higher weight = more likely to play.

**Example:**
- Variant 1: weight 1.0 (50% chance)
- Variant 2: weight 1.0 (50% chance)
- Variant 3: weight 2.0 (twice as likely as others)

## Keyboard-Free Usage

You can operate the entire UI without touching the keyboard:
1. Use mouse to select assets and variants
2. Click buttons for all operations
3. Type in dialog boxes when they appear
4. No need to remember keyboard shortcuts!

Keyboard shortcuts are still available for power users who prefer them.

---

**Version:** 2.0  
**Last Updated:** 2025-10-09  
**Supported Formats:** MP3, WAV, MIDI (.mid), OGG  
**Platform:** Windows, Linux, macOS (via pygame)
