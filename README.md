# ARPi2 - Augmented Reality Pi Game Server

Multi-player tabletop games with hand tracking using MediaPipe.

## Quick Start

### Choose Your Server Version

```bash
python start_server.py
```

This will present a menu to choose between:

1. **Pyglet/OpenGL Version** (Recommended) - High performance, complete UI
2. **Original Pygame Version** - Classic implementation

Or run directly:

- Pyglet: `python game_server_pyglet_complete.py`
- Pygame: `python launcher.py`

## Features

### Pyglet/OpenGL Version ✨

- **45-70 FPS** performance with OpenGL acceleration
- **Complete UI** with player selection screens
- **Proper panel orientations** - Text faces each player's POV
- **Hover indicators** - Circular progress rings on buttons
- **ESC Navigation** - Return to menu or exit application
- **Three Games:**
  - Monopoly (full board with properties)
  - Blackjack (dealer AI, betting system)
  - D&D Character Creation (races, classes, abilities)

### Original Pygame Version

- Classic SDL2-based rendering
- Stable reference implementation
- All original game mechanics

## Requirements

```bash
pip install pygame pyglet mediapipe opencv-python websockets numpy
```

## Controls

### Hand Tracking

- **Hover** over buttons/options for 1.5 seconds to select
- **ESC Key** - Return to menu (in game) or exit (in menu)
- **Mouse** - Fallback control when no hands detected

### Player Selection

- Select 2+ players for Monopoly/Blackjack
- Select 1+ players for D&D
- Circular slots around screen center
- Click **Start** button in middle when ready

## Architecture

```
ARPi2/
├── start_server.py              # Main launcher (choose Pygame/Pyglet)
├── game_server_pyglet_complete.py  # Pyglet server
├── launcher.py                  # Pygame server
├── pyglet_games/                # Pyglet game implementations
│   ├── monopoly_rebuilt.py      # Complete Monopoly
│   ├── blackjack_rebuilt.py     # Complete Blackjack
│   ├── dnd_complete.py          # D&D Character Creation
│   ├── ui_components_pyglet.py  # Reusable UI (buttons, panels)
│   ├── renderer.py              # OpenGL rendering utilities
│   ├── player_selection.py      # Player selection logic
│   └── player_panels.py         # Panel positioning system
├── monopoly/                    # Pygame Monopoly
├── blackjack/                   # Pygame Blackjack
├── dnd/                         # Pygame D&D
└── config.py                    # Shared configuration

```

## Performance

### Pyglet/OpenGL

- Menu: 60-70 FPS
- In-game: 45-60 FPS
- With hand tracking: 40-50 FPS

### Pygame

- Variable performance depending on complexity
- Typically 30-60 FPS

## Development

### Adding New Games (Pyglet)

1. Import reusable UI components:

```python
from pyglet_games.ui_components_pyglet import (
    PygletButton, PlayerPanel, calculate_all_panels, draw_hover_indicators
)
```

2. Use PlayerPanel for oriented text:

```python
panel.draw_text_oriented(renderer, "Text", 0.5, 0.25, 20, (255, 255, 255))
```

3. Create buttons from panel layout:

```python
button_rects = panel.get_button_layout()
buttons = [PygletButton(rect, "Label", panel.orientation) for rect in button_rects]
```

## Network

- Server runs on `ws://0.0.0.0:8765`
- Use `python show_server_ip.py` to find your local IP
- Clients connect via WebSocket for hand tracking data

## Troubleshooting

### "Port 8765 already in use"

```bash
# Windows PowerShell
Stop-Process -Name python -Force
```

### Low FPS

- Close other applications
- Reduce number of active players
- Check GPU drivers are up to date

### Hand tracking not working

- Ensure good lighting
- Keep hands visible to camera
- Adjust MediaPipe confidence thresholds in config.py

## License

MIT License - See LICENSE file for details
