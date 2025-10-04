"""
Dungeon generation module.

Exports:
- Rect: simple rectangle helper
- TILE_FLOOR, TILE_WALL: tile identifiers
- Dungeon: grid container with carve helpers
- generate_dungeon(width, height, complexity, length, room_min, room_max, seed, linearity, entropy):
	Create and return a Dungeon with rooms and tunnels. 
	
	Linearity controls the "straightness" of the main path:
	- 0.0 = chaotic/random room placement
	- 1.0 = perfectly linear chain of rooms
	
	Entropy controls side rooms and branches off the main path:
	- 0.0 = no side rooms, pure main pathway
	- 1.0 = many side rooms and branches creating complex layouts
	
	These parameters work together:
	- High linearity + Low entropy = straight corridor with few branches
	- High linearity + High entropy = straight main path with many side rooms
	- Low linearity + Low entropy = chaotic but sparse layout
	- Low linearity + High entropy = complex maze-like structure
"""
from __future__ import annotations

import random
from typing import List


class Rect:
	"""Rectangle helper class for dungeon room placement and collision detection.
	
	Represents a rectangular area with integer coordinates. Uses x1,y1 as top-left
	corner and x2,y2 as bottom-right corner (exclusive bounds).
	
	Attributes:
		x1 (int): Left edge X coordinate (inclusive)
		y1 (int): Top edge Y coordinate (inclusive)  
		x2 (int): Right edge X coordinate (exclusive)
		y2 (int): Bottom edge Y coordinate (exclusive)
	"""
	def __init__(self, x: int, y: int, w: int, h: int):
		"""Initialize rectangle from top-left corner and dimensions.
		
		Args:
			x (int): Left edge X coordinate
			y (int): Top edge Y coordinate
			w (int): Width in tiles
			h (int): Height in tiles
		"""
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h

	def center(self) -> tuple[int, int]:
		"""Get center point of rectangle.
		
		Returns:
			tuple[int, int]: (center_x, center_y) coordinates
		"""
		cx = (self.x1 + self.x2) // 2
		cy = (self.y1 + self.y2) // 2
		return cx, cy

	def intersect(self, other: "Rect") -> bool:
		"""Check if this rectangle intersects with another rectangle.
		
		Args:
			other (Rect): Rectangle to test intersection with
			
		Returns:
			bool: True if rectangles overlap, False otherwise
		"""
		return (self.x1 < other.x2 and self.x2 > other.x1 and
				self.y1 < other.y2 and self.y2 > other.y1)

	def __contains__(self, point: tuple[int, int]) -> bool:
		"""Check if a point is inside this rectangle.
		
		Args:
			point (tuple[int, int]): (x, y) coordinates to test
			
		Returns:
			bool: True if point is inside rectangle bounds
		"""
		x, y = point
		return self.x1 <= x < self.x2 and self.y1 <= y < self.y2



# Tile type constants
TILE_FLOOR = 0  # Passable floor tile
TILE_WALL = 1   # Impassable wall tile  
TILE_DOOR = 2   # Door tile (passability depends on state)

# Door state constants
DOOR_CLOSED = 0  # Door is closed (blocks movement and light)
DOOR_OPEN = 1    # Door is open (allows movement and light)
DOOR_LOCKED = 2  # Door is locked (blocks movement, requires key)

# Material identifiers (render-agnostic)
# These constants define different material types for tiles, affecting visual appearance
MAT_COBBLE = 0   # Stone floor / cobblestone (default floor material)
MAT_BRICK = 1    # Brick wall (default wall material)
MAT_DIRT = 2     # Dirt/earth surface (natural areas)
MAT_MOSS = 3     # Mossy floor/stone (damp areas)
MAT_SAND = 4     # Sand/sandstone (desert areas)
MAT_IRON = 5     # Iron bars/metal (prisons, gates)
MAT_GRASS = 6    # Grass surface (outdoor areas)
MAT_WATER = 7    # Water surface (rivers, pools)
MAT_LAVA = 8     # Lava surface (volcanic areas)
MAT_MARBLE = 9   # Marble surface (elegant areas)
MAT_WOOD = 10    # Wood surface (bridges, floors)


class Dungeon:
	"""Main dungeon data structure containing tiles, materials, doors, and rooms.
	
	Stores the complete dungeon layout including:
	- Tile types (walls/floors/doors)
	- Material assignments for rendering
	- Door states and positions  
	- Room rectangles for generation logic
	
	Attributes:
		w (int): Width in tiles
		h (int): Height in tiles
		tiles (List[List[int]]): 2D grid of tile type constants
		materials (List[List[int]]): 2D grid of material type constants
		doors (List[List[int]]): 2D grid of door states (-1 means no door)
		rooms (List[Rect]): List of rectangular room areas
	"""
	def __init__(self, w: int, h: int):
		"""Initialize dungeon with all walls.
		
		Args:
			w (int): Width in tiles
			h (int): Height in tiles
		"""
		self.w = w
		self.h = h
		# Initialize all walls (tile types, not display chars)
		self.tiles: List[List[int]] = [[TILE_WALL for _ in range(h)] for _ in range(w)]
		# Materials grid, default to brick (matches initial walls)
		self.materials: List[List[int]] = [[MAT_BRICK for _ in range(h)] for _ in range(w)]
		# Doors grid, stores DOOR_OPEN, DOOR_CLOSED, etc. A value of -1 means no door.
		self.doors: List[List[int]] = [[-1 for _ in range(h)] for _ in range(w)]
		self.rooms: List[Rect] = []
		self.throne_room_index: int = -1  # Index of the throne room in self.rooms list

	def carve_room(self, room: Rect) -> None:
		"""Carve out a rectangular room in the dungeon.
		
		Converts wall tiles to floor tiles within the room bounds,
		leaving a 1-tile border around the edges.
		
		Args:
			room (Rect): Rectangle defining the room area
		"""
		for x in range(room.x1 + 1, room.x2 - 1):
			for y in range(room.y1 + 1, room.y2 - 1):
				if 0 <= x < self.w and 0 <= y < self.h:
					self.tiles[x][y] = TILE_FLOOR
					self.materials[x][y] = MAT_COBBLE

	def carve_h_tunnel(self, x1: int, x2: int, y: int):
		for x in range(min(x1, x2), max(x1, x2) + 1):
			if 0 <= x < self.w and 0 <= y < self.h:
				self.tiles[x][y] = TILE_FLOOR
				self.materials[x][y] = MAT_COBBLE

	def carve_v_tunnel(self, y1: int, y2: int, x: int):
		for y in range(min(y1, y2), max(y1, y2) + 1):
			if 0 <= x < self.w and 0 <= y < self.h:
				self.tiles[x][y] = TILE_FLOOR
				self.materials[x][y] = MAT_COBBLE

	def add_door(self, x, y, locked=False):
		"""Places a door at (x,y) if it's a valid wall location between floors."""
		if not (0 < x < self.w - 1 and 0 < y < self.h - 1):
			return False
		if self.tiles[x][y] != TILE_WALL:
			return False

		# Check for horizontal passage (floor left/right, wall above/below)
		is_horizontal = (self.tiles[x-1][y] == TILE_FLOOR and self.tiles[x+1][y] == TILE_FLOOR and
						 self.tiles[x][y-1] == TILE_WALL and self.tiles[x][y+1] == TILE_WALL)
		# Check for vertical passage
		is_vertical = (self.tiles[x][y-1] == TILE_FLOOR and self.tiles[x][y+1] == TILE_FLOOR and
					   self.tiles[x-1][y] == TILE_WALL and self.tiles[x+1][y] == TILE_WALL)

		if is_horizontal or is_vertical:
			self.tiles[x][y] = TILE_DOOR
			self.doors[x][y] = DOOR_LOCKED if locked else DOOR_CLOSED
			self.materials[x][y] = MAT_WOOD
			return True
		return False

	def _is_room_entrance(self, x: int, y: int) -> bool:
		"""Check if a wall position is a valid room entrance.
		
		A room entrance is a wall position that:
		1. Is on the boundary of a room (adjacent to room interior)
		2. Is adjacent to a corridor or different room
		
		Args:
			x, y: Wall coordinates to check
			
		Returns:
			True if this wall position is a valid room entrance
		"""
		if self.tiles[x][y] != TILE_WALL:
			return False
			
		# Check if this wall position is adjacent to any room interior
		adjacent_to_room = False
		adjacent_to_corridor_or_different_room = False
		
		# Check all 4 directions from the wall
		directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # up, down, right, left
		
		for dx, dy in directions:
			nx, ny = x + dx, y + dy
			if 0 <= nx < self.w and 0 <= ny < self.h and self.tiles[nx][ny] == TILE_FLOOR:
				room_containing_neighbor = self._find_room_containing(nx, ny)
				
				if room_containing_neighbor is not None:
					# This direction leads to a room interior
					adjacent_to_room = True
				else:
					# This direction leads to a corridor
					adjacent_to_corridor_or_different_room = True
		
		# A valid room entrance must be adjacent to both a room and a corridor
		return adjacent_to_room and adjacent_to_corridor_or_different_room
		
	def _find_room_containing(self, x: int, y: int):
		"""Find the room that contains the given position, or None if not in any room.
		
		Args:
			x, y: Position to check
			
		Returns:
			Room object containing the position, or None if position is in a corridor
		"""
		for room in self.rooms:
			# Check if position is strictly inside the room (not on the border walls)
			if room.x1 < x < room.x2 - 1 and room.y1 < y < room.y2 - 1:
				return room
		return None
		
	def _is_position_in_room(self, x: int, y: int) -> bool:
		"""Check if a floor position is inside any room (not in a corridor).
		
		Args:
			x, y: Position to check
			
		Returns:
			True if the position is inside a room's interior
		"""
		return self._find_room_containing(x, y) is not None

	def generate(self, max_rooms: int, room_min: int, room_max: int, linearity: float = 0.0, entropy: float = 0.0):
		"""Generate rooms with optional linear progression and side branching.
		
		Args:
			max_rooms (int): Maximum number of rooms to place
			room_min (int): Minimum room size
			room_max (int): Maximum room size
			linearity (float): 0.0 = random placement, 1.0 = perfectly linear progression (series)
			entropy (float): 0.0 = no side rooms, 1.0 = many side rooms off main path
		"""
		if linearity >= 0.8:
			# High linearity: create a linear chain of rooms (series connection)
			self._generate_linear(max_rooms, room_min, room_max, entropy)
		elif linearity >= 0.4:
			# Medium linearity: biased placement with some randomness
			self._generate_biased_linear(max_rooms, room_min, room_max, linearity, entropy)
		else:
			# Low linearity: mostly random placement
			self._generate_random(max_rooms, room_min, room_max, linearity, entropy)
		
		# Mark the last room as the throne room and give it special materials
		self._setup_throne_room()
		
		# After all rooms and corridors are carved, place doors at room entrances only.
		door_candidates = []
		for y in range(1, self.h - 1):
			for x in range(1, self.w - 1):
				if self.tiles[x][y] == TILE_WALL and self._is_room_entrance(x, y):
					door_candidates.append((x, y))

		# Place doors at a random subset of room entrance candidates
		placed_doors = 0
		for x, y in door_candidates:
			if random.random() < 0.5:  # 50% chance to place a door at room entrances
				if self.add_door(x, y):
					placed_doors += 1

	def _generate_perfectly_linear(self, max_rooms: int, room_min: int, room_max: int):
		"""Generate rooms in a perfectly straight linear chain with minimal branching."""
		if max_rooms <= 0:
			return
			
		# Choose direction based on aspect ratio
		horizontal = self.w > self.h
		
		if horizontal:
			# Horizontal chain: evenly spaced along x-axis
			spacing = max(room_max + 3, self.w // (max_rooms + 1))
			center_y = self.h // 2
			
			for i in range(max_rooms):
				# Calculate exact position for this room
				center_x = spacing * (i + 1)
				if center_x >= self.w - room_max:
					break  # Don't place rooms too close to edge
				
				# Keep rooms aligned vertically
				w = random.randint(room_min, room_max)
				h = random.randint(room_min, room_max)
				x = max(1, min(self.w - w - 1, center_x - w // 2))
				y = max(1, min(self.h - h - 1, center_y - h // 2))
				
				new_room = Rect(x, y, w, h)
				self.carve_room(new_room)
				self.rooms.append(new_room)
		else:
			# Vertical chain: evenly spaced along y-axis
			spacing = max(room_max + 3, self.h // (max_rooms + 1))
			center_x = self.w // 2
			
			for i in range(max_rooms):
				# Calculate exact position for this room
				center_y = spacing * (i + 1)
				if center_y >= self.h - room_max:
					break  # Don't place rooms too close to edge
				
				# Keep rooms aligned horizontally
				w = random.randint(room_min, room_max)
				h = random.randint(room_min, room_max)
				x = max(1, min(self.w - w - 1, center_x - w // 2))
				y = max(1, min(self.h - h - 1, center_y - h // 2))
				
				new_room = Rect(x, y, w, h)
				self.carve_room(new_room)
				self.rooms.append(new_room)
		
		# Connect rooms with simple straight corridors only
		for i in range(1, len(self.rooms)):
			prev_center = self.rooms[i-1].center()
			curr_center = self.rooms[i].center()
			
			# Create single straight corridor between consecutive rooms
			if horizontal:
				# Horizontal progression: connect with straight horizontal corridor
				self.carve_h_tunnel(prev_center[0], curr_center[0], prev_center[1])
				# Only add vertical segment if rooms are at different y levels
				if prev_center[1] != curr_center[1]:
					self.carve_v_tunnel(prev_center[1], curr_center[1], curr_center[0])
			else:
				# Vertical progression: connect with straight vertical corridor
				self.carve_v_tunnel(prev_center[1], curr_center[1], prev_center[0])
				# Only add horizontal segment if rooms are at different x levels
				if prev_center[0] != curr_center[0]:
					self.carve_h_tunnel(prev_center[0], curr_center[0], curr_center[1])

	def _setup_throne_room(self) -> None:
		"""Mark the last room as a throne room and give it special materials."""
		if len(self.rooms) > 0:
			# The last room becomes the throne room
			self.throne_room_index = len(self.rooms) - 1
			throne_room = self.rooms[self.throne_room_index]
			
			# Give the throne room special materials (marble for a royal look)
			for x in range(throne_room.x1 + 1, throne_room.x2 - 1):
				for y in range(throne_room.y1 + 1, throne_room.y2 - 1):
					if 0 <= x < self.w and 0 <= y < self.h and self.tiles[x][y] == TILE_FLOOR:
						self.materials[x][y] = MAT_MARBLE
			
			# Make throne room walls also special (darker/more imposing)
			for x in range(throne_room.x1, throne_room.x2):
				for y in range(throne_room.y1, throne_room.y2):
					if 0 <= x < self.w and 0 <= y < self.h and self.tiles[x][y] == TILE_WALL:
						self.materials[x][y] = MAT_IRON  # Dark iron walls for throne room

	def is_throne_room(self, room_index: int) -> bool:
		"""Check if the given room index is the throne room."""
		return room_index == self.throne_room_index and self.throne_room_index >= 0
	
	def get_throne_room(self) -> Rect | None:
		"""Get the throne room rectangle, or None if no throne room exists."""
		if self.throne_room_index >= 0 and self.throne_room_index < len(self.rooms):
			return self.rooms[self.throne_room_index]
		return None

	def _generate_linear(self, max_rooms: int, room_min: int, room_max: int, entropy: float = 0.0):
		"""Generate rooms in a linear progression with some natural variation."""
		if max_rooms <= 0:
			return
			
		# Decide if we go horizontal or vertical for the main progression
		horizontal = self.w > self.h
		
		if horizontal:
			# Horizontal progression: left to right with Y variation
			segment_width = max(room_max + 4, self.w // max_rooms)
			base_y = self.h // 2  # Base Y position
			y_variation = min(self.h // 3, room_max * 2)  # Allow more Y variation
			
			for i in range(max_rooms):
				# Calculate position for this room in the progression
				center_x = segment_width * (i + 1)
				if center_x >= self.w - room_max:
					break
				
				# Add natural Y variation that creates a winding path
				y_offset = int(y_variation * (0.5 - 0.5 * random.random()))
				target_y = base_y + y_offset
				
				# Try to place room with variation
				placed = False
				attempts = 0
				while attempts < 20 and not placed:
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					x = max(1, min(self.w - w - 1, center_x - w // 2))
					y = max(1, min(self.h - h - 1, target_y - h // 2))
					
					new_room = Rect(x, y, w, h)
					
					# Check for overlap with existing rooms (with buffer)
					overlaps = False
					for existing in self.rooms:
						# Add 2-tile buffer around existing rooms
						buffered = Rect(existing.x1 - 2, existing.y1 - 2, 
									  (existing.x2 - existing.x1) + 4, (existing.y2 - existing.y1) + 4)
						if new_room.intersect(buffered):
							overlaps = True
							break
					
					if not overlaps:
						self.carve_room(new_room)
						self.rooms.append(new_room)
						placed = True
					else:
						# If overlap, try different Y position
						target_y += random.randint(-3, 3)
						target_y = max(room_max, min(self.h - room_max, target_y))
					
					attempts += 1
		else:
			# Vertical progression: top to bottom with X variation
			segment_height = max(room_max + 4, self.h // max_rooms)
			base_x = self.w // 2  # Base X position
			x_variation = min(self.w // 3, room_max * 2)  # Allow more X variation
			
			for i in range(max_rooms):
				# Calculate position for this room in the progression
				center_y = segment_height * (i + 1)
				if center_y >= self.h - room_max:
					break
				
				# Add natural X variation that creates a winding path
				x_offset = int(x_variation * (0.5 - 0.5 * random.random()))
				target_x = base_x + x_offset
				
				# Try to place room with variation
				placed = False
				attempts = 0
				while attempts < 20 and not placed:
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					x = max(1, min(self.w - w - 1, target_x - w // 2))
					y = max(1, min(self.h - h - 1, center_y - h // 2))
					
					new_room = Rect(x, y, w, h)
					
					# Check for overlap with existing rooms (with buffer)
					overlaps = False
					for existing in self.rooms:
						# Add 2-tile buffer around existing rooms
						buffered = Rect(existing.x1 - 2, existing.y1 - 2, 
									  (existing.x2 - existing.x1) + 4, (existing.y2 - existing.y1) + 4)
						if new_room.intersect(buffered):
							overlaps = True
							break
					
					if not overlaps:
						self.carve_room(new_room)
						self.rooms.append(new_room)
						placed = True
					else:
						# If overlap, try different X position
						target_x += random.randint(-3, 3)
						target_x = max(room_max, min(self.w - room_max, target_x))
					
					attempts += 1

		# Connect rooms with minimal corridors, preferring straight lines when close
		for i in range(1, len(self.rooms)):
			prev_center = self.rooms[i-1].center()
			curr_center = self.rooms[i].center()
			
			# Create smart connections based on room alignment
			x_diff = abs(prev_center[0] - curr_center[0])
			y_diff = abs(prev_center[1] - curr_center[1])
			
			if x_diff <= 3 and y_diff > x_diff * 2:
				# Rooms are nearly vertically aligned - use vertical corridor
				avg_x = (prev_center[0] + curr_center[0]) // 2
				self.carve_v_tunnel(prev_center[1], curr_center[1], avg_x)
			elif y_diff <= 3 and x_diff > y_diff * 2:
				# Rooms are nearly horizontally aligned - use horizontal corridor
				avg_y = (prev_center[1] + curr_center[1]) // 2
				self.carve_h_tunnel(prev_center[0], curr_center[0], avg_y)
			else:
				# Rooms need L-shaped connection - choose optimal direction first
				if x_diff > y_diff:
					# More horizontal distance - go horizontal first
					self.carve_h_tunnel(prev_center[0], curr_center[0], prev_center[1])
					self.carve_v_tunnel(prev_center[1], curr_center[1], curr_center[0])
				else:
					# More vertical distance - go vertical first
					self.carve_v_tunnel(prev_center[1], curr_center[1], prev_center[0])
					self.carve_h_tunnel(prev_center[0], curr_center[0], curr_center[1])

		# Add side rooms based on entropy
		if entropy > 0.0 and len(self.rooms) > 0:
			side_room_count = int(entropy * len(self.rooms) * 1.5)  # up to 1.5x main rooms as side rooms
			for _ in range(side_room_count):
				# Pick a random main room to branch off from
				main_room = random.choice(self.rooms)
				main_center = main_room.center()
				
				# Try to place a side room near this main room
				for attempt in range(10):  # multiple attempts per side room
					# Choose a direction: perpendicular to main path
					if horizontal:
						# Main path is horizontal, so side rooms go up/down
						side_direction = random.choice([-1, 1])  # up or down
						side_distance = random.randint(room_max + 3, room_max * 2 + 5)
						side_x = main_center[0] + random.randint(-room_max, room_max)  # some X variation
						side_y = main_center[1] + side_direction * side_distance
					else:
						# Main path is vertical, so side rooms go left/right
						side_direction = random.choice([-1, 1])  # left or right
						side_distance = random.randint(room_max + 3, room_max * 2 + 5)
						side_x = main_center[0] + side_direction * side_distance
						side_y = main_center[1] + random.randint(-room_max, room_max)  # some Y variation
					
					# Try to place the side room
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					x = max(1, min(self.w - w - 1, side_x - w // 2))
					y = max(1, min(self.h - h - 1, side_y - h // 2))
					
					side_room = Rect(x, y, w, h)
					
					# Check for overlap with existing rooms
					overlaps = False
					for existing in self.rooms:
						buffered = Rect(existing.x1 - 2, existing.y1 - 2, 
									  (existing.x2 - existing.x1) + 4, (existing.y2 - existing.y1) + 4)
						if side_room.intersect(buffered):
							overlaps = True
							break
					
					if not overlaps:
						self.carve_room(side_room)
						self.rooms.append(side_room)
						
						# Connect side room to main room with corridor
						side_center = side_room.center()
						if horizontal:
							# Connect vertically then horizontally
							self.carve_v_tunnel(main_center[1], side_center[1], main_center[0])
							self.carve_h_tunnel(main_center[0], side_center[0], side_center[1])
						else:
							# Connect horizontally then vertically
							self.carve_h_tunnel(main_center[0], side_center[0], main_center[1])
							self.carve_v_tunnel(main_center[1], side_center[1], side_center[0])
						
						break  # Successfully placed side room

	def _generate_biased_linear(self, max_rooms: int, room_min: int, room_max: int, linearity: float, entropy: float = 0.0):
		"""Generate rooms with bias toward linear progression but some randomness.
		
		When entropy is 0, creates a single linear chain regardless of linearity.
		When entropy > 0, adds side rooms based on entropy level.
		"""
		if max_rooms <= 0:
			return
			
		horizontal = self.w > self.h
		bias_strength = (linearity - 0.4) / 0.4  # 0.0 to 1.0
		
		# When entropy is 0, force linear chain behavior
		if entropy <= 0.0:
			# Create perfectly linear chain, but with some path variance based on linearity
			if horizontal:
				segment_width = max(room_max + 2, self.w // max_rooms)
				base_y = self.h // 2
				y_variation = int((1.0 - linearity) * min(self.h // 4, room_max))
				
				for i in range(max_rooms):
					center_x = segment_width * (i + 1)
					if center_x >= self.w - room_max:
						break
					
					# Add path variation based on linearity
					y_offset = random.randint(-y_variation, y_variation)
					target_y = base_y + y_offset
					
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					x = max(1, min(self.w - w - 1, center_x - w // 2))
					y = max(1, min(self.h - h - 1, target_y - h // 2))
					
					new_room = Rect(x, y, w, h)
					
					# Check for overlap
					overlaps = any(new_room.intersect(other) for other in self.rooms)
					if not overlaps:
						self.carve_room(new_room)
						
						# Connect to previous room with straight corridors
						if self.rooms:
							prev_center = self.rooms[-1].center()
							curr_center = new_room.center()
							self.carve_h_tunnel(prev_center[0], curr_center[0], prev_center[1])
							self.carve_v_tunnel(prev_center[1], curr_center[1], curr_center[0])
						
						self.rooms.append(new_room)
			else:
				segment_height = max(room_max + 2, self.h // max_rooms)
				base_x = self.w // 2
				x_variation = int((1.0 - linearity) * min(self.w // 4, room_max))
				
				for i in range(max_rooms):
					center_y = segment_height * (i + 1)
					if center_y >= self.h - room_max:
						break
					
					# Add path variation based on linearity
					x_offset = random.randint(-x_variation, x_variation)
					target_x = base_x + x_offset
					
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					x = max(1, min(self.w - w - 1, target_x - w // 2))
					y = max(1, min(self.h - h - 1, center_y - h // 2))
					
					new_room = Rect(x, y, w, h)
					
					# Check for overlap
					overlaps = any(new_room.intersect(other) for other in self.rooms)
					if not overlaps:
						self.carve_room(new_room)
						
						# Connect to previous room with straight corridors
						if self.rooms:
							prev_center = self.rooms[-1].center()
							curr_center = new_room.center()
							self.carve_v_tunnel(prev_center[1], curr_center[1], prev_center[0])
							self.carve_h_tunnel(prev_center[0], curr_center[0], curr_center[1])
						
						self.rooms.append(new_room)
			return
		else:
			# Original biased placement for entropy > 0
			for i in range(max_rooms):
				attempts = 0
				placed = False
				
				while attempts < 50 and not placed:
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					
					if not self.rooms:
						# First room - place somewhat toward start
						if horizontal:
							x = random.randint(1, self.w // 3)
							y = random.randint(1, max(1, self.h - h - 1))
						else:
							x = random.randint(1, max(1, self.w - w - 1))
							y = random.randint(1, self.h // 3)
					else:
						# Subsequent rooms - bias toward progression direction
						progress = len(self.rooms) / max_rooms
						
						if horizontal:
							# Bias toward right side based on progress
							ideal_x = int(progress * (self.w - w - 2)) + 1
							x_variance = int((1 - bias_strength) * self.w // 3)
							x = random.randint(max(1, ideal_x - x_variance), 
											 min(self.w - w - 1, ideal_x + x_variance))
							y = random.randint(1, max(1, self.h - h - 1))
						else:
							# Bias toward bottom based on progress
							ideal_y = int(progress * (self.h - h - 2)) + 1
							y_variance = int((1 - bias_strength) * self.h // 3)
							y = random.randint(max(1, ideal_y - y_variance),
											 min(self.h - h - 1, ideal_y + y_variance))
							x = random.randint(1, max(1, self.w - w - 1))
					
					new_room = Rect(x, y, w, h)
					
					if not any(new_room.intersect(other) for other in self.rooms):
						self.carve_room(new_room)
						self.rooms.append(new_room)
						placed = True
					
					attempts += 1
		
		# Connect rooms (each to previous)
		for i in range(1, len(self.rooms)):
			prev_center = self.rooms[i-1].center()
			curr_center = self.rooms[i].center()
			
			if random.random() < 0.5 + bias_strength * 0.3:
				if horizontal:
					self.carve_h_tunnel(prev_center[0], curr_center[0], prev_center[1])
					self.carve_v_tunnel(prev_center[1], curr_center[1], curr_center[0])
				else:
					self.carve_v_tunnel(prev_center[1], curr_center[1], prev_center[0])
					self.carve_h_tunnel(prev_center[0], curr_center[0], curr_center[1])
			else:
				if horizontal:
					self.carve_v_tunnel(prev_center[1], curr_center[1], prev_center[0])
					self.carve_h_tunnel(prev_center[0], curr_center[0], curr_center[1])
				else:
					self.carve_h_tunnel(prev_center[0], curr_center[0], prev_center[1])
					self.carve_v_tunnel(prev_center[1], curr_center[1], curr_center[0])

		# Add side rooms based on entropy (similar to linear method but less structured)
		if entropy > 0.0 and len(self.rooms) > 1:
			side_room_count = int(entropy * len(self.rooms) * 1.2)  # slightly fewer than pure linear
			for _ in range(side_room_count):
				# Pick a random main room to branch off from
				main_room = random.choice(self.rooms)
				main_center = main_room.center()
				
				# Try to place a side room in a random direction from this main room
				for attempt in range(8):  # fewer attempts since this is more chaotic
					# Random direction and distance
					angle = random.uniform(0, 2 * 3.14159)  # random angle
					distance = random.randint(room_max + 2, room_max * 2)
					side_x = int(main_center[0] + distance * random.uniform(-1, 1))
					side_y = int(main_center[1] + distance * random.uniform(-1, 1))
					
					# Try to place the side room
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					x = max(1, min(self.w - w - 1, side_x - w // 2))
					y = max(1, min(self.h - h - 1, side_y - h // 2))
					
					side_room = Rect(x, y, w, h)
					
					# Check for overlap
					overlaps = any(side_room.intersect(existing) for existing in self.rooms)
					
					if not overlaps:
						self.carve_room(side_room)
						self.rooms.append(side_room)
						
						# Connect side room to main room
						side_center = side_room.center()
						if random.random() < 0.5:
							self.carve_h_tunnel(main_center[0], side_center[0], main_center[1])
							self.carve_v_tunnel(main_center[1], side_center[1], side_center[0])
						else:
							self.carve_v_tunnel(main_center[1], side_center[1], main_center[0])
							self.carve_h_tunnel(main_center[0], side_center[0], side_center[1])
						
						break  # Successfully placed side room

	def _generate_random(self, max_rooms: int, room_min: int, room_max: int, linearity: float, entropy: float = 0.0):
		"""Generate rooms with mostly random placement.
		
		When entropy is 0, creates a single linear chain.
		When entropy > 0, places additional random rooms.
		"""
		# When entropy is 0, use linear placement even in "random" mode
		if entropy <= 0.0:
			self._generate_biased_linear(max_rooms, room_min, room_max, linearity, entropy)
			return
		
		# Original random placement for entropy > 0
		h_then_v_prob = 0.5 + (linearity * 0.25)  # Reduced impact for low linearity
		
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
				prev_center = self.rooms[-1].center()
				curr_center = new_room.center()
				
				if random.random() < h_then_v_prob:
					self.carve_h_tunnel(prev_center[0], curr_center[0], prev_center[1])
					self.carve_v_tunnel(prev_center[1], curr_center[1], curr_center[0])
				else:
					self.carve_v_tunnel(prev_center[1], curr_center[1], prev_center[0])
					self.carve_h_tunnel(prev_center[0], curr_center[0], curr_center[1])

			self.rooms.append(new_room)

		# For random generation, entropy just adds extra randomly placed rooms
		if entropy > 0.0 and len(self.rooms) > 0:
			extra_room_count = int(entropy * max_rooms * 0.8)  # up to 80% more rooms
			for _ in range(extra_room_count):
				for attempt in range(30):  # many attempts for random placement
					w = random.randint(room_min, room_max)
					h = random.randint(room_min, room_max)
					x = random.randint(1, max(1, self.w - w - 2))
					y = random.randint(1, max(1, self.h - h - 2))
					new_room = Rect(x, y, w, h)

					if not any(new_room.intersect(other) for other in self.rooms):
						self.carve_room(new_room)
						
						# Connect to nearest existing room
						new_center = new_room.center()
						nearest_room = min(self.rooms, key=lambda r: 
							abs(r.center()[0] - new_center[0]) + abs(r.center()[1] - new_center[1]))
						nearest_center = nearest_room.center()
						
						if random.random() < h_then_v_prob:
							self.carve_h_tunnel(nearest_center[0], new_center[0], nearest_center[1])
							self.carve_v_tunnel(nearest_center[1], new_center[1], new_center[0])
						else:
							self.carve_v_tunnel(nearest_center[1], new_center[1], nearest_center[0])
							self.carve_h_tunnel(nearest_center[0], new_center[0], new_center[1])
						
						self.rooms.append(new_room)
						break

	def is_wall(self, x: int, y: int) -> bool:
		if 0 <= x < self.w and 0 <= y < self.h:
			return self.tiles[x][y] == TILE_WALL
		return True

	def material_at(self, x: int, y: int) -> int:
		if 0 <= x < self.w and 0 <= y < self.h:
			return self.materials[x][y]
		return MAT_BRICK

	def stamp_prefab(self, px: int, py: int, cells: List[str], legend: dict):
		"""Stamp a prefab at top-left (px,py). Legend maps chars to {tile, material}.
		tile: 'wall' | 'floor' | 'void'
		material: 'brick' | 'cobble' | 'dirt' (optional)
		"""
		tile_map = {
			'wall': TILE_WALL,
			'floor': TILE_FLOOR,
		}
		mat_map = {
			'brick': MAT_BRICK,
			'cobble': MAT_COBBLE,
			'stone': MAT_COBBLE,
			'dirt': MAT_DIRT,
			'moss': MAT_MOSS,
			'sand': MAT_SAND,
			'iron': MAT_IRON,
			'grass': MAT_GRASS,
			'water': MAT_WATER,
			'lava': MAT_LAVA,
			'marble': MAT_MARBLE,
			'wood': MAT_WOOD,
		}
		h = len(cells)
		w = len(cells[0]) if h else 0
		for y in range(h):
			for x in range(w):
				ch = cells[y][x]
				entry = legend.get(ch)
				if not entry:
					continue
				if entry.get('tile') == 'void':
					continue
				dx, dy = px + x, py + y
				if not (0 <= dx < self.w and 0 <= dy < self.h):
					continue
				tile_name = entry.get('tile') if isinstance(entry, dict) else 'floor'
				if not isinstance(tile_name, str):
					tile_name = 'floor'
				mat_name = entry.get('material', 'cobble') if isinstance(entry, dict) else 'cobble'
				if not isinstance(mat_name, str):
					mat_name = 'cobble'
				t = tile_map.get(tile_name, TILE_FLOOR)
				m = mat_map.get(mat_name, MAT_COBBLE)
				self.tiles[dx][dy] = t
				self.materials[dx][dy] = m


def generate_dungeon(
	width: int = 60,
	height: int = 40,
	complexity: float = 0.5,
	length: int = 25,
	room_min: int = 4,
	room_max: int = 9,
	seed: int | None = None,
	linearity: float = 0.0,
	entropy: float = 0.0,
) -> Dungeon:
	"""Generate a complete dungeon with rooms, corridors, and doors.

	Creates a procedurally generated dungeon using various algorithms based on
	the linearity parameter. Can create anything from chaotic mazes to linear
	chains of rooms.

	Args:
		width (int): Target dungeon width in tiles (default: 60)
		height (int): Target dungeon height in tiles (default: 40)
		complexity (float): Connection complexity 0.0-1.0, adds extra corridors
		                   between rooms for maze-like layouts (default: 0.5)
		length (int): Approximate number of rooms to attempt placing (default: 25)
		room_min (int): Minimum room size in tiles (default: 4)
		room_max (int): Maximum room size in tiles (default: 9)
		seed (int | None): Optional seed for deterministic generation
		linearity (float): Layout style 0.0-1.0 where:
					  - 0.0 = chaotic/random room placement
					  - 1.0 = perfectly linear chain of rooms
					  (default: 0.0)
		entropy (float): Side room generation 0.0-1.0 where:
					- 0.0 = no side rooms off main path
					- 1.0 = many side rooms and branches
					(default: 0.0)	Returns:
		Dungeon: Fully generated dungeon instance with tiles, materials, rooms,
		         and doors populated
	"""
	rnd_state = None
	if seed is not None:
		rnd_state = random.getstate()
		random.seed(seed)
	try:
		d = Dungeon(width, height)
		max_rooms = max(1, int(length))
		d.generate(max_rooms=max_rooms, room_min=room_min, room_max=room_max, linearity=linearity, entropy=entropy)

		# Extra connections based on complexity: link random room pairs
		# But skip ALL extra connections if linearity is high (we want a pure chain)
		if linearity <= 0.5:  # Only add extra connections at very low linearity
			extra_links = max(0, int(complexity * max(0, len(d.rooms) - 1)))
			for _ in range(extra_links):
				if len(d.rooms) < 2:
					break
				a = random.choice(d.rooms)
				b = random.choice(d.rooms)
				if a is b:
					continue
				(ax, ay) = a.center()
				(bx, by) = b.center()
				if random.random() < 0.5:
					d.carve_h_tunnel(ax, bx, ay)
					d.carve_v_tunnel(ay, by, bx)
				else:
					d.carve_v_tunnel(ay, by, ax)
					d.carve_h_tunnel(ax, bx, by)

		return d
	finally:
		if rnd_state is not None:
			# Restore RNG state
			random.setstate(rnd_state)
