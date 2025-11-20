import pygame
from typing import Dict
from config import Colors
from ui_components import RotatedText, draw_circular_progress


class PopupDrawer:
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen

    def _draw_progress_indicator(self, progress_data: dict, orientation: int):
        rect = progress_data["rect"]
        progress = progress_data["progress"]
        
        if orientation == 0:
            center = (rect.right - 18, rect.top + 18)
        elif orientation == 180:
            center = (rect.right - 18, rect.bottom - 18)
        elif orientation == 90:
            center = (rect.right - 18, rect.top + 18)
        else:
            center = (rect.right - 18, rect.bottom - 18)
        
        draw_circular_progress(self.screen, center, 14, progress, Colors.ACCENT, thickness=4)

    def draw_buy_prompt(self, popup_data: Dict, panel, buttons: list):
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
        
        btn_area = buttons[0].rect.union(buttons[-1].rect) if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        
        margin = 10
        padding = 8
        
        if panel.orientation == 0:
            content_rect = pygame.Rect(
                btn_area.right + margin,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
            font_name = pygame.font.SysFont("Arial", 16, bold=True)
            font_big = pygame.font.SysFont("Arial", 16, bold=True)
            font_med = pygame.font.SysFont("Arial", 14, bold=True)
            font_small = pygame.font.SysFont("Arial", 12)
            
            bar_h = 14
            bar_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_h)
            pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
            
            text_y = content_rect.y + bar_h + padding
            RotatedText.draw_block(
                self.screen,
                [
                    (name, font_name, Colors.WHITE),
                    (f"${price}", font_big, Colors.ACCENT),
                    (status_text, font_med, status_color),
                    (f"Balance: ${player.money}", font_small, (200, 200, 200))
                ],
                pygame.Rect(content_rect.x + padding, text_y, content_rect.width - 2*padding, content_rect.height - bar_h - padding),
                panel.orientation,
                line_spacing=18,
                wrap=True
            )
        
        elif panel.orientation == 180:
            content_rect = pygame.Rect(
                btn_area.right + margin,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
            font_name = pygame.font.SysFont("Arial", 16, bold=True)
            font_big = pygame.font.SysFont("Arial", 16, bold=True)
            font_med = pygame.font.SysFont("Arial", 14, bold=True)
            font_small = pygame.font.SysFont("Arial", 12)
            
            bar_h = 14
            bar_rect = pygame.Rect(content_rect.x, content_rect.bottom - bar_h, content_rect.width, bar_h)
            pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
            
            text_y = content_rect.y
            RotatedText.draw_block(
                self.screen,
                [
                    (f"Balance: ${player.money}", font_small, (200, 200, 200)),
                    (status_text, font_med, status_color),
                    (f"${price}", font_big, Colors.ACCENT),
                    (name, font_name, Colors.WHITE)
                ],
                pygame.Rect(content_rect.x + padding, text_y, content_rect.width - 2*padding, content_rect.height - bar_h - padding),
                panel.orientation,
                line_spacing=18,
                wrap=True
            )
        
        elif panel.orientation == 90:
            content_rect = pygame.Rect(
                panel.rect.x + margin,
                btn_area.bottom + margin,
                panel.rect.width - margin * 2,
                panel.rect.height - btn_area.height - margin * 3
            )
            font_name = pygame.font.SysFont("Arial", 20, bold=True)
            font_big = pygame.font.SysFont("Arial", 20, bold=True)
            font_med = pygame.font.SysFont("Arial", 16, bold=True)
            font_small = pygame.font.SysFont("Arial", 14)
            
            bar_w = 14
            bar_rect = pygame.Rect(content_rect.x, content_rect.y, bar_w, content_rect.height)
            pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
            
            text_x = content_rect.x + bar_w + padding
            RotatedText.draw_block(
                self.screen,
                [
                    (name, font_name, Colors.WHITE),
                    (f"${price}", font_big, Colors.ACCENT),
                    (status_text, font_med, status_color),
                    (f"Balance: ${player.money}", font_small, (200, 200, 200))
                ],
                pygame.Rect(text_x, content_rect.y + padding, content_rect.width - bar_w - padding, content_rect.height - 2*padding),
                panel.orientation,
                line_spacing=24,
                wrap=True
            )
        
        else:
            content_rect = pygame.Rect(
                panel.rect.x + margin,
                btn_area.bottom + margin,
                panel.rect.width - margin * 2,
                panel.rect.height - btn_area.height - margin * 3
            )
            font_name = pygame.font.SysFont("Arial", 20, bold=True)
            font_big = pygame.font.SysFont("Arial", 20, bold=True)
            font_med = pygame.font.SysFont("Arial", 16, bold=True)
            font_small = pygame.font.SysFont("Arial", 14)
            
            bar_w = 14
            bar_rect = pygame.Rect(content_rect.right - bar_w, content_rect.y, bar_w, content_rect.height)
            pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
            
            text_x = content_rect.x
            RotatedText.draw_block(
                self.screen,
                [
                    (f"Balance: ${player.money}", font_small, (200, 200, 200)),
                    (status_text, font_med, status_color),
                    (f"${price}", font_big, Colors.ACCENT),
                    (name, font_name, Colors.WHITE)
                ],
                pygame.Rect(text_x, content_rect.y + padding, content_rect.width - bar_w - padding, content_rect.height - 2*padding),
                panel.orientation,
                line_spacing=24,
                wrap=True
            )
        
        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)

    def draw_card_popup(self, popup_data: Dict, panel, buttons: list):
        card = popup_data["card"]
        deck_type = popup_data["deck_type"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)

        btn_area = buttons[0].rect if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        title = "CHANCE" if deck_type == "chance" else "COMMUNITY CHEST"
        title_color = (255,200,60) if deck_type == "chance" else (100,180,255)
        margin = 10
        padding = 8
        
        if panel.orientation == 0:
            content_rect = pygame.Rect(btn_area.right + margin, panel.rect.y + margin,
                                      panel.rect.width - btn_area.width - margin * 3, panel.rect.height - margin * 2)
            font_title = pygame.font.SysFont("Arial", 15, bold=True)
            font_text = pygame.font.SysFont("Arial", 12)
            bar_h = 12
            bar_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_h)
            pygame.draw.rect(self.screen, title_color, bar_rect, border_radius=5)
            text_y = content_rect.y + bar_h + padding
            RotatedText.draw_block(self.screen, [(title, font_title, title_color), (card.get("text", ""), font_text, Colors.WHITE)],
                                  pygame.Rect(content_rect.x + padding, text_y, content_rect.width - 2*padding, content_rect.height - bar_h - padding),
                                  panel.orientation, line_spacing=16, wrap=True)
        elif panel.orientation == 180:
            content_rect = pygame.Rect(btn_area.right + margin, panel.rect.y + margin,
                                      panel.rect.width - btn_area.width - margin * 3, panel.rect.height - margin * 2)
            font_title = pygame.font.SysFont("Arial", 15, bold=True)
            font_text = pygame.font.SysFont("Arial", 12)
            bar_h = 12
            bar_rect = pygame.Rect(content_rect.x, content_rect.bottom - bar_h, content_rect.width, bar_h)
            pygame.draw.rect(self.screen, title_color, bar_rect, border_radius=5)
            text_y = content_rect.y
            RotatedText.draw_block(self.screen, [(card.get("text", ""), font_text, Colors.WHITE), (title, font_title, title_color)],
                                  pygame.Rect(content_rect.x + padding, text_y, content_rect.width - 2*padding, content_rect.height - bar_h - padding),
                                  panel.orientation, line_spacing=16, wrap=True)
        elif panel.orientation == 90:
            content_rect = pygame.Rect(panel.rect.x + margin, btn_area.bottom + margin,
                                      panel.rect.width - margin * 2, panel.rect.height - btn_area.height - margin * 3)
            font_title = pygame.font.SysFont("Arial", 18, bold=True)
            font_text = pygame.font.SysFont("Arial", 14)
            bar_w = 12
            bar_rect = pygame.Rect(content_rect.x, content_rect.y, bar_w, content_rect.height)
            pygame.draw.rect(self.screen, title_color, bar_rect, border_radius=5)
            text_x = content_rect.x + bar_w + padding
            RotatedText.draw_block(self.screen, [(title, font_title, title_color), (card.get("text", ""), font_text, Colors.WHITE)],
                                  pygame.Rect(text_x, content_rect.y + padding, content_rect.width - bar_w - padding, content_rect.height - 2*padding),
                                  panel.orientation, line_spacing=22, wrap=True)
        else:
            content_rect = pygame.Rect(panel.rect.x + margin, btn_area.bottom + margin,
                                      panel.rect.width - margin * 2, panel.rect.height - btn_area.height - margin * 3)
            font_title = pygame.font.SysFont("Arial", 18, bold=True)
            font_text = pygame.font.SysFont("Arial", 14)
            bar_w = 12
            bar_rect = pygame.Rect(content_rect.right - bar_w, content_rect.y, bar_w, content_rect.height)
            pygame.draw.rect(self.screen, title_color, bar_rect, border_radius=5)
            text_x = content_rect.x
            RotatedText.draw_block(self.screen, [(card.get("text", ""), font_text, Colors.WHITE), (title, font_title, title_color)],
                                  pygame.Rect(text_x, content_rect.y + padding, content_rect.width - bar_w - padding, content_rect.height - 2*padding),
                                  panel.orientation, line_spacing=22, wrap=True)

        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)

    def draw_properties_popup(self, popup_data: Dict, panel, properties, property_scroll: int, buttons: list):
        player = popup_data["player"]
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)
        
        btn_area = buttons[0].rect.union(buttons[-1].rect) if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        
        margin = 10
        if panel.orientation == 0:
            content_rect = pygame.Rect(
                btn_area.right + margin,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
        elif panel.orientation == 180:
            content_rect = pygame.Rect(
                btn_area.right + margin,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
        elif panel.orientation == 90:
            content_rect = pygame.Rect(
                panel.rect.x + margin,
                btn_area.bottom + margin,
                panel.rect.width - margin * 2,
                panel.rect.height - btn_area.height - margin * 3
            )
        else:
            content_rect = pygame.Rect(
                panel.rect.x + margin,
                btn_area.bottom + margin,
                panel.rect.width - margin * 2,
                panel.rect.height - btn_area.height - margin * 3
            )
        
        if panel.is_vertical():
            font_title = pygame.font.SysFont("Arial", 20, bold=True)
            font_line = pygame.font.SysFont("Arial", 16)
            font_small = pygame.font.SysFont("Arial", 14)
        else:
            font_title = pygame.font.SysFont("Arial", 15, bold=True)
            font_line = pygame.font.SysFont("Arial", 12)
            font_small = pygame.font.SysFont("Arial", 10)
        
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
            page_text = f"{property_scroll + 1}/{len(player.properties)}"
            
            if panel.orientation == 0:
                bar_h = 12
                bar_rect = pygame.Rect(content_rect.x, content_rect.y, content_rect.width, bar_h)
                pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
                text_y = content_rect.y + bar_h + 8
                items = [(prop.data.get("name",""), font_title, Colors.WHITE)] + [(d, font_line, Colors.WHITE) for d in details] + [(page_text, font_small, (140,140,140))]
                RotatedText.draw_block(self.screen, items, pygame.Rect(content_rect.x + 8, text_y, content_rect.width - 16, content_rect.height - bar_h - 8),
                                      panel.orientation, line_spacing=16, wrap=True)
            elif panel.orientation == 180:
                bar_h = 12
                bar_rect = pygame.Rect(content_rect.x, content_rect.bottom - bar_h, content_rect.width, bar_h)
                pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
                text_y = content_rect.y
                items = [(page_text, font_small, (140,140,140))] + [(d, font_line, Colors.WHITE) for d in reversed(details)] + [(prop.data.get("name",""), font_title, Colors.WHITE)]
                RotatedText.draw_block(self.screen, items, pygame.Rect(content_rect.x + 8, text_y, content_rect.width - 16, content_rect.height - bar_h - 8),
                                      panel.orientation, line_spacing=16, wrap=True)
            elif panel.orientation == 90:
                bar_w = 12
                bar_rect = pygame.Rect(content_rect.x, content_rect.y, bar_w, content_rect.height)
                pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
                text_x = content_rect.x + bar_w + 8
                items = [(prop.data.get("name",""), font_title, Colors.WHITE)] + [(d, font_line, Colors.WHITE) for d in details] + [(page_text, font_small, (140,140,140))]
                RotatedText.draw_block(self.screen, items, pygame.Rect(text_x, content_rect.y + 8, content_rect.width - bar_w - 16, content_rect.height - 16),
                                      panel.orientation, line_spacing=22, wrap=True)
            else:
                bar_w = 12
                bar_rect = pygame.Rect(content_rect.right - bar_w, content_rect.y, bar_w, content_rect.height)
                pygame.draw.rect(self.screen, color, bar_rect, border_radius=5)
                text_x = content_rect.x
                items = [(page_text, font_small, (140,140,140))] + [(d, font_line, Colors.WHITE) for d in reversed(details)] + [(prop.data.get("name",""), font_title, Colors.WHITE)]
                RotatedText.draw_block(self.screen, items, pygame.Rect(text_x, content_rect.y + 8, content_rect.width - bar_w - 16, content_rect.height - 16),
                                      panel.orientation, line_spacing=22, wrap=True)
        
        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)

    def draw_build_popup(self, panel, buttons: list):
        overlay = pygame.Surface(panel.rect.size, pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        self.screen.blit(overlay, panel.rect)
        font_title = pygame.font.SysFont("Arial", 20, bold=True)
        btn_area = buttons[0].rect if buttons else pygame.Rect(panel.rect.x, panel.rect.y, 0, 0)
        
        margin = 10
        if panel.orientation == 0:
            content_rect = pygame.Rect(
                btn_area.right + margin,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
        elif panel.orientation == 180:
            content_rect = pygame.Rect(
                btn_area.right + margin,
                panel.rect.y + margin,
                panel.rect.width - btn_area.width - margin * 3,
                panel.rect.height - margin * 2
            )
        elif panel.orientation == 90:
            content_rect = pygame.Rect(
                panel.rect.x + margin,
                btn_area.bottom + margin,
                panel.rect.width - margin * 2,
                panel.rect.height - btn_area.height - margin * 3
            )
        else:
            content_rect = pygame.Rect(
                panel.rect.x + margin,
                btn_area.bottom + margin,
                panel.rect.width - margin * 2,
                panel.rect.height - btn_area.height - margin * 3
            )
        
        RotatedText.draw_block(self.screen,
                               [("Building (Coming Soon)", font_title, Colors.ACCENT)],
                               content_rect, panel.orientation, line_spacing=8)
        
        for btn in buttons:
            btn.draw(self.screen)
            for pr in btn.get_hover_progress():
                self._draw_progress_indicator(pr, panel.orientation)
