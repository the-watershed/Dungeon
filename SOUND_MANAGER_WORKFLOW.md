# Sound Manager - Streamlined Workflow Update

## What's New (v3.0)

### 🎯 One-Click Editing

**Before:** Multiple steps to edit a variant
1. Click variant to select it
2. Click "Edit Variant" button
3. Enter volume manually
4. Enter weight manually
5. Adjust other properties

**Now:** Instant access to full editor
1. **Click variant** → Full effects editor opens immediately!
2. All 11 parameters available as sliders
3. Adjust everything in one place
4. Click Save when done

### 🚀 Streamlined Add Variant Workflow

**Before:** Manual number entry for each property
1. Add Variant → Choose file or copy
2. Dialog: Enter volume
3. Dialog: Enter weight
4. Click Edit to adjust other properties

**Now:** Instant editor access
1. Add Variant → Choose file or copy
2. **Effects editor opens automatically!**
3. Adjust all properties with sliders
4. Click Save

### 📊 All Properties in One Editor

The effects editor now shows **everything** with sliders:

#### Basic Properties
- ⚙️ **Volume** (0.0 - 2.0)
- ⚙️ **Weight** (0.0 - 10.0)

#### Audio Effects
- 🎵 **Pitch Shift** (-12 to +12 semitones)
- 🔊 **Distortion** (0.0 - 1.0)

#### Timing & Fade
- ⏱️ **Fade In** (0-5 seconds)
- ⏱️ **Fade Out** (0-5 seconds)
- ⏱️ **Start Time** (0-10 seconds)
- ⏱️ **End Time** (0-60 seconds)

#### Filters
- 🎛️ **Low-Pass Filter** (0-22000 Hz)
- 🎛️ **High-Pass Filter** (0-5000 Hz)
- 🌊 **Reverb** (0.0 - 1.0)

## New UI Elements

### Variant List Hint
When a variant is selected, you'll see:
```
(Click variant to edit)
```

This reminds you that clicking the variant row opens the full editor.

### Status Bar Message
The bottom status bar now shows:
```
Click variants to edit with sliders • Click assets to select • Use buttons to manage
```

### Removed Buttons
- ❌ **"Edit Variant" button** - No longer needed! Just click the variant itself

### Kept Buttons
- ✅ **"Delete Variant"** - Still available when variant is selected
- ✅ All other buttons remain unchanged

## Workflow Examples

### Example 1: Create Pitch Variants

**Goal:** Make 3 pitch variations of a sword swing

1. Import sword_swing.wav as first variant
2. Click **"Add Variant"**
3. Choose **"Yes"** to copy
4. **Effects editor opens automatically**
5. Adjust **Pitch Shift**: -3 semitones
6. Click **Save**
7. Repeat steps 2-6 with pitch +2, +5

**Result:** 4 variants with different pitches, no manual typing required!

### Example 2: Edit Existing Variant

**Goal:** Add distortion to variant #2

1. **Click variant #2** in the list
2. **Effects editor opens immediately**
3. Adjust **Distortion** slider to 0.4
4. Click **Save**

**Result:** Distortion applied, done in 4 clicks!

### Example 3: Fine-Tune Volume Levels

**Goal:** Balance volume across all variants

1. **Click variant #1**
2. Adjust **Volume** slider to 0.9
3. Click **Save**
4. **Click variant #2**
5. Adjust **Volume** slider to 0.7
6. Click **Save**
7. Repeat for other variants

**Result:** All volumes balanced with visual feedback!

## Benefits

### ⚡ Faster
- No more modal dialogs for volume/weight
- No typing numbers manually
- One click to open editor

### 👁️ More Visual
- See all parameters at once
- Sliders show current values
- Real-time value updates

### 🎨 More Creative
- Easy to experiment with sliders
- Quick iterations
- Visual comparison of values

### 🧠 Less Mental Load
- Everything in one place
- No need to remember values
- Visual workflow instead of typing

## Technical Details

### Click Behavior Changes

**Variant Row Click:**
```python
# Before: Just selected the variant
self.selected_variant_index = idx

# Now: Selects AND opens editor
self.selected_variant_index = idx
self._edit_variant_via_dialog()
```

**Add Variant:**
```python
# Before: Asked for volume/weight separately
volume = self._ask_float("Variant Volume", ...)
weight = self._ask_float("Variant Weight", ...)

# Now: Uses defaults and opens editor
variant = SoundVariant(volume=default, weight=1.0, ...)
self._edit_variant_via_dialog()  # Opens immediately
```

### Auto-Selection on Add

When you add a variant, it's automatically selected and the editor opens:
```python
self.selected_variant_index = len(asset.variants) - 1
self._edit_variant_via_dialog()
```

## Migration Notes

### If You're Used to the Old Workflow

**Old Habit:** Click variant → Click "Edit Variant" button
**New Way:** Just click the variant once!

**Old Habit:** Add Variant → Type volume → Type weight → Click Edit
**New Way:** Add Variant → Editor opens automatically!

### Keyboard Users

The keyboard shortcuts still work:
- **E** - Edit asset metadata (not variant)
- **V** - Add variant (now opens editor automatically)
- **Delete** - Delete selected asset or variant

## Tips & Tricks

### Quick Variant Tweaking
1. Click variant
2. Adjust one slider
3. Click Save
4. Click next variant
5. Repeat

### Batch Volume Adjustment
Click through variants one by one, adjusting volume slider each time.

### Experimentation
Don't be afraid to move sliders around - you can always click Cancel to discard changes!

### Visual Feedback
The sliders show exact values in bold yellow on the right side.

## Troubleshooting

### Editor Opens When I Just Want to Select

**Issue:** Clicking a variant always opens the editor, but you just want to preview.

**Solution:** 
- Preview button works on selected asset (uses random variant)
- If you need to preview specific variant, open editor and click Cancel immediately

### How Do I Delete a Variant Now?

1. Click the variant (editor opens)
2. Click **Cancel** (editor closes)
3. Click **"Delete Variant"** button

**OR** easier:

1. Click the variant
2. Look for "Delete Variant" button that appears
3. Click it directly

## Performance Notes

- Opening editor is instant (no file loading)
- Sliders update smoothly at 30 FPS during editing
- Main UI runs at 60 FPS when not editing
- No performance impact from one-click workflow

## See Also

- `SOUND_EDITING_GUIDE.md` - Complete effects reference
- `SOUND_MANAGER_QUICKREF.md` - Quick reference guide
- `SOUND_TRIGGER_GUIDE.md` - Trigger system documentation
- `README.md` - Project overview
