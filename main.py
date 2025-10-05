import os
import sys
import time
import random
import math
import re
from typing import Callable

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
	path = os.path.join(SAVE_DIR, f"{sanitize_name(name)}.json")
	with open(path, 'w', encoding='utf-8') as f:
		json.dump(data, f)
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


def run_pygame():
	try:
		import pygame
	except Exception as e:
		print("Pygame is required for the windowed mode. Install with: pip install pygame")
		raise

	# Launch character creator at startup
	player_character = None
	try:
		from char_gui import run_character_creator
		player_character = run_character_creator()
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

	# Brick exploration tracking for pygame mode
	bricks_touched = set()  # set of (x,y) brick wall tiles lit at least once
	total_bricks = count_total_bricks(dungeon)

	# Wall/floor exploration tracking for pygame mode
	walls_touched = set()
	floors_touched = set()
	# Floors actually stepped on by the player (for exploration %)
	floors_stepped = set()
	# Use reachable floors from player and exposed walls for fair totals
	reachable = compute_reachable_floors(dungeon, px, py)
	total_floors = len(reachable)
	total_walls = count_total_exposed_walls(dungeon, reachable)

	# Debug toggles/state
	debug_mode = False            # Ctrl+D toggles
	debug_show_all_visible = False
	debug_noclip = False
	light_radius = LIGHT_RADIUS   # dynamic light radius for pygame mode

	# Initialize Pygame
	# Set window position before initialization to make sure window is visible
	try:
		os.environ['SDL_VIDEO_WINDOW_POS'] = '100,100'  # Position window away from edges
	except:
		pass
	
	pygame.init()
	screen = pygame.display.set_mode((win_w, win_h))
	pygame.display.set_caption("ASCII Dungeon (Resizable)")
	clock = pygame.time.Clock()

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
		def render_glyph(ch, color=(255, 255, 255)):
			key = (ch, color)
			surf = cache.get(key)
			if surf is None:
				surf = font_obj.render(ch, antialias, color)
				cache[key] = surf
			return surf
		return render_glyph

	# Build fonts: regular for map, larger for UI panel
	font = build_font(cell_h)
	ui_font = build_font(int(cell_h * 1.5))  # 1.5x larger for UI readability

	# Build parchment background via renderer module (static, no animation). Disable vignette to avoid concentric rings.
	# Use cell_w as grain_tile to align texture pattern with character grid
	parchment_renderer = ParchmentRenderer(base_color=PARCHMENT_BG, ink_color=INK_DARK, enable_vignette=False, grain_tile=cell_w)
	parchment_renderer.build_layers(win_w, win_h)
	parchment_static = parchment_renderer.generate(win_w, win_h)
	# Build glyph renderers for both fonts
	# render_glyph: type ignore to work around nested function type inference issue
	render_glyph = build_glyph_cache(font)  # type: ignore
	render_ui_glyph = build_glyph_cache(ui_font)  # type: ignore

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

	def draw_minimap(surface: pygame.Surface, dungeon: Dungeon, explored_set: set, visible_set: set, px: int, py: int) -> None:
		"""Draw minimap with fog-of-war and current visibility.
		
		Args:
			surface (pygame.Surface): Surface to draw the minimap on
			dungeon (Dungeon): Current dungeon to map
			explored_set (set): Set of explored tile coordinates
			visible_set (set): Set of currently visible tiles
			px (int): Player X coordinate
			py (int): Player Y coordinate
		"""
		mm = SETTINGS.get('minimap', {}) or {}
		if not mm.get('enabled', True):
			return
		t = int(mm.get('tile', 4))
		margin = int(mm.get('margin', 8))
		pos = (mm.get('position', 'top-right') or 'top-right').lower()
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

		# Player marker (bright green)
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

	def draw_char_at(cell_x: int, cell_y: int, ch: str, color: tuple[int, int, int], use_ui_font: bool = False) -> None:
		"""Draw a character glyph at specified cell coordinates.
		
		Args:
			cell_x (int): X coordinate in cell units
			cell_y (int): Y coordinate in cell units
			ch (str): Character to draw
			color (tuple[int, int, int]): RGB color for the character
			use_ui_font (bool): If True, use larger UI font instead of map font
		"""
		if ch == ' ':
			return
		surf = render_ui_glyph(ch, color) if use_ui_font else render_glyph(ch, color)
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

	def draw_text_line(cell_x, cell_y, text, color=(180, 180, 180), max_len=None, use_ui_font=False):
		if max_len is None:
			max_len = len(text)
		for i, ch in enumerate(text[:max_len]):
			draw_char_at(cell_x + i, cell_y, ch, color, use_ui_font=use_ui_font)

	# Session state: multi-level support
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
		})
		# rebuild minimap/world buffers for new level
		mm_reveal, mm_noise = build_minimap_buffers(dungeon)
		wr_reveal, wr_noise = build_world_reveal_buffers(dungeon)
		current_level_index = len(levels) - 1
		add_message("New level created.")

	# Initialize with first level
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
	})
	# build minimap buffers for initial level
	mm_reveal, mm_noise = build_minimap_buffers(dungeon)
	# build world FoW buffers for initial level
	wr_reveal, wr_noise = build_world_reveal_buffers(dungeon)
	current_level_index = 0

	# Mark starting tile as stepped if it's a floor
	if 0 <= px < dungeon.w and 0 <= py < dungeon.h and dungeon.tiles[px][py] == TILE_FLOOR:
		floors_stepped.add((px, py))
		levels[current_level_index]['floors_stepped'] = floors_stepped

	# Welcome message with character name
	if player_character:
		add_message(f"Welcome, {player_character.name} the {player_character.race} {player_character.char_class}!")
		add_message(f"HP: {player_character.current_hp}/{player_character.max_hp}, AC: {player_character.armor_class}")
	else:
		add_message("Welcome to the dungeon.")

	# Menu state
	menu_open = False
	menu_mode = 'main'  # main | settings | save | load
	menu_index = 0
	save_name = ""
	load_index = 0
	load_names = []

	def draw_menu():
		# DnD-style ASCII menu frame + banner
		box_w = 58
		box_h = 24
		x0 = (grid_w - box_w) // 2
		y0 = (grid_h - box_h) // 2

		# Colors (cream background with dark ink)
		frame_col = scale_color(INK_DARK, 1.0)
		title_col = scale_color(INK_DARK, 1.0)
		text_col = scale_color(INK_DARK, 0.95)
		dim_col = scale_color(INK_DARK, 0.6)

		# Fill background behind the menu with cream for maximum contrast
		off_x, off_y = compute_offsets()
		px = off_x + x0 * cell_w
		py = off_y + y0 * cell_h
		wpx = box_w * cell_w
		hpx = box_h * cell_h
		pygame.draw.rect(screen, PARCHMENT_BG, (px, py, wpx, hpx))

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

		# Banner (original ASCII, DnD-ish motif)
		banner = [
			"o=={::::::::::::::::::::::::::::::::::::::::::::}==o",
			"       <<  D U N G E O N   M E N U  >>        ",
			"'=={::::::::::::::::::::::::::::::::::::::::::::}=='",
		]
		for i, line in enumerate(banner):
			bx = x0 + (box_w - len(line)) // 2
			draw_text_line(bx, y0 + 1 + i, line, title_col)

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
			draw_opts(options, menu_index, 6)
		elif menu_mode == 'settings':
			hud = "On" if SETTINGS.get('hud_text', True) else "Off"
			mm = SETTINGS.get('minimap', {})
			mme = "On" if (mm.get('enabled', True)) else "Off"
			options = [f"HUD: {hud}", f"Minimap: {mme}", "Back"]
			draw_opts(options, menu_index, 6)
		elif menu_mode == 'save':
			prompt = "Name thy hero and press Enter:"
			draw_text_line(x0 + 3, y0 + 6, prompt, text_col, box_w - 6)
			draw_text_line(x0 + 3, y0 + 8, "> " + save_name, title_col, box_w - 6)
			draw_text_line(x0 + 3, y0 + box_h - 3, "Esc: Back", dim_col)
		elif menu_mode == 'load':
			if not load_names:
				draw_text_line(x0 + 3, y0 + 6, "No chronicles found.", text_col)
				draw_text_line(x0 + 3, y0 + box_h - 3, "Esc: Back", dim_col)
			else:
				draw_text_line(x0 + 3, y0 + 6, "Select a chronicle:", text_col)
				for i, nm in enumerate(load_names):
					col = title_col if i == load_index else text_col
					prefix = ">> " if i == load_index else "   "
					draw_text_line(x0 + 3, y0 + 8 + i, prefix + nm, col, box_w - 6)
					draw_text_line(x0 + 3, y0 + box_h - 3, "Enter: Load | Esc: Back", dim_col)

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
					if menu_open:
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
						load_index = 0
					continue
				if event.key == pygame.K_q and not menu_open:
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
								try:
									from char_gui import run_character_creator
									created_char = run_character_creator()
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
							elif menu_index == 1:  # Settings
								menu_mode = 'settings'
								menu_index = 0
							elif menu_index == 2:  # Save
								menu_mode = 'save'
								save_name = ""
							elif menu_index == 3:  # Load
								menu_mode = 'load'
								load_names = list_saves()
								load_index = 0
							elif menu_index == 4:  # Quit
								running = False
					elif menu_mode == 'settings':
						if event.key in (pygame.K_w, pygame.K_UP):
							menu_index = (menu_index - 1) % 3
						elif event.key in (pygame.K_s, pygame.K_DOWN):
							menu_index = (menu_index + 1) % 3
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							if menu_index == 0:  # toggle HUD
								SETTINGS['hud_text'] = not SETTINGS.get('hud_text', True)
							elif menu_index == 1:  # toggle minimap
								mm = SETTINGS.get('minimap', {})
								mm['enabled'] = not mm.get('enabled', True)
								SETTINGS['minimap'] = mm
							else:
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
								d2, exp2, px2, py2, levels_data, idx = load_session(nm)
								# rebuild in-memory levels from save
								new_levels = []
								for lvl in levels_data:
									dl = decode_tiles(lvl['tiles'])
									dl = decode_materials(dl, lvl.get('materials', []))
									expl = set(tuple(e) for e in lvl.get('explored', []))
									pl = tuple(lvl.get('player', [1, 1]))
									# Restore metrics if present
									bt_list = [tuple(pt) for pt in lvl.get('bricks_touched', [])]
									tb_val = int(lvl.get('total_bricks', count_total_bricks(dl)))
									wt_list = [tuple(pt) for pt in lvl.get('walls_touched', [])]
									ft_list = [tuple(pt) for pt in lvl.get('floors_touched', [])]
									fs_list = [tuple(pt) for pt in lvl.get('floors_stepped', [])]
									tw_val = int(lvl.get('total_walls', count_total_walls(dl)))
									tf_val = int(lvl.get('total_floors', count_total_floors(dl)))
									new_levels.append({
										'dungeon': dl,
										'explored': expl,
										'player': (int(pl[0]), int(pl[1])),
										'bricks_touched': set(bt_list),
										'total_bricks': tb_val,
										'walls_touched': set(wt_list),
										'floors_touched': set(ft_list),
										'floors_stepped': set(fs_list),
										'total_walls': tw_val,
										'total_floors': tf_val,
									})
								if not new_levels:
									raise ValueError('Empty save')
								levels = new_levels
								current_level_index = int(idx)
								# switch to current level
								dungeon = levels[current_level_index]['dungeon']
								explored = levels[current_level_index]['explored']
								px, py = levels[current_level_index]['player']
								bricks_touched = levels[current_level_index].get('bricks_touched', set())
								total_bricks = levels[current_level_index].get('total_bricks', count_total_bricks(dungeon))
								# Restore combined metrics
								walls_touched = levels[current_level_index].get('walls_touched', set())
								floors_touched = levels[current_level_index].get('floors_touched', set())
								floors_stepped = levels[current_level_index].get('floors_stepped', set())
								total_walls = levels[current_level_index].get('total_walls', count_total_walls(dungeon))
								total_floors = levels[current_level_index].get('total_floors', count_total_floors(dungeon))
								fov = FOV(dungeon)
								# rebuild minimap/world buffers for loaded level
								mm_reveal, mm_noise = build_minimap_buffers(dungeon)
								wr_reveal, wr_noise = build_world_reveal_buffers(dungeon)
								menu_mode = 'main'
								add_message(f"Loaded save '{nm}'.")
							except Exception as e:
								# simple error display in title line
								pass
						continue
				# If we reach here and menu not open, handle game controls
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
		if debug_show_all_visible:
			visible = {(x, y) for x in range(dungeon.w) for y in range(dungeon.h)}
		else:
			visible = fov.compute(px, py, max(1, int(light_radius - 0.5)))  # Slightly smaller visibility radius

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
						explored.add(world_pos)
						# Calculate distance from player for lighting
						dx = wx - px
						dy = wy - py
						d = math.sqrt(dx * dx + dy * dy)
						
						# Stronger falloff: quadratic for more dramatic lighting
						if d <= 1.0:
							# Immediate vicinity gets full brightness
							tval = 1.0
						else:
							# Quadratic falloff for distance > 1
							normalized_distance = d / light_radius
							tval = max(0.1, 1.0 - (normalized_distance * normalized_distance))  # Minimum brightness of 0.1
						
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
						
						# Enhanced directional boost for walls: stronger effect
						if tile == TILE_WALL:
							wnx, wny = wall_normal(dungeon, wx, wy)
							# Light vector from tile to player (toward the light source)
							lx = px - wx
							ly = py - wy
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
						
						# Track exploration metrics when a tile becomes visible
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
				else:
					if draw_ch != ' ':
						surf = render_glyph(draw_ch, color)
						gx = off_x + (UI_COLS + 1 + sx) * cell_w + (cell_w - surf.get_width()) // 2
						gy = off_y + sy * cell_h + (cell_h - surf.get_height()) // 2
						screen.blit(surf, (gx, gy))

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
		if not menu_open:
			draw_minimap(screen, dungeon, explored, visible, px, py)

		# Draw menu last if open
		if menu_open:
			draw_menu()

		pygame.display.flip()
		clock.tick(FPS)
		frame_count += 1


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

