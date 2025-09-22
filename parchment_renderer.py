"""
ParchmentRenderer
------------------
Generates a realistic parchment-like background Surface using layered, efficient
procedural techniques suited for Pygame (no per-pixel Python loops).

Layers (in order):
- Base fill
- Tiled grain (coarse luminance variation)
- Soft blotches (semi-transparent stains of varying radii)
- Fibers (subtle hairline streaks)
- Speckles (tiny darker dots)
- Edge vignette (darkened border, rounded corners)

The result aims to capture characteristics of historical parchment: uneven tone,
subtle fibers, age stains, and darker edges. Techniques are inspired by common
procedural texturing patterns (value/fBM-like tiling, domain warping ideas) and
historical descriptions of parchment surface variability.

Usage:
    renderer = ParchmentRenderer(base_color=(245,237,215), ink_color=(40,28,18))
    surf = renderer.generate(width, height, seed=123)

This module has no dependency on the rest of the project besides pygame.
"""

from __future__ import annotations

import random
from typing import Optional, Tuple

try:
    import pygame
except Exception as e:  # pragma: no cover - pygame required by caller
    raise


Color = Tuple[int, int, int]


def _clamp(v: int, lo: int = 0, hi: int = 255) -> int:
    return lo if v < lo else hi if v > hi else v


class ParchmentRenderer:
    def __init__(
        self,
        base_color: Color = (245, 237, 215),
        ink_color: Color = (40, 28, 18),
        *,
        grain_tile: int = 8,
        blotch_count: int = 80,
        fiber_count: int = 60,
        speckle_count: int = 500,
        corner_radius: int = 12,
        enable_vignette: bool = True,
        vignette_steps: int = 24,
    ) -> None:
        self.base_color = base_color
        self.ink_color = ink_color
        self.grain_tile = max(2, int(grain_tile))
        self.blotch_count = max(0, int(blotch_count))
        self.fiber_count = max(0, int(fiber_count))
        self.speckle_count = max(0, int(speckle_count))
        self.corner_radius = max(0, int(corner_radius))
        self.enable_vignette = bool(enable_vignette)
        self.vignette_steps = max(0, int(vignette_steps))

    # Internal cached layers for animation
    _base: Optional[pygame.Surface] = None
    _blotches: Optional[pygame.Surface] = None
    _vignette: Optional[pygame.Surface] = None

    def build_layers(self, width: int, height: int, seed: Optional[int] = None) -> None:
        """Prebuild static layers for faster animated rendering."""
        state = None
        if seed is not None:
            state = random.getstate()
            random.seed(seed)
        try:
            # Base (fill + grain + fibers + speckles)
            base = pygame.Surface((width, height))
            base.fill(self.base_color)
            # Grain
            t = self.grain_tile
            tile = pygame.Surface((t, t))
            for y in range(0, height, t):
                for x in range(0, width, t):
                    delta = random.randint(-7, 7)
                    c = (
                        _clamp(self.base_color[0] + delta),
                        _clamp(self.base_color[1] + delta),
                        _clamp(self.base_color[2] + delta),
                    )
                    tile.fill(c)
                    base.blit(tile, (x, y))
            # Fibers
            for _ in range(self.fiber_count):
                length = random.randint(int(width * 0.08), int(width * 0.28))
                x = random.randint(-50, width + 50)
                y = random.randint(0, height)
                deg = random.uniform(-10.0, 10.0)
                dark = (
                    _clamp(self.base_color[0] - 12),
                    _clamp(self.base_color[1] - 12),
                    _clamp(self.base_color[2] - 12),
                )
                alpha = random.randint(18, 42)
                strip = pygame.Surface((length, 3), pygame.SRCALPHA)
                strip.fill((*dark, alpha))
                rot = pygame.transform.rotate(strip, deg)
                base.blit(rot, (x, y))
            # Speckles
            for _ in range(self.speckle_count):
                sx = random.randint(0, width - 1)
                sy = random.randint(0, height - 1)
                shade = random.randint(-30, -10)
                alpha = random.randint(20, 60)
                col = (
                    _clamp(self.base_color[0] + shade),
                    _clamp(self.base_color[1] + shade),
                    _clamp(self.base_color[2] + shade),
                    alpha,
                )
                pygame.draw.circle(base, col, (sx, sy), 1)

            # Blotches on a separate transparent layer
            blotches = pygame.Surface((width, height), pygame.SRCALPHA)
            for _ in range(self.blotch_count):
                r = random.randint(max(12, min(width, height) // 30), max(28, min(width, height) // 5))
                bx = random.randint(-r, width + r)
                by = random.randint(-r, height + r)
                shade = random.randint(-25, 12)
                alpha = random.randint(14, 38)
                col = (
                    _clamp(self.base_color[0] + shade),
                    _clamp(self.base_color[1] + shade),
                    _clamp(self.base_color[2] + shade),
                    alpha,
                )
                pygame.draw.circle(blotches, col, (bx, by), r)

            # Vignette on separate layer (optional)
            vig = pygame.Surface((width, height), pygame.SRCALPHA)
            if self.enable_vignette and self.vignette_steps > 0:
                steps = self.vignette_steps
                radius = self.corner_radius
                for i in range(steps):
                    a = int(8 + 6 * i)
                    pad = int(i * (min(width, height) * 0.01))
                    pygame.draw.rect(
                        vig,
                        (*self.ink_color, a),
                        (pad, pad, max(0, width - 2 * pad), max(0, height - 2 * pad)),
                        width=3,
                        border_radius=radius,
                    )

            self._base = base
            self._blotches = blotches
            self._vignette = vig
        finally:
            if state is not None:
                random.setstate(state)

    def render_animated(self, width: int, height: int, t: float) -> pygame.Surface:
        """Compose base + animated blotches + vignette into a new surface.

        The blotches layer is subtly domain-warped using a small rotozoom and
        translation that oscillates with time, giving a gentle 'living parchment' feel.
        """
        if self._base is None or self._blotches is None or self._vignette is None:
            # Build with default seed for stable look
            self.build_layers(width, height)

        # Create target
        out = pygame.Surface((width, height))
        base = self._base  # local alias to satisfy type checkers
        blotches = self._blotches
        vignette = self._vignette
        if base is None or blotches is None or vignette is None:
            # As a safety net, rebuild once
            self.build_layers(width, height)
            base = self._base
            blotches = self._blotches
            vignette = self._vignette
        assert base is not None and blotches is not None and vignette is not None
        out.blit(base, (0, 0))

        # Time-based warp parameters (very low amplitude)
        # Scale varies within ~±0.5%, rotation within ~±0.3°, translation within a couple of px
        import math
        s = 1.0 + 0.005 * math.sin(0.35 * t)
        rot = 0.3 * math.sin(0.21 * t)
        dx = 2.0 * math.sin(0.17 * t)
        dy = 2.0 * math.cos(0.23 * t)

        warped = pygame.transform.rotozoom(blotches, rot, s)
        # center the warped layer, then offset by dx, dy
        bx = (width - warped.get_width()) // 2 + int(dx)
        by = (height - warped.get_height()) // 2 + int(dy)
        out.blit(warped, (bx, by))

        out.blit(vignette, (0, 0))
        return out

    def generate(self, width: int, height: int, seed: Optional[int] = None) -> pygame.Surface:
        """Generate a static parchment by building layers and composing them."""
        self.build_layers(width, height, seed=seed)
        # Compose without animation (no rotozoom, no offset)
        surf = pygame.Surface((width, height))
        if self._base is not None:
            surf.blit(self._base, (0, 0))
        if self._blotches is not None:
            surf.blit(self._blotches, (0, 0))
        if self._vignette is not None:
            surf.blit(self._vignette, (0, 0))
        return surf
