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
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, panel.rect)
        color = space.data.get("color", (180,180,180))
        name = space.data.get("name","")
        font_name = pygame.font.SysFont("Arial", 22, bold=True)
        font_label = pygame.font.SysFont("Arial", 16)
        font_price = pygame.font.SysFont("Arial", 24, bold=True)
        status_ok = player.money >= price
        status_text = "Can afford" if status_ok else "Cannot afford"
        status_color = (90,200,90) if status_ok else (230,90,90)

        btn_area = buttons[0].rect.union(buttons[-1].rect)
        if panel.orientation in (0,180):
            right_rect = pygame.Rect(panel.rect.x + btn_area.width + 12,
                                     panel.rect.y + 8,
                                     panel.rect.width - btn_area.width - 20,
                                     panel.rect.height - 16)
        elif panel.orientation == 90:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + 8,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)
        else:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + btn_area.height + 12,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)

        # Color bar
        bar_h = 6
        if panel.orientation in (0,180):
            bar = pygame.Rect(right_rect.x, right_rect.y, right_rect.width, bar_h)
        else:
            bar = pygame.Rect(right_rect.x, right_rect.y, right_rect.width, bar_h)
        pygame.draw.rect(self.screen, color, bar, border_radius=3)

        # Table-style layout lines
        lines = [
            f"{name}",
            f"Price: ${price}",
            f"{status_text}",
            f"Balance: ${player.money}"
        ]
        RotatedText.draw_block(self.screen,
                               [(lines[0], font_name, Colors.WHITE)],
                               pygame.Rect(right_rect.x, right_rect.y + bar_h + 4, right_rect.width, 50),
                               panel.orientation, line_spacing=4, wrap=True)
        RotatedText.draw_block(self.screen,
                               [(lines[1], font_price, Colors.ACCENT),
                                (lines[2], font_label, status_color),
                                (lines[3], font_label, (210,210,210))],
                               pygame.Rect(right_rect.x, right_rect.y + bar_h + 60, right_rect.width, right_rect.height - 70),
                               panel.orientation, line_spacing=10, wrap=False)

        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (pr["rect"].centerx + 18, pr["rect"].top - 18),
                                       14, pr["progress"], Colors.ACCENT, thickness=4)

    def draw_card_popup(self, popup_data: Dict, panel, buttons: list):
        from ui_components import RotatedText
        card = popup_data["card"]
        deck_type = popup_data["deck_type"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)

        btn_area = buttons[0].rect
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        font_text = pygame.font.SysFont("Arial", 15)
        title = "CHANCE" if deck_type == "chance" else "COMMUNITY CHEST"
        title_color = (255,200,60) if deck_type == "chance" else (100,180,255)

        if panel.orientation in (0,180):
            right_rect = pygame.Rect(panel.rect.x + btn_area.width + 12,
                                     panel.rect.y + 8,
                                     panel.rect.width - btn_area.width - 20,
                                     panel.rect.height - 16)
        elif panel.orientation == 90:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + 8,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)
        else:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + btn_area.height + 12,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)

        bar = pygame.Rect(right_rect.x, right_rect.y, right_rect.width, 4)
        pygame.draw.rect(self.screen, title_color, bar, border_radius=2)

        RotatedText.draw_block(self.screen,
                               [(title, font_title, title_color)],
                               pygame.Rect(right_rect.x, right_rect.y + 6, right_rect.width, 48),
                               panel.orientation, line_spacing=6)
        RotatedText.draw_block(self.screen,
                               [(card.get("text",""), font_text, Colors.WHITE)],
                               pygame.Rect(right_rect.x, right_rect.y + 58, right_rect.width, right_rect.height - 64),
                               panel.orientation, line_spacing=8, wrap=True)

        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (pr["rect"].centerx + 16, pr["rect"].top - 16),
                                       14, pr["progress"], Colors.ACCENT, thickness=4)

    def draw_properties_popup(self, popup_data: Dict, panel, properties, property_scroll: int, buttons: list):
        from ui_components import RotatedText
        player = popup_data["player"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)
        font_title = pygame.font.SysFont("Arial", 18, bold=True)
        font_line = pygame.font.SysFont("Arial", 14)
        font_small = pygame.font.SysFont("Arial", 12)

        btn_area = buttons[0].rect.union(buttons[-1].rect) if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        if panel.orientation in (0,180):
            right_rect = pygame.Rect(panel.rect.x + btn_area.width + 12,
                                     panel.rect.y + 8,
                                     panel.rect.width - btn_area.width - 20,
                                     panel.rect.height - 16)
        elif panel.orientation == 90:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + 8,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)
        else:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + btn_area.height + 12,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)

        if not player.properties:
            RotatedText.draw_block(self.screen,
                                   [("No properties owned", font_line, (200,200,200))],
                                   right_rect, panel.orientation, line_spacing=6)
        else:
            prop_idx = player.properties[property_scroll]
            prop = properties[prop_idx]
            color = prop.data.get("color",(180,180,180))
            bar = pygame.Rect(right_rect.x, right_rect.y, right_rect.width, 5)
            pygame.draw.rect(self.screen, color, bar, border_radius=3)

            name_rect = pygame.Rect(right_rect.x, right_rect.y + 8, right_rect.width, 46)
            RotatedText.draw_block(self.screen,
                                   [(prop.data.get("name",""), font_title, Colors.WHITE)],
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

            body_rect = pygame.Rect(right_rect.x, name_rect.bottom + 6, right_rect.width, right_rect.height - 80)
            RotatedText.draw_block(self.screen,
                                   [(d, font_line, Colors.WHITE) for d in details],
                                   body_rect, panel.orientation, line_spacing=6)

            page_rect = pygame.Rect(right_rect.x, right_rect.bottom - 30, right_rect.width, 24)
            RotatedText.draw_block(self.screen,
                                   [(f"{property_scroll + 1}/{len(player.properties)}", font_small, (140,140,140))],
                                   page_rect, panel.orientation, line_spacing=6)

        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (pr["rect"].centerx + 16, pr["rect"].top - 16),
                                       14, pr["progress"], Colors.ACCENT, thickness=4)

    def draw_build_popup(self, panel, buttons: list):
        from ui_components import RotatedText
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        btn_area = buttons[0].rect if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        if panel.orientation in (0,180):
            right_rect = pygame.Rect(panel.rect.x + btn_area.width + 12,
                                     panel.rect.y + 8,
                                     panel.rect.width - btn_area.width - 20,
                                     panel.rect.height - 16)
        elif panel.orientation == 90:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + 8,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)
        else:
            right_rect = pygame.Rect(panel.rect.x + 8,
                                     panel.rect.y + btn_area.height + 12,
                                     panel.rect.width - 16,
                                     panel.rect.height - btn_area.height - 20)
        RotatedText.draw_block(self.screen,
                               [("Building (Coming Soon)", font_title, Colors.ACCENT)],
                               right_rect, panel.orientation, line_spacing=8)
        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                draw_circular_progress(self.screen,
                                       (pr["rect"].centerx + 16, pr["rect"].top - 16),
                                       14, pr["progress"], Colors.ACCENT, thickness=4)