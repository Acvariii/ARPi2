"""
ARPi2 Game Server Launcher
Choose between Pygame or Pyglet/OpenGL versions
"""

import sys
import os

def show_menu():
    """Display server selection menu"""
    print("\n" + "="*60)
    print(" "*15 + "ARPi2 Game Server Launcher")
    print("="*60)
    print("\nAvailable Versions:")
    print("\n  1. Pyglet/OpenGL Version (Recommended)")
    print("     - Complete UI with player selection and panels")
    print("     - High performance (45-70 FPS)")
    print("     - Includes: Monopoly, Blackjack, D&D Character Creation")
    print("     - OpenGL accelerated rendering")
    print("\n  2. Original Pygame Version")
    print("     - Classic implementation")
    print("     - Stable and well-tested")
    print("     - SDL2-based rendering")
    print("\n  3. Exit")
    print("\n" + "="*60)

def launch_pyglet():
    """Launch Pyglet/OpenGL server"""
    print("\nLaunching Pyglet/OpenGL Game Server...")
    print("Press ESC in menu to exit, or ESC in game to return to menu\n")
    os.system("python game_server_pyglet_complete.py")

def launch_pygame():
    """Launch Pygame server"""
    print("\nLaunching Pygame Game Server...")
    print("Note: This version may have different features than Pyglet\n")
    os.system("python launcher.py")

def main():
    """Main launcher loop"""
    while True:
        show_menu()
        
        choice = input("\nSelect version (1-3): ").strip()
        
        if choice == "1":
            launch_pyglet()
        elif choice == "2":
            launch_pygame()
        elif choice == "3":
            print("\nExiting launcher. Goodbye!")
            sys.exit(0)
        else:
            print("\nInvalid choice. Please select 1, 2, or 3.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nLauncher interrupted. Goodbye!")
        sys.exit(0)
