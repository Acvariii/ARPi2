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
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, panel.rect)

        content_rect = self._content_area(panel)
        color = space.data.get("color", (180,180,180))
        bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 5)
        pygame.draw.rect(self.screen, color, bar, border_radius=3)

        if panel.is_vertical():
            font_title = pygame.font.SysFont("Arial", 22, bold=True)
            font_body  = pygame.font.SysFont("Arial", 16)
            font_price = pygame.font.SysFont("Arial", 26, bold=True)
        else:
            font_title = pygame.font.SysFont("Arial", 18, bold=True)
            font_body  = pygame.font.SysFont("Arial", 14)
            font_price = pygame.font.SysFont("Arial", 22, bold=True)

        name = space.data.get("name","")
        status_ok = player.money >= price
        status_text = "✓ Can afford" if status_ok else "✗ Cannot afford"
        status_col = (100,220,100) if status_ok else (255,100,100)

        header_h = max(34, min(72, content_rect.height // 3))
        name_rect = pygame.Rect(content_rect.x, content_rect.y + 8, content_rect.width, header_h)
        body_rect = pygame.Rect(content_rect.x, name_rect.bottom + 4, content_rect.width, content_rect.bottom - (name_rect.bottom + 4))

        RotatedText.draw_block(
            self.screen,
            [(name, font_title, Colors.WHITE)],
            name_rect, panel.orientation, line_spacing=6, wrap=True
        )
        RotatedText.draw_block(
            self.screen,
            [("Price", font_body, (170,170,170)),
             (f"${price}", font_price, Colors.ACCENT),
             (status_text, font_body, status_col),
             (f"Balance: ${player.money}", font_body, (210,210,210))],
            body_rect, panel.orientation, line_spacing=8, wrap=False
        )

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
        bar = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, 4)
        pygame.draw.rect(self.screen, title_color, bar, border_radius=2)

        if panel.is_vertical():
            font_title = pygame.font.SysFont("Arial", 20, bold=True)
            font_text  = pygame.font.SysFont("Arial", 15)
        else:
            font_title = pygame.font.SysFont("Arial", 18, bold=True)
            font_text  = pygame.font.SysFont("Arial", 14)

        header_h = max(30, min(64, content_rect.height // 4))
        title_rect = pygame.Rect(content_rect.x, content_rect.y + 8, content_rect.width, header_h)
        text_rect = pygame.Rect(content_rect.x, title_rect.bottom + 6, content_rect.width, content_rect.bottom - (title_rect.bottom + 6))

        RotatedText.draw_block(
            self.screen,
            [("CHANCE" if deck_type=="chance" else "COMMUNITY CHEST", font_title, title_color)],
            title_rect, panel.orientation, line_spacing=6
        )
        RotatedText.draw_block(
            self.screen,
            [(card.get("text",""), font_text, Colors.WHITE)],
            text_rect, panel.orientation, line_spacing=8, wrap=True
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

        if panel.is_vertical():
            font_title = pygame.font.SysFont("Arial", 20, bold=True)
            font_line  = pygame.font.SysFont("Arial", 14)
            font_small = pygame.font.SysFont("Arial", 12)
        else:
            font_title = pygame.font.SysFont("Arial", 18, bold=True)
            font_line  = pygame.font.SysFont("Arial", 13)
            font_small = pygame.font.SysFont("Arial", 11)

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

            header_h = max(30, min(68, content_rect.height // 4))
            name_rect = pygame.Rect(content_rect.x, content_rect.y + 8, content_rect.width, header_h)
            details_rect = pygame.Rect(content_rect.x, name_rect.bottom + 6, content_rect.width, content_rect.bottom - (name_rect.bottom + 30))
            page_rect = pygame.Rect(content_rect.x, content_rect.bottom - 22, content_rect.width, 18)

            name = prop.data.get("name","")
            RotatedText.draw_block(self.screen,
                                   [(name, font_title, Colors.WHITE)],
                                   name_rect, panel.orientation, line_spacing=6, wrap=True)

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

            RotatedText.draw_block(self.screen,
                                   [(d, font_line, Colors.WHITE) for d in details],
                                   details_rect, panel.orientation, line_spacing=8, wrap=False)

            RotatedText.draw_block(self.screen,
                                   [(f"{property_scroll + 1} / {len(player.properties)}", font_small, (140,140,140))],
                                   page_rect, panel.orientation, line_spacing=6)

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