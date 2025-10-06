"""
Procedural sound generation for dungeon ambience.
Creates atmospheric sounds like rats, bats, water droplets, and metal squeaking.
"""

import pygame
import numpy as np
import random
import math


class SoundGenerator:
	"""Generates procedural sounds for dungeon ambience."""
	
	def __init__(self, sample_rate=22050):
		"""Initialize the sound generator.
		
		Args:
			sample_rate: Audio sample rate in Hz (default: 22050)
		"""
		self.sample_rate = sample_rate
		# Don't re-initialize mixer if already initialized (to avoid conflicts with music system)
		if not pygame.mixer.get_init():
			pygame.mixer.init(frequency=sample_rate, size=-16, channels=2, buffer=512)
		self.sounds = {}
	
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
	
	def _samples_to_sound(self, samples):
		"""Convert numpy samples to pygame.Sound.
		
		Args:
			samples: Numpy array of samples (float -1 to 1)
			
		Returns:
			pygame.Sound object
		"""
		# Normalize and convert to 16-bit integers
		samples = np.clip(samples, -1, 1)
		samples = (samples * 32767).astype(np.int16)
		
		# Convert to bytes
		sound_bytes = samples.tobytes()
		
		# Create pygame sound
		sound = pygame.mixer.Sound(buffer=sound_bytes)
		return sound
	
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


class AmbiencePlayer:
	"""Manages ambient sound playback with random timing."""
	
	def __init__(self, sound_generator):
		"""Initialize ambience player.
		
		Args:
			sound_generator: SoundGenerator instance
		"""
		self.generator = sound_generator
		self.active = False
		self.ambience_config = {
			'rat_squeak': {'probability': 0.05, 'volume': 0.5},
			'rat_scurry': {'probability': 0.03, 'volume': 0.475},
			'bat_screech': {'probability': 0.04, 'volume': 0.475},
			'bat_wings': {'probability': 0.03, 'volume': 0.45},
			'water_drip': {'probability': 0.08, 'volume': 0.5},
			'water_echo': {'probability': 0.02, 'volume': 0.475},
			'metal_creak': {'probability': 0.02, 'volume': 0.5},
			'chain_rattle': {'probability': 0.01, 'volume': 0.475},
			'distant_howl': {'probability': 0.005, 'volume': 0.35},
			'stone_scrape': {'probability': 0.01, 'volume': 0.45},
		}
		self.last_check = 0
		self.check_interval = 1000  # Check every 1000ms
	
	def update(self, current_time):
		"""Update ambience (call each frame).
		
		Args:
			current_time: Current time in milliseconds
		"""
		if not self.active:
			return
		
		if current_time - self.last_check >= self.check_interval:
			self.last_check = current_time
			
			# Check each sound type
			for sound_type, config in self.ambience_config.items():
				if random.random() < config['probability']:
					self.generator.play_random(sound_type, config['volume'])
					print(f"[AMBIENCE] Playing {sound_type} at volume {config['volume']}")
	
	def start(self):
		"""Start playing ambient sounds."""
		self.active = True
		# Ensure enough channels for simultaneous sounds
		pygame.mixer.set_num_channels(16)
		print(f"[AMBIENCE] Started! Mixer status: {pygame.mixer.get_init()}")
		# Play a test sound immediately to verify audio is working
		self.generator.play_random('water_drip', 0.8)
		print("[AMBIENCE] Test sound played (water drip)")
	
	def stop(self):
		"""Stop playing ambient sounds."""
		self.active = False
	
	def set_sound_probability(self, sound_type, probability):
		"""Adjust probability of a sound type.
		
		Args:
			sound_type: Name of sound type
			probability: Probability per check (0.0 to 1.0)
		"""
		if sound_type in self.ambience_config:
			self.ambience_config[sound_type]['probability'] = probability


# Global instance
_sound_generator = None
_ambience_player = None

def get_sound_generator():
	"""Get the global sound generator instance."""
	global _sound_generator
	if _sound_generator is None:
		_sound_generator = SoundGenerator()
		_sound_generator.pregenerate_sounds(variations_per_type=3)
	return _sound_generator

def get_ambience_player():
	"""Get the global ambience player instance."""
	global _ambience_player, _sound_generator
	if _ambience_player is None:
		if _sound_generator is None:
			_sound_generator = get_sound_generator()
		_ambience_player = AmbiencePlayer(_sound_generator)
	return _ambience_player
