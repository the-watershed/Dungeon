"""
Dungeon Cells FPS Demo (single-file)

Controls:
- W/S: move forward/back
- A/D: strafe left/right
- Q/E: turn left/right (yaw)
- Esc: quit

Specs delivered:
- First-person view, rectilinear projection, FOV 100°
- Window size 1920x1080
- Per-pixel lighting (ambient + diffuse + specular) via GLSL shaders
- "Cells" are 1x1x1 cubes on a grid with faces labeled: floor, ceiling, wall, door, pass
- By default cells have a floor, ceiling, and four white walls that are impassable
- Connecting adjacent cells turns their shared faces to PASS (or DOOR), opening passages and removing the white wall between them (forming seamless rooms)

Dependencies (install in PowerShell if missing):
  python -m pip install pygame PyOpenGL PyOpenGL_accelerate

This is a minimal single-file demo focusing on the requested mechanics. It builds a sample
room and hallway using the cell system and lets you walk around with collision.
"""

import math
import random
import sys
from ctypes import c_float, c_void_p
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, Optional, List

import pygame
from pygame.locals import DOUBLEBUF, OPENGL

from OpenGL import GL
from OpenGL.GL import shaders


# ---------------------------- Constants ----------------------------
CELL_W = 6.0  # feet along X
CELL_D = 6.0  # feet along Z
CELL_H = 8.0  # feet along Y (height)
EYE_HEIGHT = 6.0  # player eye height from floor


# ---------------------------- Math helpers (no numpy) ----------------------------
def deg_to_rad(d: float) -> float:
	return d * math.pi / 180.0


def perspective(fov_deg: float, aspect: float, znear: float, zfar: float) -> List[float]:
	f = 1.0 / math.tan(deg_to_rad(fov_deg) / 2.0)
	nf = 1.0 / (znear - zfar)  # equals 1/(zn - zf)
	# Column-major 4x4
	return [
		f / aspect, 0.0, 0.0, 0.0,         # column 0
		0.0, f, 0.0, 0.0,                   # column 1
		0.0, 0.0, (zfar + znear) * nf, -1.0,  # column 2 (m[2,2], m[3,2])
		0.0, 0.0, (2.0 * zfar * znear) * nf, 0.0,  # column 3 (m[2,3], m[3,3])
	]


def mat4_mul(a: List[float], b: List[float]) -> List[float]:
	# Column-major 4x4 multiply: c = a * b
	# c[i,j] = sum_k a[i,k] * b[k,j]
	c = [0.0] * 16
	for j in range(4):
		for i in range(4):
			c[i + j * 4] = (
				a[i + 0 * 4] * b[0 + j * 4]
				+ a[i + 1 * 4] * b[1 + j * 4]
				+ a[i + 2 * 4] * b[2 + j * 4]
				+ a[i + 3 * 4] * b[3 + j * 4]
			)
	return c


def translate(tx: float, ty: float, tz: float) -> List[float]:
	return [
		1.0, 0.0, 0.0, 0.0,
		0.0, 1.0, 0.0, 0.0,
		0.0, 0.0, 1.0, 0.0,
		tx, ty, tz, 1.0,
	]


def rotate_y(rad: float) -> List[float]:
	c = math.cos(rad)
	s = math.sin(rad)
	# Column-major layout of standard Y-rotation
	return [
		c, 0.0, -s, 0.0,   # column 0
		0.0, 1.0, 0.0, 0.0,   # column 1
		s, 0.0, c, 0.0,  # column 2
		0.0, 0.0, 0.0, 1.0,   # column 3
	]


def invert_rigid(m: List[float]) -> List[float]:
	# Invert rotation-translation matrix (upper-left 3x3 is rotation, last row is translation)
	# Assumes no scaling/shear. Matrix is column-major.
	# Extract rotation R and translation t, then inverse is [R^T | -R^T t]
	r00, r01, r02 = m[0], m[1], m[2]
	r10, r11, r12 = m[4], m[5], m[6]
	r20, r21, r22 = m[8], m[9], m[10]
	tx, ty, tz = m[12], m[13], m[14]
	# Transpose rotation
	rt = [
		r00, r10, r20, 0.0,
		r01, r11, r21, 0.0,
		r02, r12, r22, 0.0,
		0.0, 0.0, 0.0, 1.0,
	]
	inv_t = [
		1.0, 0.0, 0.0, 0.0,
		0.0, 1.0, 0.0, 0.0,
		0.0, 0.0, 1.0, 0.0,
		-(r00 * tx + r01 * ty + r02 * tz),
		-(r10 * tx + r11 * ty + r12 * tz),
		-(r20 * tx + r21 * ty + r22 * tz),
		1.0,
	]
	return mat4_mul(inv_t, rt)


# ---------------------------- Cells and Dungeon ----------------------------
class FaceType(Enum):
	FLOOR = 0
	CEILING = 1
	WALL = 2
	DOOR = 3
	PASS = 4  # fully open/passable


Dir = Tuple[int, int, int]


DIRS: Dict[str, Dir] = {
	"WEST": (-1, 0, 0),   # -X
	"EAST": (1, 0, 0),    # +X
	"NORTH": (0, 0, -1),  # -Z
	"SOUTH": (0, 0, 1),   # +Z
	"DOWN": (0, -1, 0),   # -Y (floor)
	"UP": (0, 1, 0),      # +Y (ceiling)
}


OPPOSITE: Dict[str, str] = {
	"WEST": "EAST",
	"EAST": "WEST",
	"NORTH": "SOUTH",
	"SOUTH": "NORTH",
	"DOWN": "UP",
	"UP": "DOWN",
}


@dataclass
class Cell:
	# Each face type; defaults: floor/ceiling present, side walls impassable white
	west: FaceType = FaceType.WALL
	east: FaceType = FaceType.WALL
	north: FaceType = FaceType.WALL
	south: FaceType = FaceType.WALL
	down: FaceType = FaceType.FLOOR
	up: FaceType = FaceType.CEILING

	def set_face(self, dir_name: str, f: FaceType) -> None:
		setattr(self, dir_name.lower(), f)

	def get_face(self, dir_name: str) -> FaceType:
		return getattr(self, dir_name.lower())


class Dungeon:
	def __init__(self) -> None:
		self.cells: Dict[Tuple[int, int, int], Cell] = {}

	def add_cell(self, x: int, y: int, z: int) -> None:
		self.cells[(x, y, z)] = self.cells.get((x, y, z), Cell())

	def has_cell(self, x: int, y: int, z: int) -> bool:
		return (x, y, z) in self.cells

	def get_cell(self, x: int, y: int, z: int) -> Optional[Cell]:
		return self.cells.get((x, y, z))

	def connect(self, a: Tuple[int, int, int], b: Tuple[int, int, int], as_door: bool = False) -> None:
		ax, ay, az = a
		bx, by, bz = b
		dx, dy, dz = bx - ax, by - ay, bz - az
		dir_name: Optional[str] = None
		for name, d in DIRS.items():
			if d == (dx, dy, dz):
				dir_name = name
				break
		if dir_name is None:
			raise ValueError(f"Cells are not adjacent: {a} -> {b}")
		opp = OPPOSITE[dir_name]
		self.add_cell(*a)
		self.add_cell(*b)
		ft = FaceType.DOOR if as_door else FaceType.PASS
		self.cells[a].set_face(dir_name, ft)
		self.cells[b].set_face(opp, ft)


# ---------------------------- Mesh generation ----------------------------
class Mesh:
	def __init__(self, vertices: List[float]):
		self.vertices = vertices
		# 3 pos + 3 normal + 3 color + 2 uv per vertex
		self.vertex_count = len(vertices) // 11
		self.vbo = None
		self.vao = None


def add_quad(vertices: List[float], quad: List[Tuple[float, float, float]], normal: Tuple[float, float, float], color: Tuple[float, float, float], uvs: Optional[List[Tuple[float, float]]] = None) -> None:
	# quad is 4 positions in CCW order as seen from the VISIBLE side
	# Triangulate (0,1,2) and (0,2,3)
	x, y, z = normal
	r, g, b = color
	order = [0, 1, 2, 0, 2, 3]
	for idx in order:
		px, py, pz = quad[idx]
		if uvs is None:
			u, v = 0.0, 0.0
		else:
			u, v = uvs[idx]
		vertices.extend([px, py, pz, x, y, z, r, g, b, u, v])


def build_dungeon_meshes(dun: Dungeon) -> Tuple[Mesh, Mesh, Mesh]:
	# Colors
	COL_WALL = (1.0, 1.0, 1.0)     # white walls
	# For textured floor, keep base white so texture shows as-is
	COL_FLOOR = (1.0, 1.0, 1.0)
	COL_CEIL = (1.0, 1.0, 1.0)     # white ceiling to show texture as-is

	verts_floors: List[float] = []
	verts_ceilings: List[float] = []
	verts_walls: List[float] = []
	for (x, y, z), cell in dun.cells.items():
		# Convert cell index to world-space extents in feet
		x0 = x * CELL_W
		x1 = x0 + CELL_W
		z0 = z * CELL_D
		z1 = z0 + CELL_D
		y0 = y * CELL_H
		y1 = y0 + CELL_H
		# For each face, only render if it's a boundary (i.e., not PASS/DOOR to another existing cell)
		# Faces are built so that their FRONT faces the interior of the cell (so we can cull backfaces)

		# Floor (DOWN): plane y = y, normal up (0,1,0)
		# Use UVs covering the tile once (0..1) per face
		if cell.down != FaceType.PASS and cell.down != FaceType.DOOR:
			quad = [
				(x0, y0, z0),
				(x1, y0, z0),
				(x1, y0, z1),
				(x0, y0, z1),
			]
			uvs = [(0.0, 0.0),(1.0, 0.0),(1.0, 1.0),(0.0, 1.0)]
			add_quad(verts_floors, quad, (0.0, 1.0, 0.0), COL_FLOOR, uvs)

		# Ceiling (UP): plane y = y+1, normal down (0,-1,0), textured once per tile
		if cell.up != FaceType.PASS and cell.up != FaceType.DOOR:
			quad = [
				(x0, y1, z1),
				(x1, y1, z1),
				(x1, y1, z0),
				(x0, y1, z0),
			]
			uvs = [(0.0, 1.0),(1.0, 1.0),(1.0, 0.0),(0.0, 0.0)]
			add_quad(verts_ceilings, quad, (0.0, -1.0, 0.0), COL_CEIL, uvs)

		# Walls: draw for any non-pass/non-door face so closed rooms show walls even between adjacent cells.
		# WEST (-X): plane x = x, normal +X (faces interior), CCW when viewed from +X side
		if (cell.west != FaceType.PASS and cell.west != FaceType.DOOR):
			quad = [
				(x0, y0, z1),
				(x0, y0, z0),
				(x0, y1, z0),
				(x0, y1, z1),
			]
			# UVs span entire face
			uvs = [(0.0, 0.0),(1.0, 0.0),(1.0, 1.0),(0.0, 1.0)]
			add_quad(verts_walls, quad, (1.0, 0.0, 0.0), COL_WALL, uvs)
		# EAST (+X): plane x = x+1, normal -X
		if (cell.east != FaceType.PASS and cell.east != FaceType.DOOR):
			quad = [
				(x1, y0, z0),
				(x1, y0, z1),
				(x1, y1, z1),
				(x1, y1, z0),
			]
			uvs = [(0.0, 0.0),(1.0, 0.0),(1.0, 1.0),(0.0, 1.0)]
			add_quad(verts_walls, quad, (-1.0, 0.0, 0.0), COL_WALL, uvs)
		# NORTH (-Z): plane z = z, normal +Z
		if (cell.north != FaceType.PASS and cell.north != FaceType.DOOR):
			quad = [
				(x1, y0, z0),
				(x0, y0, z0),
				(x0, y1, z0),
				(x1, y1, z0),
			]
			uvs = [(1.0, 0.0),(0.0, 0.0),(0.0, 1.0),(1.0, 1.0)]
			add_quad(verts_walls, quad, (0.0, 0.0, 1.0), COL_WALL, uvs)
		# SOUTH (+Z): plane z = z+1, normal -Z
		if (cell.south != FaceType.PASS and cell.south != FaceType.DOOR):
			quad = [
				(x0, y0, z1),
				(x1, y0, z1),
				(x1, y1, z1),
				(x0, y1, z1),
			]
			uvs = [(0.0, 0.0),(1.0, 0.0),(1.0, 1.0),(0.0, 1.0)]
			add_quad(verts_walls, quad, (0.0, 0.0, -1.0), COL_WALL, uvs)

		# Shared faces between existing neighboring cells are opened by connect() (PASS/DOOR), hence skipped.

	return Mesh(verts_floors), Mesh(verts_ceilings), Mesh(verts_walls)


# ---------------------------- OpenGL setup ----------------------------
VERT_SRC = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec3 aColor;
layout(location = 3) in vec2 aTex;

out vec3 vNormal;
out vec3 vFragPos;
out vec3 vColor;
out vec2 vTex;

uniform mat4 uView;
uniform mat4 uProj;

void main() {
	vFragPos = aPos;
	vNormal = aNormal; // world space
	vColor = aColor;
    vTex = aTex;
	gl_Position = uProj * uView * vec4(aPos, 1.0);
}
"""

FRAG_SRC = """
#version 330 core
in vec3 vNormal;
in vec3 vFragPos;
in vec3 vColor;
in vec2 vTex;
out vec4 FragColor;

uniform vec3 uLightPos;
uniform vec3 uViewPos;
uniform float uLightRadius; // cells (units)
uniform vec3 uLightColor;
uniform bool uUseTexture;
uniform sampler2D uTex;
uniform float uLightIntensity;

void main() {
	// Basic Blinn-Phong
	vec3 N = normalize(vNormal);
	vec3 Lvec = uLightPos - vFragPos;
	// Use horizontal distance for radius falloff (3 cubes out on the grid)
	float r = length(Lvec.xz);
	vec3 L = r > 0.0 ? Lvec / r : vec3(0.0, 1.0, 0.0);
	float diff = max(dot(N, L), 0.0);

	vec3 V = normalize(uViewPos - vFragPos);
	vec3 H = normalize(L + V);
	float spec = pow(max(dot(N, H), 0.0), 32.0);

	// Smooth falloff to zero at radius
	float t = clamp(1.0 - (r / uLightRadius), 0.0, 1.0);
	float attenuation = t * t; // quadratic falloff for a natural look

	vec3 base = vColor;
	if (uUseTexture) {
		base *= texture(uTex, vTex).rgb;
	}

	// Zero ambient lighting as requested
	vec3 ambient = vec3(0.0);
	vec3 diffuse = diff * base * uLightColor;
	vec3 specular = 0.10 * spec * uLightColor;

	vec3 color = ambient + attenuation * uLightIntensity * (diffuse + specular);
	FragColor = vec4(color, 1.0);
}
"""


def create_shader_program():
	vs = shaders.compileShader(VERT_SRC, GL.GL_VERTEX_SHADER)
	fs = shaders.compileShader(FRAG_SRC, GL.GL_FRAGMENT_SHADER)
	program = shaders.compileProgram(vs, fs)
	return program


def create_gl_objects(mesh: Mesh):
	vao = GL.glGenVertexArrays(1)
	vbo = GL.glGenBuffers(1)
	GL.glBindVertexArray(vao)
	GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)

	array_data = (c_float * len(mesh.vertices))(*mesh.vertices)
	GL.glBufferData(GL.GL_ARRAY_BUFFER, len(mesh.vertices) * 4, array_data, GL.GL_STATIC_DRAW)

	stride = 11 * 4  # bytes
	offset_pos = c_void_p(0)
	offset_nrm = c_void_p(3 * 4)
	offset_col = c_void_p(6 * 4)
	offset_uv = c_void_p(9 * 4)

	GL.glEnableVertexAttribArray(0)
	GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, offset_pos)
	GL.glEnableVertexAttribArray(1)
	GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, offset_nrm)
	GL.glEnableVertexAttribArray(2)
	GL.glVertexAttribPointer(2, 3, GL.GL_FLOAT, GL.GL_FALSE, stride, offset_col)
	GL.glEnableVertexAttribArray(3)
	GL.glVertexAttribPointer(3, 2, GL.GL_FLOAT, GL.GL_FALSE, stride, offset_uv)

	GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
	GL.glBindVertexArray(0)

	mesh.vbo = vbo
	mesh.vao = vao


def load_texture(path: str) -> int:
	surf = pygame.image.load(path).convert_alpha()
	w, h = surf.get_size()
	raw = pygame.image.tostring(surf, "RGBA", True)
	tex = GL.glGenTextures(1)
	GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
	GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, w, h, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, raw)
	GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
	GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
	return tex


# ---------------------------- Player and Input ----------------------------
class Player:
	def __init__(self, x: float, y: float, z: float) -> None:
		self.x = x
		self.y = y
		self.z = z
		self.yaw = 0.0  # radians, 0 looks along -Z
		self.radius = 0.2 * CELL_W  # collision radius in feet
		# Grid movement state
		self.grid_x = 0
		self.grid_z = 0
		self.facing = 0  # 0=North(-Z),1=East(+X),2=South(+Z),3=West(-X)

	def forward_vec(self) -> Tuple[float, float, float]:
		# Derived from facing for consistency
		if self.facing == 0:
			return (0.0, 0.0, -1.0)
		if self.facing == 1:
			return (1.0, 0.0, 0.0)
		if self.facing == 2:
			return (0.0, 0.0, 1.0)
		return (-1.0, 0.0, 0.0)

	def right_vec(self) -> Tuple[float, float, float]:
		fx, _, fz = self.forward_vec()
		return (fz, 0.0, -fx)

	def snap_to_cell(self):
		self.x = (self.grid_x + 0.5) * CELL_W
		self.z = (self.grid_z + 0.5) * CELL_D
		self.y = EYE_HEIGHT
		# Align yaw to 90° increments
		self.yaw = -self.facing * (math.pi / 2.0)


def collide_player_with_dungeon(p: Player, dun: Dungeon) -> None:
	# Simple wall-plane collision in current and neighbor cells. Keeps the player inside existing cells unless a PASS/DOOR exists to cross.
	# We assume y is clamped elsewhere between floor/ceiling; here we do horizontal (x,z) collision only.
	cx = math.floor(p.x)
	cz = math.floor(p.z)
	cy = 0  # single level for now

	cell = dun.get_cell(cx, cy, cz)
	if cell is None:
		# If outside any cell, try to push back to nearest existing neighbor if any; simplest: clamp back to center of nearest existing cell by snapping
		# For demo robustness: do nothing heavy here, user shouldn't get here if we always move through openings
		return

	r = p.radius

	# WEST boundary at x=cx; block if no neighbor or face not open
	neighbor = dun.get_cell(cx - 1, cy, cz)
	west_open = (neighbor is not None) and (cell.west in (FaceType.PASS, FaceType.DOOR))
	if not west_open:
		dist = p.x - cx
		if dist < r:
			p.x = cx + r

	# EAST boundary at x=cx+1
	neighbor = dun.get_cell(cx + 1, cy, cz)
	east_open = (neighbor is not None) and (cell.east in (FaceType.PASS, FaceType.DOOR))
	if not east_open:
		dist = (cx + 1.0) - p.x
		if dist < r:
			p.x = (cx + 1.0) - r

	# NORTH boundary at z=cz
	neighbor = dun.get_cell(cx, cy, cz - 1)
	north_open = (neighbor is not None) and (cell.north in (FaceType.PASS, FaceType.DOOR))
	if not north_open:
		dist = p.z - cz
		if dist < r:
			p.z = cz + r

	# SOUTH boundary at z=cz+1
	neighbor = dun.get_cell(cx, cy, cz + 1)
	south_open = (neighbor is not None) and (cell.south in (FaceType.PASS, FaceType.DOOR))
	if not south_open:
		dist = (cz + 1.0) - p.z
		if dist < r:
			p.z = (cz + 1.0) - r


# ---------------------------- Demo dungeon ----------------------------
def build_sample_dungeon() -> Tuple[Dungeon, Tuple[float, float, float]]:
	d = Dungeon()
	y = 0

	# Build a 3x3 room at z=0..2, x=0..2
	for x in range(0, 3):
		for z in range(0, 3):
			d.add_cell(x, y, z)
	# Connect interior room cells to open walls between them
	for x in range(0, 3):
		for z in range(0, 3):
			if x < 2:
				d.connect((x, y, z), (x + 1, y, z))
			if z < 2:
				d.connect((x, y, z), (x, y, z + 1))

	# Add a 1x3 hallway to the east from the middle cell (2,1)
	for x in range(3, 6):
		d.add_cell(x, y, 1)
	d.connect((2, y, 1), (3, y, 1), as_door=False)
	d.connect((3, y, 1), (4, y, 1))
	d.connect((4, y, 1), (5, y, 1))

	# Player start position in the room center
	# Start at cell (1,1) center in feet
	start = ((1 + 0.5) * CELL_W, EYE_HEIGHT, (1 + 0.5) * CELL_D)
	return d, start


# ---------------------------- Main application ----------------------------
def main():
	pygame.init()

	# Request an OpenGL 3.3 Core profile context
	try:
		pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
		pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
		pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
		pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
		pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
	except Exception:
		pass  # attributes may not be available on all platforms

	width, height = 1920, 1080
	pygame.display.set_caption("Dungeon Cells Demo")
	screen = pygame.display.set_mode((width, height), OPENGL | DOUBLEBUF)
	GL.glViewport(0, 0, width, height)

	# GL state
	GL.glEnable(GL.GL_DEPTH_TEST)
	# Disable face culling to ensure interior faces are visible regardless of winding
	# (You can re-enable and adjust windings later for performance.)
	GL.glDisable(GL.GL_CULL_FACE)
	GL.glClearColor(0.2, 0.2, 0.25, 1.0)
	clear_mask = int(GL.GL_COLOR_BUFFER_BIT) | int(GL.GL_DEPTH_BUFFER_BIT)

	# Shaders
	program = create_shader_program()
	GL.glUseProgram(program)

	# Build dungeon + mesh
	dungeon, start_pos = build_sample_dungeon()
	mesh_floors, mesh_ceilings, mesh_walls = build_dungeon_meshes(dungeon)
	create_gl_objects(mesh_floors)
	create_gl_objects(mesh_ceilings)
	create_gl_objects(mesh_walls)
	# Load wall texture
	wall_tex = load_texture("wall1.png")
	# Load floor texture
	floor_tex = load_texture("floor_cobblestone_woodframe.png")
	# Load ceiling texture (optional)
	ceiling_tex = None
	try:
		ceiling_tex = load_texture("ceiling.png")
	except Exception:
		ceiling_tex = None
	# (debug) vertex counts
	# print(f"[debug] fc={mesh_fc.vertex_count} walls={mesh_walls.vertex_count}")

	# Projection matrix (rectilinear perspective)
	proj = perspective(100.0, width / float(height), 0.05, 100.0)
	uProj = GL.glGetUniformLocation(program, "uProj")
	GL.glUniformMatrix4fv(uProj, 1, GL.GL_FALSE, (c_float * 16)(*proj))

	# Uniform locations
	uView = GL.glGetUniformLocation(program, "uView")
	uLightPos = GL.glGetUniformLocation(program, "uLightPos")
	uViewPos = GL.glGetUniformLocation(program, "uViewPos")
	uLightRadius = GL.glGetUniformLocation(program, "uLightRadius")
	uLightColor = GL.glGetUniformLocation(program, "uLightColor")
	uUseTexture = GL.glGetUniformLocation(program, "uUseTexture")
	uTex = GL.glGetUniformLocation(program, "uTex")
	uLightIntensity = GL.glGetUniformLocation(program, "uLightIntensity")

	# Player
	player = Player(*start_pos)
	# Initialize grid coords from start feet
	player.grid_x = int(math.floor(player.x / CELL_W))
	player.grid_z = int(math.floor(player.z / CELL_D))
	player.facing = 0
	player.snap_to_cell()

	clock = pygame.time.Clock()
	running = True
	wireframe = False
	depth_enabled = True
	use_identity_view = False
	# Torch flicker state
	time_sec = 0.0
	noise = 0.0
	while running:
		dt = clock.tick(120) / 1000.0  # seconds
		time_sec += dt

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
				running = False
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
				wireframe = not wireframe
				mode = GL.GL_LINE if wireframe else GL.GL_FILL
				GL.glPolygonMode(GL.GL_FRONT_AND_BACK, mode)
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
				depth_enabled = not depth_enabled
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
				use_identity_view = not use_identity_view
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
				player.facing = (player.facing + 3) % 4  # turn left
				player.snap_to_cell()
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
				player.facing = (player.facing + 1) % 4  # turn right
				player.snap_to_cell()
			elif event.type == pygame.KEYDOWN and event.key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
				# Attempt grid step based on facing and key
				gx, gz = player.grid_x, player.grid_z
				# Movement vectors in grid coords for keys relative to facing
				if event.key == pygame.K_w:
					step = [(0,-1),(1,0),(0,1),(-1,0)][player.facing]
				elif event.key == pygame.K_s:
					step = [(0,1),(-1,0),(0,-1),(1,0)][player.facing]
				elif event.key == pygame.K_a:
					step = [(-1,0),(0,-1),(1,0),(0,1)][player.facing]
				else: # D
					step = [(1,0),(0,1),(-1,0),(0,-1)][player.facing]
				nx, nz = gx + step[0], gz + step[1]
				# Check passability between (gx,gz) and (nx,nz)
				cy = 0
				cur = dungeon.get_cell(gx, cy, gz)
				nxt = dungeon.get_cell(nx, cy, nz)
				can_move = False
				if cur is not None and nxt is not None:
					dx, dz = step[0], step[1]
					if dx == -1:
						can_move = cur.west in (FaceType.PASS, FaceType.DOOR)
					elif dx == 1:
						can_move = cur.east in (FaceType.PASS, FaceType.DOOR)
					elif dz == -1:
						can_move = cur.north in (FaceType.PASS, FaceType.DOOR)
					elif dz == 1:
						can_move = cur.south in (FaceType.PASS, FaceType.DOOR)
				if can_move:
					player.grid_x, player.grid_z = nx, nz
					player.snap_to_cell()

		keys = pygame.key.get_pressed()
		# Keep player eye height constant
		player.y = EYE_HEIGHT

		# Build View matrix from yaw and position; camera looks along forward, with up (0,1,0)
		if use_identity_view:
			view = [
				1.0, 0.0, 0.0, 0.0,
				0.0, 1.0, 0.0, 0.0,
				0.0, 0.0, 1.0, 0.0,
				0.0, 0.0, 0.0, 1.0,
			]
		else:
			rot = rotate_y(-player.yaw)  # inverse rotation
			trans = translate(-player.x, -player.y, -player.z)
			# View is R(-yaw) * T(-pos) for column-major right-multiply
			view = mat4_mul(rot, trans)

		# Update uniforms
		GL.glUniformMatrix4fv(uView, 1, GL.GL_FALSE, (c_float * 16)(*view))
		GL.glUniform3f(uLightPos, player.x, player.y, player.z)
		GL.glUniform3f(uViewPos, player.x, player.y, player.z)
		GL.glUniform1f(uLightRadius, 3.0 * 0.5 * (CELL_W + CELL_D))
		# Torch-like warm light
		GL.glUniform3f(uLightColor, 1.0, 0.75, 0.45)
		# Compute torch flicker intensity: combine low-frequency sines + smoothed noise
		flicker_sin = 0.5 * math.sin(2.0 * math.pi * 2.3 * time_sec) + 0.3 * math.sin(2.0 * math.pi * 3.7 * time_sec + 1.3)
		# Smooth small random jitter
		noise = noise + 0.5 * (random.uniform(-0.02, 0.02) - noise)
		intensity = 1.0 + 0.15 * flicker_sin + noise
		# Clamp for stability
		if intensity < 0.75:
			intensity = 0.75
		elif intensity > 1.25:
			intensity = 1.25
		GL.glUniform1f(uLightIntensity, float(intensity))
		GL.glUniform1i(uTex, 0)

		# Depth toggle
		if depth_enabled:
			GL.glEnable(GL.GL_DEPTH_TEST)
		else:
			GL.glDisable(GL.GL_DEPTH_TEST)

		# Draw
		GL.glClear(clear_mask)
		# Draw ceilings (textured if available, otherwise untextured)
		if ceiling_tex is not None:
			GL.glActiveTexture(GL.GL_TEXTURE0)
			GL.glBindTexture(GL.GL_TEXTURE_2D, ceiling_tex)
			GL.glUniform1i(uUseTexture, 1)
		else:
			GL.glUniform1i(uUseTexture, 0)
		GL.glBindVertexArray(mesh_ceilings.vao)
		GL.glDrawArrays(GL.GL_TRIANGLES, 0, mesh_ceilings.vertex_count)
		GL.glBindVertexArray(0)
		# Draw floors (textured once per tile)
		GL.glActiveTexture(GL.GL_TEXTURE0)
		GL.glBindTexture(GL.GL_TEXTURE_2D, floor_tex)
		GL.glUniform1i(uUseTexture, 1)
		GL.glBindVertexArray(mesh_floors.vao)
		GL.glDrawArrays(GL.GL_TRIANGLES, 0, mesh_floors.vertex_count)
		GL.glBindVertexArray(0)
		# Draw walls textured
		GL.glActiveTexture(GL.GL_TEXTURE0)
		GL.glBindTexture(GL.GL_TEXTURE_2D, wall_tex)
		GL.glUniform1i(uUseTexture, 1)
		GL.glBindVertexArray(mesh_walls.vao)
		GL.glDrawArrays(GL.GL_TRIANGLES, 0, mesh_walls.vertex_count)
		GL.glBindVertexArray(0)
		GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

		pygame.display.flip()

	# Cleanup
	try:
		GL.glDeleteBuffers(1, [mesh_floors.vbo])
		GL.glDeleteVertexArrays(1, [mesh_floors.vao])
		GL.glDeleteBuffers(1, [mesh_ceilings.vbo])
		GL.glDeleteVertexArrays(1, [mesh_ceilings.vao])
		GL.glDeleteBuffers(1, [mesh_walls.vbo])
		GL.glDeleteVertexArrays(1, [mesh_walls.vao])
		GL.glDeleteProgram(program)
	except Exception:
		pass

	pygame.quit()


if __name__ == "__main__":
	try:
		main()
	except Exception as e:
		print("Fatal error:", e)
		# On Windows consoles, ensure traceback visible if launched by double-click
		import traceback
		traceback.print_exc()
		pygame.quit()
		sys.exit(1)

