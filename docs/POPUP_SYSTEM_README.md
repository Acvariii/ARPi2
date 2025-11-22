# Universal Popup System Documentation

## Overview

The Universal Popup System (`pyglet_games/popup_system.py`) provides a modern, grid-based popup interface for all Pyglet games. It ensures:

- **Complete coverage** - Popups fully cover underlying UI with opaque backgrounds
- **Grid-based layouts** - No text overlap, clean spacing, professional appearance
- **Orientation support** - All content readable from any player perspective (0°, 90°, 180°, 270°)
- **Reusable components** - Easy to create new popups with consistent styling

## Architecture

### Core Classes

#### `GridCell`

Represents a cell in the popup grid.

```python
GridCell(row, col, row_span=1, col_span=1)
```

#### `PopupContent`

Content item for popup (text, button, etc.).

```python
PopupContent(
    content_type,  # "title", "text", "value", "button"
    text,
    grid_cell,
    font_size=16,
    color=(255, 255, 255),
    callback=None  # For buttons
)
```

#### `PopupGrid`

Grid-based popup layout manager.

```python
grid = PopupGrid(rows, cols, orientation)
grid.add_title("TITLE", row=0)
grid.add_text("Text content", row=1)
grid.add_value("$1000", row=2, color=(100, 255, 100))
grid.add_button("OK", row=3, col=0, callback="ok")
```

#### `UniversalPopup`

Main popup controller.

```python
popup = UniversalPopup()

# Show popup
popup.show(player_idx, panel_rect, orientation, popup_type, grid, data)

# Check for button clicks
callback = popup.check_button_click(fingertips, current_time, hover_threshold)

# Draw popup
popup.draw(renderer)

# Hide popup
popup.hide()

# Check if active
if popup.active:
    # ...
```

## Usage

### Creating a Popup

```python
from pyglet_games.popup_system import PopupGrid, UniversalPopup

# Create grid (8 rows x 1 col for vertical panels, 6 rows x 2 cols for horizontal)
is_vertical = orientation in [90, 270]
if is_vertical:
    grid = PopupGrid(rows=8, cols=1, orientation=orientation)
else:
    grid = PopupGrid(rows=6, cols=2, orientation=orientation)

# Add content
grid.add_title("BUY PROPERTY", row=0)
grid.add_text("Baltic Avenue", row=2, font_size=17)
grid.add_value("$60", row=3, font_size=20, color=(100, 255, 100))
grid.add_button("Buy", row=5, col=0, callback="buy")
grid.add_button("Pass", row=5, col=1, callback="pass")

# Show popup
popup.show(
    player_idx=0,
    panel_rect=(x, y, w, h),
    orientation=0,
    popup_type="buy_prompt",
    grid=grid,
    data={"price": 60, "property": "Baltic Avenue"}
)
```

### Handling Popup Buttons

```python
# In handle_input()
if popup.active:
    callback = popup.check_button_click(fingertips, current_time, HOVER_TIME_THRESHOLD)
    if callback:
        handle_popup_callback(callback)
    return False

def handle_popup_callback(callback: str):
    if callback == "buy":
        # Handle buy action
        price = popup.data.get("price")
        # ... buy logic
        popup.hide()
    elif callback == "pass":
        popup.hide()
```

### Drawing Popups

```python
# In draw() method
def draw(self):
    # ... draw game board and panels

    # Draw popup last (on top)
    if popup.active:
        # Optional: dim entire screen
        self.renderer.draw_rect((0, 0, 0, 160), (0, 0, self.width, self.height))

        # Draw popup with complete coverage
        popup.draw(self.renderer)
```

## Pre-built Popup Factories

### Monopoly Popups

```python
from pyglet_games.popup_system import (
    create_monopoly_buy_popup,
    create_monopoly_card_popup,
    create_monopoly_properties_popup
)

# Buy property popup
grid = create_monopoly_buy_popup(
    player_money=1500,
    property_name="Park Place",
    price=350,
    orientation=0
)

# Card popup (Chance/Community Chest)
grid = create_monopoly_card_popup(
    card_text="Advance to Go. Collect $200.",
    deck_type="chance",  # or "community"
    orientation=180
)

# Properties list popup
grid = create_monopoly_properties_popup(
    properties=["Baltic Avenue", "Mediterranean Avenue"],
    orientation=90
)
```

### Blackjack Popups

```python
from pyglet_games.popup_system import create_blackjack_bet_popup

# Betting popup
grid = create_blackjack_bet_popup(
    chips=1000,
    current_bet=50,
    orientation=270
)
```

### Generic Info Popup

```python
from pyglet_games.popup_system import create_info_popup

# Generic message popup
grid = create_info_popup(
    title="GAME OVER",
    message="You went bankrupt!",
    orientation=0,
    button_text="OK"
)
```

## Design Principles

### 1. Complete Coverage

Popups use **4 layers** to ensure complete coverage of underlying UI:

```python
# Layer 1: Solid opaque dark background
renderer.draw_rect((20, 25, 30, 255), rect)

# Layer 2: Slightly lighter overlay for depth
renderer.draw_rect((30, 35, 40, 255), smaller_rect)

# Layer 3: Player color border
renderer.draw_rect(player_color, rect, width=5)

# Layer 4: Inner accent border
renderer.draw_rect((60, 65, 75), inner_rect, width=2)
```

### 2. Grid-Based Layout

- **Vertical panels** (left/right): Use more rows (8-12) for tall layout
- **Horizontal panels** (top/bottom): Use fewer rows (4-6) with multiple columns
- **Cell spacing**: Automatic via grid division
- **No overlap**: Each content item has dedicated grid cells

### 3. Orientation Support

Text and buttons automatically rotate based on panel orientation:

- **0°** (bottom): Normal orientation
- **180°** (top): Upside down
- **270°** (left): Rotated 90° to face left player
- **90°** (right): Rotated 270° to face right player

### 4. Button Placement

Buttons include padding (8px) to avoid edge overlap:

```python
padding = 8
button_rect = (x + padding, y + padding, w - 2*padding, h - 2*padding)
```

## Integration Checklist

When integrating into a new game:

- [ ] Import popup system components
- [ ] Add `self.popup = UniversalPopup()` to game `__init__`
- [ ] Create popup factory functions for your game
- [ ] Update `handle_input()` to check `popup.active` first
- [ ] Add callback handler method
- [ ] Disable game buttons when `popup.active`
- [ ] Call `popup.draw()` at end of `draw()` method
- [ ] Test all player orientations (0°, 90°, 180°, 270°)
- [ ] Verify complete button text coverage
- [ ] Check text readability from all positions

## Examples

### Monopoly Integration

```python
# In __init__
self.popup = UniversalPopup()

# Show buy prompt
def _show_buy_prompt(self, player, space):
    panel = self.panels[player.idx]
    price = space.data["price"]

    grid = create_monopoly_buy_popup(
        player.money, space.data["name"], price, panel.orientation
    )

    self.popup.show(
        player.idx, panel.rect, panel.orientation, "buy_prompt", grid,
        {"player": player, "space": space, "price": price}
    )

# Handle callbacks
def _handle_popup_callback(self, callback):
    if callback == "buy":
        player = self.popup.data["player"]
        space = self.popup.data["space"]
        price = self.popup.data["price"]
        GameLogic.buy_property(player, space, price)
        self.popup.hide()
    elif callback == "pass":
        self.popup.hide()
```

### Blackjack Integration

```python
# In __init__
self.popup = UniversalPopup()
self.result_popup_time = 0

# Show bet popup
def _show_bet_popup(self, player):
    panel = self.panels[player.idx]

    grid = create_blackjack_bet_popup(
        player.chips, player.current_bet, panel['orientation']
    )

    self.popup.show(
        player.idx, panel['rect'], panel['orientation'], "betting", grid,
        {"player": player}
    )

# Handle callbacks
def _handle_popup_callback(self, callback):
    if callback in ["bet5", "bet25", "bet100"]:
        player = self.popup.data["player"]
        amount = int(callback[3:])  # Extract number
        player.place_bet(amount)
        # Update popup to show new bet
        self._show_bet_popup(player)
    elif callback == "ready":
        self.popup.hide()
```

## Troubleshooting

### Button text still visible through popup

- Ensure you're calling `popup.draw()` AFTER all other drawing
- Check that popup layers use alpha=255 (fully opaque)
- Verify panel_rect is correct

### Text not rotated correctly

- Confirm orientation parameter is 0, 90, 180, or 270
- Check that panel orientation matches player position
- Verify renderer.draw_text() supports rotation parameter

### Buttons not responding

- Verify fingertips are being passed correctly
- Check hover_threshold value (typically 1.5 seconds)
- Ensure button callback strings match handler logic
- Confirm `popup.active` is checked before game button processing

### Text overlapping in popup

- Use more grid rows for complex content
- Increase row_span for important content
- Check that col_span doesn't exceed grid.cols
- Consider separate layouts for vertical vs horizontal panels

## Performance Notes

- Grid calculations are cached per popup type
- Button hover detection is O(n) where n = number of buttons (typically ≤ 4)
- Drawing uses Pyglet's batch rendering for efficiency
- No performance impact when popup is not active

## Future Enhancements

Possible improvements for future versions:

- [ ] Animated popup transitions (slide in/fade in)
- [ ] Multi-page popups with pagination
- [ ] Scrollable content for long lists
- [ ] Custom button styles per popup type
- [ ] Sound effects for popup open/close
- [ ] Popup stacking (multiple popups)
- [ ] Rich text formatting (bold, italic, colors)
- [ ] Image support in popups
- [ ] Confirmation dialogs with Yes/No/Cancel
- [ ] Progress bars in popups

## License

This popup system is part of the ARPi2 project and follows the same license.
