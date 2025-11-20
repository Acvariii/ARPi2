"""Popup UI drawing for Monopoly game."""
import pygame
from typing import Dict
from config import Colors
from ui_components import RotatedText, draw_circular_progress


class PopupDrawer:
    """Handles drawing all game popups."""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen

    def _draw_progress_indicator(self, progress_data: dict, orientation: int):
        """Draw hover progress indicator in orientation-aware position."""
        rect = progress_data["rect"]
        progress = progress_data["progress"]
        
        # Position indicator based on orientation
        if orientation == 0:  # Bottom panel - indicator top-right
            center = (rect.right - 18, rect.top + 18)
        elif orientation == 180:  # Top panel - indicator bottom-right (from their view: top-right)
            center = (rect.right - 18, rect.bottom - 18)
        elif orientation == 90:  # Left panel - indicator top-right
            center = (rect.right - 18, rect.top + 18)
        else:  # 270 - Right panel - indicator bottom-right (from their view: top-right)
            center = (rect.right - 18, rect.bottom - 18)
        
        draw_circular_progress(self.screen, center, 14, progress, Colors.ACCENT, thickness=4)

    def _content_area(self, panel) -> pygame.Rect:
        BUTTON_ROW_FRAC_VERTICAL = 0.22
        BUTTON_ROW_FRAC_HORIZONTAL = 0.38
        MARGIN = 8

        if panel.is_vertical():
            row_h = int(panel.rect.height * BUTTON_ROW_FRAC_VERTICAL)
        else:
            row_h = int(panel.rect.height * BUTTON_ROW_FRAC_HORIZONTAL)

        x = panel.rect.x + MARGIN
        y = panel.rect.y + MARGIN
        w = max(20, panel.rect.width - 2 * MARGIN)
        h = max(20, panel.rect.height - row_h - 2 * MARGIN)
        return pygame.Rect(x, y, w, h)

    def draw_buy_prompt(self, popup_data: Dict, panel, buttons: list):
        from ui_components import RotatedText
        player = popup_data["player"]
        space = popup_data["space"]
        price = popup_data["price"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        
        color = space.data.get("color", (180,180,180))
        name = space.data.get("name","")
        status_ok = player.money >= price
        status_text = "Can afford" if status_ok else "Cannot afford"
        status_color = (90,200,90) if status_ok else (230,90,90)
        
        # Get button area
        btn_area = buttons[0].rect.union(buttons[-1].rect) if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        
        # Content area - positioned consistently
        margin = 8
        if panel.orientation in (0, 180):  # Horizontal panels
            content_rect = pygame.Rect(
                panel.rect.x + btn_area.width + margin * 2,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
        else:  # Vertical panels
            if panel.orientation == 90:  # Left
                content_rect = pygame.Rect(
                    panel.rect.x + margin,
                    panel.rect.y + margin,
                    panel.rect.width - margin * 2,
                    panel.rect.height - btn_area.height - margin * 3
                )
            else:  # Right (270)
                content_rect = pygame.Rect(
                    panel.rect.x + margin,
                    panel.rect.y + btn_area.height + margin * 2,
                    panel.rect.width - margin * 2,
                    panel.rect.height - btn_area.height - margin * 3
                )
        
        # Color bar at top (8px thick)
        bar_h = 8
        bar_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_h)
        pygame.draw.rect(self.screen, color, bar_rect, border_radius=3)
        
        # Property name below color bar
        name_rect = pygame.Rect(
            content_rect.x,
            content_rect.y + bar_h + 6,
            content_rect.width,
            40
        )
        font_name = pygame.font.SysFont("Arial", 18, bold=True)
        RotatedText.draw_block(
            self.screen,
            [(name, font_name, Colors.WHITE)],
            name_rect,
            panel.orientation,
            line_spacing=4,
            wrap=True
        )
        
        # Details below name
        details_rect = pygame.Rect(
            content_rect.x,
            name_rect.bottom + 10,
            content_rect.width,
            content_rect.height - (name_rect.bottom - content_rect.y) - 10
        )
        
        font_label = pygame.font.SysFont("Arial", 14, bold=True)
        font_value = pygame.font.SysFont("Arial", 16)
        
        # Use larger spacing for horizontal panels
        spacing = 14 if panel.is_vertical() else 10
        
        RotatedText.draw_block(
            self.screen,
            [
                (f"Price: ${price}", font_value, Colors.ACCENT),
                (status_text, font_label, status_color),
                (f"Balance: ${player.money}", font_value, (200, 200, 200))
            ],
            details_rect,
            panel.orientation,
            line_spacing=spacing,
            padding=4
        )
        
        # Draw buttons with progress indicators
        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)

    def draw_card_popup(self, popup_data: Dict, panel, buttons: list):
        from ui_components import RotatedText
        card = popup_data["card"]
        deck_type = popup_data["deck_type"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)

        btn_area = buttons[0].rect if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        font_title = pygame.font.SysFont("Arial", 18, bold=True)
        font_text = pygame.font.SysFont("Arial", 14)
        title = "CHANCE" if deck_type == "chance" else "COMMUNITY CHEST"
        title_color = (255,200,60) if deck_type == "chance" else (100,180,255)

        # Content area
        margin = 8
        if panel.orientation in (0, 180):
            content_rect = pygame.Rect(
                panel.rect.x + btn_area.width + margin * 2,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
        else:
            if panel.orientation == 90:
                content_rect = pygame.Rect(
                    panel.rect.x + margin,
                    panel.rect.y + margin,
                    panel.rect.width - margin * 2,
                    panel.rect.height - btn_area.height - margin * 3
                )
            else:
                content_rect = pygame.Rect(
                    panel.rect.x + margin,
                    panel.rect.y + btn_area.height + margin * 2,
                    panel.rect.width - margin * 2,
                    panel.rect.height - btn_area.height - margin * 3
                )

        # Title bar
        bar_h = 5
        bar_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_h)
        pygame.draw.rect(self.screen, title_color, bar_rect, border_radius=2)

        # Title
        title_rect = pygame.Rect(
            content_rect.x,
            content_rect.y + bar_h + 4,
            content_rect.width,
            30
        )
        RotatedText.draw_block(
            self.screen,
            [(title, font_title, title_color)],
            title_rect,
            panel.orientation,
            line_spacing=4
        )

        # Card text
        text_rect = pygame.Rect(
            content_rect.x,
            title_rect.bottom + 10,
            content_rect.width,
            content_rect.height - (title_rect.bottom - content_rect.y) - 10
        )
        
        spacing = 10 if panel.is_vertical() else 8
        
        RotatedText.draw_block(
            self.screen,
            [(card.get("text", ""), font_text, Colors.WHITE)],
            text_rect,
            panel.orientation,
            line_spacing=spacing,
            padding=4,
            wrap=True
        )

        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)

    def draw_properties_popup(self, popup_data: Dict, panel, properties, property_scroll: int, buttons: list):
        from ui_components import RotatedText
        player = popup_data["player"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)
        
        btn_area = buttons[0].rect.union(buttons[-1].rect) if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        
        # Content area
        margin = 8
        if panel.orientation in (0, 180):
            content_rect = pygame.Rect(
                panel.rect.x + btn_area.width + margin * 2,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
        else:
            if panel.orientation == 90:
                content_rect = pygame.Rect(
                    panel.rect.x + margin,
                    panel.rect.y + margin,
                    panel.rect.width - margin * 2,
                    panel.rect.height - btn_area.height - margin * 3
                )
            else:
                content_rect = pygame.Rect(
                    panel.rect.x + margin,
                    panel.rect.y + btn_area.height + margin * 2,
                    panel.rect.width - margin * 2,
                    panel.rect.height - btn_area.height - margin * 3
                )
        
        font_title = pygame.font.SysFont("Arial", 16, bold=True)
        font_line = pygame.font.SysFont("Arial", 13)
        font_small = pygame.font.SysFont("Arial", 11)
        
        if not player.properties:
            RotatedText.draw_block(
                self.screen,
                [("No properties owned", font_line, (200,200,200))],
                content_rect,
                panel.orientation,
                line_spacing=6
            )
        else:
            prop_idx = player.properties[property_scroll]
            prop = properties[prop_idx]
            color = prop.data.get("color",(180,180,180))
            
            # Color bar at top
            bar_h = 6
            bar_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_h)
            pygame.draw.rect(self.screen, color, bar_rect, border_radius=3)
            
            # Property name
            name_rect = pygame.Rect(
                content_rect.x,
                content_rect.y + bar_h + 4,
                content_rect.width,
                35
            )
            RotatedText.draw_block(
                self.screen,
                [(prop.data.get("name",""), font_title, Colors.WHITE)],
                name_rect,
                panel.orientation,
                line_spacing=4,
                wrap=True
            )
            
            # Details
            details_rect = pygame.Rect(
                content_rect.x,
                name_rect.bottom + 8,
                content_rect.width,
                content_rect.height - (name_rect.bottom - content_rect.y) - 35
            )
            
            details = [
                f"Type: {prop.data.get('type','property').title()}",
                f"Value: ${prop.data.get('price',0)}",
            ]
            if prop.data.get("type") == "property":
                details.append(f"Houses: {prop.houses}")
                if prop.houses > 0:
                    rent_list = prop.data.get("rent",[0])
                    rent_val = rent_list[min(prop.houses,len(rent_list)-1)]
                    details.append(f"Rent: ${rent_val}")
            details.append(f"Status: {'Mortgaged' if prop.is_mortgaged else 'Active'}")
            
            spacing = 12 if panel.is_vertical() else 8
            
            RotatedText.draw_block(
                self.screen,
                [(d, font_line, Colors.WHITE) for d in details],
                details_rect,
                panel.orientation,
                line_spacing=spacing,
                padding=4
            )
            
            # Page indicator at bottom
            page_rect = pygame.Rect(
                content_rect.x,
                content_rect.bottom - 20,
                content_rect.width,
                18
            )
            RotatedText.draw_block(
                self.screen,
                [(f"{property_scroll + 1}/{len(player.properties)}", font_small, (140,140,140))],
                page_rect,
                panel.orientation,
                line_spacing=4
            )
        
        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)

    def draw_build_popup(self, panel, buttons: list):
        from ui_components import RotatedText
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        btn_area = buttons[0].rect if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        
        # Content area - consistent positioning
        if panel.orientation in (0, 180):  # Horizontal panels
            content_rect = pygame.Rect(panel.rect.x + btn_area.width + 12,
                                       panel.rect.y + 8,
                                       panel.rect.width - btn_area.width - 20,
                                       panel.rect.height - 16)
        else:  # Vertical panels
            if panel.orientation == 90:  # Left panel
                content_rect = pygame.Rect(panel.rect.x + 8,
                                          panel.rect.y + 8,
                                          panel.rect.width - 16,
                                          panel.rect.height - btn_area.height - 20)
            else:  # Right panel (270)
                content_rect = pygame.Rect(panel.rect.x + 8,
                                          panel.rect.y + btn_area.height + 12,
                                          panel.rect.width - 16,
                                          panel.rect.height - btn_area.height - 20)
        
        RotatedText.draw_block(self.screen,
                               [("Building (Coming Soon)", font_title, Colors.ACCENT)],
                               content_rect, panel.orientation, line_spacing=8)
        
        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)