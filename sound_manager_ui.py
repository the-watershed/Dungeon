"""Authoring tool for managing the game's sound library.

This utility presents a complete mouse-driven pygame UI for browsing, auditioning,
and editing sound assets declared in `sound_library.json`. It allows designers to
add/remove assets, attach new variants, and adjust metadata without touching code.
Supports import/export of MP3, WAV, and MIDI formats.

Features:
    - Fully mouse-navigable interface (no keyboard required)
    - Click-to-select assets and variants
    - Inline editing of all asset metadata (name, category, tags, description, etc.)
    - Import/export support for MP3, WAV, and MIDI files
    - Preview sounds directly in the UI
    - Variant management (add, edit, delete)
    - Filter assets by type
    - Auto-save on exit

Quick Start:
    - Run this file directly: python sound_manager_ui.py
    - Click assets to select them
    - Click buttons to perform actions
    - See SOUND_MANAGER_GUIDE.md for detailed documentation

Mouse Controls:
    - Click asset rows to select
    - Click variant rows to open full effects editor with sliders
    - Click buttons: Add Asset, Preview, Edit, Delete, Add Variant, Import, Export, Save
    - Hover over items to see highlights

Keyboard Shortcuts (optional):
    Up/Down or W/S    - Navigate asset list
    Left/Right or [/] - Cycle asset type filter
    Enter             - Preview selected sound
    Space             - Toggle music playback
    A                 - Add asset
    V                 - Add variant
    E                 - Edit asset metadata
    Delete            - Delete asset
    S                 - Save
    Esc               - Exit (auto-saves)

For complete documentation, see SOUND_MANAGER_GUIDE.md
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from typing import List, Optional, Tuple

import pygame

from sound_library import RESOURCES_ROOT, SoundAsset, SoundLibrary, SoundVariant

WINDOW_SIZE = (1200, 700)
FONT_NAME = "Consolas"
ASSET_TYPES = ["all", "effect", "ambient", "music", "procedural"]

# Common game event triggers - organized by category
COMMON_TRIGGERS = [
    # Discovery & Exploration
    "finding_secret",
    "discovering_treasure",
    "secret_door_revealed",
    "hidden_passage_found",
    "map_revealed",
    "area_discovered",
    
    # Doors & Containers
    "opening_door",
    "closing_door",
    "unlocking_chest",
    "chest_open",
    "chest_locked",
    "container_open",
    "gate_opening",
    "portcullis_raise",
    
    # Player Movement
    "player_footstep",
    "player_footstep_stone",
    "player_footstep_wood",
    "player_footstep_dirt",
    "player_footstep_water",
    "player_jump",
    "player_land",
    "player_run",
    "player_sneak",
    "player_swim",
    "player_climb",
    
    # Player Status
    "player_damage",
    "player_damage_critical",
    "player_death",
    "player_levelup",
    "player_heal",
    "player_poison",
    "player_cure",
    "player_resurrect",
    
    # Combat Actions
    "combat_hit",
    "combat_miss",
    "combat_critical",
    "combat_parry",
    "combat_block",
    "combat_dodge",
    "sword_swing",
    "axe_swing",
    "bow_shoot",
    "arrow_impact",
    "shield_bash",
    "backstab",
    
    # Enemy Events
    "enemy_spotted",
    "enemy_alert",
    "enemy_attack",
    "enemy_damage",
    "enemy_death",
    "enemy_flee",
    "boss_encounter",
    "boss_phase_change",
    "boss_defeated",
    
    # Magic & Spells
    "spell_cast",
    "spell_fizzle",
    "fireball_cast",
    "lightning_cast",
    "healing_cast",
    "teleport",
    "buff_applied",
    "debuff_applied",
    "enchant_item",
    
    # Items & Inventory
    "item_pickup",
    "item_drop",
    "item_equip",
    "item_unequip",
    "item_use",
    "item_break",
    "potion_drink",
    "scroll_read",
    "gold_collect",
    "gem_collect",
    
    # Interactions
    "lever_pull",
    "button_press",
    "switch_toggle",
    "crystal_activate",
    "altar_pray",
    "npc_talk",
    "merchant_greet",
    "quest_accept",
    "quest_complete",
    "quest_fail",
    
    # Traps & Hazards
    "trap_trigger",
    "trap_disarm",
    "trap_detect",
    "trap_failed_disarm",
    "spike_trap",
    "arrow_trap",
    "poison_gas",
    "floor_collapse",
    "explosion",
    "pit_trap",
    "boulder_trap",
    "flame_jet",
    
    # Dungeon-Specific Events
    "puzzle_start",
    "puzzle_solved",
    "puzzle_failed",
    "pressure_plate_step",
    "statue_move",
    "rune_activate",
    "glyph_trigger",
    "wall_slide",
    "ceiling_collapse",
    "flooding_starts",
    "darkness_spreads",
    "curse_applied",
    "blessing_received",
    
    # Creatures & Monsters
    "rat_squeak",
    "bat_screech",
    "spider_hiss",
    "skeleton_rattle",
    "zombie_groan",
    "ghost_wail",
    "dragon_roar",
    "slime_squelch",
    "wolf_howl",
    "mimic_reveal",
    "golem_stomp",
    "demon_laugh",
    
    # Dungeon Atmosphere
    "dungeon_ambient",
    "crypt_ambient",
    "cave_ambient",
    "sewer_ambient",
    "tomb_ambient",
    "catacomb_echo",
    "distant_scream",
    "ghostly_whisper",
    "ominous_chant",
    "dripping_blood",
    "bones_crunch",
    "torch_sputter",
    
    # Environment
    "water_splash",
    "water_drip",
    "fire_ignite",
    "fire_crackle",
    "wind_howl",
    "thunder",
    "rain",
    "door_creak",
    "chains_rattle",
    "metal_clang",
    "glass_shatter",
    "stone_grinding",
    "wood_splinter",
    "rope_snap",
    
    # UI & Menus
    "menu_open",
    "menu_close",
    "ui_click",
    "ui_hover",
    "ui_cancel",
    "ui_confirm",
    "page_turn",
    "inventory_open",
    "map_open",
    
    # Game Flow
    "level_start",
    "level_complete",
    "checkpoint_reach",
    "save_game",
    "load_game",
    "game_over",
    "victory",
    "defeat",
]

# UI Colors
COLOR_BG = (18, 18, 20)
COLOR_PANEL = (35, 35, 40)
COLOR_PANEL_DARK = (28, 28, 32)
COLOR_BORDER = (80, 80, 90)
COLOR_TEXT = (220, 220, 230)
COLOR_TEXT_DIM = (170, 170, 180)
COLOR_SELECTED = (255, 220, 120)
COLOR_HOVER = (60, 60, 70)
COLOR_BUTTON = (50, 100, 150)
COLOR_BUTTON_HOVER = (70, 120, 180)
COLOR_BUTTON_TEXT = (240, 240, 245)


class Button:
	"""Simple clickable button widget."""
	def __init__(self, rect: pygame.Rect, text: str, callback=None):
		self.rect = rect
		self.text = text
		self.callback = callback
		self.hovered = False
		
	def update(self, mouse_pos: Tuple[int, int]) -> None:
		self.hovered = self.rect.collidepoint(mouse_pos)
		
	def handle_click(self, mouse_pos: Tuple[int, int]) -> bool:
		if self.rect.collidepoint(mouse_pos):
			if self.callback:
				self.callback()
			return True
		return False
		
	def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
		color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON
		pygame.draw.rect(screen, color, self.rect)
		pygame.draw.rect(screen, COLOR_BORDER, self.rect, 1)
		text_surf = font.render(self.text, True, COLOR_BUTTON_TEXT)
		text_rect = text_surf.get_rect(center=self.rect.center)
		screen.blit(text_surf, text_rect)


class SoundManagerUI:
	def __init__(self) -> None:
		pygame.init()
		if not pygame.mixer.get_init():
			# Higher quality settings for better MP3 playback
			pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
		self.screen = pygame.display.set_mode(WINDOW_SIZE)
		pygame.display.set_caption("Dungeon Sound Library Manager")
		self.clock = pygame.time.Clock()
		self.font = pygame.font.SysFont(FONT_NAME, 18)
		self.font_small = pygame.font.SysFont(FONT_NAME, 14)

		self.library = SoundLibrary()
		if self.library.metadata_path.exists():
			self.library.load_from_disk()
		else:
			self.library.create_default_assets()
		self.assets: List[SoundAsset] = []
		self.selected_index = 0
		self.selected_variant_index = -1  # -1 means no variant selected
		self.filter_index = 0
		self.message = "Click variants to edit with sliders • Click assets to select • Use buttons to manage"
		self._refresh_filtered_assets()
		self._tk_root: Optional[tk.Tk] = None
		self.music_playing = False
		self._should_exit = False
		
		# UI state
		self.asset_rects: List[pygame.Rect] = []
		self.variant_rects: List[pygame.Rect] = []
		self.buttons: List[Button] = []
		self.mouse_pos = (0, 0)
		self._rebuild_ui()

	def run(self) -> None:
		self._should_exit = False
		running = True
		while running and not self._should_exit:
			self.mouse_pos = pygame.mouse.get_pos()
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self._attempt_exit()
					return
				elif event.type == pygame.KEYDOWN:
					running = self._handle_key(event.key)
				elif event.type == pygame.MOUSEBUTTONDOWN:
					if event.button == 1:  # Left click
						self._handle_click(event.pos)
			if self._should_exit or not running:
				break
			self._update()
			self._draw()
			pygame.display.flip()
			self.clock.tick(60)
		self._attempt_exit()
	
	def _update(self) -> None:
		"""Update button hover states."""
		for button in self.buttons:
			button.update(self.mouse_pos)
	
	def _handle_click(self, pos: Tuple[int, int]) -> None:
		"""Handle mouse clicks on UI elements."""
		# Check temporary variant buttons first
		if hasattr(self, '_temp_variant_buttons'):
			for button in self._temp_variant_buttons:
				if button.handle_click(pos):
					return
		
		# Check button clicks
		for button in self.buttons:
			if button.handle_click(pos):
				return
		
		# Check asset list clicks
		for idx, rect in enumerate(self.asset_rects):
			if rect.collidepoint(pos):
				self.selected_index = idx
				self.selected_variant_index = -1
				self._rebuild_ui()
				return
		
		# Check variant list clicks - open editor immediately
		for idx, rect in enumerate(self.variant_rects):
			if rect.collidepoint(pos):
				self.selected_variant_index = idx
				# Open effects editor immediately when clicking a variant
				self._edit_variant_via_dialog()
				return
	
	def _rebuild_ui(self) -> None:
		"""Rebuild button layout based on current state."""
		self.buttons.clear()
		
		# Main action buttons
		btn_y = WINDOW_SIZE[1] - 50
		btn_width = 95
		btn_height = 30
		btn_spacing = 8
		btn_x = 380
		
		self.buttons.append(Button(
			pygame.Rect(btn_x, btn_y, btn_width, btn_height),
			"Add Asset",
			self._add_asset_via_dialog
		))
		btn_x += btn_width + btn_spacing
		
		if self.assets:
			self.buttons.append(Button(
				pygame.Rect(btn_x, btn_y, btn_width, btn_height),
				"Preview",
				self._preview_selected
			))
			btn_x += btn_width + btn_spacing
			
			self.buttons.append(Button(
				pygame.Rect(btn_x, btn_y, btn_width, btn_height),
				"Edit",
				self._edit_metadata_via_dialog
			))
			btn_x += btn_width + btn_spacing
			
			self.buttons.append(Button(
				pygame.Rect(btn_x, btn_y, btn_width, btn_height),
				"Delete",
				self._delete_selected
			))
			btn_x += btn_width + btn_spacing
			
			self.buttons.append(Button(
				pygame.Rect(btn_x, btn_y, btn_width, btn_height),
				"Add Variant",
				self._add_variant_via_dialog
			))
			btn_x += btn_width + btn_spacing
			
			self.buttons.append(Button(
				pygame.Rect(btn_x, btn_y, btn_width, btn_height),
				"Import",
				self._import_sound
			))
			btn_x += btn_width + btn_spacing
			
			self.buttons.append(Button(
				pygame.Rect(btn_x, btn_y, btn_width, btn_height),
				"Export",
				self._export_sound
			))
		
		# Save button
		self.buttons.append(Button(
			pygame.Rect(WINDOW_SIZE[0] - 110, btn_y, btn_width, btn_height),
			"Save",
			self._save
		))

	def _handle_key(self, key: int) -> bool:
		if key == pygame.K_ESCAPE:
			return False
		elif key in (pygame.K_UP, pygame.K_w):
			self.selected_index = max(0, self.selected_index - 1)
			self.selected_variant_index = -1
			self._rebuild_ui()
		elif key in (pygame.K_DOWN, pygame.K_s):
			self.selected_index = min(len(self.assets) - 1, self.selected_index + 1)
			self.selected_variant_index = -1
			self._rebuild_ui()
		elif key in (pygame.K_LEFT, pygame.K_LEFTBRACKET):
			self.filter_index = (self.filter_index - 1) % len(ASSET_TYPES)
			self._refresh_filtered_assets()
		elif key in (pygame.K_RIGHT, pygame.K_RIGHTBRACKET):
			self.filter_index = (self.filter_index + 1) % len(ASSET_TYPES)
			self._refresh_filtered_assets()
		elif key == pygame.K_RETURN:
			self._preview_selected()
		elif key == pygame.K_SPACE:
			self._toggle_music()
		elif key == pygame.K_v:
			self._add_variant_via_dialog()
		elif key == pygame.K_DELETE:
			self._delete_selected()
		elif key == pygame.K_a:
			self._add_asset_via_dialog()
		elif key == pygame.K_e:
			self._edit_metadata_via_dialog()
		elif key == pygame.K_s:
			self._save()
		return True

	def _refresh_filtered_assets(self) -> None:
		filter_value = ASSET_TYPES[self.filter_index]
		if filter_value == "all":
			self.assets = sorted(self.library.list_assets(), key=lambda a: (a.asset_type, a.name))
		else:
			self.assets = sorted(self.library.list_assets(filter_value), key=lambda a: a.name)
		self.selected_index = min(self.selected_index, max(0, len(self.assets) - 1))

	def _draw(self) -> None:
		self.screen.fill(COLOR_BG)
		self._draw_header()
		self._draw_asset_list()
		self._draw_details()
		self._draw_footer()

	def _draw_header(self) -> None:
		title = self.font.render("Dungeon Sound Library Manager", True, COLOR_BUTTON_TEXT)
		self.screen.blit(title, (20, 20))
		filter_label = self.font.render(f"Filter: {ASSET_TYPES[self.filter_index].title()} (Use arrow keys or click)", True, COLOR_TEXT)
		self.screen.blit(filter_label, (20, 40))

	def _draw_asset_list(self) -> None:
		panel_rect = pygame.Rect(20, 60, 320, WINDOW_SIZE[1] - 140)
		pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect)
		pygame.draw.rect(self.screen, COLOR_BORDER, panel_rect, 1)

		self.asset_rects.clear()
		y = panel_rect.top + 10
		for index, asset in enumerate(self.assets):
			row_rect = pygame.Rect(panel_rect.left + 5, y, panel_rect.width - 10, 26)
			self.asset_rects.append(row_rect)
			
			is_selected = index == self.selected_index
			is_hovered = row_rect.collidepoint(self.mouse_pos)
			
			if is_selected:
				pygame.draw.rect(self.screen, COLOR_HOVER, row_rect)
			elif is_hovered:
				pygame.draw.rect(self.screen, COLOR_HOVER, row_rect)
			
			color = COLOR_SELECTED if is_selected else COLOR_TEXT
			text = self.font.render(f"{asset.name}", True, color)
			self.screen.blit(text, (row_rect.left + 5, row_rect.top + 2))
			meta = self.font_small.render(f"[{asset.asset_type}]", True, COLOR_TEXT_DIM)
			self.screen.blit(meta, (row_rect.right - 90, row_rect.top + 5))
			y += 28

	def _draw_details(self) -> None:
		panel_rect = pygame.Rect(360, 60, WINDOW_SIZE[0] - 380, WINDOW_SIZE[1] - 140)
		pygame.draw.rect(self.screen, COLOR_PANEL_DARK, panel_rect)
		pygame.draw.rect(self.screen, COLOR_BORDER, panel_rect, 1)

		if not self.assets:
			message = self.font.render("No assets loaded.", True, COLOR_TEXT)
			self.screen.blit(message, (panel_rect.left + 10, panel_rect.top + 10))
			return

		asset = self.assets[self.selected_index]
		lines = [
			f"Name: {asset.name}",
			f"Type: {asset.asset_type}",
			f"Category: {asset.category}",
			f"Tags: {', '.join(asset.tags) if asset.tags else '—'}",
			f"Triggers: {', '.join(asset.triggers) if asset.triggers else '—'}",
			f"Loop: {'Yes' if asset.loop else 'No'}",
			f"Stream: {'Yes' if asset.stream else 'No'}",
			f"Variants: {len(asset.variants)}",
			"",
			"Variants (click to select):"
		]
		y = panel_rect.top + 10
		for line in lines:
			text = self.font.render(line, True, COLOR_TEXT)
			self.screen.blit(text, (panel_rect.left + 10, y))
			y += 26
		
		# Draw variants as clickable rows
		self.variant_rects.clear()
		for idx, variant in enumerate(asset.variants):
			row_rect = pygame.Rect(panel_rect.left + 15, y, panel_rect.width - 30, 22)
			self.variant_rects.append(row_rect)
			
			is_selected = idx == self.selected_variant_index
			is_hovered = row_rect.collidepoint(self.mouse_pos)
			
			if is_selected:
				pygame.draw.rect(self.screen, COLOR_HOVER, row_rect)
			elif is_hovered:
				pygame.draw.rect(self.screen, (45, 45, 50), row_rect)
			
			color = COLOR_SELECTED if is_selected else COLOR_TEXT_DIM
			text = self.font_small.render(f"{idx+1}. {variant.file} (vol {variant.volume:.2f}, weight {variant.weight:.2f})", True, color)
			self.screen.blit(text, (row_rect.left + 5, row_rect.top + 2))
			y += 24
			
		# Add variant action buttons if a variant is selected
		if self.selected_variant_index >= 0 and self.selected_variant_index < len(asset.variants):
			y += 10
			
			# Show hint that clicking variant opens editor
			hint_text = self.font_small.render("(Click variant to edit)", True, COLOR_TEXT_DIM)
			self.screen.blit(hint_text, (panel_rect.left + 15, y))
			y += 20
			
			btn_rect = pygame.Rect(panel_rect.left + 15, y, 120, 25)
			del_btn = Button(btn_rect, "Delete Variant", lambda: self._delete_variant())
			del_btn.update(self.mouse_pos)
			del_btn.draw(self.screen, self.font_small)
			
			# Store these temporarily for click handling
			if not hasattr(self, '_temp_variant_buttons'):
				self._temp_variant_buttons = []
			self._temp_variant_buttons = [del_btn]
			y += 30
		else:
			if hasattr(self, '_temp_variant_buttons'):
				self._temp_variant_buttons = []
		
		if asset.description:
			wrap_lines = self._wrap_text(asset.description, panel_rect.width - 20)
			self.screen.blit(self.font.render("Description:", True, COLOR_TEXT), (panel_rect.left + 10, y + 10))
			y += 36
			for line in wrap_lines:
				self.screen.blit(self.font_small.render(line, True, COLOR_TEXT_DIM), (panel_rect.left + 10, y))
				y += 22

	def _draw_footer(self) -> None:
		footer_rect = pygame.Rect(20, WINDOW_SIZE[1] - 60, WINDOW_SIZE[0] - 40, 40)
		pygame.draw.rect(self.screen, COLOR_PANEL_DARK, footer_rect)
		pygame.draw.rect(self.screen, COLOR_BORDER, footer_rect, 1)
		message = self.font.render(self.message, True, COLOR_TEXT)
		self.screen.blit(message, (footer_rect.left + 10, footer_rect.top + 10))
		
		# Draw buttons
		for button in self.buttons:
			button.draw(self.screen, self.font_small)

	def _wrap_text(self, text: str, width: int) -> List[str]:
		words = text.split()
		s_lines: List[str] = []
		current = ""
		for word in words:
			candidate = f"{current} {word}".strip()
			if self.font.size(candidate)[0] > width and current:
				s_lines.append(current)
				current = word
			else:
				current = candidate
		if current:
			s_lines.append(current)
		return s_lines

	def _preview_selected(self) -> None:
		if not self.assets:
			return
		asset = self.assets[self.selected_index]
		if asset.asset_type == "music":
			self._toggle_music()
			return
		try:
			sound = self.library.load_sound(asset.name)
			sound.play()
			self.message = f"Previewing '{asset.name}'"
		except Exception as exc:
			self.message = f"Failed to preview: {exc}"

	def _toggle_music(self) -> None:
		if not self.assets:
			return
		asset = self.assets[self.selected_index]
		if asset.asset_type != "music":
			return
		if self.music_playing:
			pygame.mixer.music.stop()
			self.music_playing = False
			self.message = "Music stopped"
			return
		try:
			self.library.play_music(asset.name)
			self.music_playing = True
			self.message = f"Playing music '{asset.name}'"
		except Exception as exc:
			self.message = f"Failed to play music: {exc}"

	def _delete_selected(self) -> None:
		if not self.assets:
			return
		asset = self.assets[self.selected_index]
		if not self._confirm(f"Delete asset '{asset.name}'?"):
			return
		self.library.remove_asset(asset.name)
		self._refresh_filtered_assets()
		self.message = f"Deleted '{asset.name}'"

	def _add_asset_via_dialog(self) -> None:
		root = self._get_tk_root()
		file_path = filedialog.askopenfilename(
			title="Select sound file",
			filetypes=[("Audio", "*.wav *.mp3 *.ogg *.mid")]
		)
		if not file_path:
			return
		name = simpledialog.askstring("Asset Name", "Enter a unique asset name:", parent=root)
		if not name:
			return
		asset_type = self._ask_choice("Asset Type", ["effect", "ambient", "music", "procedural"], default="effect")
		if not asset_type:
			return
		category = simpledialog.askstring("Category", "Enter category: (default 'general')", parent=root) or "general"
		tags_input = simpledialog.askstring("Tags", "Enter comma-separated tags:", parent=root) or ""
		tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
		
		# Trigger assignment for new asset
		triggers = self._edit_triggers_via_dialog([], parent=root)
		
		volume = self._ask_float("Variant Volume", default=0.8)
		weight = self._ask_float("Variant Weight", default=1.0)
		loop = messagebox.askyesno("Loop", "Should this asset loop when played?", parent=root)
		stream = asset_type == "music"
		variant_file = self._mirror_to_resources(Path(file_path))
		asset = SoundAsset(
			name=name,
			asset_type=asset_type,
			category=category,
			tags=tags,
			variants=[SoundVariant(file=variant_file.name, original_file=Path(file_path).name, volume=volume, weight=weight)],
			loop=loop,
			stream=stream,
			triggers=triggers,
		)
		self.library.register_asset(asset, overwrite=False)
		self._refresh_filtered_assets()
		self.message = f"Added asset '{name}'"

	def _add_variant_via_dialog(self) -> None:
		if not self.assets:
			return
		asset = self.assets[self.selected_index]
		root = self._get_tk_root()
		
		# Ask if user wants to copy existing variant or import new file
		if asset.variants:
			result = messagebox.askyesnocancel(
				"Add Variant",
				"Copy existing sound for editing?\n\nYes = Copy existing variant\nNo = Import new file\nCancel = Abort",
				parent=root
			)
			
			if result is None:  # Cancel
				return
			elif result:  # Yes - Copy existing variant
				# Copy the first variant as template
				original_variant = asset.variants[0]
				
				# Create new variant copying all properties from the original
				variant = SoundVariant(
					file=original_variant.file,  # Reuse same file
					original_file=original_variant.original_file,
					storage_key=original_variant.storage_key,
					volume=original_variant.volume,
					weight=1.0,  # Default weight, user can adjust in editor
					pitch=original_variant.pitch,
					fade_in=original_variant.fade_in,
					fade_out=original_variant.fade_out,
					start_time=original_variant.start_time,
					end_time=original_variant.end_time,
					reverb=original_variant.reverb,
					lowpass=original_variant.lowpass,
					highpass=original_variant.highpass,
					distortion=original_variant.distortion,
				)
				self.library.add_variant(asset.name, variant)
				self._refresh_filtered_assets()
				# Auto-select the new variant and open editor
				self.selected_variant_index = len(asset.variants) - 1
				self.message = f"Added variant (copy) to '{asset.name}' - opening editor..."
				self._edit_variant_via_dialog()
				return
		
		# Import new file
		file_path = filedialog.askopenfilename(
			title="Select sound variant",
			filetypes=[("Audio", "*.wav *.mp3 *.ogg *.mid")]
		)
		if not file_path:
			return
		
		# Use default values - user can adjust in editor
		default_volume = asset.variants[0].volume if asset.variants else 0.8
		variant_path = self._mirror_to_resources(Path(file_path))
		variant = SoundVariant(
			file=variant_path.name,
			original_file=Path(file_path).name,
			volume=default_volume,
			weight=1.0,
		)
		self.library.add_variant(asset.name, variant)
		self._refresh_filtered_assets()
		# Auto-select the new variant and open editor
		self.selected_variant_index = len(asset.variants) - 1
		self.message = f"Added variant to '{asset.name}' - opening editor..."
		self._edit_variant_via_dialog()

	def _edit_metadata_via_dialog(self) -> None:
		if not self.assets:
			return
		asset = self.assets[self.selected_index]
		root = self._get_tk_root()
		
		# Asset name editing
		new_name = simpledialog.askstring("Asset Name", "Asset name:", initialvalue=asset.name, parent=root)
		if new_name and new_name != asset.name:
			# Check for duplicates
			if new_name in self.library.assets and new_name != asset.name:
				messagebox.showerror("Error", f"Asset '{new_name}' already exists", parent=root)
				return
			# Rename the asset
			self.library.assets.pop(asset.name)
			asset.name = new_name
			self.library.assets[new_name] = asset
		
		category = simpledialog.askstring("Category", "Category:", initialvalue=asset.category, parent=root)
		tags_input = simpledialog.askstring("Tags", "Comma-separated tags:", initialvalue=", ".join(asset.tags), parent=root)
		
		# Trigger assignment
		triggers_input = self._edit_triggers_via_dialog(asset.triggers, parent=root)
		
		description = simpledialog.askstring("Description", "Description:", initialvalue=asset.description, parent=root)
		loop = messagebox.askyesno("Loop", "Should this asset loop?", parent=root) if asset.asset_type != "effect" else asset.loop
		stream = messagebox.askyesno("Stream", "Stream via mixer.music?", parent=root) if asset.asset_type == "music" else asset.stream
		tags = [tag.strip() for tag in (tags_input or "").split(",") if tag.strip()]
		self.library.update_asset_metadata(
			asset.name,
			category=category or asset.category,
			tags=tags,
			description=description or asset.description,
			loop=loop,
			stream=stream,
			triggers=triggers_input,
		)
		self._refresh_filtered_assets()
		self.message = f"Updated metadata for '{asset.name}'"
	
	def _edit_triggers_via_dialog(self, current_triggers: List[str], parent=None) -> List[str]:
		"""Open a dialog to edit game event triggers for a sound."""
		root = parent or self._get_tk_root()
		
		# Create a custom dialog window
		dialog = tk.Toplevel(root)
		dialog.title("Assign Triggers")
		dialog.geometry("500x600")
		dialog.transient(root)
		
		tk.Label(dialog, text="Select game events that should trigger this sound:", 
		         font=("Arial", 10, "bold")).pack(pady=10)
		
		# Create scrollable frame for checkboxes
		canvas = tk.Canvas(dialog, height=400)
		scrollbar = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
		scrollable_frame = tk.Frame(canvas)
		
		scrollable_frame.bind(
			"<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
		)
		
		canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar.set)
		
		# Create checkboxes for each trigger
		trigger_vars = {}
		for trigger in COMMON_TRIGGERS:
			var = tk.BooleanVar(value=(trigger in current_triggers))
			trigger_vars[trigger] = var
			cb = tk.Checkbutton(scrollable_frame, text=trigger, variable=var, 
			                     anchor="w", font=("Arial", 9))
			cb.pack(fill="x", padx=20, pady=2)
		
		canvas.pack(side="left", fill="both", expand=True, padx=10)
		scrollbar.pack(side="right", fill="y")
		
		# Custom trigger entry
		tk.Label(dialog, text="Or enter custom triggers (comma-separated):").pack(pady=(10, 5))
		custom_entry = tk.Entry(dialog, width=60)
		custom_entry.pack(pady=5)
		
		# Pre-fill custom triggers not in common list
		custom_triggers = [t for t in current_triggers if t not in COMMON_TRIGGERS]
		if custom_triggers:
			custom_entry.insert(0, ", ".join(custom_triggers))
		
		# Result container
		selected_triggers = []
		
		def on_ok():
			# Collect selected common triggers
			for trigger, var in trigger_vars.items():
				if var.get():
					selected_triggers.append(trigger)
			
			# Add custom triggers
			custom = custom_entry.get().strip()
			if custom:
				custom_list = [t.strip() for t in custom.split(",") if t.strip()]
				selected_triggers.extend(custom_list)
			
			dialog.destroy()
		
		def on_cancel():
			selected_triggers.extend(current_triggers)
			dialog.destroy()
		
		# Buttons
		button_frame = tk.Frame(dialog)
		button_frame.pack(pady=10)
		tk.Button(button_frame, text="OK", command=on_ok, width=10).pack(side="left", padx=5)
		tk.Button(button_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=5)
		
		# Make dialog modal and wait (pygame updates handled by root window)
		dialog.transient(root)
		dialog.grab_set()
		dialog.focus_set()
		root.wait_window(dialog)
		
		return selected_triggers

	def _save(self) -> None:
		self.library.save_to_disk()
		self.message = "Library saved"

	def _attempt_exit(self) -> None:
		if self._should_exit:
			return
		self._should_exit = True
		self._save()
		if pygame.mixer.get_init():
			try:
				pygame.mixer.music.stop()
			except pygame.error:
				pass
		pygame.quit()
		self.library.cleanup()
		if self._tk_root is not None:
			self._tk_root.destroy()

	def _get_tk_root(self) -> tk.Tk:
		if self._tk_root is None:
			self._tk_root = tk.Tk()
			self._tk_root.withdraw()
		return self._tk_root

	def _mirror_to_resources(self, src: Path) -> Path:
		RESOURCES_ROOT.mkdir(parents=True, exist_ok=True)
		dest = RESOURCES_ROOT / src.name
		if not dest.exists():
			dest.write_bytes(src.read_bytes())
		return dest

	def _ask_choice(self, title: str, options: List[str], default: Optional[str] = None) -> Optional[str]:
		root = self._get_tk_root()
		choice = simpledialog.askstring(title, f"Enter option ({', '.join(options)}):", parent=root, initialvalue=default or options[0])
		if choice and choice.lower() in options:
			return choice.lower()
		return default

	def _ask_float(self, title: str, default: float = 1.0) -> float:
		root = self._get_tk_root()
		value_str = simpledialog.askstring(title, f"Enter value (default {default}):", parent=root)
		if not value_str:
			return default
		try:
			return float(value_str)
		except ValueError:
			return default

	def _confirm(self, message: str) -> bool:
		root = self._get_tk_root()
		return messagebox.askyesno("Confirm", message, parent=root)
	
	def _import_sound(self) -> None:
		"""Import a sound file into the selected asset as a new variant."""
		if not self.assets:
			return
		self._add_variant_via_dialog()
	
	def _export_sound(self) -> None:
		"""Export the selected asset/variant to a file."""
		if not self.assets:
			return
		asset = self.assets[self.selected_index]
		
		# Determine which variant to export
		if self.selected_variant_index >= 0 and self.selected_variant_index < len(asset.variants):
			variant = asset.variants[self.selected_variant_index]
		elif asset.variants:
			variant = asset.variants[0]
		else:
			self.message = "No variants to export"
			return
		
		root = self._get_tk_root()
		
		# Infer extension from variant
		extension = self._infer_variant_extension(variant)
		default_name = f"{asset.name}{extension}"
		
		file_types = [
			("All Audio", "*.wav *.mp3 *.mid"),
			("WAV files", "*.wav"),
			("MP3 files", "*.mp3"),
			("MIDI files", "*.mid"),
		]
		
		save_path = filedialog.asksaveasfilename(
			title="Export sound to...",
			defaultextension=extension,
			initialfile=default_name,
			filetypes=file_types,
			parent=root
		)
		
		if not save_path:
			return
		
		try:
			# Get the variant data
			audio_bytes = self.library._get_variant_bytes(asset, variant)
			Path(save_path).write_bytes(audio_bytes)
			self.message = f"Exported '{asset.name}' to {Path(save_path).name}"
		except Exception as exc:
			self.message = f"Export failed: {exc}"
			messagebox.showerror("Export Error", str(exc), parent=root)
	
	def _infer_variant_extension(self, variant: SoundVariant) -> str:
		"""Infer file extension from variant metadata."""
		for candidate in (variant.file, variant.original_file, variant.storage_key):
			if candidate:
				ext = Path(candidate).suffix
				if ext:
					return ext
		return ".wav"
	
	def _edit_variant_via_dialog(self) -> None:
		"""Edit the selected variant's properties including audio effects."""
		if not self.assets or self.selected_variant_index < 0:
			return
		asset = self.assets[self.selected_index]
		if self.selected_variant_index >= len(asset.variants):
			return
		variant = asset.variants[self.selected_variant_index]
		root = self._get_tk_root()
		
		# Create effects editor dialog
		dialog = tk.Toplevel(root)
		dialog.title(f"Edit Variant {self.selected_variant_index + 1} - {asset.name}")
		dialog.geometry("650x700")
		dialog.configure(bg="#2b2b2b")
		
		# Make dialog modal
		dialog.transient(root)
		
		# Results container
		results = {}
		
		# Main frame with scrollbar
		main_frame = tk.Frame(dialog, bg="#2b2b2b")
		main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
		
		canvas = tk.Canvas(main_frame, bg="#2b2b2b", highlightthickness=0)
		scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
		scrollable_frame = tk.Frame(canvas, bg="#2b2b2b")
		
		scrollable_frame.bind(
			"<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
		)
		
		canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar.set)
		
		canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
		
		# --- Basic Properties Section ---
		section_label = tk.Label(scrollable_frame, text="━━━ Basic Properties ━━━", 
								 font=("Consolas", 11, "bold"), bg="#2b2b2b", fg="#88ccff")
		section_label.pack(pady=(5, 10))
		
		# Volume slider
		self._create_slider(scrollable_frame, "Volume", variant.volume, 0.0, 2.0, results, "volume")
		
		# Weight slider
		self._create_slider(scrollable_frame, "Weight", variant.weight, 0.0, 10.0, results, "weight")
		
		# --- Audio Effects Section ---
		section_label = tk.Label(scrollable_frame, text="━━━ Audio Effects ━━━", 
								 font=("Consolas", 11, "bold"), bg="#2b2b2b", fg="#ffaa44")
		section_label.pack(pady=(15, 10))
		
		# Pitch shift
		self._create_slider(scrollable_frame, "Pitch Shift", variant.pitch, -12.0, 12.0, 
						   results, "pitch", tooltip="Semitones (-12 to +12)")
		
		# Distortion
		self._create_slider(scrollable_frame, "Distortion", variant.distortion, 0.0, 1.0,
						   results, "distortion", tooltip="0=clean, 1=maximum distortion")
		
		# --- Timing Section ---
		section_label = tk.Label(scrollable_frame, text="━━━ Timing & Fade ━━━", 
								 font=("Consolas", 11, "bold"), bg="#2b2b2b", fg="#88ff88")
		section_label.pack(pady=(15, 10))
		
		# Fade in
		self._create_slider(scrollable_frame, "Fade In", variant.fade_in, 0.0, 5.0,
						   results, "fade_in", tooltip="Seconds (0-5)")
		
		# Fade out
		self._create_slider(scrollable_frame, "Fade Out", variant.fade_out, 0.0, 5.0,
						   results, "fade_out", tooltip="Seconds (0-5)")
		
		# Start time
		self._create_slider(scrollable_frame, "Start Time", variant.start_time, 0.0, 10.0,
						   results, "start_time", tooltip="Playback start offset (seconds)")
		
		# End time
		self._create_slider(scrollable_frame, "End Time", variant.end_time, 0.0, 60.0,
						   results, "end_time", tooltip="Playback end cutoff (seconds, 0=full)")
		
		# --- Filter Section ---
		section_label = tk.Label(scrollable_frame, text="━━━ Filters ━━━", 
								 font=("Consolas", 11, "bold"), bg="#2b2b2b", fg="#ff88cc")
		section_label.pack(pady=(15, 10))
		
		# Low-pass filter
		self._create_slider(scrollable_frame, "Low-Pass Filter", variant.lowpass, 0.0, 22000.0,
						   results, "lowpass", tooltip="Cutoff frequency (Hz, 0=off)")
		
		# High-pass filter
		self._create_slider(scrollable_frame, "High-Pass Filter", variant.highpass, 0.0, 5000.0,
						   results, "highpass", tooltip="Cutoff frequency (Hz, 0=off)")
		
		# Reverb
		self._create_slider(scrollable_frame, "Reverb", variant.reverb, 0.0, 1.0,
						   results, "reverb", tooltip="Room effect (0=dry, 1=wet)")
		
		# --- Buttons ---
		button_frame = tk.Frame(dialog, bg="#2b2b2b")
		button_frame.pack(pady=10)
		
		def apply_changes() -> None:
			variant.volume = results.get("volume", variant.volume)
			variant.weight = results.get("weight", variant.weight)
			variant.pitch = results.get("pitch", variant.pitch)
			variant.distortion = results.get("distortion", variant.distortion)
			variant.fade_in = results.get("fade_in", variant.fade_in)
			variant.fade_out = results.get("fade_out", variant.fade_out)
			variant.start_time = results.get("start_time", variant.start_time)
			variant.end_time = results.get("end_time", variant.end_time)
			variant.lowpass = results.get("lowpass", variant.lowpass)
			variant.highpass = results.get("highpass", variant.highpass)
			variant.reverb = results.get("reverb", variant.reverb)
		
		save_btn = tk.Button(button_frame, text="Save", width=15,
						bg="#4a7c4a", fg="white", font=("Consolas", 10, "bold"))
		save_btn.pack(side=tk.LEFT, padx=5)
		
		cancel_btn = tk.Button(button_frame, text="Cancel", width=15,
							   bg="#7c4a4a", fg="white", font=("Consolas", 10, "bold"))
		cancel_btn.pack(side=tk.LEFT, padx=5)
		
		save_clicked = False
		status_message = "Variant edit cancelled"
		pump_active = True
		
		def close_dialog() -> None:
			nonlocal pump_active
			pump_active = False
			try:
				dialog.grab_release()
			except tk.TclError:
				pass
			if dialog.winfo_exists():
				dialog.destroy()
		
		def handle_save() -> None:
			nonlocal save_clicked, status_message
			save_clicked = True
			status_message = f"Updated variant {self.selected_variant_index + 1}"
			apply_changes()
			close_dialog()
		
		def handle_cancel() -> None:
			nonlocal save_clicked, status_message
			save_clicked = False
			status_message = "Variant edit cancelled"
			close_dialog()
		
		save_btn.config(command=handle_save)
		cancel_btn.config(command=handle_cancel)
		dialog.protocol("WM_DELETE_WINDOW", handle_cancel)
		dialog.transient(root)
		dialog.grab_set()
		dialog.focus_set()
		
		def pump_pygame() -> None:
			if not pump_active:
				return
			if self._should_exit:
				close_dialog()
				return
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					close_dialog()
					self._attempt_exit()
					return
			if self._should_exit:
				close_dialog()
				return
			self._draw()
			pygame.display.flip()
			self.clock.tick(60)
			dialog.after(33, pump_pygame)
		
		dialog.after(10, pump_pygame)
		root.wait_window(dialog)
		pump_active = False
		self.message = status_message
	
	def _create_slider(self, parent, label_text: str, initial_value: float, 
					  min_val: float, max_val: float, results: dict, key: str,
					  tooltip: str = "") -> None:
		"""Create a labeled slider control with value display."""
		frame = tk.Frame(parent, bg="#2b2b2b")
		frame.pack(fill=tk.X, pady=5)
		
		# Label
		label = tk.Label(frame, text=label_text, font=("Consolas", 9), 
						bg="#2b2b2b", fg="#dddddd", width=18, anchor="w")
		label.pack(side=tk.LEFT, padx=5)
		
		# Value display
		value_var = tk.DoubleVar(value=initial_value)
		value_label = tk.Label(frame, textvariable=value_var, font=("Consolas", 9, "bold"),
							   bg="#3a3a3a", fg="#ffff88", width=8, anchor="e")
		value_label.pack(side=tk.RIGHT, padx=5)
		
		# Slider
		slider = tk.Scale(frame, from_=min_val, to=max_val, resolution=0.01,
						 orient=tk.HORIZONTAL, variable=value_var, showvalue=False,
						 bg="#3a3a3a", fg="#dddddd", troughcolor="#1a1a1a",
						 highlightthickness=0, length=300)
		slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
		
		# Store result
		def on_change(val):
			results[key] = float(val)
		
		value_var.trace_add("write", lambda *args: on_change(value_var.get()))
		results[key] = initial_value
		
		# Tooltip
		if tooltip:
			tooltip_label = tk.Label(frame, text=f"  ℹ {tooltip}", font=("Consolas", 7),
									bg="#2b2b2b", fg="#888888")
			tooltip_label.pack(side=tk.LEFT, padx=2)
	
	def _delete_variant(self) -> None:
		"""Delete the selected variant from the current asset."""
		if not self.assets or self.selected_variant_index < 0:
			return
		asset = self.assets[self.selected_index]
		if self.selected_variant_index >= len(asset.variants):
			return
		
		if len(asset.variants) == 1:
			self.message = "Cannot delete last variant (delete asset instead)"
			return
		
		if not self._confirm(f"Delete variant {self.selected_variant_index + 1}?"):
			return
		
		del asset.variants[self.selected_variant_index]
		self.selected_variant_index = -1
		self.message = f"Deleted variant from '{asset.name}'"


def run_sound_manager() -> None:
	"""Convenience entry point."""
	ui = SoundManagerUI()
	ui.run()


if __name__ == "__main__":
	run_sound_manager()
