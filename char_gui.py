"""
AD&D 2nd Edition Character Creator - Pygame GUI Version
Complete character creation with all races, classes, and equipment
Integrates with main dungeon game
Uses same parchment renderer and fonts as the main game
"""

import os
import sys
import json
import random
import pygame
from typing import Dict, List, Optional, Tuple
from parchment_renderer import ParchmentRenderer

# Character Class
class Character:
    def __init__(self):
        self.name: str = ""
        self.race: str = ""
        self.char_class: str = ""
        self.alignment: str = ""
        self.level: int = 1
        
        # Ability scores
        self.strength: int = 0
        self.dexterity: int = 0
        self.constitution: int = 0
        self.intelligence: int = 0
        self.wisdom: int = 0
        self.charisma: int = 0
        
        # Combat stats
        self.max_hp: int = 0
        self.current_hp: int = 0
        self.armor_class: int = 10
        self.thac0: int = 20
        
        # Resources
        self.gold: int = 0
        self.xp: int = 0
        self.equipment: List[str] = []
        self.weight_carried: float = 0.0
        self.racial_abilities: List[str] = []
    
    def save_character(self):
        """Save character to JSON file"""
        saves_dir = "saves"
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir)
        
        data = {
            'name': self.name,
            'race': self.race,
            'class': self.char_class,
            'level': self.level,
            'xp': self.xp,
            'strength': self.strength,
            'dexterity': self.dexterity,
            'constitution': self.constitution,
            'intelligence': self.intelligence,
            'wisdom': self.wisdom,
            'charisma': self.charisma,
            'max_hp': self.max_hp,
            'current_hp': self.current_hp,
            'armor_class': self.armor_class,
            'thac0': self.thac0,
            'alignment': self.alignment,
            'gold': self.gold,
            'equipment': self.equipment,
            'weight_carried': self.weight_carried,
            'racial_abilities': self.racial_abilities
        }
        
        filepath = os.path.join(saves_dir, f"{self.name}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

# Game Data
RACES = {
    "Human": {
        "modifiers": {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0},
        "abilities": ["Extra language", "Dual-class ability"]
    },
    "Elf": {
        "modifiers": {"str": 0, "dex": 1, "con": -1, "int": 0, "wis": 0, "cha": 0},
        "abilities": ["Infravision 60'", "Detect secret doors", "Bow bonus", "Sword bonus"]
    },
    "Dwarf": {
        "modifiers": {"str": 0, "dex": 0, "con": 1, "int": 0, "wis": 0, "cha": -1},
        "abilities": ["Infravision 60'", "Magic resistance", "Detect slopes/traps", "Combat bonus vs giants"]
    },
    "Halfling": {
        "modifiers": {"str": -1, "dex": 1, "con": 0, "int": 0, "wis": 0, "cha": 0},
        "abilities": ["Infravision 30'", "Stealth bonus", "Sling/thrown weapon bonus", "Magic resistance"]
    },
    "Half-Elf": {
        "modifiers": {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0},
        "abilities": ["Infravision 60'", "Detect secret doors", "Charm resistance"]
    },
    "Gnome": {
        "modifiers": {"str": 0, "dex": 0, "con": 1, "int": 0, "wis": 0, "cha": 0},
        "abilities": ["Infravision 60'", "Detect slopes/traps", "Gnome magic", "Combat bonus vs kobolds/goblins"]
    },
    "Half-Orc": {
        "modifiers": {"str": 1, "dex": 0, "con": 1, "int": -2, "wis": 0, "cha": -2},
        "abilities": ["Infravision 60'", "Strength bonus", "Constitution bonus"]
    }
}

CLASSES = {
    "Fighter": {"hit_die": 10, "starting_gold": (5, 4, 0), "thac0": 20},
    "Mage": {"hit_die": 4, "starting_gold": (1, 4, 0), "thac0": 20},
    "Cleric": {"hit_die": 8, "starting_gold": (3, 6, 0), "thac0": 20},
    "Thief": {"hit_die": 6, "starting_gold": (2, 6, 0), "thac0": 20},
    "Ranger": {"hit_die": 10, "starting_gold": (5, 4, 0), "thac0": 20},
    "Paladin": {"hit_die": 10, "starting_gold": (5, 4, 0), "thac0": 20},
    "Druid": {"hit_die": 8, "starting_gold": (3, 6, 0), "thac0": 20},
    "Bard": {"hit_die": 6, "starting_gold": (3, 6, 0), "thac0": 20}
}

EQUIPMENT = {
    "Weapons": {
        "Dagger": {"cost": 2, "weight": 1, "damage": "1d4"},
        "Short Sword": {"cost": 10, "weight": 3, "damage": "1d6"},
        "Long Sword": {"cost": 15, "weight": 4, "damage": "1d8"},
        "Bastard Sword": {"cost": 25, "weight": 6, "damage": "1d10"},
        "Two-Handed Sword": {"cost": 50, "weight": 15, "damage": "1d10"},
        "Hand Axe": {"cost": 1, "weight": 5, "damage": "1d6"},
        "Battle Axe": {"cost": 5, "weight": 7, "damage": "1d8"},
        "War Hammer": {"cost": 2, "weight": 6, "damage": "1d4+1"},
        "Mace": {"cost": 8, "weight": 8, "damage": "1d6+1"},
        "Spear": {"cost": 1, "weight": 5, "damage": "1d6"},
        "Quarterstaff": {"cost": 1, "weight": 4, "damage": "1d6"},
        "Club": {"cost": 0, "weight": 3, "damage": "1d4"},
        "Short Bow": {"cost": 30, "weight": 2, "damage": "1d6"},
        "Long Bow": {"cost": 75, "weight": 3, "damage": "1d8"},
        "Light Crossbow": {"cost": 35, "weight": 7, "damage": "1d4"},
        "Sling": {"cost": 1, "weight": 0, "damage": "1d4"},
    },
    "Armor": {
        "Leather Armor": {"cost": 5, "weight": 15, "ac": 8},
        "Studded Leather": {"cost": 20, "weight": 25, "ac": 7},
        "Ring Mail": {"cost": 100, "weight": 30, "ac": 7},
        "Scale Mail": {"cost": 120, "weight": 40, "ac": 6},
        "Chain Mail": {"cost": 150, "weight": 40, "ac": 5},
        "Splint Mail": {"cost": 200, "weight": 45, "ac": 4},
        "Plate Mail": {"cost": 600, "weight": 50, "ac": 3},
        "Shield": {"cost": 10, "weight": 10, "ac": -1},
    },
    "Gear": {
        "Backpack": {"cost": 2, "weight": 2},
        "Bedroll": {"cost": 1, "weight": 5},
        "Rope (50ft)": {"cost": 1, "weight": 8},
        "Torches (6)": {"cost": 1, "weight": 6},
        "Lantern": {"cost": 7, "weight": 3},
        "Oil Flask": {"cost": 1, "weight": 1},
        "Waterskin": {"cost": 1, "weight": 4},
        "Rations (7 days)": {"cost": 5, "weight": 7},
        "Thieves' Tools": {"cost": 30, "weight": 1},
        "Holy Symbol": {"cost": 25, "weight": 0},
        "Spellbook": {"cost": 15, "weight": 3},
        "Tent": {"cost": 5, "weight": 20},
    },
    "Potions": {
        "Healing Potion": {"cost": 50, "weight": 0.5},
        "Antidote": {"cost": 25, "weight": 0.5},
    }
}

# Utility Functions
def roll_dice(num_dice: int, die_size: int, modifier: int = 0) -> int:
    """Roll dice and return total"""
    total = sum(random.randint(1, die_size) for _ in range(num_dice))
    return total + modifier

def roll_ability_scores() -> Dict[str, int]:
    """Roll 4d6 drop lowest for each ability"""
    def roll_one():
        rolls = [random.randint(1, 6) for _ in range(4)]
        rolls.remove(min(rolls))
        return sum(rolls)
    
    return {
        'str': roll_one(),
        'dex': roll_one(),
        'con': roll_one(),
        'int': roll_one(),
        'wis': roll_one(),
        'cha': roll_one()
    }

# Pygame GUI Settings - Match game window exactly
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 600
# Use game's parchment colors
PARCHMENT_BG = (74, 71, 65)  # 3/10 brightness level (matches game)
INK_DARK = (40, 28, 18)       # Dark ink for text
TEXT_COLOR = (245, 237, 215)  # Light parchment
HIGHLIGHT_COLOR = (200, 170, 120)  # Gold (matches WALL_LIGHT)
DIM_COLOR = (140, 130, 120)  # Dimmed text
INPUT_COLOR = (255, 255, 100)  # Yellow for input
ERROR_COLOR = (255, 100, 100)  # Red for errors
# Font sizes optimized for 1000x600 window
CELL_HEIGHT = 15  # Match game's cell height for font building

class CharacterCreatorGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AD&D 2nd Edition Character Creator")
        self.clock = pygame.time.Clock()
        
        # Build font using game's font system (single font size like the game)
        self.font = self._build_font(CELL_HEIGHT)
        
        # Generate parchment background using game's renderer
        # Use 10 pixel grain tile to align with character cell width (BASE_CELL_W = 10)
        parchment_renderer = ParchmentRenderer(base_color=PARCHMENT_BG, ink_color=INK_DARK, enable_vignette=False, grain_tile=10)
        parchment_renderer.build_layers(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.parchment_bg = parchment_renderer.generate(WINDOW_WIDTH, WINDOW_HEIGHT)
    
    def _build_font(self, ch_h: int) -> pygame.font.Font:
        """Build optimal font for given cell height (matches game's font building).
        
        Args:
            ch_h (int): Cell height in pixels
            
        Returns:
            pygame.font.Font: Font object optimized for the cell size
        """
        preferred_fonts = ["Courier New", "Consolas", "Lucida Console", "DejaVu Sans Mono", "Monaco"]
        max_size = max(6, min(48, ch_h))
        cell_w = 10  # Approximate cell width for character creator
        
        candidates = []
        # Always prioritize Blocky Sketch.ttf
        import os
        blocky_sketch_path = os.path.join(os.path.dirname(__file__), "Blocky Sketch.ttf")
        if os.path.isfile(blocky_sketch_path):
            candidates.append(("file", blocky_sketch_path))
        for fam in preferred_fonts:
            candidates.append(("sys", fam))
        
        best = None
        for size in range(max_size, 5, -1):
            for kind, ident in candidates:
                try:
                    f = pygame.font.Font(ident, size) if kind == "file" else pygame.font.SysFont(ident, size)
                    # Measure a wide sample to ensure width/height fit in cell
                    sample = "W#@"
                    surf = f.render(sample, False, (255, 255, 255))
                    gw = surf.get_width() // len(sample)
                    gh = surf.get_height()
                    if gw <= cell_w - 1 and gh <= ch_h - 1:
                        return f
                    # Track last font in case nothing fits
                    if best is None:
                        best = f
                except Exception:
                    continue
        # Fallback
        return best or pygame.font.Font(None, max(6, ch_h - 4))
        
    def draw_text(self, text, x, y, color=TEXT_COLOR, font=None, center=False):
        """Draw text on screen"""
        if font is None:
            font = self.font
        text_surface = font.render(text, True, color)
        if center:
            text_rect = text_surface.get_rect(center=(x, y))
            self.screen.blit(text_surface, text_rect)
        else:
            self.screen.blit(text_surface, (x, y))
        return text_surface.get_height()
    
    def draw_box(self, x, y, width, height, border_color=TEXT_COLOR):
        """Draw a bordered box"""
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), 2)
    
    def draw_title(self, title):
        """Draw centered title at top"""
        self.draw_text(title, WINDOW_WIDTH // 2, 30, HIGHLIGHT_COLOR, self.font, center=True)
    
    def wait_for_key(self):
        """Wait for any key press"""
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    return True
            self.clock.tick(60)
        return False
    
    def get_text_input(self, prompt, y_pos, max_length=20, allow_empty=False):
        """Get text input from user"""
        input_text = ""
        active = True
        
        while active:
            self.screen.blit(self.parchment_bg, (0, 0))
            self.draw_title("Character Creation")
            
            # Draw prompt
            self.draw_text(prompt, 50, y_pos)
            
            # Draw input box
            box_y = y_pos + 30
            self.draw_box(50, box_y, 500, 35, HIGHLIGHT_COLOR)
            self.draw_text(input_text + "|", 60, box_y + 8, INPUT_COLOR)
            
            self.draw_text("Press Enter to confirm, Escape to cancel", 50, box_y + 50, DIM_COLOR, self.font)
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if input_text or allow_empty:
                            return input_text
                    elif event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif event.unicode and len(input_text) < max_length:
                        input_text += event.unicode
            
            self.clock.tick(60)
        
        return None
    
    def show_menu(self, title, options, descriptions=None):
        """Show a menu and return selected option index"""
        selected = 0
        scroll_offset = 0
        max_visible = 12  # Maximum items visible at once (reduced for 600px height)
        
        while True:
            self.screen.blit(self.parchment_bg, (0, 0))
            self.draw_title(title)
            
            # Draw instructions
            y = 70
            self.draw_text("UP/DOWN: navigate | Enter: select | Esc: cancel", 
                          50, y, DIM_COLOR, self.font)
            y += 35
            
            # Calculate visible range
            if selected < scroll_offset:
                scroll_offset = selected
            elif selected >= scroll_offset + max_visible:
                scroll_offset = selected - max_visible + 1
            
            # Draw menu options
            for i in range(scroll_offset, min(len(options), scroll_offset + max_visible)):
                color = HIGHLIGHT_COLOR if i == selected else TEXT_COLOR
                prefix = "► " if i == selected else "  "
                self.draw_text(f"{prefix}{i+1}. {options[i]}", 50, y, color)
                
                # Draw description if available
                if descriptions and i < len(descriptions) and descriptions[i]:
                    self.draw_text(descriptions[i], 70, y + 20, DIM_COLOR, self.font)
                    y += 42
                else:
                    y += 28
            
            # Draw scroll indicators
            if scroll_offset > 0:
                self.draw_text("▲ More above", 50, 105, DIM_COLOR, self.font)
            if scroll_offset + max_visible < len(options):
                self.draw_text("▼ More below", 50, WINDOW_HEIGHT - 30, DIM_COLOR, self.font)
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected = (selected - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(options)
                    elif event.key == pygame.K_RETURN:
                        return selected
                    elif event.key == pygame.K_ESCAPE:
                        return None
            
            self.clock.tick(60)
    
    def show_info_screen(self, title, lines, wait_for_key=True):
        """Show an information screen with multiple lines"""
        self.screen.blit(self.parchment_bg, (0, 0))
        self.draw_title(title)
        
        y = 80
        for line in lines:
            if line.startswith(">>>"):
                # Highlight line
                self.draw_text(line[3:].strip(), 50, y, HIGHLIGHT_COLOR)
            elif line.startswith("---"):
                # Separator
                pygame.draw.line(self.screen, TEXT_COLOR, (50, y + 10), (WINDOW_WIDTH - 50, y + 10), 2)
            else:
                self.draw_text(line, 50, y)
            y += 24
        
        if wait_for_key:
            self.draw_text("Press any key to continue...", WINDOW_WIDTH // 2, WINDOW_HEIGHT - 30, 
                          DIM_COLOR, self.font, center=True)
        
        pygame.display.flip()
        
        if wait_for_key:
            return self.wait_for_key()
        return True
    
    def run(self):
        """Main character creator flow"""
        # Go directly to character selection screen (Create New, Random, or Load)
        character = self.check_existing_characters()
        if character:
            return character
        
        # Create new character (if "Create New Character" was selected)
        character = self.create_new_character()
        return character
    
    def check_existing_characters(self):
        """Check for existing saved characters"""
        saves_dir = "saves"
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir)
        
        save_files = [f for f in os.listdir(saves_dir) if f.endswith('.json')]
        
        # Show load menu with Random Character option
        options = ["Create New Character", "Random Level 1 Character"]
        descriptions = ["Start fresh with a new character", "Generate a random ready-to-play character"]
        
        if save_files:
            options.extend([f[:-5] for f in save_files])  # Remove .json
            descriptions.extend(["Load existing character"] * len(save_files))
        
        choice = self.show_menu("Character Selection", options, descriptions)
        
        if choice is None:
            return None
        elif choice == 0:
            return None  # Create new
        elif choice == 1:
            # Generate random character
            return self.generate_random_character()
        else:
            # Load existing character
            filename = save_files[choice - 2]  # Adjust for two new options at start
            character = self.load_character(os.path.join(saves_dir, filename))
            if character:
                self.show_info_screen("Character Loaded", [
                    f"Successfully loaded: {character.name}",
                    f"Race: {character.race}",
                    f"Class: {character.char_class}",
                    f"Level: {character.level}",
                    f"HP: {character.max_hp}",
                ])
            return character
    
    def load_character(self, filepath):
        """Load character from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            character = Character()
            character.name = data['name']
            character.race = data['race']
            character.char_class = data['class']
            character.level = data['level']
            character.xp = data['xp']
            character.strength = data['strength']
            character.dexterity = data['dexterity']
            character.constitution = data['constitution']
            character.intelligence = data['intelligence']
            character.wisdom = data['wisdom']
            character.charisma = data['charisma']
            character.max_hp = data['max_hp']
            character.current_hp = data['current_hp']
            character.armor_class = data['armor_class']
            character.thac0 = data['thac0']
            character.alignment = data['alignment']
            character.gold = data['gold']
            character.equipment = data['equipment']
            character.weight_carried = data['weight_carried']
            character.racial_abilities = data.get('racial_abilities', [])
            return character
        except Exception as e:
            self.show_info_screen("Error", [f"Failed to load character: {e}"])
            return None
    
    def create_new_character(self):
        """Create a new character through the full process"""
        character = Character()
        
        # Step 1: Choose race
        if not self.step_choose_race(character):
            return None
        
        # Step 2: Roll abilities
        if not self.step_roll_abilities(character):
            return None
        
        # Step 3: Choose class
        if not self.step_choose_class(character):
            return None
        
        # Step 4: Choose alignment
        if not self.step_choose_alignment(character):
            return None
        
        # Step 5: Purchase equipment
        if not self.step_purchase_equipment(character):
            return None
        
        # Step 6: Name character
        if not self.step_name_character(character):
            return None
        
        # Step 7: Review and save
        if not self.step_review_and_save(character):
            return None
        
        return character
    
    def generate_random_character(self):
        """Generate a random level 1 character with random race, class, equipment, and name"""
        character = Character()
        
        # Random race
        character.race = random.choice(list(RACES.keys()))
        race_data = RACES[character.race]
        character.racial_abilities = race_data['abilities']
        
        # Roll abilities with racial modifiers
        rolls = roll_ability_scores()
        race_mods = race_data['modifiers']
        for stat, mod in race_mods.items():
            if stat in rolls:
                rolls[stat] += mod
        
        character.strength = rolls['str']
        character.dexterity = rolls['dex']
        character.constitution = rolls['con']
        character.intelligence = rolls['int']
        character.wisdom = rolls['wis']
        character.charisma = rolls['cha']
        
        # Random class
        character.char_class = random.choice(list(CLASSES.keys()))
        class_data = CLASSES[character.char_class]
        
        # Roll HP
        character.max_hp = roll_dice(1, class_data['hit_die'])
        character.current_hp = character.max_hp
        
        # Set THAC0
        character.thac0 = class_data['thac0']
        
        # Roll starting gold
        character.gold = roll_dice(*class_data['starting_gold'])
        
        # Random alignment
        alignments = [
            "Lawful Good", "Neutral Good", "Chaotic Good",
            "Lawful Neutral", "True Neutral", "Chaotic Neutral",
            "Lawful Evil", "Neutral Evil", "Chaotic Evil"
        ]
        character.alignment = random.choice(alignments)
        
        # Auto-buy essential equipment based on class
        starting_gold = character.gold
        self._buy_random_equipment(character)
        
        # Generate random name
        character.name = self._generate_random_name(character.race)
        
        # Show generated character
        lines = [
            "=== RANDOM CHARACTER GENERATED ===",
            "",
            f">>> {character.name}",
            f"Race: {character.race}",
            f"Class: {character.char_class}",
            f"Alignment: {character.alignment}",
            "",
            "Ability Scores:",
            f"  STR: {character.strength}  DEX: {character.dexterity}  CON: {character.constitution}",
            f"  INT: {character.intelligence}  WIS: {character.wisdom}  CHA: {character.charisma}",
            "",
            f"Hit Points: {character.current_hp}/{character.max_hp}",
            f"Armor Class: {character.armor_class}",
            f"THAC0: {character.thac0}",
            f"Starting Gold: {starting_gold} gp",
            f"Remaining Gold: {character.gold} gp",
            "",
            f"Equipment ({len(character.equipment)} items):",
        ]
        
        for item in character.equipment[:10]:
            lines.append(f"  • {item}")
        if len(character.equipment) > 10:
            lines.append(f"  ... and {len(character.equipment) - 10} more")
        
        if not self.show_info_screen("Random Character", lines):
            return None
        
        # Save character
        character.save_character()
        
        self.show_info_screen("Character Saved", 
                             [f"Character saved successfully!",
                              f"File: saves/{character.name}.json"])
        
        return character
    
    def _buy_random_equipment(self, character):
        """Auto-purchase essential equipment based on class and available gold"""
        # Essential items everyone should have
        essentials = [
            ("Gear", "Backpack"),
            ("Gear", "Rope (50ft)"),
            ("Gear", "Torches (6)"),
            ("Gear", "Waterskin"),
            ("Gear", "Rations (7 days)"),
        ]
        
        # Try to buy essentials first
        for category, item_name in essentials:
            if category in EQUIPMENT and item_name in EQUIPMENT[category]:
                item_data = EQUIPMENT[category][item_name]
                if character.gold >= item_data['cost']:
                    character.gold -= item_data['cost']
                    character.equipment.append(item_name)
                    character.weight_carried += item_data['weight']
        
        # Class-specific equipment
        class_equipment = {
            "Fighter": [("Weapons", "Long Sword"), ("Weapons", "Shield"), ("Armor", "Chain Mail")],
            "Ranger": [("Weapons", "Long Bow"), ("Weapons", "Arrows (20)"), ("Weapons", "Long Sword"), ("Armor", "Leather Armor")],
            "Paladin": [("Weapons", "Long Sword"), ("Weapons", "Shield"), ("Armor", "Plate Mail"), ("Gear", "Holy Symbol")],
            "Mage": [("Weapons", "Dagger"), ("Gear", "Spellbook")],
            "Cleric": [("Weapons", "Mace"), ("Weapons", "Shield"), ("Armor", "Chain Mail"), ("Gear", "Holy Symbol")],
            "Druid": [("Weapons", "Quarterstaff"), ("Armor", "Leather Armor"), ("Gear", "Holy Symbol")],
            "Thief": [("Weapons", "Short Sword"), ("Weapons", "Dagger"), ("Armor", "Leather Armor"), ("Gear", "Thieves' Tools")],
            "Bard": [("Weapons", "Rapier"), ("Armor", "Leather Armor")],
        }
        
        # Buy class-specific items
        if character.char_class in class_equipment:
            for category, item_name in class_equipment[character.char_class]:
                if category in EQUIPMENT and item_name in EQUIPMENT[category]:
                    item_data = EQUIPMENT[category][item_name]
                    if character.gold >= item_data['cost']:
                        character.gold -= item_data['cost']
                        character.equipment.append(item_name)
                        character.weight_carried += item_data['weight']
                        
                        # Update AC if armor
                        if 'ac' in item_data:
                            if item_name == "Shield":
                                character.armor_class += item_data['ac']  # Shield bonus
                            else:
                                character.armor_class = min(character.armor_class, item_data['ac'])
        
        # If still have gold, try to buy a healing potion
        if character.gold >= 50:
            character.gold -= 50
            character.equipment.append("Healing Potion")
            character.weight_carried += 0.5
    
    def _generate_random_name(self, race):
        """Generate a random fantasy name based on race"""
        # Name components by race
        names = {
            "Human": {
                "male": ["Aldric", "Bran", "Cedric", "Drake", "Edwin", "Gareth", "Hugh", "Ivan", "Jorah", "Kael"],
                "female": ["Aria", "Brenna", "Cara", "Diana", "Elena", "Fiona", "Gwen", "Helena", "Iris", "Jenna"],
            },
            "Elf": {
                "male": ["Arannis", "Celeborn", "Elrond", "Fingolfin", "Galadhon", "Haldir", "Legolas", "Thranduil"],
                "female": ["Arwen", "Celebrian", "Galadriel", "Luthien", "Nessa", "Silmaril", "Tauriel", "Yavanna"],
            },
            "Dwarf": {
                "male": ["Balin", "Borin", "Dain", "Durin", "Gimli", "Gloin", "Thorin", "Thrain", "Throrin"],
                "female": ["Dis", "Katrin", "Moria", "Nara", "Orna", "Runa", "Thyra", "Vigdis"],
            },
            "Halfling": {
                "male": ["Bilbo", "Drogo", "Frodo", "Merry", "Pippin", "Samwise", "Took", "Brandybuck"],
                "female": ["Belladonna", "Daisy", "Lobelia", "Poppy", "Primula", "Rose", "Ruby"],
            },
            "Half-Elf": {
                "male": ["Aeron", "Corwin", "Eldrin", "Faelin", "Galadin", "Taliesin", "Taranthir"],
                "female": ["Aeris", "Celeste", "Elanor", "Lirien", "Myriel", "Sariel", "Thalya"],
            },
            "Gnome": {
                "male": ["Alston", "Boddynock", "Dimble", "Eldon", "Fonkin", "Gimble", "Jebeddo", "Namfoodle"],
                "female": ["Bimpnottin", "Caramip", "Donella", "Duvamil", "Ella", "Loopmottin", "Mardnab"],
            },
            "Half-Orc": {
                "male": ["Dench", "Feng", "Gell", "Henk", "Holg", "Imsh", "Keth", "Mhurren", "Ront", "Thokk"],
                "female": ["Baggi", "Emen", "Engong", "Kansif", "Myev", "Neega", "Ovak", "Ownka", "Vola"],
            }
        }
        
        # Pick random gender and name
        if race in names:
            gender = random.choice(["male", "female"])
            return random.choice(names[race][gender])
        else:
            # Fallback generic name
            return random.choice(["Adventurer", "Wanderer", "Hero", "Champion", "Seeker"])
    
    def step_choose_race(self, character):
        """Step 1: Choose race"""
        race_names = list(RACES.keys())
        descriptions = []
        
        for race in race_names:
            race_data = RACES[race]
            mods = []
            for stat, mod in race_data['modifiers'].items():
                if mod > 0:
                    mods.append(f"+{mod} {stat.upper()}")
                elif mod < 0:
                    mods.append(f"{mod} {stat.upper()}")
            desc = ", ".join(mods) if mods else "No modifiers"
            descriptions.append(desc)
        
        choice = self.show_menu("Choose Your Race", race_names, descriptions)
        
        if choice is None:
            return False
        
        character.race = race_names[choice]
        
        # Show race details
        race_data = RACES[character.race]
        lines = [
            f"You have chosen: {character.race}",
            "",
            "Racial Abilities:",
        ]
        for ability in race_data['abilities']:
            lines.append(f"  • {ability}")
        
        return self.show_info_screen("Race Selected", lines)
    
    def step_roll_abilities(self, character):
        """Step 2: Roll ability scores"""
        rolls = roll_ability_scores()
        
        # Apply racial modifiers
        race_mods = RACES[character.race]['modifiers']
        for stat, mod in race_mods.items():
            if stat in rolls:
                rolls[stat] += mod
        
        character.strength = rolls['str']
        character.dexterity = rolls['dex']
        character.constitution = rolls['con']
        character.intelligence = rolls['int']
        character.wisdom = rolls['wis']
        character.charisma = rolls['cha']
        
        lines = [
            "Your ability scores have been rolled!",
            "",
            f">>> Strength:     {character.strength}",
            f">>> Dexterity:    {character.dexterity}",
            f">>> Constitution: {character.constitution}",
            f">>> Intelligence: {character.intelligence}",
            f">>> Wisdom:       {character.wisdom}",
            f">>> Charisma:     {character.charisma}",
            "",
            "(Racial modifiers already applied)",
        ]
        
        return self.show_info_screen("Ability Scores", lines)
    
    def step_choose_class(self, character):
        """Step 3: Choose class"""
        class_names = list(CLASSES.keys())
        descriptions = []
        
        for cls in class_names:
            cls_data = CLASSES[cls]
            desc = f"Hit Die: {cls_data['hit_die']}, Start Gold: {cls_data['starting_gold']}"
            descriptions.append(desc)
        
        choice = self.show_menu("Choose Your Class", class_names, descriptions)
        
        if choice is None:
            return False
        
        character.char_class = class_names[choice]
        class_data = CLASSES[character.char_class]
        
        # Roll HP
        character.max_hp = roll_dice(1, class_data['hit_die'])
        character.current_hp = character.max_hp
        
        # Set THAC0
        character.thac0 = class_data['thac0']
        
        # Roll starting gold
        character.gold = roll_dice(*class_data['starting_gold'])
        
        lines = [
            f"You have chosen: {character.char_class}",
            "",
            f">>> Hit Points: {character.max_hp}",
            f">>> THAC0: {character.thac0}",
            f">>> Starting Gold: {character.gold} gp",
        ]
        
        return self.show_info_screen("Class Selected", lines)
    
    def step_choose_alignment(self, character):
        """Step 4: Choose alignment"""
        alignments = [
            "Lawful Good", "Neutral Good", "Chaotic Good",
            "Lawful Neutral", "True Neutral", "Chaotic Neutral",
            "Lawful Evil", "Neutral Evil", "Chaotic Evil"
        ]
        
        descriptions = [
            "Crusader, follows law and good",
            "Benefactor, does good without extremes",
            "Rebel, freedom and good heart",
            "Judge, follows law strictly",
            "Undecided, true balance",
            "Free spirit, values freedom",
            "Dominator, uses law for evil",
            "Malefactor, selfish evil",
            "Destroyer, chaotic and evil"
        ]
        
        choice = self.show_menu("Choose Your Alignment", alignments, descriptions)
        
        if choice is None:
            return False
        
        character.alignment = alignments[choice]
        
        return self.show_info_screen("Alignment Selected", 
                                     [f"Your alignment: {character.alignment}"])
    
    def step_purchase_equipment(self, character):
        """Step 5: Purchase equipment"""
        shopping = True
        
        while shopping:
            self.screen.blit(self.parchment_bg, (0, 0))
            self.draw_title("Equipment Shop")
            
            # Show current status
            y = 80
            self.draw_text(f"Gold: {character.gold} gp", 50, y, HIGHLIGHT_COLOR)
            self.draw_text(f"Weight: {character.weight_carried} lbs", 250, y, HIGHLIGHT_COLOR)
            y += 35
            
            # Show equipment menu
            categories = list(EQUIPMENT.keys())
            options = categories + ["Finish Shopping"]
            
            choice = self.show_menu("Select Category", options)
            
            if choice is None or choice == len(categories):
                shopping = False
            else:
                category = categories[choice]
                self.shop_category(character, category)
        
        return True
    
    def shop_category(self, character, category):
        """Shop in a specific equipment category"""
        items = EQUIPMENT[category]
        
        while True:
            # Build item list
            item_names = []
            descriptions = []
            
            for item_name, item_data in items.items():
                item_names.append(item_name)
                desc = f"{item_data['cost']} gp, {item_data['weight']} lbs"
                if 'damage' in item_data:
                    desc += f", Damage: {item_data['damage']}"
                if 'ac' in item_data:
                    desc += f", AC: {item_data['ac']}"
                descriptions.append(desc)
            
            item_names.append("Back")
            descriptions.append("Return to categories")
            
            choice = self.show_menu(f"{category} Shop", item_names, descriptions)
            
            if choice is None or choice == len(items):
                return
            
            # Purchase item
            item_name = item_names[choice]
            item_data = items[item_name]
            
            if character.gold >= item_data['cost']:
                character.gold -= item_data['cost']
                character.equipment.append(item_name)
                character.weight_carried += item_data['weight']
                
                # Update AC if armor
                if 'ac' in item_data:
                    character.armor_class = min(character.armor_class, item_data['ac'])
                
                self.show_info_screen("Purchase Complete", 
                                     [f"Purchased: {item_name}",
                                      f"Gold remaining: {character.gold} gp"],
                                     wait_for_key=True)
            else:
                self.show_info_screen("Insufficient Gold", 
                                     [f"You need {item_data['cost']} gp",
                                      f"You only have {character.gold} gp"],
                                     wait_for_key=True)
    
    def step_name_character(self, character):
        """Step 6: Name your character"""
        name = self.get_text_input("Enter your character's name:", 150, max_length=30)
        
        if name:
            character.name = name
            return True
        return False
    
    def step_review_and_save(self, character):
        """Step 7: Review and save character"""
        lines = [
            "=== CHARACTER COMPLETE ===",
            "",
            f"Name: {character.name}",
            f"Race: {character.race}",
            f"Class: {character.char_class}",
            f"Alignment: {character.alignment}",
            "",
            "Ability Scores:",
            f"  STR: {character.strength}  DEX: {character.dexterity}  CON: {character.constitution}",
            f"  INT: {character.intelligence}  WIS: {character.wisdom}  CHA: {character.charisma}",
            "",
            f"Hit Points: {character.current_hp}/{character.max_hp}",
            f"Armor Class: {character.armor_class}",
            f"THAC0: {character.thac0}",
            f"Gold: {character.gold} gp",
            "",
            f"Equipment ({len(character.equipment)} items):",
        ]
        
        for item in character.equipment[:10]:  # Show first 10 items
            lines.append(f"  • {item}")
        if len(character.equipment) > 10:
            lines.append(f"  ... and {len(character.equipment) - 10} more")
        
        if not self.show_info_screen("Review Character", lines):
            return False
        
        # Save character
        character.save_character()
        
        self.show_info_screen("Character Saved", 
                             [f"Character saved successfully!",
                              f"File: saves/{character.name}.json"])
        
        return True

def run_character_creator():
    """Run the character creator and return the created/loaded character"""
    try:
        creator = CharacterCreatorGUI()
        character = creator.run()
        pygame.quit()
        return character
    except Exception as e:
        print(f"Error in character creator: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        return None

if __name__ == "__main__":
    character = run_character_creator()
    if character:
        print(f"\nCharacter created: {character.name}")
    else:
        print("\nCharacter creation cancelled")
