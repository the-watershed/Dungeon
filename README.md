# Dungeon Cells Demo

A single-file Python demo of a first-person dungeon built from 1x1x1 "cells". Each cell has six faces labeled as floor, ceiling, wall, door, or pass. Adjacent cells connected as PASS/DOOR open their shared faces to form rooms and hallways.

- 1920x1080 window, rectilinear perspective, FOV 100°
- Per-pixel lighting (ambient + diffuse + specular) using OpenGL shaders
- WASD to move, Q/E to turn, ESC to quit

## Install

Use a recent Python 3.10+ on Windows. Fast path:

```pwsh
./setup.ps1
```

If PowerShell blocks the script, allow local scripts in the current session:

```pwsh
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./setup.ps1
```

Manual steps (equivalent):

```pwsh
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you have issues with PyOpenGL, try also installing your GPU vendor drivers and ensuring OpenGL 3.3+ is supported.

## Run

```pwsh
python main.py
```

## Controls

- W/S: forward/back
- A/D: strafe left/right
- Q/E: turn left/right
- Esc: quit

## Notes

- The sample dungeon builds a 3x3 room with a 1x3 hallway.
- Collision keeps you inside passable volumes. Floor and ceiling are solid; height is fixed at 0.5 in this demo.
- All code lives in `main.py` for simplicity.
