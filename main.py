import os
import sys
import time
import random
import math
import re

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


def load_settings(path: str):
	defaults = {
		"floor": " ",
		"wall": "#",
		"player": "@",
		"dark": " ",  # outside light radius
		"hud_text": True,
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

LIGHT_RADIUS = 3  # tiles
FPS = 30
MAX_ROOMS = 25
ROOM_MIN_SIZE = 4
ROOM_MAX_SIZE = 9

# Pygame rendering base configuration
BASE_GRID_W = 80
BASE_GRID_H = 40
BASE_WIN_W = 800
BASE_WIN_H = 600
BASE_CELL_W = BASE_WIN_W // BASE_GRID_W  # 20
BASE_CELL_H = BASE_WIN_H // BASE_GRID_H  # 30

# Parchment palette (RGB) and world palette
# Parchment remains for minimap; world uses dark background with brown tones
PARCHMENT_BG = (245, 237, 215)
WORLD_BG = (32, 24, 16)        # dark brown background
WALL_LIGHT = (200, 170, 120)   # light brown for walls
FLOOR_MED = (140, 100, 60)     # medium brown for floors
WALL_BROWN = (140, 100, 60)    # kept for minimap
FLOOR_BROWN = (100, 75, 45)    # kept for minimap
INK_DARK = (40, 28, 18)        # for accents and text
PLAYER_GREEN = (60, 240, 90)   # bright green for player '@'

def scale_color(color, factor):
	f = max(0.0, min(1.0, factor))
	r = min(255, int(color[0] * f))
	g = min(255, int(color[1] * f))
	b = min(255, int(color[2] * f))
	return (r, g, b)


def get_term_size():
	try:
		import shutil
		size = shutil.get_terminal_size(fallback=(80, 25))
		return size.columns, size.lines
	except Exception:
		return 80, 25


def clamp(v, a, b):
	return max(a, min(b, v))


from dungeon_gen import Dungeon, Rect, TILE_WALL, TILE_FLOOR, generate_dungeon
# ---------------------------
# Save/Load helpers
# ---------------------------
def encode_tiles(dungeon: 'Dungeon'):
	# rows as strings of '0' floor and '1' wall
	rows = []
	for y in range(dungeon.h):
		row = ['1' if dungeon.tiles[x][y] == TILE_WALL else '0' for x in range(dungeon.w)]
		rows.append(''.join(row))
	return rows


def decode_tiles(rows):
	h = len(rows)
	w = len(rows[0]) if h > 0 else 0
	d = Dungeon(w, h)
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			d.tiles[x][y] = TILE_WALL if ch == '1' else TILE_FLOOR
	return d


def session_to_dict(dungeon: 'Dungeon', explored: set, px: int, py: int, levels=None, current_index=0):
	if levels is None:
		levels = []
	# include current dungeon as level 0 if levels is empty
	if not levels:
		levels = [{
			'w': dungeon.w,
			'h': dungeon.h,
			'tiles': encode_tiles(dungeon),
			'explored': list(sorted(explored)),
			'player': [px, py],
		}]
		current_index = 0
	data = {
		'current_index': current_index,
		'levels': levels,
	}
	return data


def dict_to_session(data):
	try:
		idx = int(data.get('current_index', 0))
		levels = data.get('levels', [])
		if not levels:
			raise ValueError('No levels in save')
		idx = max(0, min(idx, len(levels) - 1))
		cur = levels[idx]
		d = decode_tiles(cur['tiles'])
		explored_list = cur.get('explored', [])
		explored = set(tuple(e) for e in explored_list)
		px, py = cur.get('player', [1, 1])
		return d, explored, int(px), int(py), levels, idx
	except Exception as e:
		raise


def sanitize_name(name: str) -> str:
	name = name.strip()
	name = re.sub(r"[^A-Za-z0-9_-]+", "_", name)
	return name[:40] if name else "player"


def save_session(name: str, dungeon: 'Dungeon', explored: set, px: int, py: int, levels=None, current_index=0):
	os.makedirs(SAVE_DIR, exist_ok=True)
	data = session_to_dict(dungeon, explored, px, py, levels=levels, current_index=current_index)
	path = os.path.join(SAVE_DIR, f"{sanitize_name(name)}.json")
	with open(path, 'w', encoding='utf-8') as f:
		json.dump(data, f)
	return path


def load_session(name: str):
	path = os.path.join(SAVE_DIR, f"{sanitize_name(name)}.json")
	with open(path, 'r', encoding='utf-8') as f:
		data = json.load(f)
	return dict_to_session(data)


def list_saves():
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
	def __init__(self, dungeon: Dungeon):
		self.dungeon = dungeon

	def compute(self, cx, cy, radius):
		visible = {(cx, cy): 0.0}

		def blocks_light(x, y):
			return self.dungeon.is_wall(x, y)

		def set_visible(x, y):
			dx = x - cx
			dy = y - cy
			dist = math.sqrt(dx * dx + dy * dy)
			if dist <= radius:
				visible[(x, y)] = dist

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
CSI = "\x1b["


def hide_cursor():
	sys.stdout.write(CSI + "?25l")
	sys.stdout.flush()


def show_cursor():
	sys.stdout.write(CSI + "?25h")
	sys.stdout.flush()


def clear_screen():
	sys.stdout.write(CSI + "2J" + CSI + "H")
	sys.stdout.flush()


def move_cursor(row=1, col=1):
	sys.stdout.write(f"{CSI}{row};{col}H")


def build_frame(dungeon: Dungeon, px, py, visible_map, explored):
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
				else:
					# Floors render as configured floor character (may be space or '#')
					row_chars.append(FLOOR_CH)
			else:
				# Complete darkness outside light radius
				row_chars.append(DARK_CH)
		lines.append(''.join(row_chars))
	return '\n'.join(lines)


def read_input_nonblocking():
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


def run_terminal():
	random.seed()
	cols, rows = get_term_size()
	# Reserve last line for HUD
	rows = max(15, rows - 1)
	cols = max(40, cols)

	# Use modular dungeon generator
	dungeon = generate_dungeon(cols, rows, complexity=0.5, length=MAX_ROOMS,
		room_min=ROOM_MIN_SIZE, room_max=ROOM_MAX_SIZE)

	# Place player at center of first room or fallback to first open tile
	if dungeon.rooms:
		px, py = dungeon.rooms[0].center()
		# ensure inside floor
		if dungeon.is_wall(px, py):
			# find nearby floor
			found = False
			for r in range(1, 10):
				for dx in range(-r, r + 1):
					for dy in range(-r, r + 1):
						x, y = px + dx, py + dy
						if 0 <= x < dungeon.w and 0 <= y < dungeon.h and not dungeon.is_wall(x, y):
							px, py = x, y
							found = True
							break
					if found:
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

	random.seed()

	# Initial window and grid
	win_w, win_h = BASE_WIN_W, BASE_WIN_H
	grid_w, grid_h = BASE_GRID_W, BASE_GRID_H
	cell_w, cell_h = BASE_CELL_W, BASE_CELL_H

	# UI panel configuration (character columns)
	UI_COLS = 12  # width of UI panel in characters
	BORDER_COL = UI_COLS  # vertical border column index

	# Dungeon uses the remaining columns
	map_w = max(10, grid_w - UI_COLS - 1)
	dungeon = generate_dungeon(map_w, grid_h, complexity=0.5, length=MAX_ROOMS,
		room_min=ROOM_MIN_SIZE, room_max=ROOM_MAX_SIZE)

	# Place player
	if dungeon.rooms:
		px, py = dungeon.rooms[0].center()
		if dungeon.is_wall(px, py):
			found = False
			for r in range(1, 10):
				for dx in range(-r, r + 1):
					for dy in range(-r, r + 1):
						x, y = px + dx, py + dy
						if 0 <= x < dungeon.w and 0 <= y < dungeon.h and not dungeon.is_wall(x, y):
							px, py = x, y
							found = True
							break
					if found:
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

	fov = FOV(dungeon)
	explored = set()

	# Initialize Pygame
	pygame.init()
	screen = pygame.display.set_mode((win_w, win_h))
	pygame.display.set_caption("ASCII Dungeon (Resizable)")
	clock = pygame.time.Clock()

	# Font/glyph cache builder (rebuild on resize)
	preferred_fonts = ["Courier New", "Consolas", "Lucida Console", "DejaVu Sans Mono", "Monaco"]

	def build_font(ch_h):
		# Improve crispness by choosing the largest font that fits the cell exactly
		# Try settings overrides first, then preferred list, scanning down sizes
		max_size = max(6, min(48, ch_h))
		font_file = (SETTINGS.get('font_file') or '').strip()
		font_name = (SETTINGS.get('font_name') or '').strip()
		candidates = []
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

	def build_glyph_cache(font_obj):
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

	font = build_font(cell_h)
	render_glyph = build_glyph_cache(font)

	# Minimap reveal buffers (progress + noise) for watercolor effect
	mm_reveal = []  # type: list[list[float]]
	mm_noise = []   # type: list[list[float]]

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

	def draw_minimap(surface, dungeon, explored_set, visible_set, px, py):
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

		# Draw background frame (optional)
		pygame.draw.rect(surface, PARCHMENT_BG, (ox - 2, oy - 2, w_px + 4, h_px + 4))
		pygame.draw.rect(surface, scale_color(INK_DARK, 0.7), (ox - 2, oy - 2, w_px + 4, h_px + 4), 1)

		# Colors for minimap
		vis_floor = scale_color(FLOOR_BROWN, 0.9)
		vis_wall = scale_color(WALL_BROWN, 1.0)
		exp_floor = scale_color(FLOOR_BROWN, 0.5)
		exp_wall = scale_color(WALL_BROWN, 0.6)

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
					# choose target color based on current visibility
					if (x, y) in visible_set:
						c_target = vis_wall if dungeon.tiles[x][y] == TILE_WALL else vis_floor
					else:
						c_target = exp_wall if dungeon.tiles[x][y] == TILE_WALL else exp_floor
					# watercolor-like reveal from parchment using per-tile progress and noise
					prog = mm_reveal[x][y] if 0 <= x < dungeon.w and 0 <= y < dungeon.h else 1.0
					noi = mm_noise[x][y] if 0 <= x < dungeon.w and 0 <= y < dungeon.h else 0.0
					alpha = clamp(pow(clamp(prog + noi, 0.0, 1.0), 1.8), 0.0, 1.0)
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

	def draw_char_at(cell_x, cell_y, ch, color):
		if ch == ' ':
			return
		surf = render_glyph(ch, color)
		gx = off_x + cell_x * cell_w + (cell_w - surf.get_width()) // 2
		gy = off_y + cell_y * cell_h + (cell_h - surf.get_height()) // 2
		screen.blit(surf, (gx, gy))

	def draw_text_line(cell_x, cell_y, text, color=(180, 180, 180), max_len=None):
		if max_len is None:
			max_len = len(text)
		for i, ch in enumerate(text[:max_len]):
			draw_char_at(cell_x + i, cell_y, ch, color)

	# Session state: multi-level support
	levels = []  # list of dicts: { 'dungeon': Dungeon, 'explored': set[(x,y)], 'player': (px,py) }
	current_level_index = 0

	def snapshot_current():
		return {'dungeon': dungeon, 'explored': set(explored), 'player': (px, py)}

	def collect_levels_for_save(level_list):
		out = []
		for lvl in level_list:
			d = lvl['dungeon']
			exp = lvl['explored']
			pxx, pyy = lvl['player']
			out.append({
				'w': d.w,
				'h': d.h,
				'tiles': encode_tiles(d),
				'explored': list(sorted(exp)),
				'player': [pxx, pyy],
			})
		return out

	def push_new_level():
		nonlocal dungeon, fov, explored, px, py, current_level_index
		nonlocal mm_reveal, mm_noise
		# Save snapshot of current first
		if levels:
			levels[current_level_index] = snapshot_current()
		# Create new level same size as current dungeon window
		nd = generate_dungeon(map_w, grid_h, complexity=0.5, length=MAX_ROOMS,
			room_min=ROOM_MIN_SIZE, room_max=ROOM_MAX_SIZE)
		# place player
		if nd.rooms:
			pxn, pyn = nd.rooms[0].center()
		else:
			pxn, pyn = 1, 1
		dungeon = nd
		fov = FOV(dungeon)
		explored = set()
		px, py = pxn, pyn
		levels.append({'dungeon': dungeon, 'explored': explored, 'player': (px, py)})
		# rebuild minimap buffers for new level
		mm_reveal, mm_noise = build_minimap_buffers(dungeon)
		current_level_index = len(levels) - 1

	# Initialize with first level
	px, py = (dungeon.rooms[0].center() if dungeon.rooms else (1, 1))
	levels.append({'dungeon': dungeon, 'explored': explored, 'player': (px, py)})
	# build minimap buffers for initial level
	mm_reveal, mm_noise = build_minimap_buffers(dungeon)
	current_level_index = 0

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
			options = ["Settings", "Save", "Load", "Quit"]
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
	while running:
		# Input
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.KEYDOWN:
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

				if menu_open:
					# Menu navigation
					if menu_mode == 'main':
						if event.key in (pygame.K_w, pygame.K_UP):
							menu_index = (menu_index - 1) % 4
						elif event.key in (pygame.K_s, pygame.K_DOWN):
							menu_index = (menu_index + 1) % 4
						elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
							if menu_index == 0:  # Settings
								menu_mode = 'settings'
								menu_index = 0
							elif menu_index == 1:  # Save
								menu_mode = 'save'
								save_name = ""
							elif menu_index == 2:  # Load
								menu_mode = 'load'
								load_names = list_saves()
								load_index = 0
							elif menu_index == 3:  # Quit
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
									expl = set(tuple(e) for e in lvl.get('explored', []))
									pl = tuple(lvl.get('player', [1, 1]))
									new_levels.append({'dungeon': dl, 'explored': expl, 'player': (int(pl[0]), int(pl[1]))})
								if not new_levels:
									raise ValueError('Empty save')
								levels = new_levels
								current_level_index = int(idx)
								# switch to current level
								dungeon = levels[current_level_index]['dungeon']
								explored = levels[current_level_index]['explored']
								px, py = levels[current_level_index]['player']
								fov = FOV(dungeon)
								# rebuild minimap buffers for loaded level
								mm_reveal, mm_noise = build_minimap_buffers(dungeon)
								menu_mode = 'main'
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
					if 0 <= nx < dungeon.w and 0 <= ny < dungeon.h and not dungeon.is_wall(nx, ny):
						px, py = nx, ny

		# Update visibility
		visible = fov.compute(px, py, LIGHT_RADIUS)
		# Animate minimap reveal
		dt = clock.get_time() / 1000.0
		reveal_rate = 2.0
		for (ex, ey) in explored:
			if 0 <= ex < dungeon.w and 0 <= ey < dungeon.h:
				if mm_reveal[ex][ey] < 1.0:
					mm_reveal[ex][ey] = clamp(mm_reveal[ex][ey] + dt * reveal_rate, 0.0, 1.0)

		# Render
		screen.fill(WORLD_BG)
		off_x, off_y = compute_offsets()

		# Camera centered on player; viewport size is map_w x grid_h
		view_w = map_w
		view_h = grid_h
		# Always center camera on player; allow camera to go out-of-bounds
		cam_x = px - view_w // 2
		cam_y = py - view_h // 2

		# Draw UI border along the visible rows only
		for sy in range(view_h):
			wy = cam_y + sy
			if 0 <= wy < dungeon.h:
				draw_char_at(BORDER_COL, sy, WALL_CH, scale_color(WALL_LIGHT, 0.9))

		# Draw tiles in viewport window
		for sy in range(view_h):
			wy = cam_y + sy
			for sx in range(view_w):
				wx = cam_x + sx
				draw_ch = ' '
				color = INK_DARK
				if 0 <= wx < dungeon.w and 0 <= wy < dungeon.h:
					# In-bounds tiles
					tile = dungeon.tiles[wx][wy]
					world_pos = (wx, wy)
					if world_pos in visible:
						explored.add(world_pos)
						if tile == TILE_WALL:
							d = visible[world_pos]
							t = 1.0 - (d / max(1e-6, LIGHT_RADIUS))
							t = clamp(t, 0.0, 1.0)
							bw = 0.6 + 0.4 * t
							color = scale_color(WALL_LIGHT, bw)
							draw_ch = WALL_CH
						else:
							d = visible[world_pos]
							t = 1.0 - (d / max(1e-6, LIGHT_RADIUS))
							t = clamp(t, 0.0, 1.0)
							bf = 0.45 + 0.35 * t
							color = scale_color(FLOOR_MED, bf)
							draw_ch = '#'
					else:
						# Out-of-bounds draws darkness glyph for consistency
						draw_ch = DARK_CH

				if draw_ch != ' ':
					surf = render_glyph(draw_ch, color)
					gx = off_x + (UI_COLS + 1 + sx) * cell_w + (cell_w - surf.get_width()) // 2
					gy = off_y + sy * cell_h + (cell_h - surf.get_height()) // 2
					screen.blit(surf, (gx, gy))

		# Draw player at the center of the viewport (screen), not moving
		# Always draw player at the center of the viewport
		pcx = clamp(view_w // 2, 0, view_w - 1)
		pcy = clamp(view_h // 2, 0, view_h - 1)
		surf = render_glyph(PLAYER_CH, PLAYER_GREEN)
		gx = off_x + (UI_COLS + 1 + pcx) * cell_w + (cell_w - surf.get_width()) // 2
		gy = off_y + pcy * cell_h + (cell_h - surf.get_height()) // 2
		screen.blit(surf, (gx, gy))

		# HUD (optional)
		if SETTINGS.get('hud_text', True) and not menu_open:
			hud_text = f"WASD move, Esc/Q quit | {dungeon.w}x{dungeon.h} | r={LIGHT_RADIUS}"
			hud_surf = font.render(hud_text, False, scale_color(WALL_LIGHT, 1.0))
			screen.blit(hud_surf, (4, win_h - hud_surf.get_height() - 4))

		# UI panel content (draw after world so it overlays if needed)
		# Simple sample stats
		ui_color = scale_color(WALL_LIGHT, 0.95)
		title = "== STATUS =="
		draw_text_line(0, 0, title[:UI_COLS], scale_color(WALL_LIGHT, 1.0), UI_COLS)
		draw_text_line(0, 2, f"Pos: {px:02d},{py:02d}"[:UI_COLS], ui_color, UI_COLS)
		draw_text_line(0, 3, f"Size:{dungeon.w:02d}x{dungeon.h:02d}"[:UI_COLS], ui_color, UI_COLS)
		draw_text_line(0, 4, f"Light:{LIGHT_RADIUS}"[:UI_COLS], ui_color, UI_COLS)

		# Minimap (after UI/world)
		if not menu_open:
			draw_minimap(screen, dungeon, explored, visible, px, py)

		# Draw menu last if open
		if menu_open:
			draw_menu()

		pygame.display.flip()
		clock.tick(FPS)


def main():
	# Always run pygame mode per user request
	run_pygame()


if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		show_cursor()
		pass

