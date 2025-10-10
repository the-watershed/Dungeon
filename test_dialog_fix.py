"""Diagnostic script to test pygame + tkinter dialog interaction."""

import pygame
import tkinter as tk
from tkinter import simpledialog
import sys

print("=== Pygame + Tkinter Dialog Test ===\n")

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Dialog Test")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

# Track state
frame_count = 0
dialog_opened = False
tk_root = None

def draw_screen(message):
    """Draw the pygame window."""
    screen.fill((30, 30, 40))
    text = font.render(message, True, (255, 255, 255))
    screen.blit(text, (50, 250))
    info = font.render(f"Frame: {frame_count}", True, (200, 200, 200))
    screen.blit(info, (50, 300))
    pygame.display.flip()

def test_method_1_wait_window():
    """Test 1: Using wait_window() - EXPECTED TO FREEZE"""
    global tk_root
    print("\n--- Test 1: wait_window() ---")
    
    if tk_root is None:
        tk_root = tk.Tk()
        tk_root.withdraw()
    
    dialog = tk.Toplevel(tk_root)
    dialog.title("Test 1: wait_window()")
    dialog.geometry("300x100")
    
    tk.Label(dialog, text="Click button to close").pack(pady=20)
    tk.Button(dialog, text="Close", command=dialog.destroy).pack()
    
    print("Calling wait_window() - pygame should freeze...")
    dialog.wait_window()
    print("Dialog closed!")

def test_method_2_manual_loop():
    """Test 2: Manual loop with winfo_exists()"""
    global tk_root, frame_count
    print("\n--- Test 2: Manual loop with winfo_exists() ---")
    
    if tk_root is None:
        tk_root = tk.Tk()
        tk_root.withdraw()
    
    dialog = tk.Toplevel(tk_root)
    dialog.title("Test 2: Manual Loop")
    dialog.geometry("300x100")
    
    tk.Label(dialog, text="Click button to close").pack(pady=20)
    tk.Button(dialog, text="Close", command=dialog.destroy).pack()
    
    print("Using manual loop...")
    loop_count = 0
    while True:
        try:
            if not dialog.winfo_exists():
                print(f"Dialog closed after {loop_count} iterations")
                break
            
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    dialog.destroy()
                    return False
            
            # Draw pygame
            draw_screen(f"Manual Loop Test - {loop_count}")
            frame_count += 1
            clock.tick(30)
            
            # Update tkinter
            tk_root.update()
            loop_count += 1
            
        except tk.TclError as e:
            print(f"TclError: {e}")
            break
        except Exception as e:
            print(f"Exception: {e}")
            break
    
    return True

def test_method_3_update_idletasks():
    """Test 3: Using update_idletasks() instead of update()"""
    global tk_root, frame_count
    print("\n--- Test 3: update_idletasks() ---")
    
    if tk_root is None:
        tk_root = tk.Tk()
        tk_root.withdraw()
    
    dialog = tk.Toplevel(tk_root)
    dialog.title("Test 3: update_idletasks()")
    dialog.geometry("300x100")
    
    tk.Label(dialog, text="Click button to close").pack(pady=20)
    tk.Button(dialog, text="Close", command=dialog.destroy).pack()
    
    print("Using update_idletasks()...")
    loop_count = 0
    while True:
        try:
            if not dialog.winfo_exists():
                print(f"Dialog closed after {loop_count} iterations")
                break
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    dialog.destroy()
                    return False
            
            draw_screen(f"update_idletasks Test - {loop_count}")
            frame_count += 1
            clock.tick(30)
            
            # Try update_idletasks
            tk_root.update_idletasks()
            dialog.update()
            loop_count += 1
            
        except tk.TclError as e:
            print(f"TclError: {e}")
            break
        except Exception as e:
            print(f"Exception: {e}")
            break
    
    return True

# Main test loop
running = True
test_stage = 0

print("\nClick in pygame window to run tests...")
print("Press 1, 2, or 3 to run specific test")
print("Press ESC to quit\n")

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_1:
                print("\n>>> Running Test 1 (wait_window - WILL FREEZE) <<<")
                test_method_1_wait_window()
            elif event.key == pygame.K_2:
                print("\n>>> Running Test 2 (manual loop) <<<")
                if not test_method_2_manual_loop():
                    running = False
            elif event.key == pygame.K_3:
                print("\n>>> Running Test 3 (update_idletasks) <<<")
                if not test_method_3_update_idletasks():
                    running = False
    
    draw_screen("Press 1, 2, or 3 to test")
    frame_count += 1
    clock.tick(60)

pygame.quit()
if tk_root:
    tk_root.destroy()
print("\n=== Test Complete ===")
