# Monopoly UI Consistency Fixes

## Overview

Fixed inconsistencies in the Monopoly game UI across different player positions (bottom, top, left, right) to ensure all players have the same UI experience from their point of view.

## Changes Made

### 1. Button Initialization (`monopoly/game.py` - `_init_buttons()`)

**Problem:** Button layout logic was inconsistent between horizontal and vertical panels.

**Fix:**

- Standardized button positioning across all orientations
- All panels now have buttons arranged horizontally in a row at the "bottom" from each player's perspective
- Consistent margin (10px) and gap (12px) values
- Same button size calculation for all orientations

### 2. Popup Button Layout (`monopoly/game.py` - `_popup_button_column()`)

**Problem:** Popup buttons were positioned differently based on orientation, creating visual inconsistency.

**Fix:**

- Orientation 0 (bottom): Buttons on left side vertically
- Orientation 180 (top): Buttons on right side vertically (which is left from their view)
- Orientation 90 (left): Buttons at bottom horizontally (which is left from their view)
- Orientation 270 (right): Buttons at top horizontally (which is left from their view)
- All players now see buttons in the same relative position (left side of popup)

### 3. Popup Content Area (`monopoly/popups.py` - all popup methods)

**Problem:** Content area calculations were inconsistent and didn't properly account for button positions.

**Fix:**

- **Horizontal panels (0, 180):** Content to the right of buttons
- **Vertical left panel (90):** Buttons at bottom, content above
- **Vertical right panel (270):** Buttons at top, content below
- All popups now use consistent content area calculations:
  - `draw_buy_prompt()`
  - `draw_card_popup()`
  - `draw_properties_popup()`
  - `draw_build_popup()`

### 4. Hover Progress Indicators (`monopoly/popups.py` - `_draw_progress_indicator()`)

**Problem:** Progress indicators were positioned at fixed offsets, not accounting for orientation.

**Fix:**

- Added new helper method `_draw_progress_indicator()`
- Indicators now positioned consistently in the top-right corner from each player's perspective:
  - Orientation 0: Top-right of button
  - Orientation 180: Bottom-right (their top-right)
  - Orientation 90: Top-right
  - Orientation 270: Bottom-right (their top-right)

## Result

All players (bottom, top, left, right) now experience:

- Consistent button layout (horizontal row at bottom of their panel)
- Consistent popup layout (buttons on left, content on right)
- Consistent hover feedback indicators
- Same visual hierarchy and spacing

## Testing Recommendations

1. Start a game with players in all 8 positions
2. For each player:
   - Verify "Roll", "Props", "Build" buttons appear in the same relative position
   - Land on a property and check the buy prompt layout
   - Draw a card and check the card popup layout
   - Open properties popup and verify navigation buttons
3. Confirm hover progress indicators appear in the expected position for all orientations
