# Sound Manager - Quick Reference

## Recent Fixes & Features

### Fixed: Dialog Lockup Issue (v2.0)

**Problem:** Opening the Effects Editor or Triggers dialog would cause the pygame window to freeze and become unresponsive.

**Solution:** Implemented a dual event loop that keeps both pygame and tkinter responsive simultaneously. The dialogs now use a flag-based approach instead of blocking calls.

**Technical Details:**
- Removed `root.withdraw()` which was causing issues
- Changed from `dialog.wait_window()` to custom loop with `dialog_open` flag
- Changed from `root.update()` to `dialog.update()` for better control
- Added comprehensive error handling with try-except blocks
- Added debug print statements for troubleshooting

### New Feature: Copy Variant for Editing

**Feature:** When adding a new variant, you can now copy the existing sound file instead of importing a new one.

**How It Works:**
1. Click **"Add Variant"** button
2. Dialog appears with 3 options:
   - **Yes** = Copy existing variant (reuses same audio file)
   - **No** = Import new audio file
   - **Cancel** = Abort operation

**Benefits:**
- No need to re-import the same audio file
- New variant inherits all properties from original (pitch, effects, etc.)
- Edit effects to create variations without duplicating files
- Faster workflow for creating multiple versions

**Example Use Cases:**
- Create high/low pitch variants (copy + adjust pitch)
- Add distortion variant (copy + increase distortion)
- Make fade variants (copy + adjust fade in/out)
- Create filtered versions (copy + apply lowpass/highpass)

## Usage Guide

### Adding Variants with Copy

**Scenario:** You want to create 3 variants of a sword swing with different pitches.

1. Import initial sword swing sound as first variant
2. Click **"Add Variant"**
3. Choose **"Yes"** to copy existing
4. Set volume and weight
5. Click variant to select it
6. Click **"Edit Variant"**
7. Adjust **Pitch Shift** to -2 semitones
8. Save
9. Repeat steps 2-8 for other pitches (+2, +4, etc.)

**Result:** Multiple pitch variants of the same sword swing, all using the same audio file but with different effects applied at playback.

### Editing Variants

**Before Opening Editor:**
- Make sure a variant is selected (click variant row in right panel)
- Verify the variant index shows in the status bar

**In Editor:**
- Scroll through all parameters
- Adjust sliders for desired effect
- Values update in real-time
- Click **"Save"** to apply (not the X button!)
- Click **"Cancel"** to discard changes

**Common Mistakes:**
- ❌ Closing dialog with X button (may not save properly)
- ❌ Not selecting a variant before clicking Edit
- ✅ Always use Save/Cancel buttons
- ✅ Select variant first, then click Edit Variant

## Troubleshooting

### Dialog Still Locks Up

**If the effects editor still freezes:**
1. Check console output for error messages
2. Force close: `Stop-Process -Name python -Force`
3. Look for these errors:
   - `TclError` - tkinter dialog closed unexpectedly
   - `Error in dialog loop` - pygame event processing issue

**Debugging:**
- Error messages now print to console
- Check for "Error in dialog loop: ..." messages
- Look for pygame or tkinter exceptions

### Variant Copy Not Working

**If copy variant doesn't work:**
- Make sure asset has at least one existing variant
- Check that variant has valid `file` or `storage_key`
- Verify resources folder contains the audio file

### Effects Not Applying

**If effects don't change sound:**
- Check file format (MP3 has limited effect support)
- WAV format recommended for full effect support
- Some effects require external libraries (pitch, reverb, filters)
- Volume, fade, distortion should work on all formats

## Technical Architecture

### Dialog Loop Pattern

```python
# Flag-based approach for responsive dialogs
dialog_open = [True]  # Use list for closure

def on_save():
    # Save logic
    dialog_open[0] = False
    dialog.destroy()

def on_cancel():
    dialog_open[0] = False
    dialog.destroy()

# Custom event loop
while dialog_open[0]:
    try:
        # Process pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                dialog_open[0] = False
                dialog.destroy()
                return
        
        # Redraw pygame
        self._draw()
        pygame.display.flip()
        self.clock.tick(30)
        
        # Update tkinter
        dialog.update()
    except tk.TclError:
        dialog_open[0] = False
        break
    except Exception as e:
        print(f"Error: {e}")
        dialog_open[0] = False
        break
```

### Variant Copy Implementation

```python
# Copy all properties from original variant
variant = SoundVariant(
    file=original_variant.file,  # Same audio file
    original_file=original_variant.original_file,
    storage_key=original_variant.storage_key,
    volume=volume,  # User specified
    weight=weight,  # User specified
    pitch=original_variant.pitch,  # Copy effects
    fade_in=original_variant.fade_in,
    fade_out=original_variant.fade_out,
    start_time=original_variant.start_time,
    end_time=original_variant.end_time,
    reverb=original_variant.reverb,
    lowpass=original_variant.lowpass,
    highpass=original_variant.highpass,
    distortion=original_variant.distortion,
)
```

## Performance Notes

- Main UI loop: 60 FPS (smooth)
- Dialog loop: 30 FPS (balanced)
- Copying variants: Instant (no file duplication)
- Memory efficient: Variants share audio data

## Future Enhancements

**Planned Improvements:**
- [ ] Batch variant creation (create 5 pitch variants at once)
- [ ] Real-time preview while adjusting sliders
- [ ] Visual waveform display
- [ ] Effect presets (quick apply common settings)
- [ ] Undo/redo for variant editing
- [ ] Duplicate variant button (copy selected variant)

## See Also

- `SOUND_EDITING_GUIDE.md` - Complete editing reference
- `SOUND_TRIGGER_GUIDE.md` - Trigger system documentation
- `SOUND_MANAGER_TECHNICAL.md` - Technical implementation details
- `README.md` - Project overview
