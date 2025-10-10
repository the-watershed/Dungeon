"""Centralized sound library for managing all audio assets used by the game.

This module consolidates music, ambience, and sound effects into a unified
registry. It supports metadata management, categorization, and randomized
variation playback. The library persists to both a JSON manifest and a packed
binary archive so the runtime and authoring tools can share a single encoded
sound database.

Usage outline:
    library = SoundLibrary()
    click = library.load_sound("ui_click")
    click.play()

The library recognizes three core asset types:
- music: streamed via pygame.mixer.music
- effect: short-form pygame.Sound objects
- ambience: looping ambience or procedural generators

See `sound_manager_ui.py` for the companion UI editor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import io
import json
import random
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pygame

from sound_archive import SoundArchive, write_sound_archive

# Default path for persisted library metadata
LIBRARY_METADATA_PATH = Path(__file__).with_name("sound_library.json")
LIBRARY_ARCHIVE_PATH = Path(__file__).with_name("sounds.snd")
RESOURCES_ROOT = Path(__file__).parent / "resources" / "sounds"


@dataclass
class SoundVariant:
    """Represents a concrete playable sound variant with audio effects."""

    file: str = ""
    volume: float = 1.0
    weight: float = 1.0
    storage_key: Optional[str] = None
    original_file: Optional[str] = None
    data: Optional[bytes] = field(default=None, repr=False, compare=False)
    
    # Audio effects
    pitch: float = 1.0  # Pitch shift multiplier (0.5 = half speed, 2.0 = double speed)
    fade_in: float = 0.0  # Fade in duration in seconds
    fade_out: float = 0.0  # Fade out duration in seconds
    start_time: float = 0.0  # Start playback at this time (seconds)
    end_time: float = 0.0  # End playback at this time (0 = full length)
    reverb: float = 0.0  # Reverb amount (0.0 to 1.0)
    lowpass: float = 0.0  # Low-pass filter cutoff (0 = off, 0.1-1.0 = filter amount)
    highpass: float = 0.0  # High-pass filter cutoff (0 = off, 0.1-1.0 = filter amount)
    distortion: float = 0.0  # Distortion/clipping amount (0.0 to 1.0)

    def as_dict(self) -> Dict[str, Any]:
        payload = {
            "file": self.file,
            "volume": self.volume,
            "weight": self.weight,
        }
        if self.storage_key:
            payload["storage_key"] = self.storage_key
        if self.original_file:
            payload["original_file"] = self.original_file
        
        # Include effects if they're non-default
        if self.pitch != 1.0:
            payload["pitch"] = self.pitch
        if self.fade_in > 0:
            payload["fade_in"] = self.fade_in
        if self.fade_out > 0:
            payload["fade_out"] = self.fade_out
        if self.start_time > 0:
            payload["start_time"] = self.start_time
        if self.end_time > 0:
            payload["end_time"] = self.end_time
        if self.reverb > 0:
            payload["reverb"] = self.reverb
        if self.lowpass > 0:
            payload["lowpass"] = self.lowpass
        if self.highpass > 0:
            payload["highpass"] = self.highpass
        if self.distortion > 0:
            payload["distortion"] = self.distortion
            
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoundVariant":
        variant = cls(
            file=data.get("file", ""),
            volume=float(data.get("volume", 1.0)),
            weight=float(data.get("weight", 1.0)),
            storage_key=data.get("storage_key"),
            original_file=data.get("original_file"),
            pitch=float(data.get("pitch", 1.0)),
            fade_in=float(data.get("fade_in", 0.0)),
            fade_out=float(data.get("fade_out", 0.0)),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            reverb=float(data.get("reverb", 0.0)),
            lowpass=float(data.get("lowpass", 0.0)),
            highpass=float(data.get("highpass", 0.0)),
            distortion=float(data.get("distortion", 0.0)),
        )
        return variant


@dataclass
class SoundAsset:
    """Logical sound entry that may contain multiple variants."""

    name: str
    asset_type: str  # music | effect | ambience | procedural
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    variants: List[SoundVariant] = field(default_factory=list)
    description: str = ""
    loop: bool = False
    stream: bool = False  # Stream via mixer.music instead of loading into memory
    triggers: List[str] = field(default_factory=list)  # Game events that trigger this sound

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "asset_type": self.asset_type,
            "category": self.category,
            "tags": list(self.tags),
            "variants": [variant.as_dict() for variant in self.variants],
            "description": self.description,
            "loop": self.loop,
            "stream": self.stream,
            "triggers": list(self.triggers),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SoundAsset":
        variants = [SoundVariant.from_dict(v) for v in data.get("variants", [])]
        return cls(
            name=data.get("name", "Unnamed"),
            asset_type=data.get("asset_type", "effect"),
            category=data.get("category", "general"),
            tags=list(data.get("tags", [])),
            variants=variants,
            description=data.get("description", ""),
            loop=bool(data.get("loop", False)),
            stream=bool(data.get("stream", False)),
            triggers=list(data.get("triggers", [])),
        )



class SoundLibrary:
    """Registry for all sounds and helper to play them."""

    def __init__(
        self,
        archive_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
    ):
        self.archive_path = Path(archive_path or LIBRARY_ARCHIVE_PATH)
        self.metadata_path = Path(metadata_path or LIBRARY_METADATA_PATH)
        self.assets: Dict[str, SoundAsset] = {}
        self._archive: Optional[SoundArchive] = None
        self._temp_music_files: Dict[str, str] = {}
        self._ensure_mixer()
        self.load()

    def _ensure_mixer(self) -> None:
        if not pygame.mixer.get_init():
            # Higher quality settings for better MP3/WAV playback
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self) -> None:
        if self._archive is not None:
            self._archive.close()
            self._archive = None
        if self.archive_path.exists():
            self._load_from_archive()
        elif self.metadata_path.exists():
            self._load_from_metadata()
        else:
            self.assets = {}

    def _load_from_metadata(self) -> None:
        with self.metadata_path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self.assets = {}
        for entry in raw.get("assets", []):
            asset = SoundAsset.from_dict(entry)
            self.assets[asset.name] = asset

    def _load_from_archive(self) -> None:
        self._archive = SoundArchive(self.archive_path)
        manifest = self._archive.manifest
        self.assets = {}
        for entry in manifest.get("assets", []):
            asset = SoundAsset.from_dict(entry)
            self.assets[asset.name] = asset

    def save(self) -> None:
        manifest = {
            "version": 1,
            "assets": [asset.as_dict() for asset in self.assets.values()],
        }
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with self.metadata_path.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
        data_map: Dict[str, bytes] = {}
        for asset in self.assets.values():
            for variant in asset.variants:
                storage_key = self._assign_storage_key(asset, variant)
                data_map[storage_key] = self._get_variant_bytes(asset, variant)
        write_sound_archive(self.archive_path, manifest, data_map)
        self.load()

    def save_to_disk(self) -> None:
        self.save()

    def load_from_disk(self) -> None:
        self.load()

    # ------------------------------------------------------------------
    # Asset management
    # ------------------------------------------------------------------
    def list_assets(self, asset_type: Optional[str] = None) -> List[SoundAsset]:
        if asset_type is None:
            return list(self.assets.values())
        return [asset for asset in self.assets.values() if asset.asset_type == asset_type]

    def list_categories(self) -> List[str]:
        return sorted({asset.category for asset in self.assets.values()})

    def get_asset(self, name: str) -> Optional[SoundAsset]:
        return self.assets.get(name)
    
    def get_assets_by_trigger(self, trigger: str) -> List[SoundAsset]:
        """Find all assets that respond to a specific game event trigger."""
        return [asset for asset in self.assets.values() if trigger in asset.triggers]
    
    def play_trigger_sound(self, trigger: str) -> None:
        """Play a random sound associated with the given trigger."""
        matching = self.get_assets_by_trigger(trigger)
        if not matching:
            return
        # Pick a random asset from those matching the trigger
        asset = random.choice(matching)
        if asset.stream:
            self.play_music(asset.name)
        else:
            self.play_sound(asset.name)

    def register_asset(self, asset: SoundAsset, overwrite: bool = False) -> None:
        if asset.name in self.assets and not overwrite:
            raise ValueError(f"Asset '{asset.name}' already exists")
        self.assets[asset.name] = asset
        for variant in asset.variants:
            self._assign_storage_key(asset, variant)

    def ensure_asset(
        self,
        name: str,
        asset_type: str,
        *,
        category: str = "general",
        tags: Optional[List[str]] = None,
        description: str = "",
        loop: bool = False,
        stream: bool = False,
    ) -> SoundAsset:
        asset = self.assets.get(name)
        if asset is None:
            asset = SoundAsset(
                name=name,
                asset_type=asset_type,
                category=category,
                tags=list(tags or []),
                description=description,
                loop=loop,
                stream=stream,
            )
            self.assets[name] = asset
        return asset

    def add_variant(self, asset_name: str, variant: SoundVariant) -> None:
        asset = self.get_asset(asset_name)
        if asset is None:
            raise KeyError(f"Cannot add variant; asset '{asset_name}' not found")
        asset.variants.append(variant)
        self._assign_storage_key(asset, variant)

    def update_asset_metadata(
        self,
        name: str,
        *,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        loop: Optional[bool] = None,
        stream: Optional[bool] = None,
        triggers: Optional[List[str]] = None,
    ) -> None:
        asset = self.get_asset(name)
        if asset is None:
            raise KeyError(f"Asset '{name}' does not exist")
        if category is not None:
            asset.category = category
        if tags is not None:
            asset.tags = list(tags)
        if description is not None:
            asset.description = description
        if loop is not None:
            asset.loop = bool(loop)
        if stream is not None:
            asset.stream = bool(stream)
        if triggers is not None:
            asset.triggers = list(triggers)

    def remove_asset(self, name: str) -> None:
        self.assets.pop(name, None)
    
    def export_variant_to_file(self, asset_name: str, variant_index: int, target_path: Path) -> None:
        """Export a specific variant to a file on disk."""
        asset = self.get_asset(asset_name)
        if not asset:
            raise KeyError(f"Asset '{asset_name}' not found")
        if variant_index < 0 or variant_index >= len(asset.variants):
            raise IndexError(f"Variant index {variant_index} out of range")
        
        variant = asset.variants[variant_index]
        audio_bytes = self._get_variant_bytes(asset, variant)
        target_path.write_bytes(audio_bytes)
    
    def import_variant_from_file(self, asset_name: str, source_path: Path, volume: float = 1.0, weight: float = 1.0) -> SoundVariant:
        """Import a sound file as a new variant for an existing asset."""
        asset = self.get_asset(asset_name)
        if not asset:
            raise KeyError(f"Asset '{asset_name}' not found")
        
        # Copy to resources directory
        RESOURCES_ROOT.mkdir(parents=True, exist_ok=True)
        dest = RESOURCES_ROOT / source_path.name
        if not dest.exists():
            dest.write_bytes(source_path.read_bytes())
        
        variant = SoundVariant(
            file=dest.name,
            original_file=source_path.name,
            volume=volume,
            weight=weight,
        )
        self.add_variant(asset_name, variant)
        return variant

    # ------------------------------------------------------------------
    # Playback helpers
    # ------------------------------------------------------------------
    def resolve_variant_path(self, variant: SoundVariant) -> Path:
        if variant.file:
            candidate = Path(variant.file)
            if candidate.is_file():
                return candidate
            resource_path = RESOURCES_ROOT / variant.file
            if resource_path.is_file():
                return resource_path
        raise FileNotFoundError(
            f"Variant data not found on disk for '{variant.file}'. Storage key: {variant.storage_key}"
        )

    def load_sound(self, name: str) -> pygame.mixer.Sound:
        asset = self.get_asset(name)
        if not asset:
            raise KeyError(f"Unknown sound asset '{name}'")
        if not asset.variants:
            raise ValueError(f"Sound asset '{name}' has no variants")
        variant = self._choose_variant(asset)
        audio_bytes = self._get_variant_bytes(asset, variant)
        
        # Determine file format
        ext = ''
        if hasattr(variant, 'file') and variant.file:
            ext = str(variant.file).lower().split('.')[-1]
        
        # MP3 and OGG need to be loaded from file, not buffer
        if ext in ('mp3', 'ogg'):
            # Try to load from file path first
            try:
                file_path = self.resolve_variant_path(variant)
                sound = pygame.mixer.Sound(str(file_path))
            except (FileNotFoundError, pygame.error):
                # Fall back to temp file from bytes
                tmp_dir = Path(tempfile.gettempdir()) / "dungeon_sound_cache"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_file = tmp_dir / f"{uuid.uuid4().hex}{self._infer_extension(variant)}"
                tmp_file.write_bytes(audio_bytes)
                sound = pygame.mixer.Sound(str(tmp_file))
                # Clean up temp file after a delay
                import threading
                def cleanup():
                    import time
                    time.sleep(2)
                    try:
                        tmp_file.unlink()
                    except:
                        pass
                threading.Thread(target=cleanup, daemon=True).start()
        else:
            # WAV can be loaded from buffer
            if variant.distortion > 0 and ext == 'wav':
                try:
                    import array
                    sound_temp = pygame.mixer.Sound(buffer=audio_bytes)
                    arr = array.array('h', sound_temp.get_raw())
                    for i in range(len(arr)):
                        arr[i] = int(arr[i] * (1.0 - variant.distortion))
                    sound = pygame.mixer.Sound(buffer=arr.tobytes())
                except Exception:
                    sound = pygame.mixer.Sound(buffer=audio_bytes)
            else:
                sound = pygame.mixer.Sound(buffer=audio_bytes)
        
        sound.set_volume(max(0.0, min(1.0, variant.volume)))
        
        # Store effects in a dict for this sound id
        if not hasattr(self, '_sound_effects'):
            self._sound_effects = {}
        effect = {
            'fade_in': int(variant.fade_in * 1000) if variant.fade_in > 0 else 0,
            'fade_out': int(variant.fade_out * 1000) if variant.fade_out > 0 else 0,
        }
        self._sound_effects[id(sound)] = effect
        return sound

    def play_sound(self, name: str) -> None:
        sound = self.load_sound(name)
        effect = getattr(self, '_sound_effects', {}).get(id(sound), {})
        fade_in = effect.get('fade_in', 0)
        channel = sound.play(fade_ms=fade_in)
        if channel:
            channel.set_volume(sound.get_volume())
            fade_out = effect.get('fade_out', 0)
            if fade_out > 0:
                import threading
                def stop_channel():
                    channel.fadeout(fade_out)
                threading.Timer(fade_out/1000.0, stop_channel).start()

    def play_music(self, name: str, loops: int = -1, fade_ms: int = 0) -> None:
        asset = self.get_asset(name)
        if not asset:
            raise KeyError(f"Unknown music asset '{name}'")
        if not asset.stream:
            raise ValueError(f"Music asset '{name}' must be marked as stream=True")
        if not asset.variants:
            raise ValueError(f"Music asset '{name}' has no variants")
        variant = self._choose_variant(asset)
        audio_bytes = self._get_variant_bytes(asset, variant)
        self._load_music_from_bytes(audio_bytes, variant)
        if variant.volume is not None:
            pygame.mixer.music.set_volume(max(0.0, min(1.0, variant.volume)))
        # Fade in
        fade_in = int(variant.fade_in * 1000) if variant.fade_in > 0 else fade_ms
        pygame.mixer.music.play(loops=loops, fade_ms=fade_in)
        # Fade out (simulate by scheduling stop)
        if variant.fade_out > 0:
            import threading
            def stop_music():
                pygame.mixer.music.fadeout(int(variant.fade_out * 1000))
            threading.Timer(variant.fade_out, stop_music).start()

    def _choose_variant(self, asset: SoundAsset) -> SoundVariant:
        if len(asset.variants) == 1:
            return asset.variants[0]
        weights = [max(0.0, variant.weight) for variant in asset.variants]
        total_weight = sum(weights)
        if total_weight <= 0:
            total_weight = float(len(weights))
            weights = [1.0] * len(weights)
        threshold = random.random() * total_weight
        cumulative = 0.0
        for weight, variant in zip(weights, asset.variants):
            cumulative += weight
            if threshold <= cumulative:
                return variant
        return asset.variants[-1]

    def _assign_storage_key(self, asset: SoundAsset, variant: SoundVariant) -> str:
        if variant.storage_key:
            return variant.storage_key
        slug = self._slugify(asset.name)
        extension = self._infer_extension(variant)
        variant.storage_key = f"assets/{slug}/{uuid.uuid4().hex}{extension}"
        return variant.storage_key

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9_-]+", "_", value.lower())
        slug = slug.strip("_")
        return slug or uuid.uuid4().hex

    def _infer_extension(self, variant: SoundVariant) -> str:
        for candidate in (variant.file, variant.original_file, variant.storage_key):
            if candidate:
                ext = Path(candidate).suffix
                if ext:
                    return ext
        return ".wav"

    def _get_variant_bytes(self, asset: SoundAsset, variant: SoundVariant) -> bytes:
        if variant.data:
            return variant.data
        if self._archive and variant.storage_key:
            try:
                data = self._archive.read_bytes(variant.storage_key)
            except KeyError:
                data = None
            if data is not None:
                return data
        if variant.file:
            try:
                path = self.resolve_variant_path(variant)
            except FileNotFoundError:
                pass
            else:
                return path.read_bytes()
        if self.archive_path.exists() and variant.storage_key:
            if self._archive is None:
                self._load_from_archive()
            if self._archive:
                try:
                    data = self._archive.read_bytes(variant.storage_key)
                except KeyError:
                    data = None
                if data is not None:
                    return data
        raise FileNotFoundError(
            f"Unable to resolve audio data for asset '{asset.name}' variant '{variant.storage_key or variant.file}'"
        )

    def _load_music_from_bytes(self, audio_bytes: bytes, variant: SoundVariant) -> None:
        extension = self._infer_extension(variant)
        stream = io.BytesIO(audio_bytes)
        stream.seek(0)
        key = variant.storage_key or variant.file or variant.original_file or uuid.uuid4().hex
        try:
            pygame.mixer.music.load(stream, namehint=extension)
            self._remove_temp_file(key)
            return
        except pygame.error:
            pass
        path = self._ensure_temp_file(key, extension, audio_bytes)
        pygame.mixer.music.load(path)

    def _ensure_temp_file(self, key: str, extension: str, audio_bytes: bytes) -> str:
        tmp_dir = Path(tempfile.gettempdir()) / "dungeon_sound_cache"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        self._remove_temp_file(key)
        filename = f"{self._slugify(key)}_{uuid.uuid4().hex}{extension}"
        path = tmp_dir / filename
        path.write_bytes(audio_bytes)
        self._temp_music_files[key] = path.as_posix()
        return path.as_posix()

    def _remove_temp_file(self, key: str) -> None:
        path_str = self._temp_music_files.pop(key, None)
        if not path_str:
            return
        path = Path(path_str)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    def cleanup(self) -> None:
        for key in list(self._temp_music_files.keys()):
            self._remove_temp_file(key)
        if self._archive is not None:
            self._archive.close()
            self._archive = None

    def __del__(self) -> None:
        try:
            self.cleanup()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helper factories
    # ------------------------------------------------------------------
    def create_default_assets(self) -> None:
        """Populate the library with core sounds discovered in resources."""
        self.assets.clear()
        if not RESOURCES_ROOT.exists():
            return
        for file in RESOURCES_ROOT.glob("*.*"):
            if not file.is_file():
                continue
            name = file.stem
            ext = file.suffix.lower()
            if ext not in {".mp3", ".wav", ".ogg", ".mid"}:
                continue
            if ext == ".mid" or name.lower().startswith("dungeon"):
                asset_type = "music"
            else:
                asset_type = "effect"
            variant = SoundVariant(
                file=file.name,
                original_file=file.name,
                volume=0.8 if asset_type == "effect" else 0.6,
            )
            asset = SoundAsset(
                name=name,
                asset_type=asset_type,
                variants=[variant],
                category="imported",
                stream=(asset_type == "music"),
                loop=(asset_type != "effect"),
            )
            self.assets[name] = asset
            self._assign_storage_key(asset, variant)


_global_library: Optional[SoundLibrary] = None


def get_sound_library() -> SoundLibrary:
    """Retrieve singleton SoundLibrary instance."""
    global _global_library
    if _global_library is None:
        _global_library = SoundLibrary()
        if not _global_library.assets:
            _global_library.create_default_assets()
    return _global_library