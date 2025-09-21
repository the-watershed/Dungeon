import os
import sys
import time
import random
import math

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

LIGHT_RADIUS = 3  # tiles
FPS = 30
MAX_ROOMS = 25
ROOM_MIN_SIZE = 4
ROOM_MAX_SIZE = 9

# Pygame rendering base configuration
BASE_GRID_W = 80
BASE_GRID_H = 40
BASE_WIN_W = 1600
BASE_WIN_H = 1200
BASE_CELL_W = BASE_WIN_W // BASE_GRID_W  # 20
BASE_CELL_H = BASE_WIN_H // BASE_GRID_H  # 30


def get_term_size():
	try:
		import shutil
		size = shutil.get_terminal_size(fallback=(80, 25))
		return size.columns, size.lines
	except Exception:
		return 80, 25


def clamp(v, a, b):
	return max(a, min(b, v))


class Rect:
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h

	def center(self):
		cx = (self.x1 + self.x2) // 2
		cy = (self.y1 + self.y2) // 2
		return cx, cy

	def intersect(self, other):
		return (self.x1 < other.x2 and self.x2 > other.x1 and
				self.y1 < other.y2 and self.y2 > other.y1)


TILE_FLOOR = 0
TILE_WALL = 1


class Dungeon:
	def __init__(self, w, h):
		self.w = w
		self.h = h
		# Initialize all walls (tile types, not display chars)
		self.tiles = [[TILE_WALL for _ in range(h)] for _ in range(w)]
		self.rooms = []  # list[Rect]

	def carve_room(self, room: Rect):
		for x in range(room.x1 + 1, room.x2 - 1):
			for y in range(room.y1 + 1, room.y2 - 1):
				if 0 <= x < self.w and 0 <= y < self.h:
					self.tiles[x][y] = TILE_FLOOR

	def carve_h_tunnel(self, x1, x2, y):
		for x in range(min(x1, x2), max(x1, x2) + 1):
			if 0 <= x < self.w and 0 <= y < self.h:
				self.tiles[x][y] = TILE_FLOOR

	def carve_v_tunnel(self, y1, y2, x):
		for y in range(min(y1, y2), max(y1, y2) + 1):
			if 0 <= x < self.w and 0 <= y < self.h:
				self.tiles[x][y] = TILE_FLOOR

	def generate(self, max_rooms=MAX_ROOMS, room_min=ROOM_MIN_SIZE, room_max=ROOM_MAX_SIZE):
		for _ in range(max_rooms):
			w = random.randint(room_min, room_max)
			h = random.randint(room_min, room_max)
			x = random.randint(1, max(1, self.w - w - 2))
			y = random.randint(1, max(1, self.h - h - 2))
			new_room = Rect(x, y, w, h)

			if any(new_room.intersect(other) for other in self.rooms):
				continue

			self.carve_room(new_room)
			if self.rooms:
				# connect to previous room with a corridor
				(prev_x, prev_y) = self.rooms[-1].center()
				(new_x, new_y) = new_room.center()
				if random.random() < 0.5:
					self.carve_h_tunnel(prev_x, new_x, prev_y)
					self.carve_v_tunnel(prev_y, new_y, new_x)
				else:
					self.carve_v_tunnel(prev_y, new_y, prev_x)
					self.carve_h_tunnel(prev_x, new_x, new_y)

			self.rooms.append(new_room)

	def is_wall(self, x, y):
		if 0 <= x < self.w and 0 <= y < self.h:
			return self.tiles[x][y] == TILE_WALL
		return True


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

	dungeon = Dungeon(cols, rows)
	dungeon.generate()

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
	dungeon = Dungeon(map_w, grid_h)
	dungeon.generate()

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
	screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
	pygame.display.set_caption("ASCII Dungeon (Resizable)")
	clock = pygame.time.Clock()

	# Font/glyph cache builder (rebuild on resize)
	preferred_fonts = ["Consolas", "Courier New", "Lucida Console", "DejaVu Sans Mono"]

	def build_font(ch_h):
		# make font size slightly smaller than cell height
		size = max(8, ch_h - 4)
		for fname in preferred_fonts:
			try:
				f = pygame.font.SysFont(fname, size)
				if f is not None:
					return f
			except Exception:
				continue
		return pygame.font.Font(None, size)

	def build_glyph_cache(font_obj):
		# Characters we need to render
		ramp = " .:-=+*%"  # kept for potential future use
		glyphs_needed = {WALL_CH, PLAYER_CH}
		for extra in (DARK_CH, FLOOR_CH):
			if extra != ' ':
				glyphs_needed.add(extra)
		cache = {}
		def render_glyph(ch, color=(255, 255, 255)):
			key = (ch, color)
			surf = cache.get(key)
			if surf is None:
				surf = font_obj.render(ch, False, color)
				cache[key] = surf
			return surf
		return render_glyph

	font = build_font(cell_h)
	render_glyph = build_glyph_cache(font)

	# Minimap helper
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
		pygame.draw.rect(surface, (20, 20, 20), (ox - 2, oy - 2, w_px + 4, h_px + 4))
		pygame.draw.rect(surface, (80, 80, 80), (ox - 2, oy - 2, w_px + 4, h_px + 4), 1)

		vis_color = (220, 220, 220)
		exp_color = (90, 90, 90)
		wall_boost = 30

		for y in range(dungeon.h):
			for x in range(dungeon.w):
				rect = (ox + x * t, oy + y * t, t, t)
				if (x, y) in visible_set:
					# brighter for visible tiles; walls slightly brighter
					if dungeon.tiles[x][y] == TILE_WALL:
						c = tuple(min(255, v + wall_boost) for v in vis_color)
					else:
						c = vis_color
					surface.fill(c, rect)
				elif (x, y) in explored_set:
					# explored but not visible
					if dungeon.tiles[x][y] == TILE_WALL:
						c = tuple(min(255, v + wall_boost) for v in exp_color)
					else:
						c = exp_color
					surface.fill(c, rect)
				else:
					# unseen stays black (implicit)
					pass

		# Player marker
		pr = (ox + px * t, oy + py * t, t, t)
		surface.fill((255, 70, 70), pr)

	def resize_window(new_w, new_h):
		nonlocal win_w, win_h, grid_w, grid_h, cell_w, cell_h, font, render_glyph
		win_w, win_h = max(200, new_w), max(150, new_h)
		screen_flags = pygame.RESIZABLE
		pygame.display.set_mode((win_w, win_h), screen_flags)

		# Keep character count fixed; adjust cell size instead
		grid_w, grid_h = BASE_GRID_W, BASE_GRID_H
		cell_w = max(5, win_w // grid_w)
		cell_h = max(8, win_h // grid_h)

		# Rebuild font and glyph cache for new cell size
		font = build_font(cell_h)
		render_glyph = build_glyph_cache(font)

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

	running = True
	while running:
		# Input
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.VIDEORESIZE:
				resize_window(event.w, event.h)
			elif event.type == pygame.KEYDOWN:
				if event.key in (pygame.K_ESCAPE, pygame.K_q):
					running = False
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

		# Render
		screen.fill((0, 0, 0))
		off_x, off_y = compute_offsets()
		for y in range(dungeon.h):
			# Draw border at right edge of UI
			draw_char_at(BORDER_COL, y, WALL_CH, (200, 200, 200))

			for x in range(dungeon.w):
				tile = dungeon.tiles[x][y]
				draw_ch = ' '
				color = (255, 255, 255)
				if (x, y) == (px, py):
					draw_ch = PLAYER_CH
					color = (255, 255, 255)
					explored.add((x, y))
				elif (x, y) in visible:
					explored.add((x, y))
					if tile == TILE_WALL:
						# wall brightness falloff by distance
						d = visible[(x, y)]
						t = 1.0 - (d / max(1e-6, LIGHT_RADIUS))
						t = clamp(t, 0.0, 1.0)
						c = int(80 + 175 * t)
						color = (c, c, c)
						draw_ch = WALL_CH
					else:
						# floors: draw configured floor with darker brightness falloff than walls
						d = visible[(x, y)]
						t = 1.0 - (d / max(1e-6, LIGHT_RADIUS))
						t = clamp(t, 0.0, 1.0)
						# darker overall: ~35 near edge to ~130 near player
						cf = int(35 + 95 * t)
						color = (cf, cf, cf)
						draw_ch = FLOOR_CH
				else:
					# complete darkness outside radius: draw config char
					draw_ch = DARK_CH
				# Offset dungeon draw by UI width + border
				if draw_ch != ' ':
					surf = render_glyph(draw_ch, color)
					gx = off_x + (UI_COLS + 1 + x) * cell_w + (cell_w - surf.get_width()) // 2
					gy = off_y + y * cell_h + (cell_h - surf.get_height()) // 2
					screen.blit(surf, (gx, gy))

		# HUD (optional)
		if SETTINGS.get('hud_text', True):
			hud_text = f"WASD move, Esc/Q quit | {dungeon.w}x{dungeon.h} | r={LIGHT_RADIUS}"
			hud_surf = font.render(hud_text, False, (180, 180, 180))
			screen.blit(hud_surf, (4, win_h - hud_surf.get_height() - 4))

		# UI panel content (draw after world so it overlays if needed)
		# Simple sample stats
		ui_color = (160, 160, 160)
		title = "== STATUS =="
		draw_text_line(0, 0, title[:UI_COLS], (200, 200, 200), UI_COLS)
		draw_text_line(0, 2, f"Pos: {px:02d},{py:02d}"[:UI_COLS], ui_color, UI_COLS)
		draw_text_line(0, 3, f"Size:{dungeon.w:02d}x{dungeon.h:02d}"[:UI_COLS], ui_color, UI_COLS)
		draw_text_line(0, 4, f"Light:{LIGHT_RADIUS}"[:UI_COLS], ui_color, UI_COLS)

		# Minimap (after UI/world)
		draw_minimap(screen, dungeon, explored, visible, px, py)

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

