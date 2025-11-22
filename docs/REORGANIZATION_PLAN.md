# ARPi2 Codebase Reorganization Plan

## New Folder Structure

```
d:\GitHub\ARPi2\
├── config.py                          # Global config
├── game_server_pyglet_complete.py    # Main server
├── pi_thin_client.py                  # Client
├── start_server.py                    # Utilities
├── show_server_ip.py
├── check_connection.py
├── setup_firewall.bat
│
├── core/                              # NEW - Shared core components
│   ├── __init__.py
│   ├── renderer.py                    # OpenGL renderer (from pyglet_games)
│   ├── ui_components.py               # Shared UI components (buttons, panels, etc)
│   └── player_selection.py            # Player selection UI
│
├── games/                             # NEW - All games in one folder
│   ├── __init__.py
│   │
│   ├── monopoly/                      # Monopoly game
│   │   ├── __init__.py
│   │   ├── game.py                    # Main game class
│   │   ├── logic.py                   # Game logic (GameLogic class)
│   │   ├── models.py                  # Data models (Property, Player)
│   │   ├── data.py                    # Game data (board, cards, constants)
│   │   ├── ui.py                      # Monopoly-specific UI
│   │   └── rendering.py               # Board/token rendering
│   │
│   ├── blackjack/                     # Blackjack game
│   │   ├── __init__.py
│   │   ├── game.py                    # Main game class
│   │   ├── logic.py                   # Card/hand logic
│   │   ├── models.py                  # Card, Hand, Deck classes
│   │   ├── data.py                    # Game constants
│   │   ├── ui.py                      # Blackjack-specific UI
│   │   └── rendering.py               # Card rendering
│   │
│   └── dnd/                           # D&D game
│       ├── __init__.py
│       ├── game.py                    # Main game class
│       ├── logic.py                   # Game logic (dice, combat, skills)
│       ├── models.py                  # Character model
│       ├── data.py                    # Races, classes, skills
│       ├── ui.py                      # D&D-specific UI
│       └── rendering.py               # Character sheet rendering
│
└── docs/                              # Documentation
    ├── Readme.ini
    ├── README.md
    ├── REFACTOR_REPORT.md
    └── REFACTORING_COMPLETE.md
```

## Migration Steps

### Phase 1: Create Core Infrastructure
1. Create `core/` folder
2. Move `pyglet_games/renderer.py` → `core/renderer.py`
3. Extract shared UI from `pyglet_games/ui_components_pyglet.py` → `core/ui_components.py`
4. Move `pyglet_games/player_selection.py` → `core/player_selection.py`
5. Move `pyglet_games/popup_system.py` → `core/popup_system.py`

### Phase 2: Reorganize Monopoly
1. Create `games/monopoly/` folder
2. Split `pyglet_games/monopoly_rebuilt.py`:
   - Game class → `game.py`
   - Board/token rendering → `rendering.py`
   - Monopoly UI (popups, buttons) → `ui.py`
3. Move existing files:
   - `monopoly/property.py`, `monopoly/player.py` → `models.py` (combined)
   - `monopoly/game_logic.py` → `logic.py`
   - `monopoly_data.py` → `data.py`

### Phase 3: Reorganize Blackjack
1. Create `games/blackjack/` folder
2. Split `pyglet_games/blackjack_complete.py`:
   - Game class → `game.py`
   - Card/Hand/Deck → `models.py`
   - Card logic/scoring → `logic.py`
   - Constants → `data.py`
   - Card rendering → `rendering.py`
   - Blackjack UI → `ui.py`

### Phase 4: Reorganize D&D
1. Create `games/dnd/` folder
2. Split `pyglet_games/dnd_complete.py`:
   - Game class → `game.py`
   - Particle effects, rendering → `rendering.py`
   - D&D-specific UI → `ui.py`
3. Move existing files:
   - `dnd/character.py` → `models.py`
   - `dnd/game_logic.py` → `logic.py`
   - Extract RACES, CLASSES, SKILLS from character.py → `data.py`
   - `dnd/creation_visuals.py` → merge into `rendering.py`

### Phase 5: Update Main Server
1. Update `game_server_pyglet_complete.py` imports
2. Update `games/__init__.py` to export all games

### Phase 6: Cleanup
1. Delete `pyglet_games/` folder
2. Delete old `monopoly/` and `dnd/` folders
3. Move docs to `docs/` folder

## Import Changes

### Before:
```python
from pyglet_games.renderer import PygletRenderer
from pyglet_games.blackjack_complete import BlackjackGame
from pyglet_games.monopoly_rebuilt import MonopolyGame
from pyglet_games.dnd_complete import DnDCharacterCreation
```

### After:
```python
from core.renderer import PygletRenderer
from games.blackjack import BlackjackGame
from games.monopoly import MonopolyGame
from games.dnd import DnDCharacterCreation
```
