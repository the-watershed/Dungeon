"""
Procedural sound generation for dungeon ambience.
Creates atmospheric sounds like rats, bats, water droplets, and metal squeaking.
"""

import os
import pygame
import pygame.sndarray
import numpy as np
import random
import math
from typing import Optional

from sound_library import get_sound_library, SoundLibrary


class SoundGenerator:
	"""Generates procedural sounds for dungeon ambience."""
	
	def __init__(self, sample_rate=22050):
		"""Initialize the sound generator.
		
		Args:
			sample_rate: Audio sample rate in Hz (default: 22050)
		"""
		self.sample_rate = sample_rate
		# Don't re-initialize mixer if already initialized (to avoid conflicts with music system)
		init_state = pygame.mixer.get_init()
		if not init_state:
			pygame.mixer.init(frequency=sample_rate, size=-16, channels=2, buffer=512)
			init_state = pygame.mixer.get_init()
		self.sounds = {}
		self._bat_squeak_base = None
		self._bat_squeak_rate = init_state[0] if init_state else self.sample_rate
		self._bat_squeak_channels = init_state[2] if init_state else 2
		self._secret_discovery_sound = None
		self._library: Optional[SoundLibrary] = None

	def _ensure_secret_discovery_sound(self) -> None:
		if self._secret_discovery_sound is not None:
			return
		if self._library is None:
			try:
				self._library = get_sound_library()
			except Exception:
				self._library = None
		if self._library is not None:
			try:
				sound = self._library.load_sound("click_1")
				self._secret_discovery_sound = sound
				return
			except Exception:
				self._secret_discovery_sound = None
		sample_path = os.path.join(os.path.dirname(__file__), 'resources', 'sounds', 'click_1.wav')
		if not os.path.isfile(sample_path):
			raise FileNotFoundError(f"Missing secret discovery sample: {sample_path}")
		self._secret_discovery_sound = pygame.mixer.Sound(sample_path)

	def play_secret_discovery_sound(self, volume: float = 0.6) -> None:
		self._ensure_secret_discovery_sound()
		if self._secret_discovery_sound is None:
			raise RuntimeError("Secret discovery sound failed to load")
		channel = self._secret_discovery_sound.play()
		if channel:
			channel.set_volume(max(0.0, min(1.0, float(volume))))
	
	def generate_sine_wave(self, frequency, duration, amplitude=0.5):
		"""Generate a sine wave.
		
		Args:
			frequency: Frequency in Hz
			duration: Duration in seconds
			amplitude: Volume (0.0 to 1.0)
			
		Returns:
			numpy array of samples
		"""
		num_samples = int(self.sample_rate * duration)
		t = np.linspace(0, duration, num_samples, False)
		wave = amplitude * np.sin(2 * np.pi * frequency * t)
		return wave
	
	def apply_envelope(self, samples, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
		"""Apply ADSR envelope to samples.
		
		Args:
			samples: Input samples
			attack: Attack time (0-1)
			decay: Decay time (0-1)
			sustain: Sustain level (0-1)
			release: Release time (0-1)
			
		Returns:
			Samples with envelope applied
		"""
		length = len(samples)
		envelope = np.ones(length)
		
		# Attack
		attack_samples = int(length * attack)
		if attack_samples > 0:
			envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
		
		# Decay
		decay_samples = int(length * decay)
		if decay_samples > 0:
			decay_start = attack_samples
			decay_end = attack_samples + decay_samples
			envelope[decay_start:decay_end] = np.linspace(1, sustain, decay_samples)
		
		# Sustain (already set to sustain level)
		sustain_start = attack_samples + decay_samples
		sustain_end = length - int(length * release)
		envelope[sustain_start:sustain_end] = sustain
		
		# Release
		release_samples = int(length * release)
		if release_samples > 0:
			envelope[-release_samples:] = np.linspace(sustain, 0, release_samples)
		
		return samples * envelope
	
	def add_noise(self, samples, amount=0.1):
		"""Add white noise to samples.
		
		Args:
			samples: Input samples
			amount: Noise amount (0.0 to 1.0)
			
		Returns:
			Samples with noise added
		"""
		noise = np.random.uniform(-amount, amount, len(samples))
		return samples + noise
	
	def generate_rat_squeak(self):
		"""Generate a rat squeaking sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.05, 0.15)
		base_freq = random.uniform(2000, 4000)
		
		# Create frequency modulation for squeaky sound
		num_samples = int(self.sample_rate * duration)
		t = np.linspace(0, duration, num_samples, False)
		
		# Frequency sweep (chirp)
		freq_mod = np.linspace(base_freq, base_freq * 1.5, num_samples)
		phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
		samples = 0.7 * np.sin(phase)
		
		# Add harmonics for texture
		samples += 0.35 * np.sin(2 * phase)
		samples += 0.18 * np.sin(3 * phase)
		
		# Add noise for realism
		samples = self.add_noise(samples, 0.05)
		
		# Apply envelope
		samples = self.apply_envelope(samples, attack=0.05, decay=0.3, sustain=0.4, release=0.5)
		
		return self._samples_to_sound(samples)
	
	def generate_rat_scurry(self):
		"""Generate rat scurrying/scratching sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.3, 0.8)
		num_samples = int(self.sample_rate * duration)
		
		# Create rapid scratching sound with filtered noise
		noise = np.random.uniform(-1, 1, num_samples)
		
		# Apply low-pass filter effect (simple moving average)
		window = 5
		filtered = np.convolve(noise, np.ones(window)/window, mode='same')
		
		# Add rhythmic pattern (paws)
		t = np.linspace(0, duration, num_samples, False)
		rhythm = np.abs(np.sin(2 * np.pi * random.uniform(8, 15) * t))
		samples = 0.6 * filtered * rhythm
		
		# Apply envelope
		samples = self.apply_envelope(samples, attack=0.1, decay=0.2, sustain=0.7, release=0.2)
		
		return self._samples_to_sound(samples)
	
	def generate_bat_screech(self):
		"""Generate a bat screeching sound (ultrasonic-style).
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.08, 0.2)
		base_freq = random.uniform(3000, 6000)
		
		num_samples = int(self.sample_rate * duration)
		t = np.linspace(0, duration, num_samples, False)
		
		# Rapid frequency modulation
		mod_freq = random.uniform(100, 300)
		freq_mod = base_freq + 500 * np.sin(2 * np.pi * mod_freq * t)
		phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
		samples = 0.6 * np.sin(phase)
		
		# Add noise for texture
		samples = self.add_noise(samples, 0.08)
		
		# Sharp envelope
		samples = self.apply_envelope(samples, attack=0.02, decay=0.4, sustain=0.3, release=0.6)
		
		return self._samples_to_sound(samples)
	
	def generate_bat_wings(self):
		"""Generate bat wing flapping sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.4, 0.8)
		num_samples = int(self.sample_rate * duration)
		
		# Low frequency whooshing
		t = np.linspace(0, duration, num_samples, False)
		
		# Multiple flaps
		flap_freq = random.uniform(4, 8)
		flap_pattern = np.abs(np.sin(2 * np.pi * flap_freq * t))
		
		# Low frequency tone for air movement
		base = 0.4 * np.sin(2 * np.pi * 120 * t)
		
		# Filtered noise for texture
		noise = np.random.uniform(-1, 1, num_samples)
		samples = (base + 0.5 * noise) * flap_pattern
		
		# Apply envelope
		samples = self.apply_envelope(samples, attack=0.1, decay=0.2, sustain=0.6, release=0.3)
		
		return self._samples_to_sound(samples)
	
	def generate_water_drip(self):
		"""Generate a water droplet sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.15, 0.3)
		num_samples = int(self.sample_rate * duration)
		t = np.linspace(0, duration, num_samples, False)
		
		# Initial impact (high frequency)
		impact_freq = random.uniform(800, 1200)
		impact = 0.8 * np.sin(2 * np.pi * impact_freq * t)
		
		# Resonance (lower frequency)
		resonance_freq = random.uniform(200, 400)
		resonance = 0.6 * np.sin(2 * np.pi * resonance_freq * t)
		
		# Combine with decay
		samples = impact + resonance
		
		# Add splash noise
		splash = np.random.uniform(-0.2, 0.2, num_samples)
		samples = samples + splash
		
		# Sharp attack, quick decay
		samples = self.apply_envelope(samples, attack=0.01, decay=0.5, sustain=0.1, release=0.4)
		
		return self._samples_to_sound(samples)
	
	def generate_water_echo(self):
		"""Generate echoing water drip in cavern.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.8, 1.5)
		num_samples = int(self.sample_rate * duration)
		
		# Generate base drip
		drip_samples = int(self.sample_rate * 0.2)
		t_drip = np.linspace(0, 0.2, drip_samples, False)
		
		freq = random.uniform(600, 1000)
		drip = 0.8 * np.sin(2 * np.pi * freq * t_drip)
		drip = self.apply_envelope(drip, attack=0.01, decay=0.6, sustain=0.2, release=0.3)
		
		# Create echoes
		samples = np.zeros(num_samples)
		samples[:drip_samples] = drip
		
		# Add multiple echoes with decay
		echo_delays = [0.15, 0.35, 0.6, 0.9]
		echo_strengths = [0.7, 0.5, 0.3, 0.15]
		
		for delay, strength in zip(echo_delays, echo_strengths):
			echo_start = int(delay * self.sample_rate)
			echo_end = echo_start + drip_samples
			if echo_end <= num_samples:
				samples[echo_start:echo_end] += strength * drip
		
		return self._samples_to_sound(samples)
	
	def generate_metal_creak(self):
		"""Generate metal creaking/squeaking sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.5, 1.5)
		num_samples = int(self.sample_rate * duration)
		t = np.linspace(0, duration, num_samples, False)
		
		# Multiple frequency components for metallic sound
		freq1 = random.uniform(300, 600)
		freq2 = random.uniform(800, 1200)
		freq3 = random.uniform(1500, 2500)
		
		# Slow frequency modulation for creaking
		mod_freq = random.uniform(1, 3)
		mod = 1 + 0.3 * np.sin(2 * np.pi * mod_freq * t)
		
		samples = (
			0.6 * np.sin(2 * np.pi * freq1 * mod * t) +
			0.4 * np.sin(2 * np.pi * freq2 * mod * t) +
			0.3 * np.sin(2 * np.pi * freq3 * mod * t)
		)
		
		# Add noise for grinding texture
		samples = self.add_noise(samples, 0.15)
		
		# Apply envelope
		samples = self.apply_envelope(samples, attack=0.15, decay=0.2, sustain=0.7, release=0.3)
		
		return self._samples_to_sound(samples)
	
	def generate_chain_rattle(self):
		"""Generate rattling chain sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.6, 1.2)
		num_samples = int(self.sample_rate * duration)
		
		# Create series of metallic clinks
		samples = np.zeros(num_samples)
		num_clinks = random.randint(8, 15)
		
		for i in range(num_clinks):
			clink_pos = int(random.uniform(0, num_samples - 1000))
			clink_dur = 0.05
			clink_samples = int(self.sample_rate * clink_dur)
			t = np.linspace(0, clink_dur, clink_samples, False)
			
			# Metallic frequencies
			freq = random.uniform(2000, 4000)
			clink = 0.7 * np.sin(2 * np.pi * freq * t)
			clink = self.apply_envelope(clink, attack=0.01, decay=0.7, sustain=0.1, release=0.2)
			
			# Add to main samples
			end_pos = min(clink_pos + clink_samples, num_samples)
			samples[clink_pos:end_pos] += clink[:end_pos - clink_pos]
		
		# Apply overall envelope
		samples = self.apply_envelope(samples, attack=0.1, decay=0.2, sustain=0.8, release=0.2)
		
		return self._samples_to_sound(samples)
	
	def generate_distant_howl(self):
		"""Generate distant creature howl.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(1.5, 3.0)
		num_samples = int(self.sample_rate * duration)
		t = np.linspace(0, duration, num_samples, False)
		
		# Low frequency howl with vibrato
		base_freq = random.uniform(150, 300)
		vibrato_freq = random.uniform(4, 8)
		vibrato_depth = 20
		
		freq_mod = base_freq + vibrato_depth * np.sin(2 * np.pi * vibrato_freq * t)
		phase = np.cumsum(2 * np.pi * freq_mod / self.sample_rate)
		
		samples = 0.5 * np.sin(phase)
		samples += 0.25 * np.sin(2 * phase)  # Harmonic
		
		# Add wind-like noise
		samples = self.add_noise(samples, 0.1)
		
		# Slow envelope
		samples = self.apply_envelope(samples, attack=0.2, decay=0.1, sustain=0.6, release=0.3)
		
		return self._samples_to_sound(samples)
	
	def generate_stone_scrape(self):
		"""Generate stone scraping sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.8, 1.8)
		num_samples = int(self.sample_rate * duration)
		
		# Heavy filtered noise for grinding
		noise = np.random.uniform(-1, 1, num_samples)
		
		# Low-pass filter
		window = 20
		filtered = np.convolve(noise, np.ones(window)/window, mode='same')
		
		# Add low rumble
		t = np.linspace(0, duration, num_samples, False)
		rumble = 0.35 * np.sin(2 * np.pi * random.uniform(40, 80) * t)
		
		samples = 0.6 * filtered + rumble
		
		# Apply envelope
		samples = self.apply_envelope(samples, attack=0.15, decay=0.15, sustain=0.7, release=0.25)
		
		return self._samples_to_sound(samples)
	
	def generate_coin_sound(self):
		"""Generate metallic coin clink sound.
		
		Returns:
			pygame.Sound object
		"""
		duration = random.uniform(0.3, 0.5)
		num_samples = int(self.sample_rate * duration)
		t = np.linspace(0, duration, num_samples, False)
		
		# Multiple high metallic frequencies for coin sound
		freq1 = random.uniform(3000, 4000)
		freq2 = random.uniform(4500, 5500)
		freq3 = random.uniform(6000, 7000)
		
		# Create bright metallic tone
		samples = (
			0.5 * np.sin(2 * np.pi * freq1 * t) +
			0.3 * np.sin(2 * np.pi * freq2 * t) +
			0.2 * np.sin(2 * np.pi * freq3 * t)
		)
		
		# Add slight jingle with quick decay
		jingle_freq = random.uniform(7000, 9000)
		jingle = 0.15 * np.sin(2 * np.pi * jingle_freq * t)
		samples = samples + jingle
		
		# Sharp attack, quick decay for metallic coin clink
		samples = self.apply_envelope(samples, attack=0.01, decay=0.3, sustain=0.2, release=0.5)
		
		return self._samples_to_sound(samples)
	
	def _samples_to_sound(self, samples):
		"""Convert numpy samples to pygame.Sound.
		
		Args:
			samples: Numpy array of samples (float -1 to 1)
			
		Returns:
			pygame.Sound object
		"""
		mixer_state = pygame.mixer.get_init()
		channels = mixer_state[2] if mixer_state else 1
		# Normalize and convert to 16-bit integers
		samples = np.clip(samples, -1, 1)
		if samples.ndim == 1:
			samples = samples[:, np.newaxis]
		if samples.shape[1] != channels:
			if channels == 2 and samples.shape[1] == 1:
				samples = np.repeat(samples, 2, axis=1)
			else:
				samples = np.tile(samples, (1, max(1, channels)))
		int_samples = (samples * 32767).astype(np.int16, copy=False)
		return pygame.sndarray.make_sound(int_samples)

	def _ensure_bat_squeak_loaded(self):
		if self._bat_squeak_base is not None:
			return
		sample_path = os.path.join(os.path.dirname(__file__), 'resources', 'sounds', 'bat_squeak.mp3')
		if not os.path.isfile(sample_path):
			raise FileNotFoundError(f"Missing bat squeak sample: {sample_path}")
		base_sound = pygame.mixer.Sound(sample_path)
		array = pygame.sndarray.array(base_sound).astype(np.float32)
		if array.ndim == 1:
			array = array[:, np.newaxis]
		max_val = float(np.max(np.abs(array))) if array.size else 0.0
		if max_val > 0:
			array /= max_val
		else:
			array = np.zeros_like(array, dtype=np.float32)
		self._bat_squeak_base = array
		mixer_state = pygame.mixer.get_init()
		if mixer_state:
			self._bat_squeak_rate = mixer_state[0]
			self._bat_squeak_channels = mixer_state[2]
		else:
			self._bat_squeak_rate = self.sample_rate
			self._bat_squeak_channels = array.shape[1]

	def _apply_edge_fade(self, samples: np.ndarray, sample_rate: int, fade_ms: float = 18.0) -> np.ndarray:
		tapered = samples.copy()
		if tapered.size == 0:
			return tapered
		fade_samples = int(sample_rate * (fade_ms / 1000.0))
		fade_samples = max(1, min(fade_samples, tapered.shape[0] // 2))
		if fade_samples <= 0:
			return tapered
		envelope = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
		tapered[:fade_samples] *= envelope[:, np.newaxis]
		tapered[-fade_samples:] *= envelope[::-1][:, np.newaxis]
		return tapered

	def _apply_mild_random_reverb(self, samples: np.ndarray, sample_rate: int, channels: int) -> np.ndarray:
		if samples.size == 0:
			return samples
		delay_ms = random.uniform(35.0, 70.0)
		delay_samples = max(1, int(sample_rate * (delay_ms / 1000.0)))
		tail_multiplier = random.uniform(1.6, 2.4)
		tail_samples = max(delay_samples, int(delay_samples * tail_multiplier))
		length = samples.shape[0] + tail_samples
		output = np.zeros((length, channels), dtype=np.float32)
		output[:samples.shape[0]] += samples
		primary_decay = random.uniform(0.28, 0.42)
		secondary_decay = primary_decay * random.uniform(0.45, 0.7)
		tertiary_decay = secondary_decay * random.uniform(0.35, 0.6)
		first_start = delay_samples
		first_end = min(first_start + samples.shape[0], length)
		output[first_start:first_end] += samples[:first_end - first_start] * primary_decay
		second_start = delay_samples * 2
		if second_start < length:
			second_end = min(second_start + samples.shape[0], length)
			output[second_start:second_end] += samples[:second_end - second_start] * secondary_decay
		third_start = int(delay_samples * 3.2)
		if tertiary_decay > 0.01 and third_start < length:
			third_end = min(third_start + samples.shape[0], length)
			output[third_start:third_end] += samples[:third_end - third_start] * tertiary_decay
		noise_len = length - samples.shape[0]
		if noise_len > 0:
			tail_noise = np.random.normal(0.0, 0.012, (noise_len, channels)).astype(np.float32)
			envelope = np.linspace(1.0, 0.0, noise_len, dtype=np.float32)
			tail_noise *= envelope[:, np.newaxis] * (primary_decay * 0.5)
			output[samples.shape[0]:] += tail_noise
		return output

	def generate_bat_squeak_sample(self):
		"""Load bat_squeak.mp3, vary pitch slightly, and add mild random reverb."""
		self._ensure_bat_squeak_loaded()
		if self._bat_squeak_base is None:
			raise RuntimeError("Bat squeak sample failed to load")
		base = self._bat_squeak_base
		pitch_factor = random.uniform(0.92, 1.08)
		orig_len = base.shape[0]
		target_len = max(1, int(round(orig_len / pitch_factor)))
		orig_idx = np.arange(orig_len, dtype=np.float32)
		target_idx = np.linspace(0, orig_len - 1, target_len, dtype=np.float32)
		stretched = np.zeros((target_len, base.shape[1]), dtype=np.float32)
		for ch in range(base.shape[1]):
			stretched[:, ch] = np.interp(target_idx, orig_idx, base[:, ch])
		segment = self._apply_edge_fade(stretched, self._bat_squeak_rate)
		reverbed = self._apply_mild_random_reverb(segment, self._bat_squeak_rate, self._bat_squeak_channels)
		if reverbed.size == 0:
			reverbed = segment
		max_val = float(np.max(np.abs(reverbed))) if reverbed.size else 0.0
		if max_val > 0:
			reverbed = reverbed / (max_val * 1.15)
		reverbed *= random.uniform(0.7, 0.85)
		reverbed = np.clip(reverbed, -1.0, 1.0)
		return self._samples_to_sound(reverbed)
	
	def pregenerate_sounds(self, variations_per_type=3):
		"""Pre-generate variations of each sound type.
		
		Args:
			variations_per_type: Number of variations to generate for each sound
		"""
		sound_types = [
			('rat_squeak', self.generate_rat_squeak),
			('rat_scurry', self.generate_rat_scurry),
			('bat_screech', self.generate_bat_screech),
			('bat_wings', self.generate_bat_wings),
			('bat_squeak', self.generate_bat_squeak_sample),
			('water_drip', self.generate_water_drip),
			('water_echo', self.generate_water_echo),
			('metal_creak', self.generate_metal_creak),
			('chain_rattle', self.generate_chain_rattle),
			('distant_howl', self.generate_distant_howl),
			('stone_scrape', self.generate_stone_scrape),
		]
		
		for sound_name, generator_func in sound_types:
			self.sounds[sound_name] = []
			for i in range(variations_per_type):
				sound = generator_func()
				self.sounds[sound_name].append(sound)
	
	def play_random(self, sound_type, volume=0.5):
		"""Play a random variation of a sound type.
		
		Args:
			sound_type: Name of sound type (e.g., 'rat_squeak')
			volume: Playback volume (0.0 to 1.0)
		"""
		if sound_type in self.sounds and self.sounds[sound_type]:
			sound = random.choice(self.sounds[sound_type])
			sound.set_volume(volume)
			sound.play()
	
	def get_sound_types(self):
		"""Get list of available sound types.
		
		Returns:
			List of sound type names
		"""
		return list(self.sounds.keys())


class WaterDripSFX:
	"""Scheduler that plays the water-drip MP3 purely as a positional-style sound effect."""

	def __init__(self, sound_generator):
		self.generator = sound_generator
		self.active = False
		self.master_volume = 0.5
		self.interval_range = (9000, 18000)
		self.next_play_time = 0
		self.sample_rate = 22050
		self.channels = 2
		self.base_array = None
		self.output_scale = float(np.iinfo(np.int16).max)
		self._active_sounds: list[tuple[pygame.mixer.Sound, pygame.mixer.Channel]] = []
		self._load_base_sample()

	def _load_base_sample(self):
		"""Load the static water drip sample from disk."""
		init = pygame.mixer.get_init()
		if init:
			self.sample_rate = init[0]
		path = os.path.join(os.path.dirname(__file__), 'resources', 'sounds', 'water_drip.mp3')
		if not os.path.isfile(path):
			raise FileNotFoundError(f"Missing water-drip sample: {path}")
		base_sound = pygame.mixer.Sound(path)
		array = pygame.sndarray.array(base_sound)
		if array.ndim == 1:
			array = array[:, np.newaxis]
		array = array.astype(np.float32)
		max_val = float(np.max(np.abs(array)))
		if max_val == 0:
			max_val = 1.0
		self.base_array = array / max_val
		self.channels = self.base_array.shape[1]

	def _resample_pitch(self, samples: np.ndarray, pitch_factor: float) -> np.ndarray:
		"""Change pitch by resampling the waveform."""
		pitch_factor = max(0.5, min(2.0, pitch_factor))
		orig_len = samples.shape[0]
		target_len = max(1, int(round(orig_len / pitch_factor)))
		orig_idx = np.arange(orig_len)
		target_idx = np.linspace(0, orig_len - 1, target_len)
		resampled = np.zeros((target_len, self.channels), dtype=np.float32)
		for ch in range(self.channels):
			resampled[:, ch] = np.interp(target_idx, orig_idx, samples[:, ch])
		return resampled

	def _apply_reverb(self, samples: np.ndarray, decay: float, pre_delay_ms: float, wet_mix: float) -> np.ndarray:
		"""Apply a diffused cave reverb with early reflections and a soft tail."""
		wet_mix = max(0.0, min(0.7, wet_mix))
		pre_delay_samples = max(0, int(self.sample_rate * (pre_delay_ms / 1000.0)))
		reverb_seconds = 0.9 + decay * 1.1  # tie decay to tail length
		tail_samples = max(1, int(self.sample_rate * reverb_seconds))
		output_len = samples.shape[0] + pre_delay_samples + tail_samples
		output = np.zeros((output_len, self.channels), dtype=np.float32)

		# Dry signal
		dry_mix = 1.0 - wet_mix * 0.4
		output[:samples.shape[0]] += samples * dry_mix

		# Early reflections with slight diffusion instead of discrete echoes
		ref_base_ms = max(25.0, pre_delay_ms)
		reflection_offsets = [ref_base_ms * 0.6, ref_base_ms, ref_base_ms + 32.0, ref_base_ms + 67.0]
		reflection_gains = [0.35, 0.3, 0.22, 0.16]
		for offset_ms, gain in zip(reflection_offsets, reflection_gains):
			offset_samples = int(self.sample_rate * (offset_ms / 1000.0))
			start = offset_samples
			end = start + samples.shape[0]
			if end > output_len:
				break
			output[start:end] += samples * (wet_mix * gain)

		# Diffuse tail using filtered noise shaped by exponential decay
		tail_start = samples.shape[0] + pre_delay_samples
		tail_noise = np.random.normal(0.0, 0.02, (tail_samples, self.channels)).astype(np.float32)
		# Gentle low-pass filter to mimic cavern absorption
		kernel = np.array([0.18, 0.25, 0.28, 0.18, 0.11], dtype=np.float32)
		for ch in range(self.channels):
			tail_noise[:, ch] = np.convolve(tail_noise[:, ch], kernel, mode='same')
		time_axis = np.linspace(0.0, reverb_seconds, tail_samples, dtype=np.float32)
		envelope = np.exp(-time_axis / max(0.25, decay * 1.75))
		tail_noise *= envelope[:, np.newaxis] * (wet_mix * 0.55)
		end_idx = tail_start + tail_samples
		if end_idx > output_len:
			tail_noise = tail_noise[:output_len - tail_start]
			tail_samples = tail_noise.shape[0]
		output[tail_start:tail_start + tail_samples] += tail_noise

		return output

	def _prepare_variant(self) -> pygame.mixer.Sound:
		if self.base_array is None:
			raise RuntimeError("Water-drip sample not loaded")
		pitch = random.uniform(0.94, 1.05)
		reverb_decay = random.uniform(0.55, 0.8)
		pre_delay = random.uniform(85, 150)
		wet_mix = random.uniform(0.38, 0.52)
		samples = self._resample_pitch(self.base_array, pitch)
		samples = self._apply_reverb(samples, reverb_decay, pre_delay, wet_mix)
		samples = np.clip(samples, -1.0, 1.0)
		int_samples = (samples * self.output_scale).astype(np.int16, copy=False)
		return pygame.sndarray.make_sound(int_samples)

	def _cleanup_finished(self):
		if not self._active_sounds:
			return
		alive = []
		for sound, channel in self._active_sounds:
			if channel and channel.get_busy():
				alive.append((sound, channel))
		self._active_sounds = alive

	def _schedule_next(self, current_time: int):
		base_interval = random.randint(*self.interval_range)
		jitter = random.uniform(0.75, 1.35)
		self.next_play_time = current_time + int(base_interval * jitter)

	def _play_drip(self, current_time: int):
		variant = self._prepare_variant()
		channel = variant.play()
		if channel:
			channel.set_volume(self.master_volume)
			self._active_sounds.append((variant, channel))
		self._schedule_next(current_time)

	def update(self, current_time):
		"""Update drip scheduler; should be called each frame."""
		self._cleanup_finished()
		if not self.active or self.base_array is None:
			return
		if self.next_play_time == 0:
			self._schedule_next(current_time)
		elif current_time >= self.next_play_time:
			self._play_drip(current_time)

	def start(self):
		"""Enable randomized playback of the sound effect."""
		self.active = True
		pygame.mixer.set_num_channels(16)
		current_time = pygame.time.get_ticks()
		warmup_delay = random.randint(750, 1750)
		self.next_play_time = current_time + warmup_delay

	def stop(self):
		"""Disable drip playback and halt active sounds."""
		self.active = False
		self.next_play_time = 0
		for _, channel in self._active_sounds:
			if channel:
				channel.stop()
		self._active_sounds.clear()

	def set_master_volume(self, value: float):
		"""Adjust ambient playback volume (0.0 to 1.0)."""
		self.master_volume = max(0.0, min(1.0, float(value)))
		for _, channel in self._active_sounds:
			if channel:
				channel.set_volume(self.master_volume)

	def set_interval_range(self, minimum_ms: int, maximum_ms: int):
		"""Override the interval range between ambience plays."""
		minimum_ms = max(250, int(minimum_ms))
		maximum_ms = max(minimum_ms + 1, int(maximum_ms))
		self.interval_range = (minimum_ms, maximum_ms)


# Global instance
_sound_generator = None
_water_drip_sfx = None

def get_sound_generator():
	"""Get the global sound generator instance."""
	global _sound_generator
	if _sound_generator is None:
		_sound_generator = SoundGenerator()
		_sound_generator.pregenerate_sounds(variations_per_type=3)
	return _sound_generator

def get_water_drip_sfx():
	"""Get the global water-drip sound effect scheduler."""
	global _water_drip_sfx, _sound_generator
	if _water_drip_sfx is None:
		if _sound_generator is None:
			_sound_generator = get_sound_generator()
		_water_drip_sfx = WaterDripSFX(_sound_generator)
	return _water_drip_sfx
