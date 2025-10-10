import os
import sys
import time
import random
import math
import re
from typing import Callable, List, Dict, Optional, Tuple

# Windows-specific: enable ANSI escape processing for colors/cursor control
msvcrt = None  # ensure defined on all platforms
if os.name == "nt":
	try:
		import msvcrt  # for non-blocking keyboard input
		import ctypes
		kernel32 = ctypes.windll.kernel32
		handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
		mode = ctypes.c_uint32()
		if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
			kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
	except Exception:
		msvcrt = None


# ---------------------------
# Config
# ---------------------------
import json


def load_settings(path: str) -> dict:
	"""Load game settings from JSON file with fallback to defaults.
	
	Args:
		path (str): Absolute or relative path to the settings JSON file
		
	Returns:
		dict: Dictionary containing all game settings. If file doesn't exist or
		      is malformed, returns default settings. Unknown keys are filtered out.
	"""
	defaults = {
		"floor": " ",
		"wall": "#",
		"player": "@",
		"dark": " ",  # outside light radius
		"hud_text": True,
		"map_style": "parchment",  # parchment | dark
		"dungeon_linearity": 1.0,  # 0.0 (chaotic) to 1.0 (linear)
		"dungeon_entropy": 0.0,   # 0.0 (no side rooms) to 1.0 (many side rooms)
		"dungeon_complexity": 0.0, # 0.0 to 1.0, adds extra connections
		"dungeon_length": 40,
		"dungeon_room_min": 3,
		"dungeon_room_max": 12,
		"dungeon_base_width": 60,  # base dungeon width
		"dungeon_base_height": 40,  # base dungeon height
		# Audio settings
		"music_volume": 0.7,  # 0.0 to 1.0
		"sound_volume": 0.8,  # 0.0 to 1.0
		"ambient_bats": True,
		"ambient_bat_interval_min": 15000,
		"ambient_bat_interval_max": 32000,
		"ambient_bat_volume_scale": 0.6,
		# Visual settings
		"show_gold_glow": True,  # Gold glow on fully searched areas
		"render_mode": "blocks",  # blocks | ascii
		"lighting_quality": "high",  # low | medium | high
		# Gameplay settings
		"auto_search": False,  # Automatically search when standing still
		"show_damage_numbers": True,  # Show damage/heal numbers
		"confirm_quit": True,  # Confirm before quitting
		"minimap": {
			"enabled": True,
			"tile": 4,        # pixels per dungeon tile on minimap
			"margin": 8,      # pixels from window edge
			"position": "top-right"  # top-left | top-right | bottom-left | bottom-right
		}
	}
	try:
		with open(path, 'r', encoding='utf-8') as f:
			data = json.load(f)
			if not isinstance(data, dict):
				return defaults
			# keep only known keys; ignore extras
			for k in list(data.keys()):
				if k not in defaults:
					data.pop(k)
			return {**defaults, **data}
	except Exception:
		return defaults


SETTINGS = load_settings(os.path.join(os.path.dirname(__file__), 'settings.json'))

FLOOR_CH = SETTINGS.get('floor', ' ')
WALL_CH = SETTINGS.get('wall', '#')
PLAYER_CH = SETTINGS.get('player', '@')
DARK_CH = SETTINGS.get('dark', ' ')

# Save directory
SAVE_DIR = os.path.join(os.path.dirname(__file__), 'saves')
LAST_CHARACTER_FILE = os.path.join(SAVE_DIR, 'last_character.json')

LIGHT_RADIUS = 5  # tiles
FPS = 30

# Pygame rendering base configuration
BASE_GRID_W = 100
BASE_GRID_H = 40
BASE_WIN_W = 1000
BASE_WIN_H = 600
BASE_CELL_W = BASE_WIN_W // BASE_GRID_W  # 10
BASE_CELL_H = BASE_WIN_H // BASE_GRID_H  # 15

# Parchment palette (RGB) and world palette
# Parchment remains for minimap; world uses dark background with brown tones
PARCHMENT_BG = (74, 71, 65)  # 3/10 brightness level
WORLD_BG = (32, 24, 16)        # dark brown background
WALL_LIGHT = (200, 170, 120)   # light brown for walls
FLOOR_MED = (140, 100, 60)     # medium brown for floors
WALL_BROWN = (140, 100, 60)    # kept for minimap
FLOOR_BROWN = (100, 75, 45)    # kept for minimap
INK_DARK = (40, 28, 18)        # for accents and text
PLAYER_GREEN = (60, 240, 90)   # bright green for player '@'
VOID_BG = (12, 12, 14)         # distinct background for outside dungeon

# New tile palette for block rendering (greys)
# Per request: walls very dark grey, floors light grey (slightly lighter)
FLOOR_DARK_GREY = (225, 225, 232)   # light grey floors
WALL_MED_GREY = (40, 40, 46)        # very dark grey walls
DIRT_BROWN = (110, 86, 60)       # dirt (reserved if needed later)
MOSS_GREEN = (72, 104, 74)
SAND_TAN = (196, 174, 120)
IRON_GREY = (110, 116, 122)
GRASS_GREEN = (86, 128, 74)
WATER_BLUE = (50, 110, 170)
LAVA_ORANGE = (208, 84, 32)
MARBLE_WHITE = (220, 220, 228)
WOOD_BROWN = (136, 94, 62)

# Torch rendering and lighting constants
TORCH_LIGHT_RADIUS = 3.0
TORCH_BASE_INTENSITY = 0.9
TORCH_FLAME_COLOR = (255, 196, 112)
TORCH_EMBER_COLOR = (255, 140, 60)
TORCH_SCONCE_COLOR = (120, 90, 60)

# Material -> base color mapping (render-agnostic; used by all renderers)
def base_color_for_material(mat: int) -> tuple[int, int, int]:
	"""Get the base RGB color for a material type.
	
	Args:
		mat (int): Material constant (MAT_BRICK, MAT_DIRT, etc.)
		
	Returns:
		tuple[int, int, int]: RGB color tuple (0-255 range)
	"""
	if mat == MAT_BRICK:
		return WALL_MED_GREY
	if mat == MAT_DIRT:
		return DIRT_BROWN
	if mat == MAT_MOSS:
		return MOSS_GREEN
	if mat == MAT_SAND:
		return SAND_TAN
	if mat == MAT_IRON:
		return IRON_GREY
	if mat == MAT_GRASS:
		return GRASS_GREEN
	if mat == MAT_WATER:
		return WATER_BLUE
	if mat == MAT_LAVA:
		return LAVA_ORANGE
	if mat == MAT_MARBLE:
		return MARBLE_WHITE
	if mat == MAT_WOOD:
		return WOOD_BROWN
	# default floors
	return FLOOR_DARK_GREY

def lit_color_for_material(mat: int, t: float) -> tuple[int, int, int]:
	"""Get the illuminated color for a material based on distance from light source.
	
	Args:
		mat (int): Material constant (MAT_BRICK, MAT_DIRT, etc.)
		t (float): Light intensity factor [0,1], where 1 is closest to player
		
	Returns:
		tuple[int, int, int]: RGB color tuple brightened based on light intensity
	"""
	# t in [0,1], near 1 close to player
	base = base_color_for_material(mat)
	if mat == MAT_BRICK or mat == MAT_IRON:
		f = 0.6 + 0.4 * t  # Darker materials get less brightness variation
	elif mat == MAT_WATER:
		f = 0.5 + 0.3 * t  # Water has moderate brightness range
	else:
		f = 0.45 + 0.35 * t  # Default materials have standard brightness range
	return scale_color(base, f)

def dimmed_color_for_material(mat: int, alpha: float) -> tuple[int, int, int]:
	"""Calculate fog-of-war dimmed color for a material.
	
	Use per-material scale ranges so walls are much darker than floors when
	revealed-but-not-visible (explored but outside current light radius).
	
	Args:
		mat (int): Material constant (MAT_BRICK, MAT_DIRT, etc.)
		alpha (float): Reveal progress [0,1] where 1 is fully revealed
		
	Returns:
		tuple[int, int, int]: RGB color tuple dimmed for fog-of-war effect
	"""
	base = base_color_for_material(mat)

	def fow_scale_for_material(m: int, a: float) -> float:
		"""Calculate fog-of-war brightness scaling factor for a material.
		
		Args:
			m (int): Material constant
			a (float): Alpha value [0,1] for reveal progress
			
		Returns:
			float: Scaling factor for color brightness in fog-of-war
		"""
		a = clamp(a, 0.0, 1.0)
		# Nearly black for walls/iron bars (very dark FoW)
		if m == MAT_BRICK or m == MAT_IRON:
			s_min, s_max = 0.03, 0.10
		elif m == MAT_WATER:
			s_min, s_max = 0.04, 0.12
		elif m in (MAT_LAVA, MAT_MARBLE, MAT_WOOD, MAT_SAND, MAT_MOSS, MAT_DIRT, MAT_GRASS):
			# Non-wall surfaces (treat like floors, very dark FoW)
			s_min, s_max = 0.12, 0.22
		else:
			# Default floors (e.g., cobble, very dark FoW)
			s_min, s_max = 0.12, 0.22
		return s_min + a * (s_max - s_min)

	scale = fow_scale_for_material(mat, alpha)
	return scale_color(base, scale)

def scale_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
	"""Scale RGB color by a brightness factor.
	
	Args:
		color (tuple[int, int, int]): Original RGB color tuple
		factor (float): Scaling factor [0,1] where 0 is black, 1 is original color
		
	Returns:
		tuple[int, int, int]: Scaled RGB color tuple, clamped to [0,255]
	"""
	f = max(0.0, min(1.0, factor))
	r = min(255, int(color[0] * f))
	g = min(255, int(color[1] * f))
	b = min(255, int(color[2] * f))
	return (r, g, b)

def lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], a: float) -> tuple[int, int, int]:
	"""Linear interpolation between two RGB colors.
	
	Args:
		c1 (tuple[int, int, int]): Start color RGB tuple
		c2 (tuple[int, int, int]): End color RGB tuple  
		a (float): Interpolation factor [0,1] where 0 returns c1, 1 returns c2
		
	Returns:
		tuple[int, int, int]: Interpolated RGB color tuple
	"""
	a = clamp(a, 0.0, 1.0)
	return (
		int(c1[0] + (c2[0] - c1[0]) * a),
		int(c1[1] + (c2[1] - c1[1]) * a),
		int(c1[2] + (c2[2] - c1[2]) * a),
	)


def get_term_size() -> tuple[int, int]:
	"""Get terminal window size in characters.
	
	Returns:
		tuple[int, int]: (columns, rows) of terminal window. Falls back to (80, 25)
		                 if unable to determine actual size.
	"""
	try:
		import shutil
		size = shutil.get_terminal_size(fallback=(80, 25))
		return size.columns, size.lines
	except Exception:
		return 80, 25


def clamp(v: float, a: float, b: float) -> float:
	"""Clamp a value between minimum and maximum bounds.
	
	Args:
		v (float): Value to clamp
		a (float): Minimum bound
		b (float): Maximum bound
		
	Returns:
		float: Value clamped to range [a, b]
	"""
	return max(a, min(b, v))


from dungeon_gen import Dungeon, Rect, TILE_WALL, TILE_FLOOR, generate_dungeon, MAT_COBBLE, MAT_BRICK, MAT_DIRT, MAT_MOSS, MAT_SAND, MAT_IRON, MAT_GRASS, MAT_WATER, MAT_LAVA, MAT_MARBLE, MAT_WOOD, TILE_DOOR, DOOR_CLOSED, DOOR_OPEN, DOOR_LOCKED
from prefab_loader import load_prefabs
from parchment_renderer import ParchmentRenderer
from sounds import get_sound_generator, get_water_drip_sfx
from music import get_music_player
# ---------------------------
# Save/Load helpers
# ---------------------------
def encode_tiles(dungeon: 'Dungeon') -> list[str]:
	"""Encode dungeon tiles into a list of strings for serialization.
	
	Args:
		dungeon (Dungeon): The dungeon object to encode
		
	Returns:
		list[str]: List of strings where each string represents a row,
		           with '0' for floors and '1' for walls
	"""
	# rows as strings of '0' floor and '1' wall
	rows = []
	for y in range(dungeon.h):
		row = ['1' if dungeon.tiles[x][y] == TILE_WALL else '0' for x in range(dungeon.w)]
		rows.append(''.join(row))
	return rows


def decode_tiles(rows: list[str]) -> 'Dungeon':
	"""Decode strings back into a Dungeon object.
	
	Args:
		rows (list[str]): List of strings where each represents a row,
		                  with '0' for floors and '1' for walls
		                  
	Returns:
		Dungeon: Reconstructed dungeon object with tiles set from encoded data
	"""
	h = len(rows)
	w = len(rows[0]) if h > 0 else 0
	d = Dungeon(w, h)
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			d.tiles[x][y] = TILE_WALL if ch == '1' else TILE_FLOOR
	return d

def encode_materials(dungeon: 'Dungeon') -> list[str]:
	"""Encode dungeon materials into a list of strings for serialization.
	
	Args:
		dungeon (Dungeon): The dungeon object whose materials to encode
		
	Returns:
		list[str]: List of strings where each string represents a row,
		           with single digit characters representing material types
	"""
	rows = []
	for y in range(dungeon.h):
		row = [str(dungeon.materials[x][y]) for x in range(dungeon.w)]
		rows.append(''.join(row))
	return rows

def decode_materials(dungeon: 'Dungeon', rows: list[str]) -> 'Dungeon':
	"""Decode material strings back into a Dungeon object's material grid.
	
	Args:
		dungeon (Dungeon): The dungeon object to update with materials
		rows (list[str]): List of strings where each represents a row,
		                  with single digits representing material types
		                  
	Returns:
		Dungeon: The same dungeon object with materials updated
	"""
	if not rows:
		return dungeon
	for y, row in enumerate(rows):
		if y >= dungeon.h:
			break
		for x, ch in enumerate(row):
			if x >= dungeon.w:
				break
			try:
				dungeon.materials[x][y] = int(ch)
			except Exception:
				pass
	return dungeon


# Reachability and exposed wall helpers
from collections import deque

def compute_reachable_floors(d: Dungeon, start_x: int, start_y: int) -> set[tuple[int, int]]:
	"""Find all floor tiles reachable from a starting position via flood fill.
	
	Uses 4-directional connectivity (up/down/left/right) to determine reachability.
	If the starting position is not a floor, searches nearby for the closest floor.
	
	Args:
		d (Dungeon): The dungeon to analyze
		start_x (int): Starting X coordinate
		start_y (int): Starting Y coordinate
		
	Returns:
		set[tuple[int, int]]: Set of (x, y) coordinates of all reachable floor tiles
	"""
	reachable = set()
	if not (0 <= start_x < d.w and 0 <= start_y < d.h):
		return reachable
	if d.tiles[start_x][start_y] != TILE_FLOOR:
		# find nearest floor within a small radius
		for r in range(1, 8):
			found = False
			for dx in range(-r, r + 1):
				for dy in range(-r, r + 1):
					x, y = start_x + dx, start_y + dy
					if 0 <= x < d.w and 0 <= y < d.h and d.tiles[x][y] == TILE_FLOOR:
						start_x, start_y = x, y
						found = True
						break
				if found:
					break
			if found:
				break
		if d.tiles[start_x][start_y] != TILE_FLOOR:
			return reachable
	q = deque()
	q.append((start_x, start_y))
	reachable.add((start_x, start_y))
	while q:
		x, y = q.popleft()
		for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
			nx, ny = x + dx, y + dy
			if 0 <= nx < d.w and 0 <= ny < d.h:
				if d.tiles[nx][ny] == TILE_FLOOR and (nx, ny) not in reachable:
					reachable.add((nx, ny))
					q.append((nx, ny))
	return reachable

def count_total_exposed_walls(d: Dungeon, reachable_floors: set[tuple[int, int]] | None = None) -> int:
	"""Count wall tiles that are adjacent to at least one floor tile.
	
	Args:
		d (Dungeon): The dungeon to analyze
		reachable_floors (set[tuple[int, int]], optional): If provided, only count
		                  walls exposed to reachable floor tiles. If None, count
		                  walls exposed to any floor tile.
		                  
	Returns:
		int: Number of wall tiles that have at least one adjacent floor tile
	"""
	total = 0
	for y in range(d.h):
		for x in range(d.w):
			if d.tiles[x][y] != TILE_WALL:
				continue
			exposed = False
			for dy in (-1, 0, 1):
				for dx in (-1, 0, 1):
					if dx == 0 and dy == 0:
						continue
					nx, ny = x + dx, y + dy
					if 0 <= nx < d.w and 0 <= ny < d.h and d.tiles[nx][ny] == TILE_FLOOR:
						if reachable_floors is None or (nx, ny) in reachable_floors:
							exposed = True
							break
				if exposed:
					break
			if exposed:
				total += 1
	return total


def count_total_exposed_bricks(d: Dungeon, reachable_floors: set[tuple[int, int]] | None = None) -> int:
	"""Count exposed brick walls (MAT_BRICK) adjacent to at least one floor tile.
	
	Args:
		d (Dungeon): The dungeon to analyze
		reachable_floors (set[tuple[int, int]], optional): If provided, only count
		                  brick walls exposed to reachable floor tiles. If None,
		                  counts exposed to any floor (not recommended for gating).
		                  
	Returns:
		int: Number of brick wall tiles that have at least one adjacent floor tile
	"""
	total = 0
	for y in range(d.h):
		for x in range(d.w):
			if d.tiles[x][y] != TILE_WALL:
				continue
			if d.materials[x][y] != MAT_BRICK:
				continue
			exposed = False
			for dy in (-1, 0, 1):
				for dx in (-1, 0, 1):
					if dx == 0 and dy == 0:
						continue
					nx, ny = x + dx, y + dy
					if 0 <= nx < d.w and 0 <= ny < d.h and d.tiles[nx][ny] == TILE_FLOOR:
						if reachable_floors is None or (nx, ny) in reachable_floors:
							exposed = True
							break
				if exposed:
					break
			if exposed:
				total += 1
	return total

def count_exposed_bricks_touched(d: Dungeon, touched: set[tuple[int,int]], reachable_floors: set[tuple[int,int]]) -> int:
	"""Count how many touched brick walls are exposed to reachable floor tiles.
	
	Safe against overcounting; processes all touched coordinates and validates
	that they are still valid brick walls exposed to reachable floors.
	
	Args:
		d (Dungeon): The dungeon to analyze
		touched (set[tuple[int,int]]): Set of (x,y) coordinates that have been touched
		reachable_floors (set[tuple[int,int]]): Set of reachable floor coordinates
		
	Returns:
		int: Number of touched brick walls that are exposed to reachable floors
	"""
	if not touched:
		return 0
	cnt = 0
	for (bx, by) in touched:
		if not (0 <= bx < d.w and 0 <= by < d.h):
			continue
		if d.tiles[bx][by] != TILE_WALL:
			continue
		if d.materials[bx][by] != MAT_BRICK:
			continue
		exposed = False
		for dy in (-1, 0, 1):
			for dx in (-1, 0, 1):
				if dx == 0 and dy == 0:
					continue
				nx, ny = bx + dx, by + dy
				if 0 <= nx < d.w and 0 <= ny < d.h and d.tiles[nx][ny] == TILE_FLOOR and (nx, ny) in reachable_floors:
					exposed = True
					break
			if exposed:
				break
		if exposed:
			cnt += 1
	return cnt

def count_total_bricks(d: Dungeon) -> int:
	"""Count total number of brick wall tiles in the dungeon.
	
	Args:
		d (Dungeon): The dungeon to analyze
		
	Returns:
		int: Total count of wall tiles with MAT_BRICK material
	"""
	total = 0
	for y in range(d.h):
		for x in range(d.w):
			try:
				if d.tiles[x][y] == TILE_WALL and d.materials[x][y] == MAT_BRICK:
					total += 1
			except Exception:
				continue
	return total

def count_total_walls(d: Dungeon) -> int:
	"""Count total number of wall tiles in the dungeon.
	
	Args:
		d (Dungeon): The dungeon to analyze
		
	Returns:
		int: Total count of wall tiles regardless of material
	"""
	total = 0
	for y in range(d.h):
		for x in range(d.w):
			if d.tiles[x][y] == TILE_WALL:
				total += 1
	return total

def count_total_floors(d: Dungeon) -> int:
	"""Count total number of floor tiles in the dungeon.
	
	Args:
		d (Dungeon): The dungeon to analyze
		
	Returns:
		int: Total count of floor tiles regardless of material
	"""
	total = 0
	for y in range(d.h):
		for x in range(d.w):
			if d.tiles[x][y] == TILE_FLOOR:
				total += 1
	return total


def session_to_dict(dungeon: 'Dungeon', explored: set, px: int, py: int, levels: list | None = None, current_index: int = 0) -> dict:
	"""Convert current game session to a dictionary for serialization.
	
	Args:
		dungeon (Dungeon): Current dungeon state
		explored (set): Set of explored tile coordinates
		px (int): Player X coordinate
		py (int): Player Y coordinate
		levels (list, optional): List of level data. If None, creates from current dungeon
		current_index (int): Index of current level in levels list
		
	Returns:
		dict: Dictionary containing all session data ready for JSON serialization
	"""
	if levels is None:
		levels = []
	# include current dungeon as level 0 if levels is empty
	if not levels:
		levels = [{
			'w': dungeon.w,
			'h': dungeon.h,
			'tiles': encode_tiles(dungeon),
			'explored': list(sorted(explored)),
			'materials': encode_materials(dungeon),
			'player': [px, py],
		}]
		current_index = 0
	data = {
		'current_index': current_index,
		'levels': levels,
	}
	return data


def dict_to_session(data: dict) -> tuple['Dungeon', set, int, int, list, int]:
	"""Convert dictionary data back to game session objects.
	
	Args:
		data (dict): Dictionary containing serialized session data
		
	Returns:
		tuple: (dungeon, explored_set, player_x, player_y, levels_list, current_index)
		
	Raises:
		ValueError: If save data is invalid or corrupted
		Exception: If deserialization fails for any reason
	"""
	try:
		idx = int(data.get('current_index', 0))
		levels = data.get('levels', [])
		if not levels:
			raise ValueError('No levels in save')
		idx = max(0, min(idx, len(levels) - 1))
		cur = levels[idx]
		d = decode_tiles(cur['tiles'])
		d = decode_materials(d, cur.get('materials', []))
		explored_list = cur.get('explored', [])
		explored = set(tuple(e) for e in explored_list)
		px, py = cur.get('player', [1, 1])
		return d, explored, int(px), int(py), levels, idx
	except Exception as e:
		raise


def sanitize_name(name: str) -> str:
	"""Sanitize a filename to be safe for filesystem use.
	
	Removes invalid characters, limits length, and provides fallback.
	
	Args:
		name (str): Raw name input from user
		
	Returns:
		str: Sanitized filename safe for filesystem use, max 40 chars
	"""
	name = name.strip()
	name = re.sub(r"[^A-Za-z0-9_-]+", "_", name)
	return name[:40] if name else "player"


def set_last_character_name(name: str) -> None:
	"""Persist the most recently used character name for quick loading.

	Args:
		name (str): Character/save name to remember.
	"""
	sanitized = sanitize_name(name)
	if not sanitized:
		return
	try:
		os.makedirs(SAVE_DIR, exist_ok=True)
		payload = {"name": sanitized, "timestamp": time.time()}
		with open(LAST_CHARACTER_FILE, 'w', encoding='utf-8') as f:
			json.dump(payload, f)
	except Exception:
		# Failing to persist the last character shouldn't break gameplay.
		pass


def get_last_character_record() -> Optional[dict]:
	"""Return the persisted last-character metadata if present."""
	try:
		with open(LAST_CHARACTER_FILE, 'r', encoding='utf-8') as f:
			data = json.load(f)
		if isinstance(data, dict):
			name = data.get('name')
			if isinstance(name, str):
				data['name'] = sanitize_name(name)
				return data
	except Exception:
		pass
	return None


def get_last_character_name() -> Optional[str]:
	"""Retrieve the most recently persisted character name, if any."""
	record = get_last_character_record()
	if record:
		name = record.get('name')
		if isinstance(name, str) and name:
			return name
	return None


def save_exists(name: str) -> bool:
	"""Check whether a sanitized save file exists on disk."""
	if not name:
		return False
	path = os.path.join(SAVE_DIR, f"{sanitize_name(name)}.json")
	return os.path.isfile(path)


def load_character_profile_snapshot(name: str):
	"""Attempt to reconstruct a character profile from a saved JSON file."""
	if not name:
		return None
	path = os.path.join(SAVE_DIR, f"{sanitize_name(name)}.json")
	if not os.path.isfile(path):
		return None
	try:
		with open(path, 'r', encoding='utf-8') as f:
			data = json.load(f)
	except Exception:
		return None
	if not isinstance(data, dict) or 'levels' in data:
		# Session saves overwrite the character sheet; nothing to load.
		return None
	try:
		from char_gui import Character
	except Exception:
		return None
	character = Character()
	field_map = {
		'name': 'name',
		'race': 'race',
		'class': 'char_class',
		'alignment': 'alignment',
		'level': 'level',
		'xp': 'xp',
		'strength': 'strength',
		'dexterity': 'dexterity',
		'constitution': 'constitution',
		'intelligence': 'intelligence',
		'wisdom': 'wisdom',
		'charisma': 'charisma',
		'max_hp': 'max_hp',
		'current_hp': 'current_hp',
		'armor_class': 'armor_class',
		'thac0': 'thac0',
		'gold': 'gold',
		'weight_carried': 'weight_carried',
	}
	for key, attr in field_map.items():
		if key in data:
			setattr(character, attr, data[key])
	if isinstance(data.get('equipment'), list):
		character.equipment = list(data['equipment'])
	if isinstance(data.get('racial_abilities'), list):
		character.racial_abilities = list(data['racial_abilities'])
	return character


def get_most_recent_save_name() -> Optional[str]:
	"""Find the newest save file by modification time."""
	if not os.path.isdir(SAVE_DIR):
		return None
	latest_name: Optional[str] = None
	latest_mtime = -1.0
	for fn in os.listdir(SAVE_DIR):
		if not fn.lower().endswith('.json'):
			continue
		path = os.path.join(SAVE_DIR, fn)
		try:
			mtime = os.path.getmtime(path)
		except OSError:
			continue
		if mtime > latest_mtime:
			latest_mtime = mtime
			latest_name = os.path.splitext(fn)[0]
	return latest_name


def default_load_index(load_names: list[str]) -> int:
	"""Choose the default selection index for the load menu."""
	if not load_names:
		return 0
	last_name = get_last_character_name()
	if last_name and last_name in load_names:
		return load_names.index(last_name)
	recent = get_most_recent_save_name()
	if recent and recent in load_names:
		return load_names.index(recent)
	return 0


def save_session(name: str, dungeon: 'Dungeon', explored: set, px: int, py: int, levels: list | None = None, current_index: int = 0) -> str:
	"""Save current game session to disk as JSON file.
	
	Args:
		name (str): Save file name (will be sanitized)
		dungeon (Dungeon): Current dungeon state
		explored (set): Set of explored tile coordinates
		px (int): Player X coordinate
		py (int): Player Y coordinate
		levels (list, optional): List of level data. If None, creates from current dungeon
		current_index (int): Index of current level in levels list
		
	Raises:
		OSError: If unable to create save directory or write file
	"""
	os.makedirs(SAVE_DIR, exist_ok=True)
	data = session_to_dict(dungeon, explored, px, py, levels=levels, current_index=current_index)
	sanitized = sanitize_name(name)
	path = os.path.join(SAVE_DIR, f"{sanitized}.json")
	with open(path, 'w', encoding='utf-8') as f:
		json.dump(data, f)
	set_last_character_name(sanitized)
	return path


def load_session(name: str) -> tuple['Dungeon', set, int, int, list, int]:
	"""Load a game session from disk.
	
	Args:
		name (str): Save file name (will be sanitized)
		
	Returns:
		tuple: (dungeon, explored_set, player_x, player_y, levels_list, current_index)
		
	Raises:
		FileNotFoundError: If save file doesn't exist
		Exception: If save file is corrupted or invalid
	"""
	path = os.path.join(SAVE_DIR, f"{sanitize_name(name)}.json")
	with open(path, 'r', encoding='utf-8') as f:
		data = json.load(f)
	return dict_to_session(data)


def hydrate_levels_from_save(levels_payload: list[dict], current_index: int) -> tuple[list[dict], int, 'Dungeon', set[tuple[int, int]], int, int, set[tuple[int, int]], int, set[tuple[int, int]], set[tuple[int, int]], set[tuple[int, int]], int, int, list[dict]]:
	"""Convert serialized level payloads into live runtime structures."""
	new_levels: list[dict] = []
	for level in levels_payload:
		dungeon_tiles = decode_tiles(level['tiles'])
		dungeon_tiles = decode_materials(dungeon_tiles, level.get('materials', []))
		explored = set(tuple(pt) for pt in level.get('explored', []))
		player_pos = level.get('player', [1, 1])
		px = int(player_pos[0]) if player_pos else 1
		py = int(player_pos[1]) if player_pos else 1
		bricks = set(tuple(pt) for pt in level.get('bricks_touched', []))
		total_bricks = int(level.get('total_bricks', count_total_bricks(dungeon_tiles)))
		walls = set(tuple(pt) for pt in level.get('walls_touched', []))
		floors = set(tuple(pt) for pt in level.get('floors_touched', []))
		floors_stepped = set(tuple(pt) for pt in level.get('floors_stepped', []))
		total_walls = int(level.get('total_walls', count_total_walls(dungeon_tiles)))
		total_floors = int(level.get('total_floors', count_total_floors(dungeon_tiles)))
		torch_payload = level.get('torches')
		if torch_payload is None:
			torch_payload = serialize_torches(generate_wall_torches(dungeon_tiles))
		torches = deserialize_torches(torch_payload)
		new_levels.append({
			'dungeon': dungeon_tiles,
			'explored': explored,
			'player': (px, py),
			'bricks_touched': bricks,
			'total_bricks': total_bricks,
			'walls_touched': walls,
			'floors_touched': floors,
			'floors_stepped': floors_stepped,
			'total_walls': total_walls,
			'total_floors': total_floors,
			'torches': serialize_torches(torches),
		})

	if not new_levels:
		raise ValueError('Empty save payload')

	idx = max(0, min(int(current_index), len(new_levels) - 1))
	current_level = new_levels[idx]
	current_torches = deserialize_torches(current_level['torches'])
	return (
		new_levels,
		idx,
		current_level['dungeon'],
		current_level['explored'],
		int(current_level['player'][0]),
		int(current_level['player'][1]),
		current_level['bricks_touched'],
		int(current_level['total_bricks']),
		current_level['walls_touched'],
		current_level['floors_touched'],
		current_level['floors_stepped'],
		int(current_level['total_walls']),
		int(current_level['total_floors']),
		current_torches,
	)


def list_saves() -> list[str]:
	"""Get list of available save files.
	
	Returns:
		list[str]: List of save file names (without .json extension), sorted alphabetically
	"""
	if not os.path.isdir(SAVE_DIR):
		return []
	files = []
	for fn in os.listdir(SAVE_DIR):
		if fn.lower().endswith('.json'):
			files.append(os.path.splitext(fn)[0])
	files.sort()
	return files


def create_torch(x: int, y: int, direction: tuple[int, int]) -> dict:
	"""Create a runtime torch descriptor with flicker phase and intensity."""
	dx, dy = direction
	if dx == 0 and dy == 0:
		direction = (0, 1)
	phase = random.uniform(0.0, math.tau)
	return {
		'x': int(x),
		'y': int(y),
		'dir': (int(direction[0]), int(direction[1])),
		'radius': TORCH_LIGHT_RADIUS,
		'base_intensity': TORCH_BASE_INTENSITY,
		'phase': phase,
	}


def rebuild_torch_lookup(torch_list: list[dict]) -> dict[tuple[int, int], dict]:
	"""Create a quick lookup dictionary for torches keyed by tile position."""
	return {(torch['x'], torch['y']): torch for torch in torch_list}


def serialize_torches(torch_list: list[dict]) -> list[dict]:
	"""Convert runtime torch descriptors into JSON-friendly dictionaries."""
	serialized = []
	for torch in torch_list:
		dir_vec = torch.get('dir', (0, 1))
		serialized.append({
			'x': int(torch.get('x', 0)),
			'y': int(torch.get('y', 0)),
			'dir': [int(dir_vec[0]), int(dir_vec[1])],
		})
	return serialized


def deserialize_torches(data: list[dict]) -> list[dict]:
	"""Create runtime torch descriptors from serialized data."""
	torches: list[dict] = []
	if not data:
		return torches
	for entry in data:
		if not isinstance(entry, dict):
			continue
		x = entry.get('x')
		y = entry.get('y')
		if x is None or y is None:
			continue
		dir_raw = entry.get('dir') or entry.get('direction') or (0, 1)
		if isinstance(dir_raw, (list, tuple)) and len(dir_raw) == 2:
			dir_vec = (int(dir_raw[0]), int(dir_raw[1]))
		else:
			dir_vec = (0, 1)
		torches.append(create_torch(int(x), int(y), dir_vec))
	return torches


def generate_wall_torches(dungeon: Dungeon, max_per_room: int = 2, placement_chance: float = 0.45) -> list[dict]:
	"""Place decorative torches on select room walls."""
	torches: list[dict] = []
	occupied: set[tuple[int, int]] = set()

	def is_near_existing(pos: tuple[int, int]) -> bool:
		px, py = pos
		for existing in torches:
			ex, ey = existing['x'], existing['y']
			if abs(ex - px) + abs(ey - py) <= 1:
				return True
		return False

	for room in dungeon.rooms:
		candidates: list[tuple[tuple[int, int], tuple[int, int]]] = []

		def consider(wx: int, wy: int, direction: tuple[int, int]) -> None:
			ix, iy = wx + direction[0], wy + direction[1]
			if not (0 <= wx < dungeon.w and 0 <= wy < dungeon.h):
				return
			if not (0 <= ix < dungeon.w and 0 <= iy < dungeon.h):
				return
			tile = dungeon.tiles[wx][wy]
			interior_tile = dungeon.tiles[ix][iy]
			if tile != TILE_WALL:
				return
			if interior_tile == TILE_WALL or interior_tile == TILE_DOOR:
				return
			candidates.append(((wx, wy), direction))

		# Room bounds minus corners to avoid exterior walls
		for x in range(room.x1 + 1, room.x2 - 1):
			consider(x, room.y1, (0, 1))      # top wall facing down
			consider(x, room.y2 - 1, (0, -1))  # bottom wall facing up
		for y in range(room.y1 + 1, room.y2 - 1):
			consider(room.x1, y, (1, 0))       # left wall facing right
			consider(room.x2 - 1, y, (-1, 0))  # right wall facing left

		if not candidates:
			continue

		random.shuffle(candidates)
		room_w = max(1, room.x2 - room.x1 - 2)
		room_h = max(1, room.y2 - room.y1 - 2)
		room_capacity = 1 if min(room_w, room_h) < 4 else max_per_room
		placed = 0
		for (pos, direction) in candidates:
			if placed >= room_capacity:
				break
			if pos in occupied or is_near_existing(pos):
				continue
			if random.random() > placement_chance:
				continue
			torch = create_torch(pos[0], pos[1], direction)
			torches.append(torch)
			occupied.add(pos)
			placed += 1

	return torches


# Field of View via symmetrical shadowcasting (8 octants)
class FOV:
	"""Field of View calculator using symmetrical shadowcasting algorithm.
	
	Implements 8-octant shadowcasting to determine which tiles are visible
	from a given position within a specified radius. Handles light blocking
	based on wall tiles.
	
	Attributes:
		dungeon (Dungeon): The dungeon to calculate FOV for
	"""
	def __init__(self, dungeon: Dungeon):
		"""Initialize FOV calculator.
		
		Args:
			dungeon (Dungeon): The dungeon object to calculate FOV for
		"""
		self.dungeon = dungeon

	def compute(self, cx: int, cy: int, radius: int) -> set[tuple[int, int]]:
		"""Compute field of view from a center position.
		
		Args:
			cx (int): Center X coordinate
			cy (int): Center Y coordinate
			radius (int): Maximum visibility radius in tiles
			
		Returns:
			set[tuple[int, int]]: Set of (x, y) coordinates of visible tiles
		"""
		visible = set()
		visible.add((cx, cy))

		def blocks_light(x, y):
			return self.dungeon.is_wall(x, y)

		def set_visible(x, y):
			dx = x - cx
			dy = y - cy
			dist = math.sqrt(dx * dx + dy * dy)
			if dist <= radius:
				visible.add((x, y))

		# Octant processing
		def cast_shadows(row, start_slope, end_slope, xx, xy, yx, yy):
			if start_slope < end_slope:
				return
			radius_sq = radius * radius
			for i in range(row, radius + 1):
				dx = -i
				dy = -i

				blocked = False
				new_start = start_slope
				while dx <= 0:
					# Translate the dx,dy into map coordinates
					X = cx + dx * xx + dy * xy
					Y = cy + dx * yx + dy * yy
					l_slope = (dx - 0.5) / (dy + 0.5)
					r_slope = (dx + 0.5) / (dy - 0.5)

					if X < 0 or Y < 0 or X >= self.dungeon.w or Y >= self.dungeon.h:
						dx += 1
						continue

					if start_slope < r_slope:
						dx += 1
						continue
					if end_slope > l_slope:
						break

					# within light radius?
					if dx * dx + dy * dy <= radius_sq:
						set_visible(X, Y)

					if blocked:
						if blocks_light(X, Y):
							new_start = r_slope
						else:
							blocked = False
							start_slope = new_start
					else:
						if blocks_light(X, Y) and i < radius:
							blocked = True
							cast_shadows(i + 1, start_slope, l_slope, xx, xy, yx, yy)
							new_start = r_slope
					dx += 1
				if blocked:
					break

		# Process the 8 octants
		octants = [
			(1, 0, 0, 1),
			(0, 1, 1, 0),
			(0, -1, 1, 0),
			(1, 0, 0, -1),
			(-1, 0, 0, -1),
			(0, -1, -1, 0),
			(0, 1, -1, 0),
			(-1, 0, 0, 1),
		]
		for xx, xy, yx, yy in octants:
			cast_shadows(1, 1.0, 0.0, xx, xy, yx, yy)

		return visible


# Rendering helpers
CSI = "\x1b["  # ANSI Control Sequence Introducer


def hide_cursor() -> None:
	"""Hide terminal cursor using ANSI escape sequence."""
	sys.stdout.write(CSI + "?25l")
	sys.stdout.flush()


def show_cursor() -> None:
	"""Show terminal cursor using ANSI escape sequence."""
	sys.stdout.write(CSI + "?25h")
	sys.stdout.flush()


def clear_screen() -> None:
	"""Clear terminal screen and move cursor to top-left."""
	sys.stdout.write(CSI + "2J" + CSI + "H")
	sys.stdout.flush()


def move_cursor(row: int = 1, col: int = 1) -> None:
	"""Move terminal cursor to specified position.
	
	Args:
		row (int): Row number (1-based)
		col (int): Column number (1-based)
	"""
	sys.stdout.write(f"{CSI}{row};{col}H")


def build_frame(dungeon: Dungeon, px: int, py: int, visible_map: set, explored: set) -> str:
	"""Build ASCII frame for terminal display.
	
	Args:
		dungeon (Dungeon): The dungeon to render
		px (int): Player X coordinate
		py (int): Player Y coordinate
		visible_map (set): Set of visible tile coordinates
		explored (set): Set of previously explored coordinates
		
	Returns:
		str: Multi-line string representing the rendered dungeon frame
	"""
	# Terminal renderer: show player '@', walls '#', and empty floor as ' '.

	w, h = dungeon.w, dungeon.h
	lines = []
	for y in range(h):
		row_chars = []
		for x in range(w):
			tile = dungeon.tiles[x][y]
			if (x, y) == (px, py):
				row_chars.append(PLAYER_CH)
				explored.add((x, y))
				continue

			if (x, y) in visible_map:
				explored.add((x, y))
				if tile == TILE_WALL:
					row_chars.append(WALL_CH)
				elif tile == TILE_DOOR:
					# Render doors with a specific character
					row_chars.append('+')  # Traditional door character
				else:
					# Floors render as configured floor character (may be space or '#')
					row_chars.append(FLOOR_CH)
			else:
				# Complete darkness outside light radius
				row_chars.append(DARK_CH)
		lines.append(''.join(row_chars))
	return '\n'.join(lines)


def read_input_nonblocking() -> str | None:
	"""Read keyboard input without blocking (Windows-specific).
	
	Returns:
		str | None: Character pressed, or None if no key was pressed
		             Returns None on non-Windows platforms where msvcrt unavailable
	"""
	if msvcrt is None:
		return None
	if msvcrt.kbhit():
		try:
			c = msvcrt.getwch()
		except Exception:
			try:
				c = msvcrt.getch().decode('utf-8', 'ignore')
			except Exception:
				c = None
		return c
	return None


def run_terminal() -> None:
	"""Run the game in terminal mode with ASCII rendering.
	
	Uses ANSI escape sequences for display and msvcrt for input on Windows.
	Game loop handles player movement, FOV calculation, and terminal rendering.
	"""
	random.seed()
	cols, rows = get_term_size()
	# Reserve last line for HUD
	rows = max(15, rows - 1)
	cols = max(40, cols)

	# Use modular dungeon generator with settings
	dungeon_params = {
		'width': cols,
		'height': rows,
		'complexity': SETTINGS.get('dungeon_complexity', 0.2),
		'length': SETTINGS.get('dungeon_length', 25),
		'room_min': SETTINGS.get('dungeon_room_min', 4),
		'room_max': SETTINGS.get('dungeon_room_max', 9),
		'linearity': SETTINGS.get('dungeon_linearity', .7),
		'entropy': SETTINGS.get('dungeon_entropy', 0.0),
	}
	dungeon = generate_dungeon(**dungeon_params)

	# Place player at center of first room, ensuring they're on a floor tile
	if dungeon.rooms:
		room = dungeon.rooms[0]
		px, py = room.center()
		
		# Ensure player starts on a floor tile within the room
		if dungeon.is_wall(px, py):
			# Search for a floor tile within the room bounds
			found = False
			for x in range(room.x1 + 1, room.x2 - 1):
				for y in range(room.y1 + 1, room.y2 - 1):
					if not dungeon.is_wall(x, y):
						px, py = x, y
						found = True
						break
				if found:
					break
	else:
		# fallback: find any floor
		px = py = 1
		for y in range(dungeon.h):
			for x in range(dungeon.w):
				if not dungeon.is_wall(x, y):
					px, py = x, y
					break
			else:
				continue
			break

	fov = FOV(dungeon)
	explored = set()
	# Bricks exploration tracking (per-level)
	def count_total_bricks(d: Dungeon) -> int:
		total = 0
		for y in range(d.h):
			for x in range(d.w):
				if d.tiles[x][y] == TILE_WALL and d.materials[x][y] == MAT_BRICK:
					total += 1
		return total
	bricks_touched = set()  # set[(x,y)] of brick walls that have been visible at least once
	total_bricks = count_total_bricks(dungeon)

	hide_cursor()
	try:
		last_time = time.perf_counter()
		accumulator = 0.0
		frame_time = 1.0 / FPS

		running = True
		while running:
			now = time.perf_counter()
			dt = now - last_time
			last_time = now
			accumulator += dt

			# Handle input (non-blocking)
			c = read_input_nonblocking()
			if c:
				c_lower = c.lower()
				dx = dy = 0
				if c_lower == 'w':
					dy = -1
				elif c_lower == 's':
					dy = 1
				elif c_lower == 'a':
					dx = -1
				elif c_lower == 'd':
					dx = 1
				elif c_lower == 'q':
					running = False

				nx, ny = px + dx, py + dy
				if 0 <= nx < dungeon.w and 0 <= ny < dungeon.h and not dungeon.is_wall(nx, ny):
					px, py = nx, ny

			# Update and render at fixed FPS
			if accumulator >= frame_time:
				accumulator = 0.0
				# Compute visibility
				visible = fov.compute(px, py, LIGHT_RADIUS)

				# Draw
				clear_screen()
				move_cursor(1, 1)
				frame = build_frame(dungeon, px, py, visible, explored)
				sys.stdout.write(frame)
				# HUD on last line
				move_cursor(dungeon.h + 1, 1)
				sys.stdout.write(f"WASD to move, Q to quit | {dungeon.w}x{dungeon.h} | Light r={LIGHT_RADIUS}\n")
				sys.stdout.flush()

			# Small sleep to avoid 100% CPU
			time.sleep(0.001)

	finally:
		show_cursor()


# ===========================
# INVENTORY SYSTEM - Slot-Based with Containers
# ===========================

class InventoryItem:
	"""Represents an item with all its properties for display and sorting"""
	def __init__(self, name: str, category: str, properties: dict):
		self.name = name
		self.category = category  # Weapons, Armor, Gear, Potions, Containers
		self.cost = properties.get('cost', 0)
		self.weight = properties.get('weight', 0)
		self.damage = properties.get('damage', '')
		self.ac = properties.get('ac', None)
		self.speed = properties.get('speed', None)
		self.size = properties.get('size', 'medium')  # small, medium, large
		self.properties = properties
		
		# Equipment slot properties
		self.equippable = properties.get('equippable', False)
		self.equipment_slot = properties.get('equipment_slot', None)  # head, neck, body, wrist, hands, ring, legs, feet, trinket, main_hand, off_hand
		self.usable_from_inventory = properties.get('usable_from_inventory', False)  # Can be used without equipping
		
		# Container-specific properties
		self.is_container = properties.get('is_container', False)
		self.slots = properties.get('slots', 0)  # Number of slots if container
		self.max_item_size = properties.get('max_item_size', 'large')  # Max size items it can hold
		self.weight_reduction = properties.get('weight_reduction', 0.0)  # % weight reduction (0.0-1.0)
		
		# Container contents (if this is a container)
		self.contents: List[Optional['InventoryItem']] = [None] * self.slots if self.is_container else []
	
	def get_type_display(self) -> str:
		"""Return the item type/category"""
		if self.is_container:
			return f"Container ({self.slots})"
		return self.category
	
	def get_damage_display(self) -> str:
		"""Return damage string or '-' if not applicable"""
		return self.damage if self.damage else '-'
	
	def get_ac_display(self) -> str:
		"""Return AC modifier or '-' if not applicable"""
		if self.ac is not None:
			if self.ac > 0:
				return f"+{self.ac}"
			elif self.ac < 0:
				return str(self.ac)
			else:
				return "0"
		return '-'
	
	def get_speed_display(self) -> str:
		"""Return speed factor or '-' if not applicable"""
		return str(self.speed) if self.speed is not None else '-'
	
	def get_container_info(self) -> str:
		"""Return container capacity info"""
		if not self.is_container:
			return ''
		used = sum(1 for item in self.contents if item is not None)
		return f"{used}/{self.slots} slots"
	
	def get_effective_weight(self) -> float:
		"""Calculate effective weight including container contents and reduction"""
		base_weight = self.weight
		if self.is_container:
			contents_weight = sum(item.get_effective_weight() for item in self.contents if item is not None)
			# Apply weight reduction to contents
			reduced_contents = contents_weight * (1.0 - self.weight_reduction)
			return base_weight + reduced_contents
		return base_weight
	
	def can_fit_item(self, item: 'InventoryItem') -> bool:
		"""Check if item can fit in this container"""
		if not self.is_container:
			return False
		# Check if there's an empty slot
		if not any(slot is None for slot in self.contents):
			return False
		# Check size restrictions
		size_order = {'small': 0, 'medium': 1, 'large': 2}
		item_size = size_order.get(item.size, 1)
		max_size = size_order.get(self.max_item_size, 2)
		return item_size <= max_size
	
	def add_item(self, item: 'InventoryItem') -> bool:
		"""Add item to first empty slot in container"""
		if not self.can_fit_item(item):
			return False
		for i in range(len(self.contents)):
			if self.contents[i] is None:
				self.contents[i] = item
				return True
		return False
	
	def remove_item(self, index: int) -> Optional['InventoryItem']:
		"""Remove and return item at index"""
		if 0 <= index < len(self.contents) and self.contents[index] is not None:
			item = self.contents[index]
			self.contents[index] = None
			return item
		return None


class CharacterInventory:
	"""Manages character's 8-slot inventory system"""
	BASE_SLOTS = 8
	
	def __init__(self):
		self.slots: List[Optional[InventoryItem]] = [None] * self.BASE_SLOTS
	
	def get_total_weight(self) -> float:
		"""Calculate total carried weight"""
		return sum(item.get_effective_weight() for item in self.slots if item is not None)
	
	def get_item_count(self) -> int:
		"""Count total items including container contents"""
		count = sum(1 for item in self.slots if item is not None)
		for item in self.slots:
			if item and item.is_container:
				count += sum(1 for content_item in item.contents if content_item is not None)
		return count
	
	def add_item_auto(self, item: InventoryItem) -> bool:
		"""Auto-add item: fill empty main slots first, then containers"""
		# First, try to add to empty main slot
		for i in range(self.BASE_SLOTS):
			if self.slots[i] is None:
				self.slots[i] = item
				return True
		
		# No empty main slots, try to add to containers
		for container in self.slots:
			if container and container.is_container and container.add_item(item):
				return True
		
		return False  # Inventory full
	
	def get_all_items_flat(self) -> List[InventoryItem]:
		"""Get all items as flat list (for old inventory display compatibility)"""
		items = []
		for item in self.slots:
			if item:
				items.append(item)
				if item.is_container:
					items.extend([content for content in item.contents if content is not None])
		return items


class CharacterEquipment:
	"""Manages character's equipped/worn items (paperdoll)"""
	SLOT_ORDER = ['head', 'neck', 'body', 'left_wrist', 'right_wrist', 'hands', 
	              'left_ring', 'right_ring', 'legs', 'feet', 'trinket', 'main_hand', 'off_hand']
	
	SLOT_DISPLAY_NAMES = {
		'head': 'Head',
		'neck': 'Neck',
		'body': 'Body',
		'left_wrist': 'Left Wrist',
		'right_wrist': 'Right Wrist',
		'hands': 'Hands',
		'left_ring': 'Left Ring',
		'right_ring': 'Right Ring',
		'legs': 'Legs',
		'feet': 'Feet',
		'trinket': 'Trinket',
		'main_hand': 'Main Hand',
		'off_hand': 'Off-Hand'
	}
	
	def __init__(self):
		self.equipped: Dict[str, Optional[InventoryItem]] = {slot: None for slot in self.SLOT_ORDER}
	
	def can_equip(self, item: InventoryItem, slot: str = None) -> tuple[bool, str]:
		"""Check if item can be equipped. Returns (can_equip, reason)"""
		if not item.equippable:
			return False, "Item is not equippable"
		
		target_slot = slot if slot else item.equipment_slot
		if not target_slot:
			return False, "Item has no equipment slot defined"
		
		# Handle special cases for ring/wrist (can go in left or right)
		if item.equipment_slot == 'ring' and slot in ['left_ring', 'right_ring']:
			return True, ""
		if item.equipment_slot == 'wrist' and slot in ['left_wrist', 'right_wrist']:
			return True, ""
		
		# Standard slot matching
		if target_slot in self.SLOT_ORDER:
			return True, ""
		
		return False, f"Invalid equipment slot: {target_slot}"
	
	def equip_item(self, item: InventoryItem, slot: str = None) -> Optional[InventoryItem]:
		"""Equip item to slot. Returns previously equipped item if any."""
		target_slot = slot if slot else item.equipment_slot
		
		# For rings/wrists without specific slot, find first empty or use left
		if item.equipment_slot == 'ring' and not slot:
			if self.equipped['left_ring'] is None:
				target_slot = 'left_ring'
			elif self.equipped['right_ring'] is None:
				target_slot = 'right_ring'
			else:
				target_slot = 'left_ring'  # Default to left, will swap
		
		if item.equipment_slot == 'wrist' and not slot:
			if self.equipped['left_wrist'] is None:
				target_slot = 'left_wrist'
			elif self.equipped['right_wrist'] is None:
				target_slot = 'right_wrist'
			else:
				target_slot = 'left_wrist'  # Default to left, will swap
		
		can_equip, reason = self.can_equip(item, target_slot)
		if not can_equip:
			return None
		
		# Swap out currently equipped item
		old_item = self.equipped[target_slot]
		self.equipped[target_slot] = item
		return old_item
	
	def unequip_item(self, slot: str) -> Optional[InventoryItem]:
		"""Remove item from slot. Returns the item."""
		if slot in self.equipped:
			item = self.equipped[slot]
			self.equipped[slot] = None
			return item
		return None
	
	def get_equipped_item(self, slot: str) -> Optional[InventoryItem]:
		"""Get item in slot"""
		return self.equipped.get(slot, None)
	
	def get_total_ac_bonus(self) -> int:
		"""Calculate total AC bonus from all equipped items"""
		bonus = 0
		for item in self.equipped.values():
			if item and item.ac is not None:
				bonus += item.ac
		return bonus
	
	def get_equipped_weight(self) -> float:
		"""Calculate weight of all equipped items"""
		return sum(item.get_effective_weight() for item in self.equipped.values() if item is not None)


def load_equipment_database():
	"""Load equipment data from char_gui.py"""
	try:
		from char_gui import EQUIPMENT
		items = []
		for category, item_dict in EQUIPMENT.items():
			for item_name, props in item_dict.items():
				items.append(InventoryItem(item_name, category, props))
		return items
	except Exception as e:
		print(f"Error loading equipment database: {e}")
		return []


def parse_character_inventory(character) -> List[InventoryItem]:
	"""Parse character's equipment list into InventoryItem objects"""
	if not character or not hasattr(character, 'equipment'):
		return []
	
	# Load the equipment database
	equipment_db = load_equipment_database()
	
	# Create a lookup dict for quick access
	db_lookup = {item.name: item for item in equipment_db}
	
	# Parse character's equipment
	inventory = []
	for item_name in character.equipment:
		if item_name in db_lookup:
			inventory.append(db_lookup[item_name])
		else:
			# Unknown item - create a basic entry
			inventory.append(InventoryItem(item_name, "Unknown", {}))
	
	return inventory


def show_splash_screen(screen: Optional["pygame.Surface"] = None, clock: Optional["pygame.time.Clock"] = None) -> bool:
	"""Display splash screen with DUNGEON title. Press any key to continue."""
	import pygame
	from parchment_renderer import ParchmentRenderer
	import os

	created_display = False

	if not pygame.get_init():
		pygame.init()

	if screen is None:
		win_w, win_h = BASE_WIN_W, BASE_WIN_H
		screen = pygame.display.set_mode((win_w, win_h))
		created_display = True
	else:
		win_w, win_h = screen.get_size()

	if clock is None:
		clock = pygame.time.Clock()

	prev_caption = pygame.display.get_caption()
	pygame.display.set_caption("DUNGEON")
	
	# Create dark grey parchment background
	DARK_GREY_BASE = (27, 27, 30)  # Dark grey (twice as dark)
	DARK_GREY_INK = (17, 17, 19)   # Even darker for texture
	splash_renderer = ParchmentRenderer(
		base_color=DARK_GREY_BASE,
		ink_color=DARK_GREY_INK,
		enable_vignette=True,
		vignette_steps=20,
		grain_tile=10,
		blotch_count=80,
		fiber_count=50,
		speckle_count=500
	)
	splash_renderer.build_layers(win_w, win_h, seed=999)
	splash_bg = splash_renderer.generate(win_w, win_h)
	
	# Load Blocky Sketch font at 49pt
	import os
	font_path = os.path.join(os.path.dirname(__file__), "Blocky Sketch.ttf")
	if os.path.isfile(font_path):
		title_font = pygame.font.Font(font_path, 49)
	else:
		# Fallback to system font
		title_font = pygame.font.Font(None, 49)
	
	# Render "DUNGEON" text in white
	text_surface_full = title_font.render("DUNGEON", True, (255, 255, 255))
	
	# Calculate center position
	text_rect = text_surface_full.get_rect(center=(win_w // 2, win_h // 2))

	# Start intro music (Title.mid) while the splash screen is visible
	try:
		title_music_path = os.path.join(os.path.dirname(__file__), 'resources', 'sounds', 'Title.mid')
		if os.path.isfile(title_music_path):
			intro_volume = SETTINGS.get('music_volume', 0.7)
			music_player = get_music_player()
			music_player.play_midi_file(title_music_path, loops=-1, fade_ms=1500, volume=intro_volume)
		else:
			print(f"[AUDIO] Title music not found at {title_music_path}")
	except Exception as e:
		print(f"[AUDIO] Could not start intro music: {e}")
	
	
	# Combined loop: delay, fade in, then wait indefinitely
	delay_duration = 3.0  # seconds
	fade_duration = 3.0  # seconds
	
	delay_frames = int(delay_duration * 60)  # 60 FPS
	fade_frames = int(fade_duration * 60)  # 60 FPS
	total_animation_frames = delay_frames + fade_frames
	
	hint_font = pygame.font.Font(None, 20)
	hint_text = "Press any key to continue..."
	
	frame = 0
	waiting = True
	
	while waiting:
		# Process events
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				return False
			if event.type == pygame.KEYDOWN:
				waiting = False
				break

		# Draw background
		screen.blit(splash_bg, (0, 0))
		
		# Phase 1: Blank parchment (frames 0 to delay_frames)
		if frame < delay_frames:
			pass  # Just show background
		
		# Phase 2: Fade in text (frames delay_frames to total_animation_frames)
		elif frame < total_animation_frames:
			fade_progress = (frame - delay_frames) / fade_frames
			alpha = int(255 * fade_progress)
			
			# Fade in main text
			text_surface = text_surface_full.copy()
			text_surface.set_alpha(alpha)
			screen.blit(text_surface, text_rect)
			
			# Fade in hint text slightly after main text (after 50% of fade)
			if fade_progress > 0.5:
				hint_progress = (fade_progress - 0.5) / 0.5
				hint_alpha = int(255 * hint_progress)
				hint_surface = hint_font.render(hint_text, True, (180, 180, 180))
				hint_surface.set_alpha(hint_alpha)
				hint_rect = hint_surface.get_rect(center=(win_w // 2, win_h - 50))
				screen.blit(hint_surface, hint_rect)
		
		# Phase 3: Stay visible indefinitely until keypress
		else:
			screen.blit(text_surface_full, text_rect)
			hint_surface = hint_font.render(hint_text, True, (180, 180, 180))
			hint_rect = hint_surface.get_rect(center=(win_w // 2, win_h - 50))
			screen.blit(hint_surface, hint_rect)
		
		pygame.display.flip()
		clock.tick(60)
		frame += 1
	
	# Ambient audio continues into character creator/game without interruption
	
		if prev_caption and not created_display:
			title, icon = prev_caption if len(prev_caption) == 2 else (prev_caption[0], "")
			pygame.display.set_caption(title, icon)
		elif created_display:
			pygame.display.set_caption("")

	return True


def prompt_load_last_character(name: str, last_played_ts: Optional[float] = None) -> bool:
	"""Show a modal prompt asking whether to resume the last saved character."""
	import pygame

	screen = pygame.display.get_surface()
	if screen is None:
		# Fallback: ensure a window exists if splash was skipped somehow.
		screen = pygame.display.set_mode((BASE_WIN_W, BASE_WIN_H))

	clock = pygame.time.Clock()
	pygame.event.clear()
	pygame.mouse.set_visible(True)

	win_w, win_h = screen.get_size()
	panel_w, panel_h = min(520, win_w - 80), 240
	panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
	panel_rect.center = (win_w // 2, win_h // 2)

	bg_surface = pygame.Surface((win_w, win_h))
	bg_surface.fill(WORLD_BG)
	overlay = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
	overlay.fill((0, 0, 0, 120))

	font_path = os.path.join(os.path.dirname(__file__), "Blocky Sketch.ttf")
	try:
		title_font = pygame.font.Font(font_path, 34)
	except Exception:
		title_font = pygame.font.Font(None, 38)
	text_font = pygame.font.Font(None, 24)
	button_font = pygame.font.Font(None, 26)

	last_played_text = None
	if last_played_ts:
		try:
			stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(last_played_ts))
			last_played_text = f"Last ventured: {stamp}"
		except Exception:
			last_played_text = None

	def draw_prompt(yes_color=WALL_LIGHT, no_color=WALL_LIGHT):
		screen.blit(bg_surface, (0, 0))
		screen.blit(overlay, (0, 0))
		pygame.draw.rect(screen, (52, 44, 38), panel_rect)
		pygame.draw.rect(screen, WALL_LIGHT, panel_rect, 3)

		title = title_font.render(f"Resume {name}'s journey?", True, (240, 230, 210))
		title_rect = title.get_rect(center=(panel_rect.centerx, panel_rect.top + 50))
		screen.blit(title, title_rect)

		sub_lines = [
			"Press Y to load your last save.",
			"Press N to forge a new hero.",
		]
		if last_played_text:
			sub_lines.insert(0, last_played_text)
		for i, line in enumerate(sub_lines):
			text = text_font.render(line, True, (210, 200, 180))
			rect = text.get_rect(center=(panel_rect.centerx, panel_rect.top + 105 + i * 26))
			screen.blit(text, rect)

		yes_text = "[Y] Resume adventure"
		no_text = "[N] Start fresh"
		yes_surface = button_font.render(yes_text, True, yes_color)
		no_surface = button_font.render(no_text, True, no_color)
		yes_rect = yes_surface.get_rect(center=(panel_rect.centerx - panel_rect.width // 4, panel_rect.bottom - 45))
		no_rect = no_surface.get_rect(center=(panel_rect.centerx + panel_rect.width // 4, panel_rect.bottom - 45))
		screen.blit(yes_surface, yes_rect)
		screen.blit(no_surface, no_rect)
		return yes_rect, no_rect

	yes_rect, no_rect = draw_prompt()
	pygame.display.flip()

	while True:
		mouse_pos = pygame.mouse.get_pos()
		yes_hover = yes_rect.collidepoint(mouse_pos)
		no_hover = no_rect.collidepoint(mouse_pos)

		yes_color = (255, 240, 200) if yes_hover else WALL_LIGHT
		no_color = (255, 240, 200) if no_hover else WALL_LIGHT
		yes_rect, no_rect = draw_prompt(yes_color=yes_color, no_color=no_color)
		pygame.display.flip()

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				return False
			if event.type == pygame.KEYDOWN:
				if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_SPACE):
					return True
				if event.key in (pygame.K_n, pygame.K_ESCAPE):
					return False
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if yes_rect.collidepoint(event.pos):
					return True
				if no_rect.collidepoint(event.pos):
					return False

		clock.tick(60)

def run_pygame():
	try:
		import pygame
	except Exception as e:
		print("Pygame is required for the windowed mode. Install with: pip install pygame")
		raise

	try:
		os.environ['SDL_VIDEO_WINDOW_POS'] = '100,100'
	except Exception:
		pass

	# Initialize pygame mixer ONCE at the very beginning
	# This prevents re-initialization conflicts between music and sound systems
	pygame.init()
	if not pygame.mixer.get_init():
		pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
		pygame.mixer.set_num_channels(16)  # Allow multiple sounds simultaneously
	print(f"[AUDIO] Pygame mixer initialized: {pygame.mixer.get_init()}")
	
	# Apply initial volume settings from config
	music_vol = SETTINGS.get('music_volume', 0.7)
	pygame.mixer.music.set_volume(music_vol)
	print(f"[AUDIO] Music volume set to {int(music_vol * 100)}%")

	win_w, win_h = BASE_WIN_W, BASE_WIN_H
	screen = pygame.display.set_mode((win_w, win_h))
	clock = pygame.time.Clock()

	icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'dungeon_icon.bmp')
	if sys.platform.startswith('win'):
		try:
			import ctypes
			ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Dungeon.Dungeon')
		except Exception as appid_error:
			print(f"[UI] Failed to set AppUserModelID: {appid_error}")
	if os.path.isfile(icon_path):
		try:
			icon_surface = pygame.image.load(icon_path)
			pygame.display.set_icon(icon_surface)
		except Exception as icon_error:
			print(f"[UI] Failed to load window icon from {icon_path}: {icon_error}")

	# Show splash screen first
	if not show_splash_screen(screen=screen, clock=clock):
		return

	pygame.display.set_caption("ASCII Dungeon (Resizable)")

	# Ensure dungeon music plays across character creator and gameplay scenes
	music_player = None
	dungeon_music_path = os.path.join(os.path.dirname(__file__), 'resources', 'sounds', 'Dungeon.mid')
	try:
		if not os.path.isfile(dungeon_music_path):
			raise FileNotFoundError(dungeon_music_path)
		music_player = get_music_player()
		if not music_player.is_playing():
			music_player.play_midi_file(dungeon_music_path, loops=-1, fade_ms=3000, volume=music_vol)
	except Exception as e:
		print(f"[AUDIO] Could not start dungeon music: {e}")

	startup_session: Optional[tuple] = None
	startup_save_name: Optional[str] = None
	startup_character = None

	last_record = get_last_character_record()
	if last_record:
		candidate_name = last_record.get('name')
		candidate_ts = last_record.get('timestamp') if isinstance(last_record.get('timestamp'), (int, float)) else None
		if candidate_name and save_exists(candidate_name):
			if prompt_load_last_character(candidate_name, candidate_ts):
				try:
					startup_session = load_session(candidate_name)
					startup_save_name = candidate_name
					startup_character = load_character_profile_snapshot(candidate_name)
					print(f"[LOAD] Resuming last save '{candidate_name}'.")
				except Exception as e:
					print(f"[LOAD] Failed to load save '{candidate_name}': {e}")

	# Launch character creator at startup
	player_character = startup_character
	if startup_session is None:
		try:
			from char_gui import run_character_creator
			player_character = run_character_creator(screen=screen, clock=clock)
			if not player_character:
				print("Character creation cancelled. Exiting game.")
				return
			print(f"Welcome, {player_character.name}! Starting your adventure...")
		except Exception as e:
			print(f"Error launching character creator: {e}")
			import traceback
			traceback.print_exc()
			print("Starting game without character...")

	random.seed()

	# Initial window and grid
	win_w, win_h = BASE_WIN_W, BASE_WIN_H
	grid_w, grid_h = BASE_GRID_W, BASE_GRID_H
	cell_w, cell_h = BASE_CELL_W, BASE_CELL_H

	# UI panel configuration (character columns)
	UI_COLS = 20  # width of UI panel in characters
	BORDER_COL = UI_COLS  # vertical border column index

	# Dungeon uses the remaining columns
	map_w = max(10, grid_w - UI_COLS - 1 - 20)
	dungeon_params = {
		'width': map_w,
		'height': grid_h,
		'complexity': SETTINGS.get('dungeon_complexity', 0.2),
		'length': SETTINGS.get('dungeon_length', 25),
		'room_min': SETTINGS.get('dungeon_room_min', 4),
		'room_max': SETTINGS.get('dungeon_room_max', 9),
		'linearity': SETTINGS.get('dungeon_linearity', 1.0),
		'entropy': SETTINGS.get('dungeon_entropy', 0.0),
	}
	levels: list[dict] = []
	current_level_index = 0
	using_loaded_save = False

	dungeon: Optional[Dungeon] = None
	explored: set[tuple[int, int]] = set()
	px = py = 1
	bricks_touched: set[tuple[int, int]] = set()
	total_bricks = 0
	walls_touched: set[tuple[int, int]] = set()
	floors_touched: set[tuple[int, int]] = set()
	floors_stepped: set[tuple[int, int]] = set()
	total_walls = 0
	total_floors = 0
	torches: list[dict] = []
	torch_lookup: dict[tuple[int, int], dict] = {}

	if startup_session is not None:
		try:
			_, _, _, _, levels_payload, idx = startup_session
			(levels, current_level_index, dungeon, explored, px, py,
			 bricks_touched, total_bricks, walls_touched, floors_touched,
			 floors_stepped, total_walls, total_floors, torches) = hydrate_levels_from_save(levels_payload, idx)
			torch_lookup = rebuild_torch_lookup(torches)
			using_loaded_save = True
			if startup_save_name:
				set_last_character_name(startup_save_name)
		except Exception as e:
			print(f"[LOAD] Save data was invalid, starting new dungeon: {e}")
			startup_session = None
			if player_character is None:
				try:
					from char_gui import run_character_creator
					player_character = run_character_creator(screen=screen, clock=clock)
					if not player_character:
						print("Character creation cancelled. Exiting game.")
						return
					print(f"Welcome, {player_character.name}! Starting your adventure...")
				except Exception as creator_error:
					print(f"Error launching character creator after failed load: {creator_error}")
					import traceback
					traceback.print_exc()
					print("Continuing without character...")

	if not using_loaded_save or dungeon is None:
		dungeon = generate_dungeon(**dungeon_params)
		print(f"[DUNGEON] Generated {len(dungeon.rooms)} rooms (requested: {dungeon_params['length']})")
		# Place player at center of first room, ensuring they're on a floor tile
		if dungeon.rooms:
			room = dungeon.rooms[0]
			px, py = room.center()
			if dungeon.is_wall(px, py):
				found = False
				for x in range(room.x1 + 1, room.x2 - 1):
					for y in range(room.y1 + 1, room.y2 - 1):
						if not dungeon.is_wall(x, y):
							px, py = x, y
							found = True
							break
					if found:
						break
		else:
			px = py = 1
			for y in range(dungeon.h):
				for x in range(dungeon.w):
					if not dungeon.is_wall(x, y):
						px, py = x, y
						break
				else:
					continue
				break
		explored = set()
		bricks_touched = set()
		walls_touched = set()
		floors_touched = set()
		floors_stepped = set()
		torches = generate_wall_torches(dungeon)
		torch_lookup = rebuild_torch_lookup(torches)
		levels = []
		current_level_index = 0
		total_bricks = count_total_bricks(dungeon)
		reachable = compute_reachable_floors(dungeon, px, py)
		total_floors = len(reachable)
		total_walls = count_total_exposed_walls(dungeon, reachable)
	else:
		print(f"[LOAD] Loaded dungeon with {len(dungeon.rooms)} rooms from save.")
		reachable = compute_reachable_floors(dungeon, px, py)
		if not total_floors:
			total_floors = len(reachable)
		if not total_walls:
			total_walls = count_total_exposed_walls(dungeon, reachable)
		if not total_bricks:
			total_bricks = count_total_bricks(dungeon)
		if not torches:
			torches = generate_wall_torches(dungeon)
			torch_lookup = rebuild_torch_lookup(torches)
		else:
			torch_lookup = rebuild_torch_lookup(torches)

	fov = FOV(dungeon)

	# Secret discovery system with varying difficulty levels
	# Each floor tile has a 1% chance of having a secret
	tile_secrets = {}  # (x, y) -> difficulty DC (5, 10, 15, 20, 25)
	tile_search_progress = {}  # (x, y) -> seconds of accumulated search time
	tile_search_alpha = {}  # (x, y) -> visual fade-in alpha (0.0 to 1.0) for secret tiles
	revealed_secrets = set()  # set of (x, y) for found secrets
	tile_secrets_checked = set()  # set of (x, y) for secrets that have had their perception check rolled
	
	# Gradual illumination system - all visible tiles gradually brighten
	tile_illumination_progress = {}  # (x, y) -> seconds of accumulated illumination time
	tile_illumination_alpha = {}  # (x, y) -> illumination alpha (0.0 to 1.0)
	tile_illumination_source = {}  # (x, y) -> 'player' or 'torch'
	
	# Secret difficulty distribution (weighted towards easier secrets)
	# DC 5 = Trivial (impossible to miss with any perception)
	# DC 10 = Easy (most characters will find)
	# DC 15 = Normal (requires some perception)
	# DC 20 = Hard (requires good perception or lucky roll)
	# DC 25 = Very Hard (requires excellent perception and good roll)
	difficulty_weights = [
		(5, 30),   # 30% trivial
		(10, 35),  # 35% easy
		(15, 20),  # 20% normal
		(20, 10),  # 10% hard
		(25, 5),   # 5% very hard
	]
	
	# Generate secrets for floor tiles (1% chance)
	for y in range(dungeon.h):
		for x in range(dungeon.w):
			if not dungeon.is_wall(x, y):  # Only floor tiles can have secrets
				if random.random() < 0.01:  # 1% chance
					# Randomly assign difficulty based on weights
					roll = random.randint(1, 100)
					cumulative = 0
					difficulty = 15  # Default
					for dc, weight in difficulty_weights:
						cumulative += weight
						if roll <= cumulative:
							difficulty = dc
							break
					tile_secrets[(x, y)] = difficulty
					tile_search_alpha[(x, y)] = 0.0  # Start with no visual enhancement
	
	# Count secrets by difficulty
	secret_counts = {}
	for dc in tile_secrets.values():
		secret_counts[dc] = secret_counts.get(dc, 0) + 1
	print(f"[SECRETS] Generated {len(tile_secrets)} secrets: {secret_counts}")

	# Brick exploration tracking for pygame mode
	if not using_loaded_save:
		bricks_touched = set()
		total_bricks = count_total_bricks(dungeon)
	else:
		bricks_touched = set(bricks_touched)
		if not total_bricks:
			total_bricks = count_total_bricks(dungeon)

	# Wall/floor exploration tracking for pygame mode
	if not using_loaded_save:
		walls_touched = set()
		floors_touched = set()
		floors_stepped = set()
	else:
		walls_touched = set(walls_touched)
		floors_touched = set(floors_touched)
		floors_stepped = set(floors_stepped)

	# Use reachable floors from player and exposed walls for fair totals
	reachable = compute_reachable_floors(dungeon, px, py)
	if not total_floors:
		total_floors = len(reachable)
	if not total_walls:
		total_walls = count_total_exposed_walls(dungeon, reachable)

	# Static ambient light sources (wall torches)
	if not torches:
		torches = generate_wall_torches(dungeon)
	torch_lookup = rebuild_torch_lookup(torches)
	if levels and 0 <= current_level_index < len(levels):
		levels[current_level_index]['torches'] = serialize_torches(torches)

	# Debug toggles/state
	debug_mode = False            # Ctrl+D toggles
	debug_show_all_visible = False
	debug_noclip = False
	light_radius = LIGHT_RADIUS   # dynamic light radius for pygame mode

	# Simple message log for bottom-left feedback
	message_log: list[dict] = []  # { 't': float, 'text': str }
	# One-run milestone tracker for exploration announcements
	announced_milestones: set[int] = set()

	def add_message(text: str) -> None:
		"""Add a message to the message log with timestamp.
		
		Automatically manages log size to prevent memory growth.
		
		Args:
			text (str): Message text to add to log
		"""
		# Keep log small to avoid memory growth
		message_log.append({'t': time.time(), 'text': str(text)})
		if len(message_log) > 200:
			del message_log[:50]

	# Load prefab library
	prefabs = load_prefabs(os.path.join(os.path.dirname(__file__), 'prefabs'))

	# Map style setting
	map_style = (SETTINGS.get('map_style', 'parchment') or 'parchment').lower()
	render_mode = (SETTINGS.get('render_mode', 'blocks') or 'blocks').lower()  # blocks | ascii

	# Font/glyph cache builder (rebuild on resize)
	preferred_fonts = ["Courier New", "Consolas", "Lucida Console", "DejaVu Sans Mono", "Monaco"]

	def build_font(ch_h: int) -> pygame.font.Font:
		"""Build optimal font for given cell height.
		
		Tries to find the largest font that fits exactly in the cell dimensions.
		Searches through preferred fonts and sizes to maximize crispness.
		
		Args:
			ch_h (int): Cell height in pixels
			
		Returns:
			pygame.font.Font: Font object optimized for the cell size
		"""
		# Improve crispness by choosing the largest font that fits the cell exactly
		# Try settings overrides first, then preferred list, scanning down sizes
		max_size = max(6, min(48, ch_h))
		font_file = (SETTINGS.get('font_file') or '').strip()
		font_name = (SETTINGS.get('font_name') or '').strip()
		candidates = []
		# Always prioritize Blocky Sketch.ttf
		blocky_sketch_path = os.path.join(os.path.dirname(__file__), "Blocky Sketch.ttf")
		if os.path.isfile(blocky_sketch_path):
			candidates.append(("file", blocky_sketch_path))
		if font_file:
			path = os.path.join(os.path.dirname(__file__), font_file)
			if os.path.isfile(path):
				candidates.append(("file", path))
		if font_name:
			candidates.append(("sys", font_name))
		for fam in preferred_fonts:
			candidates.append(("sys", fam))

		best = None
		for size in range(max_size, 5, -1):
			for kind, ident in candidates:
				try:
					f = pygame.font.Font(ident, size) if kind == "file" else pygame.font.SysFont(ident, size)
					# Measure a wide sample to ensure width/height fit in cell
					sample = "W#@"
					surf = f.render(sample, False, (255, 255, 255))
					gw = surf.get_width() // len(sample)
					gh = surf.get_height()
					if gw <= cell_w - 1 and gh <= cell_h - 1:
						return f
					# Track last font in case nothing fits; prefer Courier New
					if best is None and ident:
						best = f
				except Exception:
					continue
		# Fallback
		return best or pygame.font.Font(None, max(6, ch_h - 4))

	def build_glyph_cache(font_obj: pygame.font.Font):
		"""Build glyph rendering cache for performance.
		
		Creates a caching function that renders and stores glyph surfaces
		to avoid repeated font rendering operations.
		
		Args:
			font_obj (pygame.font.Font): Font to use for glyph rendering
			
		Returns:
			callable: Function that takes (char, color) and returns pygame.Surface
		"""
		# Characters we need to render
		ramp = " .:-=+*%"  # kept for potential future use
		glyphs_needed = {WALL_CH, PLAYER_CH}
		for extra in (DARK_CH, FLOOR_CH):
			if extra != ' ':
				glyphs_needed.add(extra)
		cache = {}
		antialias = bool(SETTINGS.get('font_antialias', True))
		def render_glyph(ch, color=(255, 255, 255), bold=False):
			key = (ch, color, bold)
			surf = cache.get(key)
			if surf is None:
				if bold:
					font_obj.set_bold(True)
				surf = font_obj.render(ch, antialias, color)
				if bold:
					font_obj.set_bold(False)
				cache[key] = surf
			return surf
		return render_glyph

	# Build fonts: regular for map, larger for UI panel, extra large for titles
	font = build_font(cell_h)
	ui_font = build_font(int(cell_h * 1.5))  # 1.5x larger for UI readability
	title_font = build_font(48)  # 48pt font for menu titles
	# Enable bold for title font for extra impact
	title_font.set_bold(True)

	# Build parchment background via renderer module (static, no animation). Disable vignette to avoid concentric rings.
	# Use cell_w as grain_tile to align texture pattern with character grid
	parchment_renderer = ParchmentRenderer(base_color=PARCHMENT_BG, ink_color=INK_DARK, enable_vignette=False, grain_tile=cell_w)
	parchment_renderer.build_layers(win_w, win_h)
	parchment_static = parchment_renderer.generate(win_w, win_h)
	# Build glyph renderers for all fonts
	# render_glyph: type ignore to work around nested function type inference issue
	render_glyph = build_glyph_cache(font)  # type: ignore
	render_ui_glyph = build_glyph_cache(ui_font)  # type: ignore
	render_title_glyph = build_glyph_cache(title_font)  # type: ignore

	try:
		os.makedirs(os.path.dirname(icon_path), exist_ok=True)
		icon_size = 64
		icon_surface = pygame.Surface((icon_size, icon_size))
		icon_surface.fill((0, 0, 0))
		glyph_surface = title_font.render('D', True, (255, 255, 255))
		gw, gh = glyph_surface.get_size()
		if gw == 0 or gh == 0:
			raise ValueError("Title font produced empty glyph")
		max_dim = icon_size - 8
		scale = min(1.0, max_dim / gw, max_dim / gh)
		if scale < 1.0:
			new_w = max(1, int(round(gw * scale)))
			new_h = max(1, int(round(gh * scale)))
			glyph_surface = pygame.transform.smoothscale(glyph_surface, (new_w, new_h))
		rect = glyph_surface.get_rect(center=(icon_size // 2, icon_size // 2))
		icon_surface.blit(glyph_surface, rect)
		pygame.image.save(icon_surface, icon_path)
		pygame.display.set_icon(icon_surface.convert())
	except Exception as icon_error:
		print(f"[UI] Failed to regenerate window icon: {icon_error}")

	# Prebuild texture patterns for different materials
	def build_material_texture(w, h, material_type):
		"""Create texture patterns specific to different material types."""
		pat = pygame.Surface((w, h), pygame.SRCALPHA)
		pat.fill((0, 0, 0, 0))
		
		if material_type == 'cobble':
			# Cobblestone: irregular stone pattern
			alpha = 120  # Much more visible
			dark_col = (*INK_DARK, alpha)
			light_col = (*WALL_LIGHT, alpha // 2)
			# Create irregular stone blocks
			for y in range(0, h, 3):
				for x in range(0, w, 4):
					# Vary block sizes slightly
					bw = min(3 + (x + y) % 2, w - x)
					bh = min(2 + (x + y) % 2, h - y)
					if (x + y) % 3 == 0:
						pat.fill(dark_col, (x, y, bw, 1))  # Top edge
						pat.fill(dark_col, (x, y, 1, bh))  # Left edge
					else:
						pat.fill(light_col, (x + bw - 1, y, 1, bh))  # Right highlight
		
		elif material_type == 'brick':
			# Brick: regular rectangular pattern
			alpha = 120  # Much more visible
			mortar_col = (*INK_DARK, alpha)
			highlight_col = (*WALL_LIGHT, alpha // 3)
			brick_w, brick_h = 6, 3
			for y in range(0, h, brick_h):
				offset = (brick_w // 2) if (y // brick_h) % 2 else 0
				for x in range(-offset, w, brick_w):
					if x >= 0 and y < h:
						# Mortar lines
						pat.fill(mortar_col, (x, y, min(brick_w, w - x), 1))
						pat.fill(mortar_col, (x, y, 1, min(brick_h, h - y)))
						# Brick highlight
						if x + brick_w - 1 < w and y + brick_h - 1 < h:
							pat.fill(highlight_col, (x + brick_w - 1, y + 1, 1, brick_h - 2))
		
		elif material_type == 'marble':
			# Marble: veined pattern
			alpha = 80  # More visible
			vein_col = (*INK_DARK, alpha)
			highlight_col = (*MARBLE_WHITE, alpha // 2)
			# Create diagonal veins
			for i in range(w + h):
				x = i % w
				y = (i * 2) % h
				if x < w and y < h:
					pat.fill(vein_col, (x, y, 1, 1))
				# Counter diagonal
				x2 = (w - 1 - i) % w
				y2 = (i * 3) % h
				if x2 < w and y2 < h and (x2 + y2) % 4 == 0:
					pat.fill(highlight_col, (x2, y2, 1, 1))
		
		elif material_type == 'wood':
			# Wood: grain pattern
			alpha = 90  # More visible
			grain_col = (*INK_DARK, alpha)
			highlight_col = (*WALL_LIGHT, alpha // 2)
			# Horizontal wood grain
			for y in range(0, h, 2):
				grain_y = y + ((y // 4) % 2)  # Slight wave
				if grain_y < h:
					for x in range(0, w, 3):
						pat.fill(grain_col, (x, grain_y, min(2, w - x), 1))
			# Vertical highlights
			for x in range(2, w, 8):
				for y in range(h):
					if (x + y) % 3 == 0:
						pat.fill(highlight_col, (x, y, 1, 1))
		
		elif material_type == 'iron':
			# Iron: metallic pattern with rivets
			alpha = 100  # More visible
			rivet_col = (*INK_DARK, alpha)
			highlight_col = (*IRON_GREY, alpha // 2)
			# Rivets in grid pattern
			for y in range(2, h, 6):
				for x in range(2, w, 6):
					# Rivet shadow
					pat.fill(rivet_col, (x, y, 2, 2))
					# Rivet highlight
					if x + 1 < w and y + 1 < h:
						pat.fill(highlight_col, (x + 1, y, 1, 1))
			# Metal panel lines
			for y in range(0, h, 8):
				pat.fill(rivet_col, (0, y, w, 1))
		
		else:
			# Default: simple checkerboard dither
			alpha = 100  # Much more visible
			col = (*INK_DARK, alpha)
			for y in range(0, h, 2):
				for x in range(0, w, 2):
					pat.fill(col, (x, y, 1, 1))
					if x + 1 < w and y + 1 < h:
						pat.fill(col, (x + 1, y + 1, 1, 1))
		
		return pat

	def build_dither_pattern(w, h):
		"""Build default dither pattern (backwards compatibility)."""
		return build_material_texture(w, h, 'default')

	# Create texture patterns for each material type
	texture_patterns = {}
	material_types = ['cobble', 'brick', 'marble', 'wood', 'iron', 'moss', 'sand', 'grass', 'water', 'lava', 'dirt', 'default']
	for mat_type in material_types:
		texture_patterns[mat_type] = build_material_texture(cell_w, cell_h, mat_type)
	
	def get_material_texture_name(mat_constant: int) -> str:
		"""Map material constants to texture names.
		
		Args:
			mat_constant (int): Material constant from dungeon_gen.py
			
		Returns:
			str: Corresponding texture name for the material
		"""
		material_map = {
			MAT_COBBLE: 'cobble',
			MAT_BRICK: 'brick', 
			MAT_DIRT: 'dirt',
			MAT_MOSS: 'moss',
			MAT_SAND: 'sand',
			MAT_IRON: 'iron',
			MAT_GRASS: 'grass',
			MAT_WATER: 'water',
			MAT_LAVA: 'lava',
			MAT_MARBLE: 'marble',
			MAT_WOOD: 'wood'
		}
		return material_map.get(mat_constant, 'default')
	
	def get_material_ascii_char_and_color(mat_constant: int, is_wall: bool) -> tuple[str, tuple[int, int, int]]:
		"""Get ASCII character and color for a material type.
		
		Args:
			mat_constant (int): Material constant from dungeon_gen.py
			is_wall (bool): True if this is a wall tile, False for floor
			
		Returns:
			tuple[str, tuple[int, int, int]]: Character and RGB color
		"""
		if is_wall:
			# WALLS: Use solid/dense characters - always clearly distinguishable from floors
			if mat_constant == MAT_BRICK:
				return '█', (80, 50, 30)  # SOLID block, dark brick brown
			elif mat_constant == MAT_IRON:
				return '█', (60, 66, 72)  # SOLID block, dark iron grey
			elif mat_constant == MAT_MARBLE:
				return '█', (120, 120, 128)  # SOLID block, darker marble
			elif mat_constant == MAT_WOOD:
				return '█', (86, 54, 32)  # SOLID block, dark wood brown
			elif mat_constant == MAT_MOSS:
				return '█', (42, 64, 44)  # SOLID block, dark moss green
			elif mat_constant == MAT_SAND:
				return '█', (126, 104, 60)  # SOLID block, dark sandstone
			elif mat_constant == MAT_DIRT:
				return '█', (70, 56, 40)  # SOLID block, dark dirt brown
			else:
				return '█', (90, 60, 40)  # SOLID block, dark default wall
		else:
			# FLOORS: Use very light colors nearly as light as parchment (245, 237, 215)
			if mat_constant == MAT_COBBLE:
				return ' ', (240, 232, 210)  # Nearly parchment with slight grey tint
			elif mat_constant == MAT_DIRT:
				return ' ', (240, 230, 200)  # Nearly parchment with slight brown tint
			elif mat_constant == MAT_MOSS:
				return ' ', (240, 240, 215)  # Nearly parchment with very slight green tint
			elif mat_constant == MAT_SAND:
				return ' ', (248, 240, 220)  # Nearly parchment with slight sand tint
			elif mat_constant == MAT_GRASS:
				return ' ', (242, 240, 218)  # Nearly parchment with very slight green tint
			elif mat_constant == MAT_WATER:
				return ' ', (235, 235, 220)  # Nearly parchment with very slight blue tint
			elif mat_constant == MAT_LAVA:
				return ' ', (248, 235, 210)  # Nearly parchment with very slight orange tint
			elif mat_constant == MAT_MARBLE:
				return ' ', (250, 245, 225)  # Slightly lighter than parchment
			elif mat_constant == MAT_WOOD:
				return ' ', (242, 232, 205)  # Nearly parchment with slight wood tint
			elif mat_constant == MAT_BRICK:
				return ' ', (243, 230, 200)  # Nearly parchment with slight brick tint
			elif mat_constant == MAT_IRON:
				return ' ', (240, 237, 220)  # Nearly parchment with very slight grey tint
			else:
				return ' ', (245, 235, 210)  # Nearly identical to parchment
	
	dither_pattern = build_dither_pattern(cell_w, cell_h)

	# Minimap reveal buffers (progress + noise) for watercolor effect
	mm_reveal = []  # type: list[list[float]]
	mm_noise = []   # type: list[list[float]]

	# World FoW reveal buffers (progress + noise) similar to minimap
	wr_reveal = []  # type: list[list[float]]
	wr_noise = []   # type: list[list[float]]

	def build_minimap_buffers(d: Dungeon):
		# progress 0..1 and static noise per tile
		reveal = [[0.0 for _ in range(d.h)] for _ in range(d.w)]
		noise = [[(random.random() * 0.3 - 0.15) for _ in range(d.h)] for _ in range(d.w)]
		# any already-explored tiles start fully revealed
		for (ex, ey) in explored:
			if 0 <= ex < d.w and 0 <= ey < d.h:
				reveal[ex][ey] = 1.0
		return reveal, noise

	# Minimap helper
	# Build initial buffers for current dungeon
	mm_reveal, mm_noise = build_minimap_buffers(dungeon)

	def build_world_reveal_buffers(d: Dungeon):
		# progress 0..1 and static noise per tile for world FoW
		reveal = [[0.0 for _ in range(d.h)] for _ in range(d.w)]
		noise = [[(random.random() * 0.3 - 0.15) for _ in range(d.h)] for _ in range(d.w)]
		for (ex, ey) in explored:
			if 0 <= ex < d.w and 0 <= ey < d.h:
				reveal[ex][ey] = 1.0
		return reveal, noise

	wr_reveal, wr_noise = build_world_reveal_buffers(dungeon)

	# One-frame alpha panel drawer in grid coordinates
	def draw_panel_grid(x_cells: int, y_cells: int, w_cells: int, h_cells: int, color: tuple[int, int, int] = (0,0,0), alpha: int = 128) -> None:
		"""Draw a translucent panel background with grid overlay.
		
		Args:
			x_cells (int): Starting X position in cell coordinates
			y_cells (int): Starting Y position in cell coordinates
			w_cells (int): Width in cell units
			h_cells (int): Height in cell units
			color (tuple[int, int, int]): RGB color for panel background
			alpha (int): Transparency level (0-255)
		"""
		if w_cells <= 0 or h_cells <= 0:
			return
		px0 = off_x + x_cells * cell_w
		py0 = off_y + y_cells * cell_h
		pw = max(0, w_cells * cell_w)
		ph = max(0, h_cells * cell_h)
		if pw <= 0 or ph <= 0:
			return
		s = pygame.Surface((pw, ph), pygame.SRCALPHA)
		r, g, b = color
		alpha = max(0, min(255, int(alpha)))
		s.fill((r, g, b, alpha))
		screen.blit(s, (px0, py0))

	def draw_message_log() -> None:
		"""Draw recent messages in bottom-left corner of screen.
		
		Displays up to 8 recent messages with fade effect based on age.
		Older messages become more transparent until they disappear.
		"""
		# Render a small translucent panel with last few messages at bottom-left of the map viewport
		# Make window 50% taller: from 4 to 6 lines
		max_lines = 6
		# width in cells within the map area
		width_cells = max(10, min(34, map_w - 2))
		if width_cells <= 0:
			return
		lines = [m['text'] for m in message_log[-max_lines:]]
		height_cells = len(lines) + 2 if lines else 0
		if height_cells <= 0:
			return
		x_cells = UI_COLS + 1
		y_cells = grid_h - height_cells
		# Panel background (darker ink, still translucent)
		darker_bg = scale_color(INK_DARK, 0.6)
		draw_panel_grid(x_cells, y_cells, width_cells, height_cells, darker_bg, alpha=150)
		# Title line (light-colored font)
		draw_text_line(x_cells + 1, y_cells, "Messages"[:width_cells - 2], MARBLE_WHITE, width_cells - 2)
		# Message lines (light-colored font)
		for i, text in enumerate(lines):
			draw_text_line(x_cells + 1, y_cells + 1 + i, ("- " + text)[:width_cells - 2], scale_color(MARBLE_WHITE, 0.92), width_cells - 2)

	def prepare_light_sources(player_x: int, player_y: int, radius: float, torch_list: list[dict], ticks: int) -> list[dict]:
		"""Build a list of dynamic light sources for the current frame."""
		sources: list[dict] = [{
			'pos': (player_x, player_y),
			'radius': max(1.0, float(radius)),
			'intensity': 1.0,
			'falloff': 'quadratic',
			'is_torch': False,
		}]
		for torch in torch_list:
			base = torch.get('base_intensity', TORCH_BASE_INTENSITY)
			phase = torch.get('phase', 0.0)
			flicker = 0.82 + 0.18 * math.sin(0.006 * ticks + phase)
			intensity = base * flicker
			torch['current_intensity'] = intensity
			sources.append({
				'pos': (torch['x'], torch['y']),
				'radius': torch.get('radius', TORCH_LIGHT_RADIUS),
				'intensity': intensity,
				'falloff': 'quadratic',
				'is_torch': True,
		})
		return sources

	def evaluate_light_sources(sources: list[dict], wx: int, wy: int) -> tuple[float, Optional[tuple[int, int]]]:
		"""Compute brightness contribution from light sources at given tile."""
		best_val = 0.0
		best_pos: Optional[tuple[int, int]] = None
		for src in sources:
			sx, sy = src['pos']
			dx = wx - sx
			dy = wy - sy
			dist = math.hypot(dx, dy)
			radius = src['radius']
			if dist > radius:
				continue
			if radius <= 1e-6:
				continue
			falloff = src.get('falloff', 'quadratic')
			if src.get('is_torch'):
				if dist > radius:
					continue
				norm = dist / radius
				val = src['intensity'] * max(0.0, 1.0 - norm * norm)
			elif falloff == 'linear':
				norm = dist / radius
				val = src['intensity'] * max(0.0, 1.0 - norm)
			else:
				norm = dist / radius
				val = src['intensity'] * max(0.0, 1.0 - norm * norm)
			if dist <= 0.5:
				val = max(val, src['intensity'])
			if val > best_val:
				best_val = val
				best_pos = (sx, sy)
		return best_val, best_pos

	def draw_torch_overlay(cell_x: int, cell_y: int, torch: dict) -> None:
		"""Render a small torch flame and sconce overlay in block mode."""
		intensity = clamp(torch.get('current_intensity', TORCH_BASE_INTENSITY), 0.5, 1.1)
		dir_x, dir_y = torch.get('dir', (0, 1))
		flame_height = max(4, int(cell_h * 0.45))
		flame_width = max(2, int(cell_w * 0.3))
		offset_x = int(dir_x * cell_w * 0.18)
		offset_y = int(dir_y * cell_h * 0.18)
		center_x = (cell_w - flame_width) // 2 + offset_x
		center_y = (cell_h - flame_height) // 2 + offset_y
		# Draw sconce/stem
		sconce_height = max(3, flame_height // 3)
		sconce_y = center_y + flame_height - sconce_height
		draw_cell_px_rect(cell_x, cell_y, center_x, sconce_y, flame_width, sconce_height, TORCH_SCONCE_COLOR, alpha=0.85)
		# Outer flame
		draw_cell_px_rect(cell_x, cell_y, center_x, center_y, flame_width, flame_height, TORCH_FLAME_COLOR, alpha=0.75 * intensity)
		# Inner ember/glow
		inner_width = max(1, flame_width - 2)
		inner_height = max(2, flame_height - 3)
		draw_cell_px_rect(cell_x, cell_y, center_x + (flame_width - inner_width) / 2, center_y + 1, inner_width, inner_height, TORCH_EMBER_COLOR, alpha=0.65 * intensity)

	# Simple wall-normal helper for directional lighting on walls
	def wall_normal(d: Dungeon, x: int, y: int):
		if not d.is_wall(x, y):
			return 0.0, 0.0
		nx, ny = 0.0, 0.0
		for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
			x2, y2 = x + dx, y + dy
			if 0 <= x2 < d.w and 0 <= y2 < d.h and not d.is_wall(x2, y2):
				# normal points toward open space
				nx += dx
				ny += dy
		# normalize
		length = math.hypot(nx, ny)
		if length > 1e-6:
			return nx / length, ny / length
		return 0.0, 0.0

	def draw_minimap(surface: pygame.Surface, dungeon: Dungeon, explored_set: set, visible_set: set, px: int, py: int, win_w: int, win_h: int) -> None:
		"""Draw minimap with fog-of-war and current visibility.
		
		Args:
			surface (pygame.Surface): Surface to draw the minimap on
			dungeon (Dungeon): Current dungeon to map
			explored_set (set): Set of explored tile coordinates
			visible_set (set): Set of currently visible tiles
			px (int): Player X coordinate
			py (int): Player Y coordinate
			win_w (int): Window width in pixels
			win_h (int): Window height in pixels
		"""
		mm = SETTINGS.get('minimap', {}) or {}
		if not mm.get('enabled', True):
			return
		t = int(mm.get('tile', 4))
		margin = int(mm.get('margin', 8))
		pos = (mm.get('position', 'top-right') or 'top-right').lower()
		
		# Calculate minimap size with automatic scaling for large dungeons
		max_minimap_width = win_w // 4  # Max 25% of screen width
		max_minimap_height = win_h // 3  # Max 33% of screen height
		
		w_px = dungeon.w * t
		h_px = dungeon.h * t
		
		# Scale down if minimap is too large
		if w_px > max_minimap_width or h_px > max_minimap_height:
			scale_w = max_minimap_width / w_px if w_px > max_minimap_width else 1.0
			scale_h = max_minimap_height / h_px if h_px > max_minimap_height else 1.0
			scale = min(scale_w, scale_h)
			t = max(1, int(t * scale))
			w_px = dungeon.w * t
			h_px = dungeon.h * t
		
		# Determine anchor position
		if pos == 'top-left':
			ox, oy = margin, margin
		elif pos == 'bottom-left':
			ox, oy = margin, win_h - h_px - margin
		elif pos == 'bottom-right':
			ox, oy = win_w - w_px - margin, win_h - h_px - margin
		else:  # top-right
			ox, oy = win_w - w_px - margin, margin

		# Fancy minimap frame: base fill + outer shadow + inner highlight + decorative studs
		frame_x = ox - 2
		frame_y = oy - 2
		frame_w = w_px + 4
		frame_h = h_px + 4
		outer = scale_color(INK_DARK, 0.6)
		inner = MARBLE_WHITE
		base = PARCHMENT_BG
		# Base fill
		pygame.draw.rect(surface, base, (frame_x, frame_y, frame_w, frame_h))
		# Outer shadow line (2px)
		pygame.draw.rect(surface, outer, (frame_x, frame_y, frame_w, frame_h), 2)
		# Inner highlight line (1px just inside)
		pygame.draw.rect(surface, inner, (frame_x + 2, frame_y + 2, frame_w - 4, frame_h - 4), 1)
		# Decorative studs every 4 tiles along vertical edges
		stud_w = max(2, min(4, t - 1))
		stud_h = max(2, min(4, t - 1))
		left_x = frame_x + 3
		right_x = frame_x + frame_w - 3 - stud_w
		for ty in range(0, dungeon.h, 4):
			sy_px = oy + ty * t + (t - stud_h) // 2
			if sy_px < frame_y + 2 or sy_px + stud_h > frame_y + frame_h - 2:
				continue
			pygame.draw.rect(surface, inner, (left_x, sy_px, stud_w, stud_h))
			pygame.draw.rect(surface, inner, (right_x, sy_px, stud_w, stud_h))

		# Colors for minimap - use same lighting and colors as main game view
		def mini_color(x, y, visible_now, alpha_reveal):
			if 0 <= x < dungeon.w and 0 <= y < dungeon.h:
				m = dungeon.materials[x][y]
				tile = dungeon.tiles[x][y]
				is_wall = (tile == TILE_WALL)
				
				# Get same base color as main game (respects wall vs floor distinction)
				_, base = get_material_ascii_char_and_color(m, is_wall)
				
				if visible_now:
					# Calculate lighting same as main game view
					dx = x - px
					dy = y - py
					d = math.sqrt(dx * dx + dy * dy)
					
					# Same lighting calculation as main game
					if d <= 1.0:
						tval = 1.0
					else:
						normalized_distance = d / light_radius
						tval = max(0.1, 1.0 - (normalized_distance * normalized_distance))
					
					# Apply lighting to base color (same as main game)
					return scale_color(base, tval)
				# FoW: much darker walls vs darker floors (match main game)
				def fow_scale_for_material(m2: int, a: float) -> float:
					a = clamp(a, 0.0, 1.0)
					if m2 == MAT_BRICK or m2 == MAT_IRON:
						s_min, s_max = 0.06, 0.15
					else:
						s_min, s_max = 0.15, 0.30
					return s_min + a * (s_max - s_min)
				s = fow_scale_for_material(m, alpha_reveal)
				return scale_color(base, s)
			return INK_DARK

		def lerp(c1, c2, a):
			ar = clamp(a, 0.0, 1.0)
			return (
				int(c1[0] + (c2[0] - c1[0]) * ar),
				int(c1[1] + (c2[1] - c1[1]) * ar),
				int(c1[2] + (c2[2] - c1[2]) * ar),
			)
		wall_boost = 30

		for y in range(dungeon.h):
			for x in range(dungeon.w):
				rect = (ox + x * t, oy + y * t, t, t)
				if (x, y) in explored_set or (x, y) in visible_set:
					# watercolor-like reveal from parchment using per-tile progress and noise
					prog = mm_reveal[x][y] if 0 <= x < dungeon.w and 0 <= y < dungeon.h else 1.0
					noi = mm_noise[x][y] if 0 <= x < dungeon.w and 0 <= y < dungeon.h else 0.0
					alpha = clamp(pow(clamp(prog + noi, 0.0, 1.0), 1.8), 0.0, 1.0)
					c_target = mini_color(x, y, (x, y) in visible_set, alpha)
					c = lerp(PARCHMENT_BG, c_target, alpha)
					surface.fill(c, rect)
		else:
			# unseen stays black (implicit)
			pass

		# === Gold glow for fully searched areas (outermost perimeter only) ===
		# Light gold color (255, 215, 0) with transparency
		gold_color = (255, 215, 0)
		
		# Find all tiles that are fully searched (illumination >= 1.0)
		# Draw glow on ANY tile (wall or floor) that borders an unsearched area
		for y in range(dungeon.h):
			for x in range(dungeon.w):
				if tile_illumination_source.get((x, y)) == 'player' and tile_illumination_alpha.get((x, y), 0.0) >= 1.0:
					# Check which sides of this tile face unsearched areas
					# Draw glow lines only on those outer edges
					px = ox + x * t
					py = oy + y * t
					
					glow_surf = pygame.Surface((t, t), pygame.SRCALPHA)
					
					# Check each cardinal direction
					# Top
					if (x, y-1) not in tile_illumination_alpha or tile_illumination_alpha.get((x, y-1), 0.0) < 1.0:
						for i in range(2):
							alpha = 100 - (i * 35)  # 100, 65
							glow_color_alpha = (*gold_color, alpha)
							offset = i
							pygame.draw.line(glow_surf, glow_color_alpha, (0, offset), (t, offset), 1)
					# Bottom
					if (x, y+1) not in tile_illumination_alpha or tile_illumination_alpha.get((x, y+1), 0.0) < 1.0:
						for i in range(2):
							alpha = 100 - (i * 35)
							glow_color_alpha = (*gold_color, alpha)
							offset = i
							pygame.draw.line(glow_surf, glow_color_alpha, (0, t-1-offset), (t, t-1-offset), 1)
					# Left
					if (x-1, y) not in tile_illumination_alpha or tile_illumination_alpha.get((x-1, y), 0.0) < 1.0:
						for i in range(2):
							alpha = 100 - (i * 35)
							glow_color_alpha = (*gold_color, alpha)
							offset = i
							pygame.draw.line(glow_surf, glow_color_alpha, (offset, 0), (offset, t), 1)
					# Right
					if (x+1, y) not in tile_illumination_alpha or tile_illumination_alpha.get((x+1, y), 0.0) < 1.0:
						for i in range(2):
							alpha = 100 - (i * 35)
							glow_color_alpha = (*gold_color, alpha)
							offset = i
							pygame.draw.line(glow_surf, glow_color_alpha, (t-1-offset, 0), (t-1-offset, t), 1)
					
					surface.blit(glow_surf, (px, py))

		# Player marker (bright green) - draw last so it's on top
		pr = (ox + px * t, oy + py * t, t, t)
		surface.fill(PLAYER_GREEN, pr)

	# No resize in fixed-window mode

	# Centering offsets (updated each frame based on current sizes)
	def compute_offsets():
		vw = cell_w * grid_w
		vh = cell_h * grid_h
		off_x = (win_w - vw) // 2
		off_y = (win_h - vh) // 2
		return off_x, off_y

	def draw_char_at(cell_x: int, cell_y: int, ch: str, color: tuple[int, int, int], use_ui_font: bool = False, use_title_font: bool = False, bold: bool = False) -> None:
		"""Draw a character glyph at specified cell coordinates.
		
		Args:
			cell_x (int): X coordinate in cell units
			cell_y (int): Y coordinate in cell units
			ch (str): Character to draw
			color (tuple[int, int, int]): RGB color for the character
			use_ui_font (bool): If True, use larger UI font instead of map font
			use_title_font (bool): If True, use extra large title font (48pt)
			bold (bool): If True, render text in bold
		"""
		if ch == ' ':
			return
		if use_title_font:
			surf = render_title_glyph(ch, color, bold)
		elif use_ui_font:
			surf = render_ui_glyph(ch, color, bold)
		else:
			surf = render_glyph(ch, color, bold)
		gx = off_x + cell_x * cell_w + (cell_w - surf.get_width()) // 2
		gy = off_y + cell_y * cell_h + (cell_h - surf.get_height()) // 2
		screen.blit(surf, (gx, gy))

	def draw_block_at(cell_x: int, cell_y: int, color: tuple[int, int, int], inset: int = 0, with_dither: bool = True, material_type: str = 'default') -> None:
		"""Draw a colored block at specified cell coordinates.
		
		Args:
			cell_x (int): X coordinate in cell units
			cell_y (int): Y coordinate in cell units
			color (tuple[int, int, int]): RGB color for the block
			inset (int): Pixel inset from cell edges (creates border)
			with_dither (bool): Whether to apply texture pattern
			material_type (str): Type of material texture to apply
		"""
		# Fill a solid rectangle for the cell, optional inset for borders
		px = off_x + cell_x * cell_w + inset
		py = off_y + cell_y * cell_h + inset
		pw = max(0, cell_w - inset * 2)
		ph = max(0, cell_h - inset * 2)
		if pw <= 0 or ph <= 0:
			return
		screen.fill(color, (px, py, pw, ph))
		
		if with_dither:
			# Use material-specific texture pattern
			pattern = texture_patterns.get(material_type, dither_pattern)
			if pattern is not None:
				try:
					# Use a clipped blit to match inset, but ensure we don't exceed pattern bounds
					if inset > 0 and inset * 2 < min(pattern.get_width(), pattern.get_height()):
						# Create a subsurface that fits within both the pattern and target rectangle
						clip_w = min(pw, pattern.get_width() - inset)
						clip_h = min(ph, pattern.get_height() - inset)
						if clip_w > 0 and clip_h > 0:
							src = pattern.subsurface((inset, inset, clip_w, clip_h))
							screen.blit(src, (px, py))
					else:
						# No inset or inset too large, use full pattern
						screen.blit(pattern, (px, py), (0, 0, pw, ph))
				except pygame.error:
					# Fallback: just skip the texture if there's an issue
					pass

	def draw_overlay_at(cell_x, cell_y, color, alpha, inset=0):
		# Alpha-blended rectangle on top of parchment/world for subtle fades
		px = off_x + cell_x * cell_w + inset
		py = off_y + cell_y * cell_h + inset
		pw = max(0, cell_w - inset * 2)
		ph = max(0, cell_h - inset * 2)
		if pw <= 0 or ph <= 0:
			return
		alpha = clamp(alpha, 0.0, 1.0)
		if alpha <= 0.0:
			return
		s = pygame.Surface((pw, ph), pygame.SRCALPHA)
		r, g, b = color
		s.fill((r, g, b, int(255 * alpha)))
		screen.blit(s, (px, py))

	def draw_cell_px_rect(cell_x, cell_y, rx, ry, rw, rh, color, alpha=None):
		# Draw a pixel-precise rectangle inside a cell
		px = off_x + cell_x * cell_w + int(rx)
		py = off_y + cell_y * cell_h + int(ry)
		rw = int(max(0, rw))
		rh = int(max(0, rh))
		if rw <= 0 or rh <= 0:
			return
		if alpha is None:
			pygame.draw.rect(screen, color, (px, py, rw, rh))
		else:
			s = pygame.Surface((rw, rh), pygame.SRCALPHA)
			r, g, b = color
			s.fill((r, g, b, int(255 * clamp(alpha, 0.0, 1.0))))
			screen.blit(s, (px, py))

	def draw_text_line(cell_x, cell_y, text, color=(180, 180, 180), max_len=None, use_ui_font=False, use_title_font=False, bold=False):
		if max_len is None:
			max_len = len(text)
		for i, ch in enumerate(text[:max_len]):
			draw_char_at(cell_x + i, cell_y, ch, color, use_ui_font=use_ui_font, use_title_font=use_title_font, bold=bold)

	# Session state: multi-level support
	if not using_loaded_save:
		levels = []  # list of dicts: dungeon/explored/player + touched/totals for bricks, walls, floors
		current_level_index = 0

	def snapshot_current():
		return {
			'dungeon': dungeon,
			'explored': set(explored),
			'player': (px, py),
			'bricks_touched': set(bricks_touched),
			'total_bricks': int(total_bricks),
			'walls_touched': set(walls_touched),
			'floors_touched': set(floors_touched),
			'floors_stepped': set(floors_stepped),
			'total_walls': int(total_walls),
			'total_floors': int(total_floors),
			'torches': serialize_torches(torches),
		}

	def collect_levels_for_save(level_list):
		out = []
		for lvl in level_list:
			d = lvl['dungeon']
			exp = lvl['explored']
			pxx, pyy = lvl['player']
			bt = lvl.get('bricks_touched', set())
			tb = lvl.get('total_bricks')
			if tb is None:
				tb = count_total_bricks(d)
			wt = lvl.get('walls_touched', set())
			ft = lvl.get('floors_touched', set())
			fs = lvl.get('floors_stepped', set())
			tw = lvl.get('total_walls')
			tf = lvl.get('total_floors')
			if tw is None or tf is None:
				# compute fair totals based on reachability from saved player pos
				pf_x, pf_y = int(pxx), int(pyy)
				rf = compute_reachable_floors(d, pf_x, pf_y)
				tf = len(rf)
				tw = count_total_exposed_walls(d, rf)
			out.append({
				'w': d.w,
				'h': d.h,
				'tiles': encode_tiles(d),
				'materials': encode_materials(d),
				'explored': list(sorted(exp)),
				'player': [pxx, pyy],
				'bricks_touched': list(sorted(bt)),
				'total_bricks': int(tb),
				'walls_touched': list(sorted(wt)),
				'floors_touched': list(sorted(ft)),
				'floors_stepped': list(sorted(fs)),
				'total_walls': int(tw),
				'total_floors': int(tf),
				'torches': serialize_torches(deserialize_torches(lvl.get('torches', []))),
			})
		return out

	def push_new_level() -> None:
		"""Generate and switch to a new dungeon level.
		
		Saves current level state, generates new dungeon with same dimensions,
		resets player position to first room, and updates all tracking variables.
		Updates the global level list and switches context to new level.
		"""
		nonlocal dungeon, fov, explored, px, py, current_level_index
		nonlocal mm_reveal, mm_noise, wr_reveal, wr_noise
		nonlocal bricks_touched, total_bricks, walls_touched, floors_touched, floors_stepped, total_walls, total_floors
		nonlocal torches, torch_lookup
		# Save snapshot of current first
		if levels:
			levels[current_level_index] = snapshot_current()
		# Create new level same size as current dungeon window
		dungeon_params = {
			'width': map_w,
			'height': grid_h,
			'complexity': SETTINGS.get('dungeon_complexity', 0.2),
			'length': SETTINGS.get('dungeon_length', 25),
			'room_min': SETTINGS.get('dungeon_room_min', 4),
			'room_max': SETTINGS.get('dungeon_room_max', 9),
			'linearity': SETTINGS.get('dungeon_linearity', 0.8),
			'entropy': SETTINGS.get('dungeon_entropy', 0.0),
		}
		nd = generate_dungeon(**dungeon_params)
		# Place player at center of first room in new level
		if nd.rooms:
			room = nd.rooms[0]
			pxn, pyn = room.center()
			
			# Ensure player starts on a floor tile within the room
			if nd.is_wall(pxn, pyn):
				# Search for a floor tile within the room bounds
				found = False
				room_w = room.x2 - room.x1
				room_h = room.y2 - room.y1
				for dx in range(-(room_w//2), room_w//2 + 1):
					for dy in range(-(room_h//2), room_h//2 + 1):
						x, y = pxn + dx, pyn + dy
						if (room.x1 < x < room.x2 - 1 and room.y1 < y < room.y2 - 1 and 
							not nd.is_wall(x, y)):
							pxn, pyn = x, y
							found = True
							break
					if found:
						break
		else:
			pxn, pyn = 1, 1
		# switch to new level
		dungeon = nd
		fov = FOV(dungeon)
		explored = set()
		px, py = pxn, pyn
		bricks_touched = set()
		total_bricks = count_total_bricks(dungeon)
		walls_touched = set()
		floors_touched = set()
		floors_stepped = set()
		# fair totals for new level
		rf = compute_reachable_floors(dungeon, px, py)
		total_floors = len(rf)
		total_walls = count_total_exposed_walls(dungeon, rf)
		torches = generate_wall_torches(dungeon)
		torch_lookup = rebuild_torch_lookup(torches)
		levels.append({
			'dungeon': dungeon,
			'explored': explored,
			'player': (px, py),
			'bricks_touched': bricks_touched,
			'total_bricks': total_bricks,
			'walls_touched': walls_touched,
			'floors_touched': floors_touched,
			'floors_stepped': floors_stepped,
			'total_walls': total_walls,
			'total_floors': total_floors,
			'torches': serialize_torches(torches),
		})
		# rebuild minimap/world buffers for new level
		mm_reveal, mm_noise = build_minimap_buffers(dungeon)
		wr_reveal, wr_noise = build_world_reveal_buffers(dungeon)
		current_level_index = len(levels) - 1
		levels[current_level_index]['torches'] = serialize_torches(torches)
		add_message("New level created.")

	# Initialize with first level for new games
	if not levels:
		px, py = (dungeon.rooms[0].center() if dungeon.rooms else (1, 1))
		levels.append({
			'dungeon': dungeon,
			'explored': explored,
			'player': (px, py),
			'bricks_touched': bricks_touched,
			'total_bricks': total_bricks,
			'walls_touched': walls_touched,
			'floors_touched': floors_touched,
			'floors_stepped': floors_stepped,
			'total_walls': total_walls,
			'total_floors': total_floors,
			'torches': serialize_torches(torches),
		})
		current_level_index = 0

	# build minimap and world FoW buffers for current level
	mm_reveal, mm_noise = build_minimap_buffers(dungeon)
	wr_reveal, wr_noise = build_world_reveal_buffers(dungeon)

	# Mark starting tile as stepped if it's a floor (new games only)
	if not using_loaded_save and 0 <= px < dungeon.w and 0 <= py < dungeon.h and dungeon.tiles[px][py] == TILE_FLOOR:
		floors_stepped.add((px, py))
		levels[current_level_index]['floors_stepped'] = floors_stepped
	levels[current_level_index]['torches'] = serialize_torches(torches)

	# Welcome message with character name
	if player_character:
		add_message(f"Welcome, {player_character.name} the {player_character.race} {player_character.char_class}!")
		add_message(f"HP: {player_character.current_hp}/{player_character.max_hp}, AC: {player_character.armor_class}")
	else:
		add_message("Welcome to the dungeon.")

	# Initialize water drip sound effect controller (but don't start yet)
	sound_generator = None
	try:
		sound_generator = get_sound_generator()
		drip_sfx = get_water_drip_sfx()
		if drip_sfx:
			drip_sfx.set_master_volume(0.5)
			drip_sfx.set_interval_range(9000, 18000)
		drip_started = drip_sfx.active
	except Exception as e:
		print(f"Could not load water-drip sounds: {e}")
		drip_sfx = None
		drip_started = False

	ambient_bat_enabled = bool(SETTINGS.get('ambient_bats', True))
	ambient_bat_next_time = 0
	ambient_bat_interval_min = max(3000, int(SETTINGS.get('ambient_bat_interval_min', 8000)))
	ambient_bat_interval_max = int(SETTINGS.get('ambient_bat_interval_max', 18000))
	if ambient_bat_interval_max <= ambient_bat_interval_min:
		ambient_bat_interval_max = ambient_bat_interval_min + 5000
	ambient_bat_volume_scale = clamp(float(SETTINGS.get('ambient_bat_volume_scale', 0.6)), 0.0, 1.0)
	ambient_bat_volume = clamp(float(SETTINGS.get('sound_volume', 0.8)) * ambient_bat_volume_scale, 0.0, 1.0)
	if sound_generator is None:
		ambient_bat_enabled = False

	def schedule_next_bat_squeak(now_ms: int) -> int:
		return now_ms + random.randint(ambient_bat_interval_min, ambient_bat_interval_max)

	# Dungeon fade-in effect
	dungeon_fade_alpha = 0.0  # Start fully transparent
	dungeon_fade_duration = 2.0  # Fade in over 2 seconds
	dungeon_fade_complete = False

	# Menu state
	menu_open = False
	menu_mode = 'main'  # main | settings | save | load
	menu_index = 0
	save_name = ""
	load_index = 0
	load_names = []

	# Create dark granite parchment for menu (generated once, cached)
	menu_parchment = None
	def get_menu_parchment():
		nonlocal menu_parchment
		if menu_parchment is None:
			# Dark granite color (dark grey-brown)
			GRANITE_BASE = (45, 45, 50)  # Dark bluish-grey like granite
			GRANITE_INK = (20, 20, 22)   # Even darker for texture
			menu_parch_renderer = ParchmentRenderer(
				base_color=GRANITE_BASE,
				ink_color=GRANITE_INK,
				enable_vignette=True,
				vignette_steps=16,
				grain_tile=cell_w,
				blotch_count=60,
				fiber_count=40,
				speckle_count=400
			)
			box_w = 58
			box_h = 24
			wpx = box_w * cell_w
			hpx = box_h * cell_h
			menu_parch_renderer.build_layers(wpx, hpx, seed=42)  # Fixed seed for consistency
			menu_parchment = menu_parch_renderer.generate(wpx, hpx)
		return menu_parchment

	def draw_menu():
		# DnD-style ASCII menu frame + banner
		box_w = 58
		box_h = 24
		x0 = (grid_w - box_w) // 2
		y0 = (grid_h - box_h) // 2

		# Colors - light text on dark granite parchment
		frame_col = MARBLE_WHITE
		title_col = WALL_LIGHT  # Golden brown for titles
		text_col = MARBLE_WHITE
		dim_col = scale_color(MARBLE_WHITE, 0.5)

		# Blit dark granite parchment background behind the menu
		off_x, off_y = compute_offsets()
		px = off_x + x0 * cell_w
		py = off_y + y0 * cell_h
		wpx = box_w * cell_w
		hpx = box_h * cell_h
		menu_bg = get_menu_parchment()
		screen.blit(menu_bg, (px, py))

		# Border (clean, high-contrast, no noisy fill)
		# Top and bottom
		for x in range(box_w):
			ch = '=' if 0 < x < box_w - 1 else '+'
			draw_char_at(x0 + x, y0, ch, frame_col)
			draw_char_at(x0 + x, y0 + box_h - 1, ch, frame_col)
		# Sides
		for y in range(1, box_h - 1):
			draw_char_at(x0, y0 + y, '|', frame_col)
			draw_char_at(x0 + box_w - 1, y0 + y, '|', frame_col)
		# Interior left blank (background already filled)

		# Large title text at 3x size
		title_text = "DUNGEON MENU"
		# Calculate position to center the title (accounting for 3x font size taking more space)
		# With 3x font, each character takes approximately 3 cells of width
		title_width_cells = len(title_text) * 3
		title_x = x0 + (box_w - title_width_cells) // 2
		title_y = y0 + 2
		draw_text_line(title_x, title_y, title_text, title_col, use_title_font=True)
		
		# Decorative border under title (using regular font)
		border_line = "=" * (box_w - 6)
		draw_text_line(x0 + 3, y0 + 5, border_line, dim_col)

		def draw_opts(opts, sel_idx, ystart):
			for i, text in enumerate(opts):
				selected = (i == sel_idx)
				col = title_col if selected else text_col
				prefix = ">> " if selected else "   "
				suffix = " <<" if selected else ""
				line = f"{prefix}{text}{suffix}"
				draw_text_line(x0 + 3, y0 + ystart + i, line, col, box_w - 6)

		if menu_mode == 'main':
			options = ["Character Creator", "Settings", "Save", "Load", "Quit"]
			draw_opts(options, menu_index, 8)  # Moved down from 6 to 8
		elif menu_mode == 'settings':
			# Volume sliders
			music_vol = int(SETTINGS.get('music_volume', 0.7) * 100)
			sound_vol = int(SETTINGS.get('sound_volume', 0.8) * 100)
			
			# Toggle settings
			hud = "On" if SETTINGS.get('hud_text', True) else "Off"
			mm = SETTINGS.get('minimap', {})
			mme = "On" if (mm.get('enabled', True)) else "Off"
			glow = "On" if SETTINGS.get('show_gold_glow', True) else "Off"
			render = SETTINGS.get('render_mode', 'blocks').capitalize()
			auto_search = "On" if SETTINGS.get('auto_search', False) else "Off"
			
			options = [
				f"Music Volume: {music_vol}%",
				f"Sound Volume: {sound_vol}%",
				f"HUD Text: {hud}",
				f"Minimap: {mme}",
				f"Gold Glow: {glow}",
				f"Render Mode: {render}",
				f"Auto Search: {auto_search}",
				"Back"
			]
			draw_opts(options, menu_index, 8)
		elif menu_mode == 'save':
			prompt = "Name thy hero and press Enter:"
			draw_text_line(x0 + 3, y0 + 8, prompt, text_col, box_w - 6)  # Moved down from 6 to 8
			draw_text_line(x0 + 3, y0 + 10, "> " + save_name, title_col, box_w - 6)  # Moved down from 8 to 10
			draw_text_line(x0 + 3, y0 + box_h - 3, "Esc: Back", dim_col)
		elif menu_mode == 'load':
			if not load_names:
				draw_text_line(x0 + 3, y0 + 8, "No chronicles found.", text_col)  # Moved down from 6 to 8
				draw_text_line(x0 + 3, y0 + box_h - 3, "Esc: Back", dim_col)
			else:
				draw_text_line(x0 + 3, y0 + 8, "Select a chronicle:", text_col)  # Moved down from 6 to 8
				for i, nm in enumerate(load_names):
					col = title_col if i == load_index else text_col
					prefix = ">> " if i == load_index else "   "
					draw_text_line(x0 + 3, y0 + 8 + i, prefix + nm, col, box_w - 6)
					draw_text_line(x0 + 3, y0 + box_h - 3, "Enter: Load | Esc: Back", dim_col)

	# Inventory state
	inventory_open = False
	inventory_main_slot = 0  # Which of the 8 main slots is selected (0-7)
	inventory_viewing_container = False  # Are we looking inside a container?
	inventory_container_slot = 0  # Which slot in the container is selected
	inventory_scroll_offset = 0  # Scroll offset for inventory list
	inventory_viewing_paperdoll = False  # Are we navigating equipped items with TAB?
	inventory_paperdoll_slot = 0  # Which equipment slot is selected (0-12)
	inventory_prompt_mode = None  # 'equip_or_use' when showing disambiguation prompt
	inventory_prompt_item = None  # Item being prompted about

	# Create dark brown parchment for inventory (generated once, cached)
	inventory_parchment = None
	def get_inventory_parchment():
		nonlocal inventory_parchment
		if inventory_parchment is None:
			# Dark brown parchment color (aged leather/wood tone)
			DARK_BROWN_BASE = (52, 38, 28)  # Dark brown leather/aged parchment
			DARK_BROWN_INK = (30, 22, 16)   # Even darker brown for texture
			inv_parch_renderer = ParchmentRenderer(
				base_color=DARK_BROWN_BASE,
				ink_color=DARK_BROWN_INK,
				enable_vignette=True,
				vignette_steps=20,
				grain_tile=cell_w,
				blotch_count=100,
				fiber_count=70,
				speckle_count=600
			)
			inv_parch_renderer.build_layers(win_w, win_h, seed=123)  # Fixed seed for consistency
			inventory_parchment = inv_parch_renderer.generate(win_w, win_h)
		return inventory_parchment

	def draw_inventory_slotbased():
		"""Draw inventory with paperdoll equipment system and info panel at bottom"""
		nonlocal inventory_main_slot, inventory_viewing_container, inventory_container_slot
		nonlocal inventory_scroll_offset, inventory_viewing_paperdoll, inventory_paperdoll_slot
		nonlocal inventory_prompt_mode, inventory_prompt_item
		
		if not player_character:
			return
		
		# Get character inventory (convert old list-based to slot-based if needed)
		if not hasattr(player_character, 'inventory') or not isinstance(getattr(player_character, 'inventory', None), CharacterInventory):
			player_character.inventory = CharacterInventory()
			if hasattr(player_character, 'equipment') and player_character.equipment:
				equipment_db = load_equipment_database()
				db_lookup = {item.name: item for item in equipment_db}
				for item_name in player_character.equipment:
					if item_name in db_lookup:
						player_character.inventory.add_item_auto(db_lookup[item_name])
		
		# Initialize equipment (paperdoll) if not present
		if not hasattr(player_character, 'equipped'):
			setattr(player_character, 'equipped', CharacterEquipment())
		
		inv = getattr(player_character, 'inventory', CharacterInventory())
		equipped = getattr(player_character, 'equipped', CharacterEquipment())
		
		# Colors - Match main UI palette
		frame_col = MARBLE_WHITE
		title_col = WALL_LIGHT  # Golden brown for titles, matching game UI highlights
		text_col = MARBLE_WHITE
		dim_col = scale_color(MARBLE_WHITE, 0.5)  # Dimmed white text
		highlight_col = WALL_LIGHT  # Golden brown for selection highlight
		paperdoll_highlight = scale_color(WALL_LIGHT, 0.9)  # Slightly brighter for paperdoll
		
		# Full screen background - Use dark brown parchment
		inv_bg = get_inventory_parchment()
		screen.blit(inv_bg, (0, 0))
		
		# Layout: Left = inventory list, Right = paperdoll, Bottom 8 lines = info panel
		INFO_PANEL_HEIGHT = 8
		info_panel_y = grid_h - INFO_PANEL_HEIGHT
		inventory_max_y = info_panel_y - 1
		
		# === CHARACTER STATS HEADER (Top section) ===
		header_y = 1
		
		# Title with character name and class/race
		title = f"{player_character.name} - Lvl {player_character.level} {player_character.race} {player_character.char_class}"
		draw_text_line(2, header_y, title, title_col, bold=True)
		header_y += 1
		
		# Alignment and XP
		align_xp = f"Alignment: {player_character.alignment} | XP: {player_character.xp}"
		draw_text_line(2, header_y, align_xp, text_col)
		header_y += 1
		
		# Combat stats line
		total_ac = player_character.armor_class + equipped.get_total_ac_bonus()
		combat_stats = f"HP: {player_character.current_hp}/{player_character.max_hp} | AC: {total_ac} | THAC0: {player_character.thac0}"
		draw_text_line(2, header_y, combat_stats, text_col)
		header_y += 1
		
		# Ability scores (all 6 in two rows)
		ability_line1 = f"STR: {player_character.strength:2d}  DEX: {player_character.dexterity:2d}  CON: {player_character.constitution:2d}"
		ability_line2 = f"INT: {player_character.intelligence:2d}  WIS: {player_character.wisdom:2d}  CHA: {player_character.charisma:2d}"
		draw_text_line(2, header_y, ability_line1, text_col)
		header_y += 1
		draw_text_line(2, header_y, ability_line2, text_col)
		header_y += 1
		
		# Resources and weight
		total_weight = inv.get_total_weight() + equipped.get_equipped_weight()
		item_count = inv.get_item_count()
		resources = f"Gold: {player_character.gold}gp | Weight: {total_weight:.1f} lbs | Items: {item_count}"
		draw_text_line(2, header_y, resources, text_col)
		header_y += 1
		
		# Separator line
		draw_text_line(2, header_y, "=" * (grid_w - 4), dim_col)
		header_y += 1
		
		# Help text - context sensitive
		if inventory_prompt_mode == 'equip_or_use':
			help_text = "E: Equip | U: Use | ESC: Cancel"
		elif inventory_viewing_paperdoll:
			help_text = "TAB: Navigate Equipment | ENTER: Unequip | ESC/TAB: Back"
		elif inventory_viewing_container:
			help_text = "UP/DOWN: Navigate | LEFT/ESC: Back | TAB: View Equipment"
		else:
			help_text = "UP/DOWN: Navigate | ENTER: Equip/Open | TAB: View Equipment | ESC: Close"
		draw_text_line(2, header_y, help_text[:grid_w - 4], dim_col)
		header_y += 1
		
		# === LEFT PANEL: Scrollable Inventory List ===
		left_x = 2
		left_y = header_y + 1
		left_width = 45
		list_max_height = inventory_max_y - left_y
		
		# Build flattened inventory list for display
		inventory_display_list = []
		
		if inventory_viewing_container:
			# Show container contents
			selected_item = inv.slots[inventory_main_slot] if 0 <= inventory_main_slot < len(inv.slots) else None
			if selected_item and selected_item.is_container:
				for i, content_item in enumerate(selected_item.contents):
					inventory_display_list.append({
						'type': 'container_item',
						'index': i,
						'item': content_item,
						'selectable': True
					})
		else:
			# Show main 8 slots and optionally expand containers
			for slot_num in range(CharacterInventory.BASE_SLOTS):
				item = inv.slots[slot_num]
				inventory_display_list.append({
					'type': 'main_slot',
					'index': slot_num,
					'item': item,
					'selectable': True
				})
		
		# Calculate scroll
		total_items = len(inventory_display_list)
		if inventory_viewing_container:
			current_selection = inventory_container_slot
		else:
			current_selection = inventory_main_slot
		
		# Auto-scroll to keep selection visible
		if current_selection < inventory_scroll_offset:
			inventory_scroll_offset = current_selection
		if current_selection >= inventory_scroll_offset + list_max_height:
			inventory_scroll_offset = current_selection - list_max_height + 1
		inventory_scroll_offset = max(0, min(inventory_scroll_offset, max(0, total_items - list_max_height)))
		
		# Draw inventory header
		if inventory_viewing_container:
			selected_container = inv.slots[inventory_main_slot] if 0 <= inventory_main_slot < len(inv.slots) else None
			if selected_container and selected_container.is_container:
				header = f"=== {selected_container.name.upper()} ==="
				draw_text_line(left_x, left_y, header[:left_width], title_col)
				left_y += 1
				capacity = f"{selected_container.get_container_info()}"
				draw_text_line(left_x, left_y, capacity[:left_width], dim_col)
				left_y += 1
		else:
			draw_text_line(left_x, left_y, "=== INVENTORY (8 SLOTS) ===", title_col)
			left_y += 1
		
		draw_text_line(left_x, left_y, "-" * left_width, dim_col)
		left_y += 1
		list_start_y = left_y
		
		# Draw visible inventory items
		for i in range(list_max_height):
			display_index = inventory_scroll_offset + i
			if display_index >= len(inventory_display_list):
				break
			
			entry = inventory_display_list[display_index]
			is_selected = (entry['index'] == current_selection and not inventory_viewing_paperdoll)
			col = highlight_col if is_selected else (text_col if entry['item'] else dim_col)
			prefix = "> " if is_selected else "  "
			
			if entry['item'] is None:
				line = f"{prefix}[{entry['index']+1}] <empty>"
			else:
				item = entry['item']
				name_display = item.name[:28]
				if item.is_container:
					container_info = item.get_container_info()
					line = f"{prefix}[{entry['index']+1}] {name_display} [{container_info}]"
				else:
					weight_str = f"{item.get_effective_weight():.1f}lb"
					line = f"{prefix}[{entry['index']+1}] {name_display} ({weight_str})"
			
			# Draw with bold if selected
			draw_text_line(left_x, list_start_y + i, line[:left_width], col, bold=is_selected)
		
		# Scroll indicators
		if inventory_scroll_offset > 0:
			draw_text_line(left_x + left_width - 5, list_start_y - 1, "▲", dim_col)
		if inventory_scroll_offset + list_max_height < total_items:
			draw_text_line(left_x + left_width - 5, inventory_max_y, "▼", dim_col)
		
		# === RIGHT PANEL: Paperdoll Equipment Slots ===
		right_x = 50
		right_y = header_y + 1  # Align with inventory list start
		right_width = 35
		
		draw_text_line(right_x, right_y, "=== EQUIPPED ===", title_col)
		right_y += 1
		draw_text_line(right_x, right_y, "-" * right_width, dim_col)
		right_y += 1
		
		# Display equipment slots
		for i, slot_name in enumerate(CharacterEquipment.SLOT_ORDER):
			is_selected = (i == inventory_paperdoll_slot and inventory_viewing_paperdoll)
			equipped_item = equipped.get_equipped_item(slot_name)
			
			col = paperdoll_highlight if is_selected else text_col
			prefix = "> " if is_selected else "  "
			
			slot_label = CharacterEquipment.SLOT_DISPLAY_NAMES[slot_name]
			if equipped_item:
				item_name = equipped_item.name[:18]
				line = f"{prefix}{slot_label:13s}: {item_name}"
			else:
				line = f"{prefix}{slot_label:13s}: <empty>"
			
			# Draw with bold if selected
			draw_text_line(right_x, right_y + i, line[:right_width], col if equipped_item or is_selected else dim_col, bold=is_selected)
		
		# === BOTTOM INFO PANEL (8 lines with border) ===
		info_x = 2
		info_y = info_panel_y
		info_width = grid_w - 4
		
		# Border line
		draw_text_line(info_x, info_y, "-" * info_width, dim_col)
		info_y += 1
		
		# Show appropriate info based on context
		if inventory_prompt_mode == 'equip_or_use':
			# Show prompt
			if inventory_prompt_item:
				draw_text_line(info_x, info_y, f"Item: {inventory_prompt_item.name}", title_col)
				info_y += 1
				draw_text_line(info_x, info_y, "This item can be equipped or used.", text_col)
				info_y += 1
				draw_text_line(info_x, info_y, "Press E to Equip, U to Use, or ESC to Cancel.", text_col)
		
		elif inventory_viewing_paperdoll:
			# Show details of selected equipped item
			slot_name = CharacterEquipment.SLOT_ORDER[inventory_paperdoll_slot]
			equipped_item = equipped.get_equipped_item(slot_name)
			
			if equipped_item:
				draw_text_line(info_x, info_y, f"=== {equipped_item.name} ===", title_col)
				info_y += 1
				draw_text_line(info_x, info_y, f"Category: {equipped_item.category} | Size: {equipped_item.size} | Weight: {equipped_item.get_effective_weight():.1f} lbs", text_col)
				info_y += 1
				if equipped_item.damage:
					draw_text_line(info_x, info_y, f"Damage: {equipped_item.damage}", text_col)
					info_y += 1
				if equipped_item.ac is not None:
					draw_text_line(info_x, info_y, f"AC Modifier: {equipped_item.get_ac_display()}", text_col)
					info_y += 1
			else:
				slot_label = CharacterEquipment.SLOT_DISPLAY_NAMES[slot_name]
				draw_text_line(info_x, info_y, f"=== {slot_label} ===", title_col)
				info_y += 1
				draw_text_line(info_x, info_y, "Nothing equipped in this slot.", dim_col)
		
		else:
			# Show details of selected inventory item
			if inventory_viewing_container:
				selected_container = inv.slots[inventory_main_slot] if 0 <= inventory_main_slot < len(inv.slots) else None
				if selected_container and selected_container.is_container and 0 <= inventory_container_slot < len(selected_container.contents):
					selected_item = selected_container.contents[inventory_container_slot]
				else:
					selected_item = None
			else:
				selected_item = inv.slots[inventory_main_slot] if 0 <= inventory_main_slot < len(inv.slots) else None
			
			if selected_item:
				draw_text_line(info_x, info_y, f"=== {selected_item.name} ===", title_col)
				info_y += 1
				
				info_line = f"Category: {selected_item.category} | Size: {selected_item.size} | Weight: {selected_item.get_effective_weight():.1f} lbs | Value: {selected_item.cost} gp"
				draw_text_line(info_x, info_y, info_line[:info_width], text_col)
				info_y += 1
				
				if selected_item.is_container:
					draw_text_line(info_x, info_y, f"Container: {selected_item.slots} slots, max size {selected_item.max_item_size}, {int(selected_item.weight_reduction*100)}% weight reduction", text_col)
					info_y += 1
				
				if selected_item.damage:
					draw_text_line(info_x, info_y, f"Damage: {selected_item.damage} | Speed: {selected_item.get_speed_display()}", text_col)
					info_y += 1
				if selected_item.ac is not None:
					draw_text_line(info_x, info_y, f"AC Modifier: {selected_item.get_ac_display()}", text_col)
					info_y += 1
			else:
				draw_text_line(info_x, info_y, "=== EMPTY SLOT ===", title_col)
				info_y += 1
				draw_text_line(info_x, info_y, "This slot is empty.", dim_col)

	running = True
	frame_count = 0
	while running:
		# Input
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.KEYDOWN:
				# Debug mode toggle: Ctrl + D
				mods = pygame.key.get_mods()
				if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_d:
					debug_mode = not debug_mode
					continue

				# Debug commands (only when debug mode enabled and menu not open)
				if debug_mode and not menu_open:
					if event.key == pygame.K_F1:
						# Toggle: show entire map as visible (override FOV)
						debug_show_all_visible = not debug_show_all_visible
						continue
					if event.key == pygame.K_F2:
						# Action: reveal all tiles (FoW)
						explored = set((x, y) for x in range(dungeon.w) for y in range(dungeon.h))
						# push reveal progress to done
						for x in range(dungeon.w):
							for y in range(dungeon.h):
								mm_reveal[x][y] = 1.0
								wr_reveal[x][y] = 1.0
						# mark all current walls/floors/brick as touched
						bricks_touched = set((x, y) for x in range(dungeon.w) for y in range(dungeon.h)
										     if dungeon.tiles[x][y] == TILE_WALL and dungeon.materials[x][y] == MAT_BRICK)
						walls_touched = set((x, y) for x in range(dungeon.w) for y in range(dungeon.h)
									    if dungeon.tiles[x][y] == TILE_WALL)
						floors_touched = set((x, y) for x in range(dungeon.w) for y in range(dungeon.h)
								    if dungeon.tiles[x][y] == TILE_FLOOR)
						# For debug reveal, consider all reachable floors as stepped
						reachable = compute_reachable_floors(dungeon, px, py)
						floors_stepped = set(reachable)
						# keep level snapshot in sync if present
						if levels and 0 <= current_level_index < len(levels):
							levels[current_level_index]['bricks_touched'] = bricks_touched
							levels[current_level_index]['walls_touched'] = walls_touched
							levels[current_level_index]['floors_touched'] = floors_touched
							levels[current_level_index]['floors_stepped'] = floors_stepped
						continue
					if event.key == pygame.K_F3:
						# Toggle: noclip movement (ignore walls)
						debug_noclip = not debug_noclip
						continue
					if event.key == pygame.K_F4:
						# Decrease light radius (min 1)
						light_radius = max(1, int(light_radius) - 1)
						continue
					if event.key == pygame.K_F5:
						# Increase light radius (max reasonable cap)
						light_radius = min(20, int(light_radius) + 1)
						continue

				if event.key == pygame.K_ESCAPE:
					if inventory_open:
						# Handle prompt mode first
						if inventory_prompt_mode == 'equip_or_use':
							inventory_prompt_mode = None
							inventory_prompt_item = None
						# If viewing paperdoll, return to inventory
						elif inventory_viewing_paperdoll:
							inventory_viewing_paperdoll = False
						# If viewing container, close container first
						elif inventory_viewing_container:
							inventory_viewing_container = False
							inventory_container_slot = 0
						# Otherwise close inventory
						else:
							inventory_open = False
							inventory_scroll_offset = 0
					elif menu_open:
						if menu_mode in ('save', 'load'):
							menu_mode = 'main'
						elif menu_mode == 'settings':
							menu_mode = 'main'
						else:
							menu_open = False
					else:
						menu_open = True
						menu_mode = 'main'
						menu_index = 0
						save_name = ""
						load_names = list_saves()
						load_index = default_load_index(load_names)
					continue
				
				# Inventory screen toggle
				if event.key == pygame.K_i and not menu_open and not inventory_open:
					if player_character:
						inventory_open = True
						inventory_main_slot = 0
						inventory_viewing_container = False
						inventory_container_slot = 0
						inventory_scroll_offset = 0
						inventory_viewing_paperdoll = False
						inventory_paperdoll_slot = 0
						inventory_prompt_mode = None
						inventory_prompt_item = None
					else:
						add_message("No character loaded. Cannot open inventory.")
					continue
				
				if event.key == pygame.K_q and not menu_open and not inventory_open:
					running = False
				# Developer hotkey: generate new level 'N'
				if event.key == pygame.K_n and not menu_open:
					push_new_level()
					continue

				# Developer hotkey: stamp a prefab near player 'P'
				if event.key == pygame.K_p and not menu_open:
					if prefabs:
						# choose a random prefab from the loaded library
						pf = random.choice(list(prefabs.values()))
						# stamp top-left anchored near player
						x0 = max(0, px - pf.width // 2)
						y0 = max(0, py - pf.height // 2)
						dungeon.stamp_prefab(x0, y0, pf.cells, pf.legend)
						# refresh FOV
						fov = FOV(dungeon)
						# update totals (dungeon changed)
						total_bricks = count_total_bricks(dungeon)
						reachable = compute_reachable_floors(dungeon, px, py)
						total_floors = len(reachable)
						total_walls = count_total_exposed_walls(dungeon, reachable)
						# reconcile touched sets against current dungeon state
						bricks_touched = set((x, y) for (x, y) in bricks_touched
							if 0 <= x < dungeon.w and 0 <= y < dungeon.h and
							   dungeon.tiles[x][y] == TILE_WALL and dungeon.materials[x][y] == MAT_BRICK)
						walls_touched = set((x, y) for (x, y) in walls_touched
							if 0 <= x < dungeon.w and 0 <= y < dungeon.h and any(
								0 <= x+dx < dungeon.w and 0 <= y+dy < dungeon.h and dungeon.tiles[x+dx][y+dy] == TILE_FLOOR and ((x+dx, y+dy) in reachable)
								for dx in (-1,0,1) for dy in (-1,0,1) if not (dx==0 and dy==0)
							))
						floors_touched = set((x, y) for (x, y) in floors_touched
							if 0 <= x < dungeon.w and 0 <= y < dungeon.h and dungeon.tiles[x][y] == TILE_FLOOR)
						if 0 <= current_level_index < len(levels):
							levels[current_level_index]['total_bricks'] = total_bricks
							levels[current_level_index]['total_walls'] = total_walls
							levels[current_level_index]['total_floors'] = total_floors
							levels[current_level_index]['bricks_touched'] = bricks_touched
							levels[current_level_index]['walls_touched'] = walls_touched
							levels[current_level_index]['floors_touched'] = floors_touched
							# Reconcile stepped floors to valid floors
							floors_stepped = set((x, y) for (x, y) in floors_stepped
												if 0 <= x < dungeon.w and 0 <= y < dungeon.h and dungeon.tiles[x][y] == TILE_FLOOR)
							levels[current_level_index]['floors_stepped'] = floors_stepped
					continue

				if inventory_open:
					# Inventory/Equipment navigation with paperdoll
					if not player_character or not hasattr(player_character, 'inventory'):
						continue
					
					inv = player_character.inventory
					equipped = player_character.equipped if hasattr(player_character, 'equipped') else CharacterEquipment()
					
					# Handle prompt mode first (equip or use disambiguation)
					if inventory_prompt_mode == 'equip_or_use':
						if event.key == pygame.K_e:
							# Equip the item
							if inventory_prompt_item:
								old_item = equipped.equip_item(inventory_prompt_item)
								if old_item:
									# Swap: put old item in inventory slot where new item was
									if inventory_viewing_container:
										selected_container = inv.slots[inventory_main_slot]
										if selected_container and selected_container.is_container:
											selected_container.contents[inventory_container_slot] = old_item
									else:
										inv.slots[inventory_main_slot] = old_item
								else:
									# No swap needed, just remove from inventory
									if inventory_viewing_container:
										selected_container = inv.slots[inventory_main_slot]
										if selected_container and selected_container.is_container:
											selected_container.contents[inventory_container_slot] = None
									else:
										inv.slots[inventory_main_slot] = None
							inventory_prompt_mode = None
							inventory_prompt_item = None
						elif event.key == pygame.K_u:
							# Use the item (placeholder - implement actual use logic)
							if inventory_prompt_item:
								add_message(f"Used {inventory_prompt_item.name}")
								# TODO: Implement actual item use logic here
							inventory_prompt_mode = None
							inventory_prompt_item = None
						elif event.key == pygame.K_ESCAPE:
							# Cancel
							inventory_prompt_mode = None
							inventory_prompt_item = None
						continue
					
					# TAB - Toggle between inventory and paperdoll navigation
					if event.key == pygame.K_TAB:
						if inventory_viewing_paperdoll:
							# Return to inventory navigation
							inventory_viewing_paperdoll = False
						else:
							# Switch to paperdoll navigation
							inventory_viewing_paperdoll = True
							inventory_paperdoll_slot = 0
						continue
					
					# Handle navigation based on current mode
					if inventory_viewing_paperdoll:
						# PAPERDOLL NAVIGATION
						if event.key in (pygame.K_UP, pygame.K_w):
							inventory_paperdoll_slot = (inventory_paperdoll_slot - 1) % len(CharacterEquipment.SLOT_ORDER)
						
						elif event.key in (pygame.K_DOWN, pygame.K_s):
							inventory_paperdoll_slot = (inventory_paperdoll_slot + 1) % len(CharacterEquipment.SLOT_ORDER)
						
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							# Unequip item and try to add to inventory
							slot_name = CharacterEquipment.SLOT_ORDER[inventory_paperdoll_slot]
							unequipped = equipped.unequip_item(slot_name)
							if unequipped:
								if not inv.add_item_auto(unequipped):
									# Couldn't fit in inventory, re-equip
									equipped.equip_item(unequipped, slot_name)
									add_message(f"Inventory full! Cannot unequip {unequipped.name}")
								else:
									add_message(f"Unequipped {unequipped.name}")
					
					else:
						# INVENTORY NAVIGATION
						if event.key in (pygame.K_UP, pygame.K_w):
							if inventory_viewing_container:
								# Navigate within container
								selected_item = inv.slots[inventory_main_slot] if 0 <= inventory_main_slot < len(inv.slots) else None
								if selected_item and selected_item.is_container:
									inventory_container_slot = max(0, inventory_container_slot - 1)
							else:
								# Navigate main slots
								inventory_main_slot = max(0, inventory_main_slot - 1)
						
						elif event.key in (pygame.K_DOWN, pygame.K_s):
							if inventory_viewing_container:
								# Navigate within container
								selected_item = inv.slots[inventory_main_slot] if 0 <= inventory_main_slot < len(inv.slots) else None
								if selected_item and selected_item.is_container:
									inventory_container_slot = min(len(selected_item.contents) - 1, inventory_container_slot + 1)
							else:
								# Navigate main slots
								inventory_main_slot = min(CharacterInventory.BASE_SLOTS - 1, inventory_main_slot + 1)
						
						elif event.key == pygame.K_LEFT:
							# LEFT arrow - Close container and return to main inventory
							if inventory_viewing_container:
								inventory_viewing_container = False
								inventory_container_slot = 0
						
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							# ENTER - Open container OR equip/use item
							if inventory_viewing_container:
								# In container - try to equip/use item
								selected_container = inv.slots[inventory_main_slot]
								if selected_container and selected_container.is_container:
									selected_item = selected_container.contents[inventory_container_slot]
									if selected_item:
										# Check if equippable and/or usable
										is_equippable = selected_item.equippable
										is_usable = selected_item.usable_from_inventory
										
										if is_equippable and is_usable:
											# Show prompt
											inventory_prompt_mode = 'equip_or_use'
											inventory_prompt_item = selected_item
										elif is_equippable:
											# Just equip
											old_item = equipped.equip_item(selected_item)
											if old_item:
												selected_container.contents[inventory_container_slot] = old_item
											else:
												selected_container.contents[inventory_container_slot] = None
											add_message(f"Equipped {selected_item.name}")
										elif is_usable:
											# Just use
											add_message(f"Used {selected_item.name}")
											# TODO: Implement use logic
										elif selected_item.is_container:
											# Open nested container (future feature)
											add_message("Nested containers not yet supported")
							else:
								# In main inventory
								selected_item = inv.slots[inventory_main_slot] if 0 <= inventory_main_slot < len(inv.slots) else None
								if selected_item:
									if selected_item.is_container:
										# Open container
										inventory_viewing_container = True
										inventory_container_slot = 0
									else:
										# Try to equip/use
										is_equippable = selected_item.equippable
										is_usable = selected_item.usable_from_inventory
										
										if is_equippable and is_usable:
											# Show prompt
											inventory_prompt_mode = 'equip_or_use'
											inventory_prompt_item = selected_item
										elif is_equippable:
											# Just equip
											old_item = equipped.equip_item(selected_item)
											if old_item:
												inv.slots[inventory_main_slot] = old_item
											else:
												inv.slots[inventory_main_slot] = None
											add_message(f"Equipped {selected_item.name}")
										elif is_usable:
											# Just use
											add_message(f"Used {selected_item.name}")
											# TODO: Implement use logic
						
						# Number keys for quick slot selection
						elif event.key >= pygame.K_1 and event.key <= pygame.K_8:
							slot_num = event.key - pygame.K_1
							inventory_main_slot = slot_num
							inventory_viewing_container = False
							inventory_container_slot = 0
					
					continue

				if menu_open:
					# Menu navigation
					if menu_mode == 'main':
						if event.key in (pygame.K_w, pygame.K_UP):
							menu_index = (menu_index - 1) % 5
						elif event.key in (pygame.K_s, pygame.K_DOWN):
							menu_index = (menu_index + 1) % 5
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							if menu_index == 0:  # Character Creator
								# Launch character creator GUI
								menu_open = False
								was_drip_active = False
								previous_drip_volume = 0.5
								if drip_sfx:
									was_drip_active = bool(drip_sfx.active)
									previous_drip_volume = getattr(drip_sfx, 'master_volume', 0.5)
									if was_drip_active:
										drip_sfx.stop()
										drip_started = False
								try:
									from char_gui import run_character_creator
									created_char = run_character_creator(screen=screen, clock=clock)
									if created_char:
										# Load character stats into game
										player_character = created_char
										add_message(f"Welcome, {created_char.name} the {created_char.race} {created_char.char_class}!")
										add_message(f"HP: {created_char.current_hp}/{created_char.max_hp}, AC: {created_char.armor_class}")
									else:
										add_message("Character creation cancelled.")
								except Exception as e:
									add_message(f"Error in Character Creator: {e}")
									import traceback
									traceback.print_exc()
								finally:
									if drip_sfx and was_drip_active:
										drip_sfx.set_master_volume(previous_drip_volume)
										drip_sfx.start()
										drip_started = True
							elif menu_index == 1:  # Settings
								menu_mode = 'settings'
								menu_index = 0
							elif menu_index == 2:  # Save
								menu_mode = 'save'
								save_name = ""
							elif menu_index == 3:  # Load
								menu_mode = 'load'
								load_names = list_saves()
								load_index = default_load_index(load_names)
							elif menu_index == 4:  # Quit
								running = False
					elif menu_mode == 'settings':
						if event.key in (pygame.K_w, pygame.K_UP):
							menu_index = (menu_index - 1) % 8
						elif event.key in (pygame.K_s, pygame.K_DOWN):
							menu_index = (menu_index + 1) % 8
						# Left/Right for volume sliders
						elif event.key in (pygame.K_a, pygame.K_LEFT):
							if menu_index == 0:  # Music volume
								vol = max(0.0, SETTINGS.get('music_volume', 0.7) - 0.05)
								SETTINGS['music_volume'] = vol
								pygame.mixer.music.set_volume(vol)
							elif menu_index == 1:  # Sound volume
								vol = max(0.0, SETTINGS.get('sound_volume', 0.8) - 0.05)
								SETTINGS['sound_volume'] = vol
						elif event.key in (pygame.K_d, pygame.K_RIGHT):
							if menu_index == 0:  # Music volume
								vol = min(1.0, SETTINGS.get('music_volume', 0.7) + 0.05)
								SETTINGS['music_volume'] = vol
								pygame.mixer.music.set_volume(vol)
							elif menu_index == 1:  # Sound volume
								vol = min(1.0, SETTINGS.get('sound_volume', 0.8) + 0.05)
								SETTINGS['sound_volume'] = vol
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							if menu_index == 2:  # toggle HUD
								SETTINGS['hud_text'] = not SETTINGS.get('hud_text', True)
							elif menu_index == 3:  # toggle minimap
								mm = SETTINGS.get('minimap', {})
								mm['enabled'] = not mm.get('enabled', True)
								SETTINGS['minimap'] = mm
							elif menu_index == 4:  # toggle gold glow
								SETTINGS['show_gold_glow'] = not SETTINGS.get('show_gold_glow', True)
							elif menu_index == 5:  # cycle render mode
								current = SETTINGS.get('render_mode', 'blocks')
								SETTINGS['render_mode'] = 'ascii' if current == 'blocks' else 'blocks'
								render_mode = SETTINGS['render_mode']
							elif menu_index == 6:  # toggle auto search
								SETTINGS['auto_search'] = not SETTINGS.get('auto_search', False)
							elif menu_index == 7:  # Back
								menu_mode = 'main'
						# no player movement when menu open
						continue
					elif menu_mode == 'save':
						# text input
						if event.key == pygame.K_BACKSPACE:
							save_name = save_name[:-1]
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							nm = sanitize_name(save_name)
							if nm:
								# update current snapshot, then save all levels
								if levels:
									levels[current_level_index] = snapshot_current()
								path = save_session(nm, dungeon, explored, px, py,
													levels=collect_levels_for_save(levels),
													current_index=current_level_index)
								menu_mode = 'main'
								add_message(f"Game saved as '{nm}'.")
						else:
							ch = event.unicode
							if ch and re.match(r"[A-Za-z0-9_-]", ch):
								if len(save_name) < 40:
									save_name += ch
						continue
					elif menu_mode == 'load':
						if not load_names:
							continue
						if event.key in (pygame.K_w, pygame.K_UP):
							load_index = (load_index - 1) % len(load_names)
						elif event.key in (pygame.K_s, pygame.K_DOWN):
							load_index = (load_index + 1) % len(load_names)
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							nm = load_names[load_index]
							try:
								_, _, _, _, levels_data, idx = load_session(nm)
								(
									levels,
									current_level_index,
									dungeon,
									explored,
									px,
									py,
									bricks_touched,
									total_bricks,
									walls_touched,
									floors_touched,
									floors_stepped,
									total_walls,
									total_floors,
									torches,
								) = hydrate_levels_from_save(levels_data, idx)
								torch_lookup = rebuild_torch_lookup(torches)
								if levels and 0 <= current_level_index < len(levels):
									levels[current_level_index]['torches'] = serialize_torches(torches)
								fov = FOV(dungeon)
								# rebuild minimap/world buffers for loaded level
								mm_reveal, mm_noise = build_minimap_buffers(dungeon)
								wr_reveal, wr_noise = build_world_reveal_buffers(dungeon)
								using_loaded_save = True
								menu_mode = 'main'
								set_last_character_name(nm)
								add_message(f"Loaded save '{nm}'.")
							except Exception as e:
								# simple error display in title line
								pass
						continue
				# If we reach here and menu/inventory not open, handle game controls
				if not inventory_open:
					dx = dy = 0
					if event.key == pygame.K_w:
						dy = -1
					elif event.key == pygame.K_s:
						dy = 1
				
					elif event.key == pygame.K_a:
						dx = -1
					elif event.key == pygame.K_d:
						dx = 1
					if dx != 0 or dy != 0:
						nx, ny = px + dx, py + dy
						if 0 <= nx < dungeon.w and 0 <= ny < dungeon.h:
							if debug_noclip or not dungeon.is_wall(nx, ny):
								px, py = nx, ny
								# Track floors stepped-on
								if dungeon.tiles[px][py] == TILE_FLOOR and (px, py) not in floors_stepped:
									floors_stepped.add((px, py))
									if levels and 0 <= current_level_index < len(levels):
										levels[current_level_index]['floors_stepped'] = floors_stepped

		# Update visibility after input
		player_visible: set[tuple[int, int]]
		torch_lit_tiles: set[tuple[int, int]]
		if debug_show_all_visible:
			visible = {(x, y) for x in range(dungeon.w) for y in range(dungeon.h)}
			los_visible = set(visible)
			player_visible = set(visible)
			torch_lit_tiles = set()
		else:
			base_radius = max(1, int(light_radius - 0.5))
			extra_reach = 0.0
			if torches:
				for torch in torches:
					tx, ty = torch['x'], torch['y']
					dist = math.hypot(tx - px, ty - py)
					torch_radius = torch.get('radius', TORCH_LIGHT_RADIUS)
					extra_reach = max(extra_reach, dist + torch_radius)
			extended_radius = max(base_radius, int(math.ceil(extra_reach)))
			los_visible = fov.compute(px, py, extended_radius)
			visible = set()
			player_visible = set()
			torch_lit_tiles = set()
			base_radius_sq = base_radius * base_radius
			for (vx, vy) in los_visible:
				dx = vx - px
				dy = vy - py
				if dx * dx + dy * dy <= base_radius_sq:
					visible.add((vx, vy))
					player_visible.add((vx, vy))
			for torch in torches:
				tx, ty = torch['x'], torch['y']
				if (tx, ty) not in los_visible:
					continue
				torch_radius = torch.get('radius', TORCH_LIGHT_RADIUS)
				torch_radius_sq = torch_radius * torch_radius
				reach = int(math.ceil(torch_radius))
				for dy in range(-reach, reach + 1):
					for dx in range(-reach, reach + 1):
						x = tx + dx
						y = ty + dy
						if not (0 <= x < dungeon.w and 0 <= y < dungeon.h):
							continue
						if dx * dx + dy * dy > torch_radius_sq + 1e-6:
							continue
						if (x, y) in los_visible:
							visible.add((x, y))
							torch_lit_tiles.add((x, y))

		# Animate minimap reveal
		dt = clock.get_time() / 1000.0
		reveal_rate = 2.0
		for (ex, ey) in explored:
			if 0 <= ex < dungeon.w and 0 <= ey < dungeon.h:
				if mm_reveal[ex][ey] < 1.0:
					mm_reveal[ex][ey] = clamp(mm_reveal[ex][ey] + dt * reveal_rate, 0.0, 1.0)
				# Animate world FoW reveal similarly
				if wr_reveal[ex][ey] < 1.0:
					wr_reveal[ex][ey] = clamp(wr_reveal[ex][ey] + dt * reveal_rate, 0.0, 1.0)

		# Update dungeon fade-in
		if not dungeon_fade_complete:
			dungeon_fade_alpha = min(1.0, dungeon_fade_alpha + dt / dungeon_fade_duration)
			if dungeon_fade_alpha >= 1.0:
				dungeon_fade_complete = True
				# Ensure water-drip SFX scheduling resumes after fade completes
				if drip_sfx:
					drip_sfx.set_master_volume(0.5)
					if not drip_sfx.active:
						print("[AUDIO] Starting water-drip SFX...")
						drip_sfx.start()
						add_message("Water drips echo through the halls.")
						print(f"[AUDIO] Water-drip active: {drip_sfx.active}")
			drip_started = bool(drip_sfx and drip_sfx.active)

		# Update water-drip scheduling and ambient bat audio
		current_ticks = pygame.time.get_ticks()
		if drip_sfx:
			drip_sfx.update(current_ticks)
		if ambient_bat_enabled and dungeon_fade_complete and sound_generator:
			if ambient_bat_next_time == 0:
				ambient_bat_next_time = schedule_next_bat_squeak(current_ticks)
			elif current_ticks >= ambient_bat_next_time:
				try:
					source_map = getattr(sound_generator, 'sounds', {})
					if source_map and source_map.get('bat_squeak'):
						sound_generator.play_random('bat_squeak', ambient_bat_volume)
					else:
						bat_sound = sound_generator.generate_bat_squeak_sample()
						bat_sound.set_volume(ambient_bat_volume)
						bat_sound.play()
				except Exception as ambient_err:
					print(f"[AUDIO] Failed to play bat squeak ambience: {ambient_err}")
					ambient_bat_enabled = False
				else:
					ambient_bat_next_time = schedule_next_bat_squeak(current_ticks)

		# Update secret searching and gradual illumination for tiles in light radius
		if player_character and dungeon_fade_complete:
			# Calculate perception modifier from wisdom (D&D style: (score - 10) / 2)
			wisdom_mod = (player_character.wisdom - 10) // 2
			# Base search time is 2 seconds, reduced by perception modifier
			# Each +1 wisdom mod reduces search time by 0.2 seconds (min 1 second)
			base_search_time = 2.0
			search_time_required = max(1.0, base_search_time - (wisdom_mod * 0.2))

			# Torch-lit tiles stay fully illuminated regardless of player proximity
			for (tx, ty) in torch_lit_tiles:
				if tile_illumination_source.get((tx, ty)) != 'player':
					tile_illumination_source[(tx, ty)] = 'torch'
					tile_illumination_alpha[(tx, ty)] = max(tile_illumination_alpha.get((tx, ty), 0.0), 1.0)
					tile_illumination_progress[(tx, ty)] = max(tile_illumination_progress.get((tx, ty), 0.0), search_time_required)
			
			# Check all tiles in light radius
			for (vx, vy) in player_visible:
				# Update gradual illumination for ALL visible tiles
				if (vx, vy) not in tile_illumination_alpha:
					tile_illumination_alpha[(vx, vy)] = 0.0
					tile_illumination_progress[(vx, vy)] = 0.0
				
				# Only illuminate if not already at full brightness
				if tile_illumination_alpha[(vx, vy)] < 1.0:
					tile_illumination_progress[(vx, vy)] += dt
					# Calculate illumination alpha based on time (same as search time)
					progress_ratio = min(1.0, tile_illumination_progress[(vx, vy)] / search_time_required)
					tile_illumination_alpha[(vx, vy)] = progress_ratio
				tile_illumination_source[(vx, vy)] = 'player'
				# Update visual fade-in for all visible tiles with secrets (even revealed ones)
				if (vx, vy) in tile_secrets:
					if (vx, vy) not in tile_search_alpha:
						tile_search_alpha[(vx, vy)] = 0.0
					
					# Only accumulate search progress for secrets that haven't been checked yet
					if (vx, vy) not in revealed_secrets and (vx, vy) not in tile_secrets_checked:
						# Accumulate search time
						if (vx, vy) not in tile_search_progress:
							tile_search_progress[(vx, vy)] = 0.0
						
						tile_search_progress[(vx, vy)] += dt
						
						# Update visual alpha based on search progress (0.0 to 1.0)
						progress_ratio = min(1.0, tile_search_progress[(vx, vy)] / search_time_required)
						tile_search_alpha[(vx, vy)] = progress_ratio
						
						# Check if tile is fully searched (only roll once)
						if tile_search_progress[(vx, vy)] >= search_time_required:
							# Mark this secret as checked (one roll only)
							tile_secrets_checked.add((vx, vy))
							
							# Get difficulty DC for this secret
							secret_dc = tile_secrets[(vx, vy)]
							
							# Roll perception check: d20 + wisdom modifier vs secret DC (ONE TIME ONLY)
							perception_roll = random.randint(1, 20) + wisdom_mod
							
							if perception_roll >= secret_dc:
								# Secret found!
								revealed_secrets.add((vx, vy))
								tile_search_alpha[(vx, vy)] = 1.0  # Fully bright
								
								# Difficulty label for message
								difficulty_labels = {5: "trivial", 10: "easy", 15: "normal", 20: "hard", 25: "very hard"}
								difficulty_label = difficulty_labels.get(secret_dc, "unknown")
								
								add_message(f"You discovered a {difficulty_label} secret! (Roll: {perception_roll} vs DC {secret_dc})")
								print(f"[SECRETS] Found secret at ({vx}, {vy}) - Roll: {perception_roll}, DC: {secret_dc} ({difficulty_label})")
								
								# Play coin sound
								if sound_generator:
									try:
										sound_generator.play_secret_discovery_sound(0.6)
									except Exception as e:
										print(f"[SECRETS] Could not play secret discovery sound: {e}")
							else:
								# Failed perception check - secret remains hidden permanently
								print(f"[SECRETS] Searched ({vx}, {vy}) but didn't find secret - Roll: {perception_roll}, DC: {secret_dc} (ONE TIME CHECK - FAILED)")
								# Keep visual alpha at maximum to show it was searched
								tile_search_alpha[(vx, vy)] = 1.0

		# Compute reachable floors once per frame for exploration logic
		reachable_this_frame = compute_reachable_floors(dungeon, px, py)

		# Render
		# Static parchment background (no spiral/animation)
		screen.blit(parchment_static, (0, 0))
		off_x, off_y = compute_offsets()

		# Camera centered on player; viewport size is map_w x grid_h
		view_w = map_w
		view_h = grid_h
		# Always center camera on player; allow camera to go out-of-bounds
		cam_x = px - view_w // 2
		cam_y = py - view_h // 2

	# Do not paint an opaque viewport background; let parchment show under floors

		# Draw UI border across the full window height
		if render_mode == 'blocks':
			border_base = scale_color(WALL_LIGHT, 0.95)
			border_shadow = scale_color(INK_DARK, 0.6)
			border_high = MARBLE_WHITE
			for sy in range(view_h):
				cx = BORDER_COL
				cy = sy
				# Base fill with subtle dither texture
				draw_block_at(cx, cy, border_base, inset=0, with_dither=True)
				# Right-side dark separating line (toward map)
				draw_cell_px_rect(cx, cy, cell_w - 1, 0, 1, cell_h, border_shadow)
				# Left-side highlight edge (toward UI)
				draw_cell_px_rect(cx, cy, 0, 0, 1, cell_h, border_high)
				# Decorative studs every 4 rows
				if (sy % 4) == 0:
					stud_w = max(2, cell_w // 5)
					stud_h = max(2, cell_h // 5)
					sx = (cell_w - stud_w) // 2
					sy_px = (cell_h - stud_h) // 2
					# Outer light stud with inner dark dot
					draw_cell_px_rect(cx, cy, sx, sy_px, stud_w, stud_h, border_high, alpha=0.9)
					inner = max(1, min(stud_w, stud_h) // 2)
					draw_cell_px_rect(cx, cy, sx + (stud_w - inner)//2, sy_px + (stud_h - inner)//2, inner, inner, border_shadow, alpha=0.9)
		else:
			for sy in range(view_h):
				draw_char_at(BORDER_COL, sy, WALL_CH, scale_color(WALL_LIGHT, 0.9))

		ticks = pygame.time.get_ticks()
		light_sources = prepare_light_sources(px, py, light_radius, torches, ticks)
		torch_only_sources = [src for src in light_sources if src.get('is_torch')]

		# Draw tiles in viewport window
		for sy in range(view_h):
			wy = cam_y + sy
			for sx in range(view_w):
				wx = cam_x + sx
				draw_ch = ' '
				color = INK_DARK
				block_color = None
				mat = MAT_BRICK  # Default material for out-of-bounds areas
				if 0 <= wx < dungeon.w and 0 <= wy < dungeon.h:
					# In-bounds tiles
					tile = dungeon.tiles[wx][wy]
					mat = dungeon.materials[wx][wy]
					world_pos = (wx, wy)
					
					if world_pos in visible:
						visible_by_player = world_pos in player_visible
						if visible_by_player:
							if world_pos not in explored:
								explored.add(world_pos)
							if 0 <= wx < dungeon.w and 0 <= wy < dungeon.h:
								if mm_reveal and mm_reveal[wx][wy] < 1.0:
									mm_reveal[wx][wy] = 1.0
								if wr_reveal and wr_reveal[wx][wy] < 1.0:
									wr_reveal[wx][wy] = 1.0
						light_value, primary_source = evaluate_light_sources(light_sources, wx, wy)
						tval = max(0.1, min(light_value, 1.0))
						# Get material-specific character and color
						is_wall = (tile == TILE_WALL)
						is_door = (tile == TILE_DOOR)
						
						if is_door:
							# Doors get special rendering
							door_state = dungeon.doors[wx][wy] if 0 <= wx < dungeon.w and 0 <= wy < dungeon.h else -1
							if door_state == DOOR_OPEN:
								draw_ch = "'"  # Open door
								base_color = (120, 80, 50)  # Medium brown
							elif door_state == DOOR_LOCKED:
								draw_ch = "+"  # Locked door (solid)
								base_color = (80, 50, 30)   # Dark brown
							else:  # DOOR_CLOSED or default
								draw_ch = "+"  # Closed door
								base_color = (100, 65, 40)  # Brown
						else:
							draw_ch, base_color = get_material_ascii_char_and_color(mat, is_wall)
						
						# Ensure floors don't render characters
						if tile == TILE_FLOOR:
							draw_ch = ' '
						
						# Apply lighting to the material color
						color = scale_color(base_color, tval)
						torch_here = torch_lookup.get(world_pos)
						if torch_only_sources:
							torch_light, _ = evaluate_light_sources(torch_only_sources, wx, wy)
							if torch_light > 0.0:
								warmth = min(60, int(80 * torch_light))
								color = (
									min(255, color[0] + warmth),
									min(255, color[1] + warmth // 2),
									color[2]
								)
						if torch_here and render_mode != 'blocks':
							flame_scale = clamp(torch_here.get('current_intensity', TORCH_BASE_INTENSITY), 0.6, 1.0)
							draw_ch = '†'
							color = (
								min(255, int(TORCH_FLAME_COLOR[0] * flame_scale)),
								min(255, int(TORCH_FLAME_COLOR[1] * flame_scale)),
								min(255, int(TORCH_FLAME_COLOR[2] * flame_scale)),
							)
						
						# Apply gradual illumination - tiles start dim and brighten over time
						if (wx, wy) in tile_illumination_alpha:
							illum_alpha = tile_illumination_alpha[(wx, wy)]
							# Start at 20% brightness, fade up to 100% over search time
							min_brightness = 0.2
							illum_multiplier = min_brightness + (1.0 - min_brightness) * illum_alpha
							color = scale_color(color, illum_multiplier)
						
						# Apply search progress visual enhancement (for tiles with secrets)
						if (wx, wy) in tile_search_alpha:
							search_alpha = tile_search_alpha[(wx, wy)]
							if search_alpha > 0.0:
								# Gradually brighten and add a subtle golden tint as search progresses
								# Boost brightness by up to 40% at full search
								brightness_boost = 1.0 + (0.4 * search_alpha)
								color = scale_color(color, brightness_boost)
								
								# Add subtle golden tint (more pronounced as search progresses)
								gold_tint = int(30 * search_alpha)  # Up to +30 to red/green channels
								color = (
									min(255, color[0] + gold_tint),
									min(255, color[1] + int(gold_tint * 0.8)),  # Slightly less green for gold
									color[2]  # No blue boost
								)
						
						# Enhanced directional boost for walls: stronger effect
						if tile == TILE_WALL:
							wnx, wny = wall_normal(dungeon, wx, wy)
							light_origin = primary_source if primary_source else (px, py)
							lx = light_origin[0] - wx
							ly = light_origin[1] - wy
							llen = math.hypot(lx, ly)
							if llen > 1e-6:
								lx /= llen
								ly /= llen
							# Only apply if we have a meaningful normal
							ndotl = max(0.0, wnx * lx + wny * ly)
							if ndotl > 0.0:
								# Stronger boost for walls facing the player
								boost = 0.5 * ndotl * tval  # Scale by distance too
								color = scale_color(color, 1.0 + boost)
						
						# Track exploration metrics only when the player truly reveals the tile
						if visible_by_player:
							# - Brick-specific subset
							if tile == TILE_WALL and mat == MAT_BRICK:
								bricks_touched.add((wx, wy))
							# - Combined wall/floor sets
							if tile == TILE_WALL:
								# Only count walls that border a reachable floor tile
								for dx in (-1,0,1):
									for dy in (-1,0,1):
										if dx==0 and dy==0:
											continue
										nx, ny = wx+dx, wy+dy
										if 0 <= nx < dungeon.w and 0 <= ny < dungeon.h and dungeon.tiles[nx][ny] == TILE_FLOOR and (nx, ny) in reachable_this_frame:
											walls_touched.add((wx, wy))
											break
							else:
								floors_touched.add((wx, wy))
						
						block_color = color
					# Explored but not currently visible: dimmed FoW rendering with INVERTED lighting
					elif (wx, wy) in explored:
						prog = wr_reveal[wx][wy]
						noi = wr_noise[wx][wy]
						alpha = clamp(pow(clamp(prog + noi, 0.0, 1.0), 1.8), 0.0, 1.0)
						
						# Calculate distance for INVERTED lighting in FoW
						dx = wx - px
						dy = wy - py
						d = math.sqrt(dx * dx + dy * dy)
						
						# INVERTED lighting: distant areas are brighter in FoW (darker overall)
						if d <= 1.0:
							# Areas immediately next to player are darkest in FoW
							fow_brightness = 0.08
						else:
							# Distant areas get progressively brighter, maxing at edge of light radius
							normalized_distance = min(d / light_radius, 1.0)
							fow_brightness = 0.08 + (0.22 * normalized_distance)  # Range: 0.08 to 0.30
						if torch_only_sources:
							torch_light_fow, _ = evaluate_light_sources(torch_only_sources, wx, wy)
							if torch_light_fow > 0.0:
								fow_brightness = max(fow_brightness, 0.10 + 0.35 * torch_light_fow)
						
						# Get material-specific character and color for FOG OF WAR
						is_wall = (tile == TILE_WALL)
						is_door = (tile == TILE_DOOR)
						
						if is_door:
							# Doors in fog of war
							door_state = dungeon.doors[wx][wy] if 0 <= wx < dungeon.w and 0 <= wy < dungeon.h else -1
							if door_state == DOOR_OPEN:
								draw_ch = "'"  # Open door
								base_color = (120, 80, 50)  # Medium brown
							elif door_state == DOOR_LOCKED:
								draw_ch = "+"  # Locked door (solid)
								base_color = (80, 50, 30)   # Dark brown
							else:  # DOOR_CLOSED or default
								draw_ch = "+"  # Closed door
								base_color = (100, 65, 40)  # Brown
						else:
							draw_ch, base_color = get_material_ascii_char_and_color(mat, is_wall)
						
						if is_wall:
							# FoW walls: Use denser character and apply inverted lighting
							draw_ch = '▓'  # Dense dither for FoW walls
							color = scale_color(base_color, fow_brightness)
						elif is_door:
							# FoW doors: Keep door character but dim the color
							color = scale_color(base_color, fow_brightness)
						else:
							# FoW floors: Use blank space (invisible, blends with parchment)
							draw_ch = ' '  # Blank for FoW floors (invisible, blends with parchment)
							floor_brightness = fow_brightness * 0.5  # Make floors much darker than walls
							color = scale_color(base_color, floor_brightness)
							if torch_only_sources:
								torch_warm, _ = evaluate_light_sources(torch_only_sources, wx, wy)
								if torch_warm > 0.0:
									warm_boost = min(45, int(70 * torch_warm))
									color = (
										min(255, color[0] + warm_boost),
										min(255, color[1] + warm_boost // 2),
										color[2]
									)
						
						# Ensure floors don't render characters
						if tile == TILE_FLOOR:
							draw_ch = ' '
						block_color = color
				# else: out-of-bounds rendering
				else:
					# DARKNESS: Unexplored areas - leave as pure parchment (no character)
					draw_ch = ' '
					block_color = None

				# Render according to mode
				if render_mode == 'blocks':
					if block_color is not None:
						# Fill the map cell rectangle (offset by UI columns)
						cell_x = UI_COLS + 1 + sx
						cell_y = sy
						# Slight inset for crisp borders
						inset = 1
						# Use material-specific texture
						material_texture_name = get_material_texture_name(mat)
						draw_block_at(cell_x, cell_y, block_color, inset=inset, with_dither=True, material_type=material_texture_name)
						if torch_lookup and (wx, wy) in torch_lookup:
							draw_torch_overlay(cell_x, cell_y, torch_lookup[(wx, wy)])
				else:
					if draw_ch != ' ':
						surf = render_glyph(draw_ch, color)
						gx = off_x + (UI_COLS + 1 + sx) * cell_w + (cell_w - surf.get_width()) // 2
						gy = off_y + sy * cell_h + (cell_h - surf.get_height()) // 2
						screen.blit(surf, (gx, gy))

		# === Gold glow for fully searched tiles in main view (outermost perimeter, persists in FoW) ===
		gold_color = (255, 215, 0)
		for sy in range(view_h):
			wy = cam_y + sy
			for sx in range(view_w):
				wx = cam_x + sx
				if 0 <= wx < dungeon.w and 0 <= wy < dungeon.h:
					# Check if this tile is fully searched and explored (not just visible - persist in FoW)
					# Draw glow on ANY tile (wall or floor) that borders unsearched area
					if tile_illumination_source.get((wx, wy)) == 'player' and tile_illumination_alpha.get((wx, wy), 0.0) >= 1.0 and (wx, wy) in explored:
						# Draw gold glow on outer edges only
						cell_x = UI_COLS + 1 + sx
						cell_y = sy
						
						if render_mode == 'blocks':
							# Block mode: draw glow lines on outer edges
							glow_surf = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
							
							# Check each cardinal direction for unsearched neighbors
							# Top
							if (wx, wy-1) not in tile_illumination_alpha or tile_illumination_alpha.get((wx, wy-1), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i * 2
									pygame.draw.line(glow_surf, glow_color_alpha, (0, offset), (cell_w, offset), 2)
							# Bottom
							if (wx, wy+1) not in tile_illumination_alpha or tile_illumination_alpha.get((wx, wy+1), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i * 2
									pygame.draw.line(glow_surf, glow_color_alpha, (0, cell_h-1-offset), (cell_w, cell_h-1-offset), 2)
							# Left
							if (wx-1, wy) not in tile_illumination_alpha or tile_illumination_alpha.get((wx-1, wy), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i * 2
									pygame.draw.line(glow_surf, glow_color_alpha, (offset, 0), (offset, cell_h), 2)
							# Right
							if (wx+1, wy) not in tile_illumination_alpha or tile_illumination_alpha.get((wx+1, wy), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i * 2
									pygame.draw.line(glow_surf, glow_color_alpha, (cell_w-1-offset, 0), (cell_w-1-offset, cell_h), 2)
							
							gx = off_x + cell_x * cell_w
							gy = off_y + cell_y * cell_h
							screen.blit(glow_surf, (gx, gy))
						else:
							# ASCII mode: draw glow lines on outer edges
							glow_surf = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
							
							# Check each cardinal direction for unsearched neighbors
							# Top
							if (wx, wy-1) not in tile_illumination_alpha or tile_illumination_alpha.get((wx, wy-1), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i
									pygame.draw.line(glow_surf, glow_color_alpha, (0, offset), (cell_w, offset), 1)
							# Bottom
							if (wx, wy+1) not in tile_illumination_alpha or tile_illumination_alpha.get((wx, wy+1), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i
									pygame.draw.line(glow_surf, glow_color_alpha, (0, cell_h-1-offset), (cell_w, cell_h-1-offset), 1)
							# Left
							if (wx-1, wy) not in tile_illumination_alpha or tile_illumination_alpha.get((wx-1, wy), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i
									pygame.draw.line(glow_surf, glow_color_alpha, (offset, 0), (offset, cell_h), 1)
							# Right
							if (wx+1, wy) not in tile_illumination_alpha or tile_illumination_alpha.get((wx+1, wy), 0.0) < 1.0:
								for i in range(2):
									alpha = 100 - (i * 35)
									glow_color_alpha = (*gold_color, alpha)
									offset = i
									pygame.draw.line(glow_surf, glow_color_alpha, (cell_w-1-offset, 0), (cell_w-1-offset, cell_h), 1)
							
							gx = off_x + cell_x * cell_w
							gy = off_y + cell_y * cell_h
							screen.blit(glow_surf, (gx, gy))

		# Draw player at the center of the viewport
		pcx = int(clamp(view_w // 2, 0, view_w - 1))
		pcy = int(clamp(view_h // 2, 0, view_h - 1))
		if render_mode == 'blocks':
			# Player as a colored block with a thin outline
			cell_x = UI_COLS + 1 + pcx
			cell_y = pcy
			inset = 1
			draw_block_at(cell_x, cell_y, PLAYER_GREEN, inset=inset, with_dither=False)
			# Outline
			px0 = off_x + cell_x * cell_w + inset
			py0 = off_y + cell_y * cell_h + inset
			pw = cell_w - inset * 2
			ph = cell_h - inset * 2
			pygame.draw.rect(screen, INK_DARK, (px0, py0, pw, ph), width=1)
		else:
			surf = render_glyph(PLAYER_CH, PLAYER_GREEN)
			gx = off_x + (UI_COLS + 1 + pcx) * cell_w + (cell_w - surf.get_width()) // 2
			gy = off_y + pcy * cell_h + (cell_h - surf.get_height()) // 2
			screen.blit(surf, (gx, gy))

		# Draw revealed secrets as glowing "S"
		for (secret_x, secret_y) in revealed_secrets:
			# Calculate screen position relative to player
			sx = secret_x - px + view_w // 2
			sy = secret_y - py + view_h // 2
			
			# Only draw if within viewport
			if 0 <= sx < view_w and 0 <= sy < view_h:
				# Create pulsing glow effect using frame counter
				pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 200.0)
				# Gold color with pulsing brightness
				glow_color = (
					int(255 * pulse),
					int(215 * pulse),
					int(0 * pulse)
				)
				
				# Draw the "S" character
				secret_surf = render_glyph('S', glow_color)
				gx = off_x + (UI_COLS + 1 + sx) * cell_w + (cell_w - secret_surf.get_width()) // 2
				gy = off_y + sy * cell_h + (cell_h - secret_surf.get_height()) // 2
				screen.blit(secret_surf, (gx, gy))

		# HUD (optional)
		if SETTINGS.get('hud_text', True) and not menu_open:
			hud_text = f"WASD move, Esc/Q quit | {dungeon.w}x{dungeon.h} | r={light_radius}"
			hud_surf = font.render(hud_text, False, scale_color(WALL_LIGHT, 1.0))
			screen.blit(hud_surf, (4, win_h - hud_surf.get_height() - 4))

		# Bottom-left feedback area (message log) over the map
		if not menu_open:
			draw_message_log()

		# UI panel content (draw after world so it overlays if needed)
		# Enhanced organized UI with sections
		ui_color = scale_color(WALL_LIGHT, 0.95)
		section_color = scale_color(WALL_LIGHT, 1.0)
		dim_color = scale_color(WALL_LIGHT, 0.7)
		
		line_y = 0
		
		if player_character:
			# === CHARACTER SECTION ===
			draw_text_line(0, line_y, "== CHARACTER =="[:UI_COLS], section_color, UI_COLS, use_ui_font=True)
			line_y += 1
			name_short = player_character.name[:UI_COLS]
			draw_text_line(0, line_y, name_short, section_color, UI_COLS, use_ui_font=True)
			line_y += 1
			race_class = f"{player_character.race} {player_character.char_class}"[:UI_COLS]
			draw_text_line(0, line_y, race_class, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			level_xp = f"Level 1  XP:{player_character.xp}"[:UI_COLS]
			draw_text_line(0, line_y, level_xp, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "-"*UI_COLS, dim_color, UI_COLS, use_ui_font=True)
			line_y += 1
			
			# === VITALS SECTION ===
			hp_text = f"HP: {player_character.current_hp}/{player_character.max_hp}"[:UI_COLS]
			draw_text_line(0, line_y, hp_text, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			ac_text = f"AC: {player_character.armor_class}"[:UI_COLS]
			draw_text_line(0, line_y, ac_text, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			thac0_text = f"THAC0: {player_character.thac0}"[:UI_COLS]
			draw_text_line(0, line_y, thac0_text, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "-"*UI_COLS, dim_color, UI_COLS, use_ui_font=True)
			line_y += 1
			
			# === ATTRIBUTES SECTION ===
			draw_text_line(0, line_y, "STR DEX CON"[:UI_COLS], dim_color, UI_COLS, use_ui_font=True)
			line_y += 1
			stats = f"{player_character.strength:>3} {player_character.dexterity:>3} {player_character.constitution:>3}"[:UI_COLS]
			draw_text_line(0, line_y, stats, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "INT WIS CHA"[:UI_COLS], dim_color, UI_COLS, use_ui_font=True)
			line_y += 1
			stats2 = f"{player_character.intelligence:>3} {player_character.wisdom:>3} {player_character.charisma:>3}"[:UI_COLS]
			draw_text_line(0, line_y, stats2, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "-"*UI_COLS, dim_color, UI_COLS, use_ui_font=True)
			line_y += 1
			
			# === INVENTORY/GOLD ===
			gold_text = f"Gold: {player_character.gold}gp"[:UI_COLS]
			draw_text_line(0, line_y, gold_text, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			equip_count = len(player_character.equipment) if hasattr(player_character, 'equipment') else 0
			inv_text = f"Items: {equip_count}"[:UI_COLS]
			draw_text_line(0, line_y, inv_text, ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "-"*UI_COLS, dim_color, UI_COLS, use_ui_font=True)
			line_y += 1
		else:
			# === BASIC INFO (no character) ===
			draw_text_line(0, line_y, "== EXPLORER =="[:UI_COLS], section_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, f"Pos: ({px},{py})"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, f"Dungeon: {dungeon.w}x{dungeon.h}"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, f"Light: {light_radius}"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "-"*UI_COLS, dim_color, UI_COLS, use_ui_font=True)
			line_y += 1
		
		# === DUNGEON INFO SECTION ===
		draw_text_line(0, line_y, "== DUNGEON =="[:UI_COLS], section_color, UI_COLS, use_ui_font=True)
		line_y += 1
		draw_text_line(0, line_y, f"Level: {current_level_index + 1}"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
		line_y += 1
		
		# Exploration percent: floors stepped + exposed brick walls illuminated
		exposed_bricks_total = count_total_exposed_bricks(dungeon, reachable_this_frame)
		floors_total = max(0, total_floors or 0)
		combined_total = max(1, floors_total + exposed_bricks_total)
		exposed_bricks_touched = count_exposed_bricks_touched(dungeon, bricks_touched, reachable_this_frame)
		combined_touched = len(floors_stepped)
		combined_touched = min(combined_touched, floors_total)
		combined_touched += min(exposed_bricks_touched, exposed_bricks_total)
		ratio = 0.0 if combined_total <= 0 else (combined_touched / combined_total)
		ratio = max(0.0, min(1.0, ratio))
		pct = int(round(ratio * 100))
		if exposed_bricks_touched < exposed_bricks_total and pct == 100:
			pct = 99
		draw_text_line(0, line_y, f"Explored: {pct}%"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
		line_y += 1
		draw_text_line(0, line_y, "-"*UI_COLS, dim_color, UI_COLS, use_ui_font=True)
		line_y += 1
		
		# === SHORTCUTS SECTION ===
		draw_text_line(0, line_y, "== SHORTCUTS =="[:UI_COLS], section_color, UI_COLS, use_ui_font=True)
		line_y += 1
		draw_text_line(0, line_y, "I: Inventory"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
		line_y += 1
		draw_text_line(0, line_y, "C: Character"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
		line_y += 1
		draw_text_line(0, line_y, "M: Map"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
		line_y += 1
		draw_text_line(0, line_y, "Esc: Menu"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
		line_y += 1

		# Milestone messages for combined exploration
		for threshold in (25, 50, 75, 100):
			if pct >= threshold and threshold not in announced_milestones:
				add_message(f"Exploration {threshold}% uncovered.")
				announced_milestones.add(threshold)

		# Debug UI pane additions
		if debug_mode:
			line_y += 1
			draw_text_line(0, line_y, "== DEBUG =="[:UI_COLS], scale_color(WALL_LIGHT, 1.0), UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, f"F1 Vis:{'On' if debug_show_all_visible else 'Off'}"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "F2 Reveal"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, f"F3 Clip:{'Off' if debug_noclip else 'On'}"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "F4/F5 Lr"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "N NewLvl"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "P Stamp"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)
			line_y += 1
			draw_text_line(0, line_y, "Ctrl+D dbg"[:UI_COLS], ui_color, UI_COLS, use_ui_font=True)

			door_counts = count_doors(dungeon)
			debug_text = [
				f"Player: ({px}, {py})",
				f"Level: {current_level_index + 1}",
				f"Size: {dungeon.w}x{dungeon.h}",
				"---",
				"Doors:",
				f"  Total: {door_counts['total']}",
				f"  Open: {door_counts['open']}",
				f"  Closed: {door_counts['closed']}",
				f"  Locked: {door_counts['locked']}",
				f"  Unlocked: {door_counts['unlocked']}",
				"---",
				"Commands:",
				"  R: Reveal/Unreveal",
				"  L: Level up",
				"  K: Level down",
				"  P: Regen level",
				"  S: Save session",
				"  O: Load session",
			]
			for i, line in enumerate(debug_text):
				draw_text_line(0, 14 + i, line, ui_color, UI_COLS, use_ui_font=True)

		# Minimap (after UI/world)
		if not menu_open and not inventory_open:
			draw_minimap(screen, dungeon, explored, visible, px, py, win_w, win_h)

		# Draw inventory if open
		if inventory_open:
			draw_inventory_slotbased()
		# Draw menu last if open
		elif menu_open:
			draw_menu()

		# Apply dungeon fade-in overlay (fade from black to transparent)
		if not dungeon_fade_complete:
			fade_overlay = pygame.Surface((win_w, win_h))
			fade_overlay.fill((0, 0, 0))
			fade_alpha = int(255 * (1.0 - dungeon_fade_alpha))  # Invert: start at 255 (opaque black), end at 0 (transparent)
			fade_overlay.set_alpha(fade_alpha)
			screen.blit(fade_overlay, (0, 0))

		pygame.display.flip()
		clock.tick(FPS)
		frame_count += 1

	# Cleanup when game loop exits
	if drip_sfx:
		drip_sfx.stop()


def count_doors(dungeon):
    """Counts doors by state in the given dungeon."""
    total = 0
    closed = 0
    open_doors = 0
    locked = 0
    for y in range(dungeon.h):
        for x in range(dungeon.w):
            door_state = dungeon.doors[x][y]
            if door_state != -1:
                total += 1
                if door_state == DOOR_CLOSED:
                    closed += 1
                elif door_state == DOOR_OPEN:
                    open_doors += 1
                elif door_state == DOOR_LOCKED:
                    locked += 1
    unlocked = total - locked
    return {
        "total": total,
        "closed": closed,
        "open": open_doors,
        "locked": locked,
        "unlocked": unlocked,
    }


def main():
	# Always run pygame mode per user request
	run_pygame()


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		show_cursor()
		pass

