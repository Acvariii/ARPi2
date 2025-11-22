# ARPi2 Refactoring Report

## Analysis Summary

**Date:** November 22, 2025  
**Python Version:** 3.11.9

## Files to Remove (Pygame/Unused)

### 1. **Pygame Implementations** (Obsolete - Using Pyglet now)

- `launcher.py` - Pygame game launcher (replaced by game_server_pyglet_complete.py)
- `ui_components.py` - Pygame UI components (replaced by pyglet_games/ui_components_pyglet.py)
- `player_panel.py` - Pygame player panels (replaced by pyglet_games/player_panels.py)
- `monopoly/` folder - Entire Pygame Monopoly implementation (replaced by pyglet_games/monopoly_rebuilt.py)
- `dnd/game.py` - Pygame D&D game (replaced by pyglet_games/dnd_complete.py)
- `dnd/game_old.py` - Old D&D implementation
- `dnd/drawing.py` - Pygame D&D drawing (replaced by pyglet_games/dnd_complete.py)
- `dnd/__init__.py` - Pygame D&D init (imports unused classes)

### 2. **Blackjack Folder** (Old Pygame implementation)

- `blackjack/` folder - Entire folder (replaced by pyglet_games/blackjack_complete.py)

### 3. **Duplicate/Backup Files in pyglet_games/**

- `pyglet_games/blackjack_rebuilt.py` - Older version (superseded by blackjack_complete.py)
- `pyglet_games/monopoly_rebuilt_backup.py` - Backup file

### 4. **Unused Constants/Data Files**

- `constants.py` - Contains COMMUNITY_CHEST_CARDS & CHANCE_CARDS imported by Pygame Monopoly only
  - **Keep but refactor** - Used by monopoly_data.py which is still referenced

## Files to Keep

### Core Infrastructure

- ✅ `config.py` - Central configuration (used by all games)
- ✅ `monopoly_data.py` - Monopoly game data (used by Pygame Monopoly BUT imported by pyglet version)
- ✅ `constants.py` - Card data (imported by monopoly_data.py)

### Pyglet Game Server (ACTIVE)

- ✅ `game_server_pyglet_complete.py` - Main server entry point
- ✅ `pyglet_games/renderer.py` - OpenGL rendering engine
- ✅ `pyglet_games/player_selection.py` - Player selection UI
- ✅ `pyglet_games/player_panels.py` - Player panel system
- ✅ `pyglet_games/ui_components_pyglet.py` - Pyglet UI components
- ✅ `pyglet_games/popup_system.py` - Universal popup system
- ✅ `pyglet_games/monopoly_rebuilt.py` - Pyglet Monopoly game
- ✅ `pyglet_games/blackjack_complete.py` - Pyglet Blackjack game (1572 lines, COMPLETE)
- ✅ `pyglet_games/dnd_complete.py` - Pyglet D&D character creation

### Client System

- ✅ `pi_thin_client.py` - Raspberry Pi thin client for hand tracking
- ✅ `show_server_ip.py` - Utility to display server IP
- ✅ `start_server.py` - Server startup script

### D&D Core Logic (Still Used)

- ✅ `dnd/character.py` - Character data structures (imported by pyglet_games/dnd_complete.py)
- ✅ `dnd/game_logic.py` - D&D game mechanics (imported by pyglet_games/dnd_complete.py)
- ✅ `dnd/creation_visuals.py` - Character creation visuals (imported by pyglet D&D)

### Other Files

- ✅ `Readme.ini` - Documentation
- ✅ `README.md` - Documentation
- ✅ `.gitignore` - Git configuration
- ✅ `setup_firewall.bat` - Windows firewall setup
- ✅ `check_connection.py` - Connection testing utility
- ✅ `CLEANUP_SUMMARY.md`, `POPUP_REDESIGN_STATUS.md`, `POPUP_SYSTEM_README.md` - Documentation

## Import Dependencies Analysis

### Constants.py Usage

```python
# Used by:
monopoly/game_logic.py:  from constants import COMMUNITY_CHEST_CARDS, CHANCE_CARDS
monopoly/game.py:        from constants import COMMUNITY_CHEST_CARDS, CHANCE_CARDS
monopoly_data.py:        # Imports these from constants.py (via copy or reference)
```

**Decision:** Move COMMUNITY_CHEST_CARDS and CHANCE_CARDS into monopoly_data.py, delete constants.py

### Monopoly_data.py Usage

```python
# Used by:
monopoly/player.py:      from monopoly_data import STARTING_MONEY, PROPERTY_GROUPS
monopoly/game_logic.py:  from monopoly_data import (PROPERTIES, RAILROADS, UTILITIES...)
monopoly/game.py:        from monopoly_data import (PROPERTIES, RAILROADS, UTILITIES...)
```

**Note:** These imports are from the OLD Pygame monopoly folder which will be deleted.
**Action:** Check if pyglet_games/monopoly_rebuilt.py needs this data.

## Refactoring Actions

### 1. Consolidate Game Data

- [x] Move COMMUNITY_CHEST_CARDS and CHANCE_CARDS from constants.py into monopoly_data.py
- [ ] Verify pyglet_games/monopoly_rebuilt.py doesn't need monopoly_data.py (it might have data embedded)
- [ ] Delete constants.py if no longer needed

### 2. Clean D&D Folder

- [ ] Delete dnd/game.py (Pygame version)
- [ ] Delete dnd/game_old.py (old backup)
- [ ] Delete dnd/drawing.py (Pygame drawing)
- [ ] Delete dnd/**init**.py (imports unused Pygame classes)
- [x] Keep dnd/character.py (used by pyglet version)
- [x] Keep dnd/game_logic.py (used by pyglet version)
- [x] Keep dnd/creation_visuals.py (used by pyglet version)

### 3. Delete Entire Pygame Implementations

- [ ] Delete monopoly/ folder (entire Pygame Monopoly)
- [ ] Delete blackjack/ folder (entire Pygame Blackjack)
- [ ] Delete launcher.py (Pygame launcher)
- [ ] Delete ui_components.py (Pygame UI)
- [ ] Delete player_panel.py (Pygame panels)

### 4. Clean pyglet_games Folder

- [ ] Delete pyglet_games/blackjack_rebuilt.py (superseded by blackjack_complete.py)
- [ ] Delete pyglet_games/monopoly_rebuilt_backup.py (backup file)

### 5. Verify No Broken Imports

- [ ] Run game_server_pyglet_complete.py to ensure it still works
- [ ] Check for any remaining imports of deleted modules

## Estimated Impact

### Files to Delete: ~18 files

- launcher.py (~200 lines)
- ui_components.py (~500 lines)
- player_panel.py (~150 lines)
- constants.py (~100 lines, merge into monopoly_data.py first)
- monopoly/\*.py (~2000+ lines total)
- blackjack/\*.py (~1000+ lines total)
- dnd/game.py + game_old.py + drawing.py (~2000+ lines total)
- pyglet_games/blackjack_rebuilt.py (~1200 lines)
- pyglet_games/monopoly_rebuilt_backup.py (~800 lines)

### Total Lines Removed: ~8000+ lines

### Folders to Delete: 2 (monopoly/, blackjack/)

## Risk Assessment

**Low Risk** - All deleted code is Pygame-based, completely replaced by Pyglet versions.
The active game server (game_server_pyglet_complete.py) uses only:

- pyglet_games/\* (keeping the active versions)
- config.py
- dnd/character.py, dnd/game_logic.py, dnd/creation_visuals.py (D&D data structures)

## Testing Plan

1. Backup workspace before deletion
2. Delete files in stages
3. Run `python game_server_pyglet_complete.py` after each stage
4. Verify all 3 games load and function:
   - Monopoly player selection and game
   - Blackjack player selection and game
   - D&D character creation

## Post-Cleanup Structure

```
d:\GitHub\ARPi2\
├── config.py                          # Central config
├── monopoly_data.py                   # Monopoly game data (check if needed)
├── game_server_pyglet_complete.py    # Main server (ACTIVE)
├── pi_thin_client.py                  # Client
├── show_server_ip.py                  # Utility
├── start_server.py                    # Startup
├── check_connection.py                # Utility
├── setup_firewall.bat                 # Setup
├── Readme.ini, README.md              # Docs
├── dnd/
│   ├── __init__.py                    # NEW - minimal imports only
│   ├── character.py                   # Character data
│   ├── game_logic.py                  # Game mechanics
│   └── creation_visuals.py            # Visuals
└── pyglet_games/
    ├── __init__.py
    ├── renderer.py                    # OpenGL renderer
    ├── player_selection.py            # Player selection
    ├── player_panels.py               # Player panels
    ├── ui_components_pyglet.py        # UI components
    ├── popup_system.py                # Popups
    ├── monopoly_rebuilt.py            # Monopoly (Pyglet)
    ├── blackjack_complete.py          # Blackjack (Pyglet) ✅ COMPLETE
    └── dnd_complete.py                # D&D (Pyglet)
```

## Additional Cleanup Opportunities

- [ ] Remove **pycache** directories (regenerated automatically)
- [ ] Check .gitignore includes **pycache**
- [ ] Verify dnd_saves/ is intentionally kept (save files)
