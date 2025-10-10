"""Utilities for reading and writing the packaged sound archive."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable
import zipfile


MANIFEST_NAME = "manifest.json"


class SoundArchive:
    """Read-only access to the packaged sound archive."""

    def __init__(self, archive_path: Path):
        self.archive_path = Path(archive_path)
        if not self.archive_path.is_file():
            raise FileNotFoundError(f"Sound archive not found: {self.archive_path}")
        self._zip = zipfile.ZipFile(self.archive_path, "r")
        with self._zip.open(MANIFEST_NAME) as manifest_file:
            self.manifest = json.load(manifest_file)

    def iter_storage_keys(self) -> Iterable[str]:
        for info in self._zip.infolist():
            if info.filename == MANIFEST_NAME or info.is_dir():
                continue
            yield info.filename

    def read_bytes(self, storage_key: str) -> bytes:
        with self._zip.open(storage_key) as handle:
            return handle.read()

    def close(self) -> None:
        self._zip.close()


def write_sound_archive(archive_path: Path, manifest: Dict, data_map: Dict[str, bytes]) -> None:
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True))
        for storage_key, payload in data_map.items():
            zf.writestr(storage_key, payload)
