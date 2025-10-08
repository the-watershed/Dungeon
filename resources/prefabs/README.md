Prefab Library

This folder contains JSON prefab areas that can be stamped into generated dungeons.

Schema (v1):
{
  "name": "Orc Barracks",
  "version": 1,
  "width": 11,
  "height": 7,
  "cells": [
    "###########",
    "#.........#",
    "#.###.###.#",
    "#.#.....#.#",
    "#.###.###.#",
    "#.........#",
    "###########"
  ],
  "legend": {
    "#": { "tile": "wall", "material": "brick" },
    ".": { "tile": "floor", "material": "cobble" },
    " ": { "tile": "void" }
  },
  "tags": ["barracks", "orc", "rooms"],
  "notes": "Walls are solid brick; floors are cobblestone."
}

Legend tile values: wall | floor | void
Legend material values (current set): brick | cobble | dirt | moss | sand | iron | grass | water | lava | marble | wood

Placement contract:
- Stamping respects existing map bounds and will not write outside.
- Void cells are skipped (no change).
- Optionally can require a minimum buffer (empty space) around the prefab.

Bundle files:
- You can package multiple prefabs in a single JSON file using a top-level `prefabs` array.
- Optional metadata keys like `bundle` or `version` at the top level are ignored by the loader.

Example bundle file:
{
  "bundle": "High Value Prefabs v1",
  "prefabs": [
    { "name": "Egyptian Antechamber", "width": 11, "height": 7, "cells": ["###########", "#.........#", "#.###.###.#", "#.#.....#.#", "#.###.###.#", "#.........#", "###########"], "legend": {"#": {"tile":"wall","material":"sand"}, ".": {"tile":"floor","material":"sand"}}, "tags": ["egyptian","crypt","antechamber"] },
    { "name": "Prison Cell Block", "width": 13, "height": 7, "cells": ["#############","#|.|.|.|.|.|#","#...........#","#|.|.|.|.|.|#","#...........#","#|.|.|.|.|.|#","#############"], "legend": {"#": {"tile":"wall","material":"brick"}, ".": {"tile":"floor","material":"cobble"}, "|": {"tile":"wall","material":"iron"}}, "tags": ["jail","prison","cells"] }
  ]
}

Loader behavior:
- Files with a single top-level prefab object are loaded as one prefab.
- Files with a top-level `prefabs` array are loaded as multiple prefabs, each entry must conform to the single-prefab schema.
- Invalid or mismatched shapes are skipped; valid entries are still loaded.
