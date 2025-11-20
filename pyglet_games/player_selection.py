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
        
        # Calculate slot positions
        self.slots = self._calculate_slots()
    
    def _calculate_slots(self) -> List[Tuple[int, int, int, int]]:
        """Calculate position and size of each player slot (x, y, width, height)."""
        slots = []
        
        # Panel dimensions
        panel_width = self.screen_width - 160
        panel_height = self.screen_height - 120
        panel_x = 80
        panel_y = 60
        
        # Slot dimensions
        slot_width = 180
        slot_height = 200
        spacing = 20
        
        # Calculate grid layout (4x2)
        total_width = (slot_width * 4) + (spacing * 3)
        total_height = (slot_height * 2) + spacing
        
        start_x = panel_x + (panel_width - total_width) // 2
        start_y = panel_y + 140
        
        for row in range(2):
            for col in range(4):
                x = start_x + col * (slot_width + spacing)
                y = start_y + row * (slot_height + spacing)
                slots.append((x, y, slot_width, slot_height))
        
        return slots
    
    def update_with_fingertips(self, fingertip_meta: List[Dict]):
        """Update selection based on fingertip positions."""
        current_time = time.time()
        active_hovers = set()
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            for i, (x, y, w, h) in enumerate(self.slots):
                if x <= pos[0] <= x + w and y <= pos[1] <= y + h:
                    key = f"slot_{i}"
                    active_hovers.add(key)
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self.selected[i] = not self.selected[i]
                        del self.hover_states[key]
        
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
