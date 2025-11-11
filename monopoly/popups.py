"""Popup UI drawing for Monopoly game."""
import pygame
from typing import Dict
from config import Colors
from ui_components import RotatedText, draw_circular_progress


class PopupDrawer:
    """Handles drawing all game popups."""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
    
    def _content_area(self, panel) -> pygame.Rect:
        # Single consistent content rectangle (above button row)
        if panel.is_vertical():
            return panel.get_grid_rect(0.1, 0.6, 3.8, 7.5, 4, 12)
        else:
            return panel.get_grid_rect(0.6, 0.3, 10.8, 2.4, 12, 4)

    def draw_buy_prompt(self, popup_data: Dict, panel, buttons: list):
        from ui_components import RotatedText
        player = popup_data["player"]
        space = popup_data["space"]
        price = popup_data["price"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, panel.rect)

        content_rect = self._content_area(panel)
        color = space.data.get("color", (180,180,180))
        bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 6)
        pygame.draw.rect(self.screen, color, bar, border_radius=3)

        font_title = pygame.font.SysFont("Arial", 24, bold=True)
        font_body  = pygame.font.SysFont("Arial", 18)
        font_price = pygame.font.SysFont("Arial", 28, bold=True)

        name = space.data.get("name","")
        status_ok = player.money >= price
        status_text = "✓ Can afford" if status_ok else "✗ Cannot afford"
        status_col = (100,220,100) if status_ok else (255,100,100)

        lines = [
            (name, font_title, Colors.WHITE),
            ("Price", font_body, (170,170,170)),
            (f"${price}", font_price, Colors.ACCENT),
            (status_text, font_body, status_col),
            (f"Balance: ${player.money}", font_body, (210,210,210))
        ]
        RotatedText.draw_block(self.screen, lines, content_rect, panel.orientation, line_spacing=10)

        for btn in buttons:
            btn.draw(self.screen)
            for p in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (p["rect"].centerx + 20, p["rect"].top - 20),
                                       16, p["progress"], Colors.ACCENT, thickness=4)

    def draw_card_popup(self, popup_data: Dict, panel, buttons: list):
        from ui_components import RotatedText
        card = popup_data["card"]
        deck_type = popup_data["deck_type"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,190))
        self.screen.blit(overlay, panel.rect)

        content_rect = self._content_area(panel)
        title_color = (255,200,60) if deck_type == "chance" else (100,180,255)
        bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 5)
        pygame.draw.rect(self.screen, title_color, bar, border_radius=2)

        font_title = pygame.font.SysFont("Arial", 22, bold=True)
        font_text  = pygame.font.SysFont("Arial", 16)

        # Use wrap (single text line entry)
        lines = [
            (("CHANCE" if deck_type=="chance" else "COMMUNITY CHEST"), font_title, title_color),
            (card.get("text",""), font_text, Colors.WHITE)
        ]
        # First line remains single; wrap second
        RotatedText.draw_block(
            self.screen,
            [lines[0]],
            pygame.Rect(content_rect.x, content_rect.y + 8, content_rect.width, 60),
            panel.orientation,
            line_spacing=6
        )
        RotatedText.draw_block(
            self.screen,
            [lines[1]],
            pygame.Rect(content_rect.x, content_rect.y + 70, content_rect.width, content_rect.height - 80),
            panel.orientation,
            line_spacing=10,
            wrap=True
        )

        for btn in buttons:
            btn.draw(self.screen)
            for p in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (p["rect"].centerx + 20, p["rect"].top - 20),
                                       16, p["progress"], Colors.ACCENT, thickness=4)

    def draw_properties_popup(self, popup_data: Dict, panel, properties, property_scroll: int, buttons: list):
        from ui_components import RotatedText
        player = popup_data["player"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,190))
        self.screen.blit(overlay, panel.rect)
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        font_line  = pygame.font.SysFont("Arial", 14)
        font_small = pygame.font.SysFont("Arial", 12)

        content_rect = self._content_area(panel)

        if not player.properties:
            RotatedText.draw_block(self.screen,
                                   [("No properties owned", font_line, (200,200,200))],
                                   content_rect, panel.orientation)
        else:
            prop_idx = player.properties[property_scroll]
            prop = properties[prop_idx]
            color = prop.data.get("color",(180,180,180))
            bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 5)
            pygame.draw.rect(self.screen, color, bar, border_radius=2)

            name = prop.data.get("name","")
            details = [
                f"Type: {prop.data.get('type','property').title()}",
                f"Value: ${prop.data.get('price',0)}"
            ]
            if prop.data.get("type") == "property":
                details.append(f"Houses: {prop.houses}")
                if prop.houses > 0:
                    rent_list = prop.data.get("rent",[0])
                    rent_val = rent_list[min(prop.houses,len(rent_list)-1)]
                    details.append(f"Rent: ${rent_val}")
            details.append(f"Status: {'Mortgaged' if prop.is_mortgaged else 'Active'}")

            RotatedText.draw_block(self.screen,
                                   [(name, font_title, Colors.WHITE)],
                                   pygame.Rect(content_rect.x, content_rect.y + 10,
                                               content_rect.width, 60),
                                   panel.orientation,
                                   line_spacing=6)

            RotatedText.draw_block(self.screen,
                                   [(d, font_line, Colors.WHITE) for d in details],
                                   pygame.Rect(content_rect.x, content_rect.y + 80,
                                               content_rect.width, content_rect.height - 130),
                                   panel.orientation,
                                   line_spacing=10)

            page = f"{property_scroll + 1} / {len(player.properties)}"
            RotatedText.draw_block(self.screen,
                                   [(page, font_small, (140,140,140))],
                                   pygame.Rect(content_rect.x, content_rect.bottom - 40,
                                               content_rect.width, 30),
                                   panel.orientation)

        for btn in buttons:
            btn.draw(self.screen)
            for p in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (p["rect"].centerx + 20, p["rect"].top - 20),
                                       16, p["progress"], Colors.ACCENT, thickness=4)

    def draw_build_popup(self, panel, buttons: list):
        from ui_components import RotatedText
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,190))
        self.screen.blit(overlay, panel.rect)
        font = pygame.font.SysFont("Arial", 24, bold=True)
        content_rect = self._content_area(panel)
        RotatedText.draw_block(self.screen,
                               [("Building (Coming Soon)", font, Colors.ACCENT)],
                               content_rect, panel.orientation)
        for btn in buttons:
            btn.draw(self.screen)
            for p in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (p["rect"].centerx + 20, p["rect"].top - 20),
                                       16, p["progress"], Colors.ACCENT, thickness=4)