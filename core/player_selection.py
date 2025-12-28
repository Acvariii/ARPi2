"""Player selection UI for Pyglet games."""
import time
from typing import List, Dict, Tuple
from config import PLAYER_COLORS, HOVER_TIME_THRESHOLD, Colors


class PlayerSelectionUI:
    """Player selection screen with 8 player slots."""
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected = [False] * 8
        self.hover_states = {}
        self.start_ready = False  # Track if start button was clicked
        
        # Calculate slot positions
        self.slots = self._calculate_slots()
        
        # Start button in center
        self.start_button_pos = (screen_width // 2, screen_height // 2)
        self.start_button_radius = 80
    
    def _calculate_slots(self) -> List[Tuple[int, int, int, int]]:
        """Calculate circular position for each player slot (x, y, radius, radius)."""
        slots = []
        
        # Circular layout matching Pygame
        spacing_x = self.screen_width // 4
        spacing_y = self.screen_height // 3
        slot_radius = 55
        
        # Positions: 3 bottom, 3 top, 1 left, 1 right
        positions = [
            (spacing_x * 1, self.screen_height - spacing_y // 2),  # Bottom left
            (spacing_x * 2, self.screen_height - spacing_y // 2),  # Bottom center
            (spacing_x * 3, self.screen_height - spacing_y // 2),  # Bottom right
            (spacing_x * 1, spacing_y // 2),  # Top left
            (spacing_x * 2, spacing_y // 2),  # Top center
            (spacing_x * 3, spacing_y // 2),  # Top right
            (spacing_x // 2, self.screen_height // 2),  # Left
            (self.screen_width - spacing_x // 2, self.screen_height // 2)  # Right
        ]
        
        for x, y in positions:
            # Return as (x, y, radius, radius) for compatibility
            slots.append((x - slot_radius, y - slot_radius, slot_radius * 2, slot_radius * 2))
        
        return slots
    
    def update_with_fingertips(self, fingertip_meta: List[Dict], min_players: int = 2):
        """Update selection based on fingertip positions."""
        current_time = time.time()
        active_hovers = set()
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            is_click = bool(meta.get("click"))
            
            # Check start button first (if enough players selected)
            if self.selected_count() >= min_players:
                cx, cy = self.start_button_pos
                dist = ((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2) ** 0.5
                
                if dist <= self.start_button_radius:
                    if is_click:
                        self.start_ready = True
                        continue
                    key = "start_button"
                    active_hovers.add(key)
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self.start_ready = True
                        del self.hover_states[key]
                    continue
            
            # Check player slots
            for i, (x, y, w, h) in enumerate(self.slots):
                # Calculate center and check circular distance
                cx = x + w // 2
                cy = y + h // 2
                radius = w // 2
                dist = ((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2) ** 0.5
                
                if dist <= radius:
                    if is_click:
                        if i != 7:
                            self.selected[i] = not self.selected[i]
                        break
                    key = f"slot_{i}"
                    active_hovers.add(key)
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        # Don't allow deselecting Player 8 (DM)
                        if i != 7:
                            self.selected[i] = not self.selected[i]
                        del self.hover_states[key]
                    break
        
        # Remove stale hover states
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
    
    def get_hover_progress(self) -> List[Dict]:
        """Get hover progress for each active slot."""
        current_time = time.time()
        progress_list = []
        
        for key, state in self.hover_states.items():
            slot_idx = int(key.split("_")[1])
            hover_duration = current_time - state["start_time"]
            progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
            x, y, w, h = self.slots[slot_idx]
            progress_list.append({
                "pos": (x, y),
                "progress": progress,
                "slot": slot_idx
            })
        
        return progress_list
    
    def selected_count(self) -> int:
        """Get number of selected players."""
        return sum(self.selected)
    
    def get_selected_indices(self) -> List[int]:
        """Get list of selected player indices."""
        return [i for i, selected in enumerate(self.selected) if selected]
    
    def reset(self):
        """Reset all selections."""
        self.selected = [False] * 8
        self.hover_states = {}
        self.start_ready = False
    
    def closest_player_color(self, pos: Tuple[int, int]) -> Tuple[int, int, int]:
        """Get the closest player color for a cursor position."""
        min_dist = float('inf')
        closest_idx = 0
        
        for i, (x, y, w, h) in enumerate(self.slots):
            cx = x + w // 2
            cy = y + h // 2
            dist = ((pos[0] - cx) ** 2 + (pos[1] - cy) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        
        return PLAYER_COLORS[closest_idx]
