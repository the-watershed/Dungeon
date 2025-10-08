"""
Music system for creating and playing MIDI music in the game.
Handles song creation from JSON definitions and playback control.
"""

import pygame.mixer
import pygame.midi
from midiutil import MIDIFile
import json
import os
import tempfile


class MusicPlayer:
	"""Handles MIDI music creation and playback."""
	
	def __init__(self):
		"""Initialize the music player."""
		self.current_song = None
		self.temp_midi_file = None
		# Don't re-initialize mixer if already initialized
		if not pygame.mixer.get_init():
			pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
		pygame.midi.init()
	
	def load_song_definition(self, json_path):
		"""Load a song definition from a JSON file.
		
		Args:
			json_path: Path to the JSON file containing song data
			
		Returns:
			dict: Song definition data
		"""
		with open(json_path, 'r') as f:
			return json.load(f)
	
	def create_midi_from_definition(self, song_def):
		"""Create a MIDI file from a song definition.
		
		Args:
			song_def: Dictionary containing song data with structure:
				{
					"title": "Song Title",
					"tempo": 120,
					"time_signature": [4, 4],
					"tracks": [
						{
							"name": "Track Name",
							"instrument": 0,  # MIDI instrument number
							"channel": 0,
							"notes": [
								{
									"pitch": 60,  # MIDI note number (60 = middle C)
									"start": 0.0,  # Start time in beats
									"duration": 1.0,  # Duration in beats
									"velocity": 100  # Volume (0-127)
								},
								...
							]
						},
						...
					]
				}
		
		Returns:
			str: Path to created MIDI file
		"""
		# Create MIDI file
		num_tracks = len(song_def.get("tracks", []))
		midi = MIDIFile(num_tracks)
		
		tempo = song_def.get("tempo", 120)
		time_sig = song_def.get("time_signature", [4, 4])
		
		# Set up each track
		for track_idx, track in enumerate(song_def.get("tracks", [])):
			# Set track name and tempo
			midi.addTrackName(track_idx, 0, track.get("name", f"Track {track_idx}"))
			midi.addTempo(track_idx, 0, tempo)
			
			# Set time signature
			midi.addTimeSignature(track_idx, 0, time_sig[0], time_sig[1], 24)
			
			# Set instrument
			channel = track.get("channel", track_idx)
			instrument = track.get("instrument", 0)
			midi.addProgramChange(track_idx, channel, 0, instrument)
			
			# Add notes
			for note in track.get("notes", []):
				midi.addNote(
					track=track_idx,
					channel=channel,
					pitch=note["pitch"],
					time=note["start"],
					duration=note["duration"],
					volume=note["velocity"]
				)
		
		# Write to temporary file
		temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.mid', delete=False)
		midi.writeFile(temp_file)
		temp_file.close()
		
		self.temp_midi_file = temp_file.name
		return temp_file.name
	
	def play_song(self, song_def_path, loops=-1, fade_ms=0):
		"""Load and play a song from its JSON definition.
		
		Args:
			song_def_path: Path to JSON file containing song definition
			loops: Number of times to loop (-1 = infinite)
			fade_ms: Fade in duration in milliseconds
		"""
		# Load song definition
		song_def = self.load_song_definition(song_def_path)
		
		# Create MIDI file
		midi_path = self.create_midi_from_definition(song_def)
		
		# Load and play
		pygame.mixer.music.load(midi_path)
		pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
		
		self.current_song = song_def.get("title", "Unknown")

	def play_midi_file(self, midi_path, loops=-1, fade_ms=0, volume=None):
		"""Play an existing MIDI file from disk.

		Args:
			midi_path: Path to the MIDI file to play
			loops: Number of times to loop (-1 = infinite)
			fade_ms: Fade in duration in milliseconds
			volume: Optional volume override (0.0 to 1.0)
		"""
		if not os.path.isfile(midi_path):
			raise FileNotFoundError(f"MIDI file not found: {midi_path}")
		pygame.mixer.music.load(midi_path)
		if volume is not None:
			pygame.mixer.music.set_volume(max(0.0, min(1.0, float(volume))))
		pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
		self.current_song = os.path.basename(midi_path)
	
	def stop(self, fade_ms=0):
		"""Stop the currently playing music.
		
		Args:
			fade_ms: Fade out duration in milliseconds
		"""
		if fade_ms > 0:
			pygame.mixer.music.fadeout(fade_ms)
		else:
			pygame.mixer.music.stop()
	
	def pause(self):
		"""Pause the currently playing music."""
		pygame.mixer.music.pause()
	
	def unpause(self):
		"""Resume paused music."""
		pygame.mixer.music.unpause()
	
	def set_volume(self, volume):
		"""Set music volume.
		
		Args:
			volume: Volume level (0.0 to 1.0)
		"""
		pygame.mixer.music.set_volume(volume)
	
	def is_playing(self):
		"""Check if music is currently playing.
		
		Returns:
			bool: True if music is playing
		"""
		return pygame.mixer.music.get_busy()
	
	def cleanup(self):
		"""Clean up temporary files."""
		if self.temp_midi_file and os.path.exists(self.temp_midi_file):
			try:
				os.unlink(self.temp_midi_file)
			except:
				pass
		pygame.mixer.quit()
		pygame.midi.quit()


# Global music player instance
_music_player = None

def get_music_player():
	"""Get the global music player instance."""
	global _music_player
	if _music_player is None:
		_music_player = MusicPlayer()
	return _music_player
