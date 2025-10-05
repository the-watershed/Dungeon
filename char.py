"""
AD&D 2nd Edition Character Creation System
Complete character creation with dice rolling, equipment purchasing, and save/load functionality.
Integrated with Pygame for GUI display.
"""

import os
import sys
import random
import json
import time
import pygame
from typing import Dict, List, Tuple, Optional

# Character data structures
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
        
        # Derived stats
        self.hit_points: int = 0
        self.max_hit_points: int = 0
        self.armor_class: int = 10
        self.thac0: int = 20
        
        # Resources
        self.gold: int = 0
        self.equipment: List[str] = []
        self.spells: List[str] = []
        
        # Character details
        self.age: int = 0
        self.height: str = ""
        self.weight: str = ""
        self.languages: List[str] = ["Common"]

# Game data
RACES = {
    "Human": {
        "str_mod": 0, "dex_mod": 0, "con_mod": 0, "int_mod": 0, "wis_mod": 0, "cha_mod": 0,
        "classes": ["Fighter", "Mage", "Cleric", "Thief", "Ranger", "Paladin", "Druid", "Bard"],
        "special": ["Extra language", "Dual-class ability"]
    },
    "Elf": {
        "str_mod": 0, "dex_mod": +1, "con_mod": -1, "int_mod": 0, "wis_mod": 0, "cha_mod": 0,
        "classes": ["Fighter", "Mage", "Cleric", "Thief", "Ranger", "Fighter/Mage", "Fighter/Thief", "Mage/Thief"],
        "special": ["Infravision 60'", "Detect secret doors", "Bow bonus", "Sword bonus"]
    },
    "Dwarf": {
        "str_mod": 0, "dex_mod": 0, "con_mod": +1, "int_mod": 0, "wis_mod": 0, "cha_mod": -1,
        "classes": ["Fighter", "Cleric", "Thief", "Fighter/Cleric", "Fighter/Thief"],
        "special": ["Infravision 60'", "Magic resistance", "Detect slopes/traps", "Combat bonus vs giants"]
    },
    "Halfling": {
        "str_mod": -1, "dex_mod": +1, "con_mod": 0, "int_mod": 0, "wis_mod": 0, "cha_mod": 0,
        "classes": ["Fighter", "Cleric", "Thief", "Fighter/Thief"],
        "special": ["Infravision 30'", "Stealth bonus", "Sling/thrown weapon bonus", "Magic resistance"]
    },
    "Half-Elf": {
        "str_mod": 0, "dex_mod": 0, "con_mod": 0, "int_mod": 0, "wis_mod": 0, "cha_mod": 0,
        "classes": ["Fighter", "Mage", "Cleric", "Thief", "Ranger", "Druid", "Bard"],
        "special": ["Infravision 60'", "Detect secret doors", "Charm resistance"]
    },
    "Gnome": {
        "str_mod": 0, "dex_mod": 0, "con_mod": +1, "int_mod": 0, "wis_mod": 0, "cha_mod": 0,
        "classes": ["Fighter", "Mage", "Cleric", "Thief", "Fighter/Cleric", "Fighter/Thief", "Cleric/Thief"],
        "special": ["Infravision 60'", "Detect slopes/traps", "Gnome magic", "Combat bonus vs kobolds/goblins"]
    },
    "Half-Orc": {
        "str_mod": +1, "dex_mod": 0, "con_mod": +1, "int_mod": -2, "wis_mod": 0, "cha_mod": -2,
        "classes": ["Fighter", "Cleric", "Thief", "Fighter/Cleric", "Fighter/Thief", "Cleric/Thief"],
        "special": ["Infravision 60'", "Strength bonus", "Constitution bonus"]
    }
}

CLASSES = {
    "Fighter": {"hit_die": 10, "gold_dice": "5d4", "prime": "Strength"},
    "Mage": {"hit_die": 4, "gold_dice": "1d4", "prime": "Intelligence"},
    "Cleric": {"hit_die": 8, "gold_dice": "3d6", "prime": "Wisdom"},
    "Thief": {"hit_die": 6, "gold_dice": "2d6", "prime": "Dexterity"},
    "Ranger": {"hit_die": 10, "gold_dice": "5d4", "prime": "Strength/Dexterity/Wisdom"},
    "Paladin": {"hit_die": 10, "gold_dice": "5d4", "prime": "Strength/Charisma"},
    "Druid": {"hit_die": 8, "gold_dice": "3d6", "prime": "Wisdom/Charisma"},
    "Bard": {"hit_die": 6, "gold_dice": "3d6", "prime": "Dexterity/Charisma"},
    "Fighter/Mage": {"hit_die": 7, "gold_dice": "4d4", "prime": "Strength/Intelligence"},
    "Fighter/Thief": {"hit_die": 8, "gold_dice": "4d4", "prime": "Strength/Dexterity"},
    "Fighter/Cleric": {"hit_die": 9, "gold_dice": "4d4", "prime": "Strength/Wisdom"},
    "Mage/Thief": {"hit_die": 5, "gold_dice": "2d4", "prime": "Intelligence/Dexterity"},
    "Cleric/Thief": {"hit_die": 7, "gold_dice": "3d4", "prime": "Wisdom/Dexterity"}
}

ALIGNMENTS = [
    "Lawful Good", "Neutral Good", "Chaotic Good",
    "Lawful Neutral", "True Neutral", "Chaotic Neutral", 
    "Lawful Evil", "Neutral Evil", "Chaotic Evil"
]

# Equipment catalog with 50+ items
EQUIPMENT = {
    # Weapons
    "Dagger": {"cost": 2, "weight": 1, "type": "weapon"},
    "Short Sword": {"cost": 10, "weight": 3, "type": "weapon"},
    "Long Sword": {"cost": 15, "weight": 4, "type": "weapon"},
    "Bastard Sword": {"cost": 25, "weight": 6, "type": "weapon"},
    "Two-Handed Sword": {"cost": 50, "weight": 15, "type": "weapon"},
    "Scimitar": {"cost": 15, "weight": 4, "type": "weapon"},
    "Rapier": {"cost": 20, "weight": 2, "type": "weapon"},
    "Hand Axe": {"cost": 1, "weight": 5, "type": "weapon"},
    "Battle Axe": {"cost": 5, "weight": 7, "type": "weapon"},
    "War Hammer": {"cost": 2, "weight": 6, "type": "weapon"},
    "Mace": {"cost": 8, "weight": 8, "type": "weapon"},
    "Morning Star": {"cost": 10, "weight": 12, "type": "weapon"},
    "Flail": {"cost": 15, "weight": 15, "type": "weapon"},
    "Spear": {"cost": 1, "weight": 5, "type": "weapon"},
    "Trident": {"cost": 15, "weight": 5, "type": "weapon"},
    "Halberd": {"cost": 10, "weight": 15, "type": "weapon"},
    "Quarterstaff": {"cost": 1, "weight": 4, "type": "weapon"},
    "Club": {"cost": 0, "weight": 3, "type": "weapon"},
    "Light Crossbow": {"cost": 35, "weight": 7, "type": "weapon"},
    "Heavy Crossbow": {"cost": 50, "weight": 14, "type": "weapon"},
    "Short Bow": {"cost": 30, "weight": 2, "type": "weapon"},
    "Long Bow": {"cost": 75, "weight": 3, "type": "weapon"},
    "Composite Bow": {"cost": 100, "weight": 3, "type": "weapon"},
    "Sling": {"cost": 1, "weight": 0, "type": "weapon"},
    "Dart": {"cost": 0.5, "weight": 0.5, "type": "weapon"},
    "Arrows (20)": {"cost": 3, "weight": 3, "type": "ammo"},
    "Crossbow Bolts (20)": {"cost": 2, "weight": 2, "type": "ammo"},
    "Sling Stones (20)": {"cost": 0, "weight": 5, "type": "ammo"},
    
    # Armor
    "Leather Armor": {"cost": 5, "weight": 15, "type": "armor", "ac": 8},
    "Studded Leather": {"cost": 20, "weight": 25, "type": "armor", "ac": 7},
    "Ring Mail": {"cost": 100, "weight": 30, "type": "armor", "ac": 7},
    "Scale Mail": {"cost": 120, "weight": 40, "type": "armor", "ac": 6},
    "Chain Mail": {"cost": 150, "weight": 40, "type": "armor", "ac": 5},
    "Splint Mail": {"cost": 200, "weight": 45, "type": "armor", "ac": 4},
    "Banded Mail": {"cost": 250, "weight": 35, "type": "armor", "ac": 4},
    "Plate Mail": {"cost": 600, "weight": 50, "type": "armor", "ac": 3},
    "Shield, Small": {"cost": 3, "weight": 5, "type": "shield", "ac": 1},
    "Shield, Medium": {"cost": 7, "weight": 10, "type": "shield", "ac": 1},
    "Shield, Large": {"cost": 10, "weight": 15, "type": "shield", "ac": 1},
    
    # Adventuring Gear
    "Backpack": {"cost": 2, "weight": 2, "type": "gear"},
    "Belt Pouch": {"cost": 1, "weight": 1, "type": "gear"},
    "Rope, Hemp (50')": {"cost": 2, "weight": 20, "type": "gear"},
    "Rope, Silk (50')": {"cost": 10, "weight": 8, "type": "gear"},
    "Grappling Hook": {"cost": 1, "weight": 4, "type": "gear"},
    "Torch": {"cost": 0.01, "weight": 1, "type": "gear"},
    "Lantern, Hooded": {"cost": 7, "weight": 2, "type": "gear"},
    "Lantern, Bullseye": {"cost": 12, "weight": 3, "type": "gear"},
    "Oil, Flask": {"cost": 0.1, "weight": 1, "type": "gear"},
    "Candle": {"cost": 0.01, "weight": 0, "type": "gear"},
    "Tinder Box": {"cost": 0.8, "weight": 1, "type": "gear"},
    "Blanket, Winter": {"cost": 0.5, "weight": 3, "type": "gear"},
    "Bedroll": {"cost": 0.1, "weight": 5, "type": "gear"},
    "Tent, Small": {"cost": 5, "weight": 10, "type": "gear"},
    "Tent, Large": {"cost": 25, "weight": 40, "type": "gear"},
    "Hammer": {"cost": 0.5, "weight": 2, "type": "gear"},
    "Crowbar": {"cost": 2, "weight": 5, "type": "gear"},
    "Piton": {"cost": 0.3, "weight": 0.5, "type": "gear"},
    "Spike, Iron": {"cost": 0.1, "weight": 1, "type": "gear"},
    "Chain, 10'": {"cost": 30, "weight": 20, "type": "gear"},
    "Lock, Good": {"cost": 100, "weight": 1, "type": "gear"},
    "Manacles": {"cost": 15, "weight": 2, "type": "gear"},
    "Mirror, Steel": {"cost": 5, "weight": 0.5, "type": "gear"},
    "Pole, 10'": {"cost": 0.2, "weight": 8, "type": "gear"},
    "Sack, Large": {"cost": 0.2, "weight": 0.5, "type": "gear"},
    "Sack, Small": {"cost": 0.1, "weight": 0.2, "type": "gear"},
    "Thieves' Tools": {"cost": 30, "weight": 1, "type": "gear"},
    "Holy Symbol, Silver": {"cost": 25, "weight": 1, "type": "gear"},
    "Holy Symbol, Wooden": {"cost": 1, "weight": 0, "type": "gear"},
    "Holy Water, Vial": {"cost": 25, "weight": 1, "type": "gear"},
    "Spell Component Pouch": {"cost": 5, "weight": 2, "type": "gear"},
    "Spellbook": {"cost": 15, "weight": 3, "type": "gear"},
    "Scroll Case": {"cost": 1, "weight": 0.5, "type": "gear"},
    "Ink, Vial": {"cost": 8, "weight": 0, "type": "gear"},
    "Quill": {"cost": 0.02, "weight": 0, "type": "gear"},
    "Parchment, Sheet": {"cost": 0.2, "weight": 0, "type": "gear"},
    "Sealing Wax": {"cost": 1, "weight": 1, "type": "gear"},
    "Signet Ring": {"cost": 5, "weight": 0, "type": "gear"},
    "Rations, Trail (1 day)": {"cost": 0.5, "weight": 1, "type": "gear"},
    "Rations, Iron (1 day)": {"cost": 2, "weight": 1, "type": "gear"},
    "Waterskin": {"cost": 0.8, "weight": 4, "type": "gear"},
    "Wine, Common": {"cost": 0.2, "weight": 6, "type": "gear"},
    "Ale, Gallon": {"cost": 0.2, "weight": 8, "type": "gear"},
    "Healing Potion": {"cost": 400, "weight": 0.5, "type": "potion"},
    "Antidote": {"cost": 150, "weight": 0.5, "type": "potion"},
    "Acid, Vial": {"cost": 10, "weight": 1, "type": "gear"}
}

# Pygame GUI Settings
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 1200
BG_COLOR = (74, 71, 65)  # Dark parchment
TEXT_COLOR = (245, 237, 215)  # Light parchment
HIGHLIGHT_COLOR = (200, 170, 120)  # Gold
DIM_COLOR = (140, 130, 120)  # Dimmed text
FONT_SIZE = 24
TITLE_FONT_SIZE = 32

# Utility functions
def init_pygame():
    """Initialize Pygame window"""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("AD&D 2nd Edition Character Creator")
    return screen

def draw_text(screen, text, x, y, color=None, font_size=FONT_SIZE, center=False):
    """Draw text on screen"""
    if color is None:
        color = TEXT_COLOR
    font = pygame.font.Font(None, font_size)
    text_surface = font.render(text, True, color)
    if center:
        text_rect = text_surface.get_rect(center=(x, y))
        screen.blit(text_surface, text_rect)
    else:
        screen.blit(text_surface, (x, y))

def draw_box(screen, x, y, width, height, border_color=TEXT_COLOR):
    """Draw a bordered box"""
    pygame.draw.rect(screen, border_color, (x, y, width, height), 2)

def wait_for_key_pygame():
    """Wait for any key press in Pygame"""
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                return True
        pygame.time.wait(10)
    return False

def roll_dice(dice_str: str) -> Tuple[int, List[int]]:
    """Roll dice and return total and individual rolls"""
    if 'd' not in dice_str:
        return int(dice_str), [int(dice_str)]
    
    parts = dice_str.split('d')
    num_dice = int(parts[0]) if parts[0] else 1
    die_size = int(parts[1])
    
    rolls = [random.randint(1, die_size) for _ in range(num_dice)]
    return sum(rolls), rolls

def ability_modifier(score: int) -> int:
    """Calculate ability score modifier"""
    if score <= 3: return -3
    elif score <= 5: return -2
    elif score <= 8: return -1
    elif score <= 12: return 0
    elif score <= 15: return 1
    elif score <= 17: return 2
    else: return 3

def print_ascii_title():
    title = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ░█▀▀█ ░█▀▀▄ ░█▀▀▄   ░█▀▀█ ░█▄─░█ ░█▀▀▄   ░█▀▀▄ ░█▀▀▄ ░█▀▀█ ░█▀▀█ ░█▀▀▀ ║
║    ░█▄▄█ ░█─░█ ░█─░█   ░█▄▄█ ░█░█░█ ░█─░█   ░█─░█ ░█▄▄▀ ░█▄▄█ ░█─▄▄ ░█▀▀▀ ║
║    ░█─░█ ░█▄▄▀ ░█▄▄▀   ░█─░█ ░█──▀█ ░█▄▄▀   ░█▄▄▀ ░█─░█ ░█─░█ ░█▄▄█ ░█▄▄▄ ║
║                                                                              ║
║              ▒█▀▀█ █░█ █▀▀█ █▀▀█ █▀▀█ █▀▀ ▀▀█▀▀ █▀▀ █▀▀█                  ║
║              ▒█░░░ █▀█ █▄▄█ █▄▄▀ █▄▄█ █░░ ░░█░░ █▀▀ █▄▄▀                  ║
║              ▒█▄▄█ ▀░▀ ▀░░▀ ▀░▀▀ ▀░░▀ ▀▀▀ ░░▀░░ ▀▀▀ ▀░▀▀                  ║
║                                                                              ║
║                    ░█▀▀█ █▀▀█ █▀▀ █▀▀█ ▀▀█▀▀ ░▀░ █▀▀█ █▀▀▄                ║
║                    ░█─── █▄▄▀ █▀▀ █▄▄█ ░░█░░ ▀█▀ █░░█ █░░█                ║
║                    ░█▄▄█ ▀░▀▀ ▀▀▀ ▀░░▀ ░░▀░░ ▀▀▀ ▀▀▀▀ ▀░░▀                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(title)

def animate_text(text: str, delay: float = 0.03):
    """Print text with typewriter effect"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def step_1_roll_abilities(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                            STEP 1: ABILITY SCORES                           ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    animate_text("Choose your ability score generation method:")
    print("\n1. Method I (Standard): Roll 3d6 for each ability in order")
    print("2. Method II: Roll 3d6 twelve times, choose best six")
    print("3. Method III: Roll 3d6 six times per stat, choose highest")
    print("4. Method IV: Roll 2d6+6 for each stat")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            break
        print("Invalid choice. Please enter 1, 2, 3, or 4.")
    
    abilities = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
    scores = []
    
    print(f"\n{'='*78}")
    print("ROLLING ABILITY SCORES")
    print(f"{'='*78}")
    
    if choice == '1':  # Method I
        for ability in abilities:
            input(f"\nPress Enter to roll 3d6 for {ability}...")
            total, rolls = roll_dice("3d6")
            print(f"{ability}: {rolls} = {total}")
            scores.append(total)
    
    elif choice == '2':  # Method II
        all_rolls = []
        print("\nRolling 12 sets of 3d6...")
        for i in range(12):
            input(f"Press Enter to roll set {i+1}...")
            total, rolls = roll_dice("3d6")
            print(f"Set {i+1}: {rolls} = {total}")
            all_rolls.append(total)
        
        all_rolls.sort(reverse=True)
        print(f"\nYour 12 rolls (highest to lowest): {all_rolls}")
        print(f"Taking the 6 highest: {all_rolls[:6]}")
        
        for i, ability in enumerate(abilities):
            scores.append(all_rolls[i])
    
    elif choice == '3':  # Method III
        for ability in abilities:
            ability_rolls = []
            print(f"\nRolling 6 sets of 3d6 for {ability}:")
            for i in range(6):
                input(f"  Press Enter to roll set {i+1}...")
                total, rolls = roll_dice("3d6")
                print(f"  Set {i+1}: {rolls} = {total}")
                ability_rolls.append(total)
            
            best = max(ability_rolls)
            print(f"  Best roll for {ability}: {best}")
            scores.append(best)
    
    elif choice == '4':  # Method IV
        print("\nRolling 2d6+6 for each ability:")
        for ability in abilities:
            input(f"\nPress Enter to roll 2d6+6 for {ability}...")
            total, rolls = roll_dice("2d6")
            final_score = total + 6
            print(f"{ability}: {rolls}+6 = {final_score}")
            scores.append(final_score)
    
    # Assign scores to character
    character.strength = scores[0]
    character.dexterity = scores[1]
    character.constitution = scores[2]
    character.intelligence = scores[3]
    character.wisdom = scores[4]
    character.charisma = scores[5]
    
    print(f"\n{'='*78}")
    print("FINAL ABILITY SCORES:")
    print(f"{'='*78}")
    print(f"Strength:     {character.strength:2d} (modifier: {ability_modifier(character.strength):+d})")
    print(f"Dexterity:    {character.dexterity:2d} (modifier: {ability_modifier(character.dexterity):+d})")
    print(f"Constitution: {character.constitution:2d} (modifier: {ability_modifier(character.constitution):+d})")
    print(f"Intelligence: {character.intelligence:2d} (modifier: {ability_modifier(character.intelligence):+d})")
    print(f"Wisdom:       {character.wisdom:2d} (modifier: {ability_modifier(character.wisdom):+d})")
    print(f"Charisma:     {character.charisma:2d} (modifier: {ability_modifier(character.charisma):+d})")
    
    wait_for_key()

def step_2_choose_race(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                               STEP 2: RACE                                  ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    animate_text("Choose your character's race:")
    print()
    
    race_list = list(RACES.keys())
    for i, race in enumerate(race_list, 1):
        race_data = RACES[race]
        print(f"{i}. {race}")
        print(f"   Ability Modifiers: STR{race_data['str_mod']:+d} DEX{race_data['dex_mod']:+d} CON{race_data['con_mod']:+d} INT{race_data['int_mod']:+d} WIS{race_data['wis_mod']:+d} CHA{race_data['cha_mod']:+d}")
        print(f"   Special Abilities: {', '.join(race_data['special'])}")
        print()
    
    while True:
        try:
            choice = int(input(f"Enter your choice (1-{len(race_list)}): ")) - 1
            if 0 <= choice < len(race_list):
                character.race = race_list[choice]
                break
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(race_list)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    # Apply racial modifiers
    race_data = RACES[character.race]
    character.strength += race_data['str_mod']
    character.dexterity += race_data['dex_mod']
    character.constitution += race_data['con_mod']
    character.intelligence += race_data['int_mod']
    character.wisdom += race_data['wis_mod']
    character.charisma += race_data['cha_mod']
    
    print(f"\nYou chose: {character.race}")
    print(f"\nUpdated ability scores after racial modifiers:")
    print(f"Strength:     {character.strength:2d}")
    print(f"Dexterity:    {character.dexterity:2d}")
    print(f"Constitution: {character.constitution:2d}")
    print(f"Intelligence: {character.intelligence:2d}")
    print(f"Wisdom:       {character.wisdom:2d}")
    print(f"Charisma:     {character.charisma:2d}")
    
    wait_for_key()

def step_3_choose_class(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                              STEP 3: CLASS                                  ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Get available classes for race
    available_classes = RACES[character.race]['classes']
    
    animate_text(f"Available classes for {character.race}:")
    print()
    
    for i, char_class in enumerate(available_classes, 1):
        class_data = CLASSES.get(char_class, {"hit_die": 6, "gold_dice": "3d6", "prime": "None"})
        print(f"{i}. {char_class}")
        print(f"   Hit Die: d{class_data['hit_die']}")
        print(f"   Starting Gold: {class_data['gold_dice']} × 10 gp")
        print(f"   Prime Requisite: {class_data['prime']}")
        print()
    
    while True:
        try:
            choice = int(input(f"Enter your choice (1-{len(available_classes)}): ")) - 1
            if 0 <= choice < len(available_classes):
                character.char_class = available_classes[choice]
                break
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(available_classes)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    print(f"\nYou chose: {character.char_class}")
    wait_for_key()

def step_4_determine_hit_points(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                           STEP 4: HIT POINTS                                ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    class_data = CLASSES[character.char_class]
    hit_die = class_data['hit_die']
    con_mod = ability_modifier(character.constitution)
    
    animate_text(f"Rolling hit points for {character.char_class}...")
    print(f"Hit Die: d{hit_die}")
    print(f"Constitution Modifier: {con_mod:+d}")
    print()
    
    input("Press Enter to roll your hit points...")
    
    hp_roll = random.randint(1, hit_die)
    total_hp = max(1, hp_roll + con_mod)  # Minimum 1 HP
    
    print(f"Hit Point Roll: {hp_roll}")
    print(f"Constitution Modifier: {con_mod:+d}")
    print(f"Total Hit Points: {total_hp}")
    
    character.hit_points = total_hp
    character.max_hit_points = total_hp
    
    wait_for_key()

def step_5_choose_alignment(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                            STEP 5: ALIGNMENT                                ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    animate_text("Choose your character's alignment:")
    print()
    
    for i, alignment in enumerate(ALIGNMENTS, 1):
        print(f"{i}. {alignment}")
    
    while True:
        try:
            choice = int(input(f"\nEnter your choice (1-{len(ALIGNMENTS)}): ")) - 1
            if 0 <= choice < len(ALIGNMENTS):
                character.alignment = ALIGNMENTS[choice]
                break
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(ALIGNMENTS)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    print(f"\nYou chose: {character.alignment}")
    wait_for_key()

def step_6_roll_starting_gold(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                         STEP 6: STARTING GOLD                               ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    class_data = CLASSES[character.char_class]
    gold_dice = class_data['gold_dice']
    
    animate_text(f"Rolling starting gold for {character.char_class}...")
    print(f"Gold Roll: {gold_dice} × 10 gp")
    print()
    
    input("Press Enter to roll your starting gold...")
    
    gold_roll, rolls = roll_dice(gold_dice)
    total_gold = gold_roll * 10
    
    print(f"Gold Roll: {rolls} = {gold_roll}")
    print(f"Starting Gold: {gold_roll} × 10 = {total_gold} gp")
    
    character.gold = total_gold
    
    wait_for_key()

def step_7_buy_equipment(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                          STEP 7: BUY EQUIPMENT                              ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    animate_text(f"You have {character.gold} gold pieces to spend on equipment.")
    print()
    
    # Organize equipment by type
    equipment_by_type = {}
    for item, data in EQUIPMENT.items():
        item_type = data['type']
        if item_type not in equipment_by_type:
            equipment_by_type[item_type] = []
        equipment_by_type[item_type].append((item, data))
    
    while True:
        print(f"\nCurrent Gold: {character.gold} gp")
        print("Current Equipment:", ", ".join(character.equipment) if character.equipment else "None")
        print()
        print("Equipment Categories:")
        categories = list(equipment_by_type.keys())
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category.title()}")
        print(f"{len(categories) + 1}. Finish Shopping")
        
        try:
            choice = int(input("\nChoose a category: ")) - 1
            if choice == len(categories):
                break
            elif 0 <= choice < len(categories):
                category = categories[choice]
                buy_from_category(character, equipment_by_type[category], category)
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def buy_from_category(character: Character, items: List[Tuple[str, Dict]], category: str):
    while True:
        clear_screen()
        print(f"╔══════════════════════════════════════════════════════════════════════════════╗")
        print(f"║                          {category.upper().center(46)}                          ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        print(f"\nCurrent Gold: {character.gold} gp")
        print()
        
        for i, (item, data) in enumerate(items, 1):
            affordable = "✓" if character.gold >= data['cost'] else "✗"
            print(f"{i:2d}. {affordable} {item:<25} {data['cost']:6.1f} gp  (Weight: {data['weight']})")
        
        print(f"{len(items) + 1:2d}. Return to categories")
        
        try:
            choice = int(input("\nWhat would you like to buy? ")) - 1
            if choice == len(items):
                break
            elif 0 <= choice < len(items):
                item_name, item_data = items[choice]
                if character.gold >= item_data['cost']:
                    character.gold -= item_data['cost']
                    character.equipment.append(item_name)
                    print(f"\nPurchased {item_name} for {item_data['cost']} gp!")
                    input("Press Enter to continue...")
                else:
                    print(f"\nNot enough gold! {item_name} costs {item_data['cost']} gp.")
                    input("Press Enter to continue...")
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def step_8_final_details(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                         STEP 8: FINAL DETAILS                               ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    animate_text("Let's finish your character with some final details...")
    print()
    
    character.name = input("Character Name: ").strip()
    
    try:
        character.age = int(input("Age: "))
    except ValueError:
        character.age = 25
    
    character.height = input("Height: ").strip()
    character.weight = input("Weight: ").strip()
    
    # Calculate derived stats
    character.armor_class = 10 - ability_modifier(character.dexterity)
    
    # Adjust AC for armor
    for item in character.equipment:
        if item in EQUIPMENT and EQUIPMENT[item]['type'] in ['armor', 'shield']:
            if 'ac' in EQUIPMENT[item]:
                if EQUIPMENT[item]['type'] == 'armor':
                    character.armor_class = EQUIPMENT[item]['ac'] - ability_modifier(character.dexterity)
                elif EQUIPMENT[item]['type'] == 'shield':
                    character.armor_class -= EQUIPMENT[item]['ac']
    
    # Set THAC0 (simplified)
    character.thac0 = 20  # Base for level 1
    if character.char_class in ['Fighter', 'Ranger', 'Paladin'] or 'Fighter' in character.char_class:
        character.thac0 -= 1  # Better combat progression
    
    print(f"\nCharacter creation complete!")
    wait_for_key()

def display_character_sheet(character: Character):
    clear_screen()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                            CHARACTER SHEET                                  ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    print(f"Name: {character.name}")
    print(f"Race: {character.race}")
    print(f"Class: {character.char_class}")
    print(f"Alignment: {character.alignment}")
    print(f"Level: {character.level}")
    print()
    
    print("ABILITY SCORES:")
    print(f"  Strength:     {character.strength:2d} ({ability_modifier(character.strength):+d})")
    print(f"  Dexterity:    {character.dexterity:2d} ({ability_modifier(character.dexterity):+d})")
    print(f"  Constitution: {character.constitution:2d} ({ability_modifier(character.constitution):+d})")
    print(f"  Intelligence: {character.intelligence:2d} ({ability_modifier(character.intelligence):+d})")
    print(f"  Wisdom:       {character.wisdom:2d} ({ability_modifier(character.wisdom):+d})")
    print(f"  Charisma:     {character.charisma:2d} ({ability_modifier(character.charisma):+d})")
    print()
    
    print("COMBAT STATS:")
    print(f"  Hit Points: {character.hit_points}/{character.max_hit_points}")
    print(f"  Armor Class: {character.armor_class}")
    print(f"  THAC0: {character.thac0}")
    print()
    
    print(f"Gold: {character.gold} gp")
    print()
    
    print("EQUIPMENT:")
    if character.equipment:
        for item in character.equipment:
            print(f"  • {item}")
    else:
        print("  None")
    print()
    
    print(f"Age: {character.age}")
    print(f"Height: {character.height}")
    print(f"Weight: {character.weight}")
    
    wait_for_key()

def save_character(character: Character):
    if not character.name:
        print("Cannot save character without a name!")
        return
    
    # Create saves directory if it doesn't exist
    save_dir = os.path.join(os.path.dirname(__file__), 'saves')
    os.makedirs(save_dir, exist_ok=True)
    
    # Save character data
    char_data = {
        'name': character.name,
        'race': character.race,
        'char_class': character.char_class,
        'alignment': character.alignment,
        'level': character.level,
        'strength': character.strength,
        'dexterity': character.dexterity,
        'constitution': character.constitution,
        'intelligence': character.intelligence,
        'wisdom': character.wisdom,
        'charisma': character.charisma,
        'hit_points': character.hit_points,
        'max_hit_points': character.max_hit_points,
        'armor_class': character.armor_class,
        'thac0': character.thac0,
        'gold': character.gold,
        'equipment': character.equipment,
        'spells': character.spells,
        'age': character.age,
        'height': character.height,
        'weight': character.weight,
        'languages': character.languages
    }
    
    filename = f"{character.name.replace(' ', '_').lower()}.json"
    filepath = os.path.join(save_dir, filename)
    
    try:
        with open(filepath, 'w') as f:
            json.dump(char_data, f, indent=2)
        print(f"Character saved as {filename}")
    except Exception as e:
        print(f"Error saving character: {e}")

def load_character() -> Optional[Character]:
    save_dir = os.path.join(os.path.dirname(__file__), 'saves')
    
    if not os.path.exists(save_dir):
        print("No saved characters found.")
        return None
    
    # List saved characters
    char_files = [f for f in os.listdir(save_dir) if f.endswith('.json')]
    
    if not char_files:
        print("No saved characters found.")
        return None
    
    print("Saved Characters:")
    for i, filename in enumerate(char_files, 1):
        char_name = filename[:-5].replace('_', ' ').title()
        print(f"{i}. {char_name}")
    
    try:
        choice = int(input(f"Choose character to load (1-{len(char_files)}): ")) - 1
        if 0 <= choice < len(char_files):
            filepath = os.path.join(save_dir, char_files[choice])
            with open(filepath, 'r') as f:
                char_data = json.load(f)
            
            character = Character()
            for key, value in char_data.items():
                setattr(character, key, value)
            
            print(f"Loaded character: {character.name}")
            return character
        else:
            print("Invalid choice.")
            return None
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading character: {e}")
        return None

def main_menu():
    while True:
        clear_screen()
        print_ascii_title()
        
        print("\n" + "="*78)
        animate_text("Welcome to the AD&D 2nd Edition Character Creator!", 0.02)
        print("="*78)
        print()
        print("1. Create New Character")
        print("2. Load Existing Character")
        print("3. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        if choice == '1':
            character = Character()
            
            step_1_roll_abilities(character)
            step_2_choose_race(character)
            step_3_choose_class(character)
            step_4_determine_hit_points(character)
            step_5_choose_alignment(character)
            step_6_roll_starting_gold(character)
            step_7_buy_equipment(character)
            step_8_final_details(character)
            
            display_character_sheet(character)
            
            save_choice = input("Save character? (y/n): ").strip().lower()
            if save_choice == 'y':
                save_character(character)
            
            input("\nPress Enter to return to main menu...")
            
        elif choice == '2':
            character = load_character()
            if character:
                display_character_sheet(character)
                input("Press Enter to return to main menu...")
        
        elif choice == '3':
            clear_screen()
            animate_text("Thank you for using the AD&D Character Creator!")
            animate_text("May your adventures be legendary!")
            break
        
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
