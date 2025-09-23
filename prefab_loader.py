import json
import os
from typing import Any, Dict, Tuple

class Prefab:
    def __init__(self, name: str, width: int, height: int, cells: list[str], legend: Dict[str, Dict[str, Any]], tags: list[str] | None = None):
        self.name = name
        self.width = width
        self.height = height
        self.cells = cells
        self.legend = legend or {}
        self.tags = tags or []

    @staticmethod
    def from_file(path: str) -> "Prefab":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        name = data.get('name') or os.path.basename(path)
        width = int(data.get('width'))
        height = int(data.get('height'))
        cells = data.get('cells') or []
        legend = data.get('legend') or {}
        tags = data.get('tags') or []
        # basic validation
        if len(cells) != height or any(len(row) != width for row in cells):
            raise ValueError(f"Prefab shape mismatch in {path}")
        return Prefab(name, width, height, cells, legend, tags)


def load_prefabs(folder: str) -> dict[str, Prefab]:
    out: dict[str, Prefab] = {}
    if not os.path.isdir(folder):
        return out
    for fn in os.listdir(folder):
        if not fn.lower().endswith('.json'):
            continue
        p = os.path.join(folder, fn)
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'prefabs' in data and isinstance(data['prefabs'], list):
                # Bundle file
                for ent in data['prefabs']:
                    try:
                        name = ent.get('name') or "Prefab"
                        width = int(ent.get('width'))
                        height = int(ent.get('height'))
                        cells = ent.get('cells') or []
                        legend = ent.get('legend') or {}
                        tags = ent.get('tags') or []
                        if len(cells) != height or any(len(row) != width for row in cells):
                            continue
                        pf = Prefab(name, width, height, cells, legend, tags)
                        out[pf.name] = pf
                    except Exception:
                        continue
            else:
                # Single prefab file
                pf = Prefab.from_file(p)
                out[pf.name] = pf
        except Exception:
            # skip invalid prefab
            continue
    return out
