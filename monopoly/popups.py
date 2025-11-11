"""Popup UI drawing for Monopoly game."""
import pygame
from typing import Dict
from config import Colors
from ui_components import RotatedText, draw_circular_progress


class PopupDrawer:
    """Handles drawing all game popups."""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
    
    def draw_buy_prompt(self, popup_data: Dict, panel, buttons: list):
        """Draw property purchase prompt."""
        player = popup_data["player"]
        position = popup_data["position"]
        price = popup_data["price"]
        space = popup_data["space"]
        
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        font_title = pygame.font.SysFont("Arial", 22, bold=True)
        font_info = pygame.font.SysFont("Arial", 16)
        font_price = pygame.font.SysFont("Arial", 26, bold=True)
        
        name = space.data.get("name", "")
        price_text = f"${price}"
        
        if panel.is_vertical():
            content_rect = panel.get_grid_rect(0.4, 2, 1.2, 5, 4, 12)
        else:
            content_rect = panel.get_grid_rect(1.5, 0.8, 6, 2, 12, 4)
        
        color = space.data.get("color", (200, 200, 200))
        bar_height = 5
        color_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_height)
        pygame.draw.rect(self.screen, color, color_bar, border_radius=2)
        
        y = content_rect.y + bar_height + 25
        RotatedText.draw(self.screen, name, font_title, Colors.WHITE,
                       (content_rect.centerx, y), panel.orientation, 
                       max_width=content_rect.width - 20)
        
        y += 45
        RotatedText.draw(self.screen, "Price", font_info, (180, 180, 180),
                       (content_rect.centerx, y), panel.orientation)
        
        y += 35
        RotatedText.draw(self.screen, price_text, font_price, Colors.ACCENT,
                       (content_rect.centerx, y), panel.orientation)
        
        y += 50
        if player.money >= price:
            status_text = "✓ Can afford"
            status_color = (100, 220, 100)
        else:
            status_text = "✗ Cannot afford"
            status_color = (255, 100, 100)
        
        RotatedText.draw(self.screen, status_text, font_info, status_color,
                       (content_rect.centerx, y), panel.orientation)
        
        y += 35
        balance_text = f"Balance: ${player.money}"
        RotatedText.draw(self.screen, balance_text, font_info, (200, 200, 200),
                       (content_rect.centerx, y), panel.orientation)
        
        for btn in buttons:
            btn.draw(self.screen)
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(self.screen, (center_x, center_y), 16,
                                     progress_info["progress"], Colors.ACCENT, thickness=4)
    
    def draw_card_popup(self, popup_data: Dict, panel, buttons: list):
        """Draw card text popup."""
        card = popup_data["card"]
        deck_type = popup_data["deck_type"]
        
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        font_text = pygame.font.SysFont("Arial", 14)
        
        title = "CHANCE" if deck_type == "chance" else "COMMUNITY CHEST"
        card_text = card.get("text", "")
        title_color = (255, 200, 60) if deck_type == "chance" else (100, 180, 255)
        
        if panel.is_vertical():
            content_rect = panel.get_grid_rect(0.4, 2, 1.2, 5, 4, 12)
        else:
            content_rect = panel.get_grid_rect(1.5, 0.8, 6, 2, 12, 4)
        
        bar_height = 3
        top_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_height)
        pygame.draw.rect(self.screen, title_color, top_bar, border_radius=2)
        
        title_y = content_rect.y + bar_height + 25
        RotatedText.draw(self.screen, title, font_title, title_color,
                       (content_rect.centerx, title_y), panel.orientation)
        
        text_area = content_rect.copy()
        text_area.y = title_y + 40
        text_area.height = content_rect.height - 70
        text_area = text_area.inflate(-40, -40)
        
        RotatedText.draw_wrapped(self.screen, card_text, font_text, Colors.WHITE,
                               text_area, panel.orientation)
        
        for btn in buttons:
            btn.draw(self.screen)
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(self.screen, (center_x, center_y), 16,
                                     progress_info["progress"], Colors.ACCENT, thickness=4)
    
    def draw_properties_popup(self, popup_data: Dict, panel, properties, property_scroll: int, buttons: list):
        """Draw properties list popup."""
        player = popup_data["player"]
        
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        font_title = pygame.font.SysFont("Arial", 18, bold=True)
        font_label = pygame.font.SysFont("Arial", 13)
        font_value = pygame.font.SysFont("Arial", 14, bold=True)
        font_small = pygame.font.SysFont("Arial", 12)
        
        if not player.properties:
            no_props_text = "No properties owned"
            RotatedText.draw(self.screen, no_props_text, font_value, (180, 180, 180),
                           (panel.rect.centerx, panel.rect.centery), panel.orientation)
        else:
            prop_idx = player.properties[property_scroll]
            prop = properties[prop_idx]
            
            if panel.is_vertical():
                content_rect = panel.get_grid_rect(0.4, 2, 1.2, 5, 4, 12)
            else:
                content_rect = panel.get_grid_rect(1.5, 0.8, 6, 2, 12, 4)
            
            color = prop.data.get("color", (200, 200, 200))
            bar_height = 5
            color_bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_height)
            pygame.draw.rect(self.screen, color, color_bar, border_radius=2)
            
            name = prop.data.get("name", "")
            name_y = content_rect.y + bar_height + 25
            RotatedText.draw(self.screen, name, font_title, Colors.WHITE,
                           (content_rect.centerx, name_y), panel.orientation,
                           max_width=content_rect.width - 20)
            
            y = name_y + 45
            line_spacing = 28
            
            details = [
                f"Type: {prop.data.get('type', 'property').title()}",
                f"Value: ${prop.data.get('price', 0)}",
            ]
            
            if prop.data.get("type") == "property":
                details.append(f"Houses: {prop.houses}")
                if prop.houses > 0:
                    rent = prop.data.get("rent", [0])[min(prop.houses, len(prop.data.get("rent", [0])) - 1)]
                    details.append(f"Rent: ${rent}")
            
            details.append(f"Status: {'Mortgaged' if prop.is_mortgaged else 'Active'}")
            
            for detail in details:
                RotatedText.draw(self.screen, detail, font_label, Colors.WHITE,
                               (content_rect.centerx, y), panel.orientation)
                y += line_spacing
            
            page_text = f"Property {property_scroll + 1} of {len(player.properties)}"
            page_y = content_rect.bottom - 20
            RotatedText.draw(self.screen, page_text, font_small, (120, 120, 120),
                           (content_rect.centerx, page_y), panel.orientation)
        
        for btn in buttons:
            btn.draw(self.screen)
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(self.screen, (center_x, center_y), 16,
                                     progress_info["progress"], Colors.ACCENT, thickness=4)
    
    def draw_build_popup(self, panel, buttons: list):
        """Draw building options popup."""
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        font_title = pygame.font.SysFont("Arial", 22, bold=True)
        title_text = "Building (Coming Soon)"
        RotatedText.draw(self.screen, title_text, font_title, Colors.ACCENT,
                       (panel.rect.centerx, panel.rect.centery), panel.orientation)
        
        for btn in buttons:
            btn.draw(self.screen)
            for progress_info in btn.get_hover_progress():
                center_x = progress_info["rect"].centerx + 20
                center_y = progress_info["rect"].top - 20
                draw_circular_progress(self.screen, (center_x, center_y), 16,
                                     progress_info["progress"], Colors.ACCENT, thickness=4)