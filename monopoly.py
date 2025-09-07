import time
import math
import pygame
from typing import List, Dict, Tuple
from ui_elements import PlayerSelectionUI

# simplified property model for demo
DEFAULT_PROPERTIES = [
    {"name": "Mediterranean Ave", "price": 60, "color": (139,69,19)},
    {"name": "Baltic Ave", "price": 60, "color": (139,69,19)},
    # ... (for brevity only a few; you can expand to full 28 properties later)
]

class Player:
    def __init__(self, idx:int, color:Tuple[int,int,int]):
        self.idx = idx
        self.color = color
        self.money = 1500
        self.pos = 0
        self.properties: List[int] = []
        self.token_anim_target = None
        self.token_anim_progress = 0.0

class MonopolyGame:
    def __init__(self, screen: pygame.Surface, hand_to_screen_fn):
        self.screen = screen
        self.hand_to_screen = hand_to_screen_fn
        self.players = [Player(i, col) for i, col in enumerate([
            (255,77,77),(77,255,77),(77,77,255),(255,200,77),
            (200,77,255),(77,255,200),(255,120,120),(180,180,80)
        ])]
        self.current = 0
        self.properties = DEFAULT_PROPERTIES.copy()
        self.board_spaces = 40
        self.last_roll = (0,0)
        self.selection_ui = PlayerSelectionUI(screen)
        # per-player UI overlays
        self.properties_open = [False]*8
        # hover popup state for property overlay closure
        self.popup_hover = {}  # key (player, hand) -> start_time

    def draw_board(self):
        w,h = self.screen.get_size()
        # background
        pygame.draw.rect(self.screen, (20,80,30), pygame.Rect(0,0,w,h))
        # outer board rectangle
        margin = 60
        board_rect = pygame.Rect(margin, margin, w-2*margin, h-2*margin)
        pygame.draw.rect(self.screen, (200,200,200), board_rect, width=6, border_radius=8)
        # draw 40 spaces (simplified as tick marks)
        for i in range(40):
            ang = (i / 40.0) * 2*math.pi
            # draw simple ticks along edges
            # skip complex geometry for brevity

        # draw player slots (edge boards)
        self.selection_ui.draw_slots()

    def _space_coords_for(self, pos:int) -> Tuple[int,int]:
        # map 0..39 to points around board rectangle
        w,h = self.screen.get_size()
        margin = 60
        board_w = w - 2*margin
        board_h = h - 2*margin
        # corners: 0 bottom-right corner (Go) proceeding counter-clockwise in our mapping
        # We'll place 0 at bottom-right, 10 bottom-left, 20 top-left, 30 top-right
        if pos < 10:
            # bottom edge, from right to left
            t = pos / 10.0
            x = margin + board_w*(1 - t)
            y = margin + board_h
        elif pos < 20:
            t = (pos-10)/10.0
            x = margin
            y = margin + board_h*(1 - t)
        elif pos < 30:
            t = (pos-20)/10.0
            x = margin + board_w*(t)
            y = margin
        else:
            t = (pos-30)/10.0
            x = margin + board_w
            y = margin + board_h*(t)
        return int(x), int(y)

    def update(self, fingertip_meta: List[Dict]):
        # update selection UI hover toggles
        self.selection_ui.update_with_fingertips(fingertip_meta)
        # update hover popup logic for property overlays (closable by hover)
        now = time.time()
        for meta in fingertip_meta:
            px,py = meta["pos"]
            hand = meta["hand"]
            # see if the fingertip is hovering a properties overlay close area
            for pid in range(8):
                if not self.properties_open[pid]:
                    continue
                # compute overlay rect in center for simplicity
                ow, oh = 360, 280
                ow_rect = pygame.Rect(self.screen.get_width()//2 - ow//2, self.screen.get_height()//2 - oh//2, ow, oh)
                if ow_rect.collidepoint((px,py)):
                    key = (pid, hand)
                    if key not in self.popup_hover:
                        self.popup_hover[key] = now
                    elif now - self.popup_hover[key] >= 1.0:
                        # close overlay
                        self.properties_open[pid] = False
                        # remove keys for that pid
                        self.popup_hover = {k:v for k,v in self.popup_hover.items() if k[0]!=pid}
                else:
                    # remove any stale keys for this hand/pid
                    for k in list(self.popup_hover.keys()):
                        if k == (pid, hand):
                            self.popup_hover.pop(k, None)

        # animate tokens toward targets if any
        for p in self.players:
            if p.token_anim_target is not None:
                p.token_anim_progress += 0.06
                if p.token_anim_progress >= 1.0:
                    p.pos = p.token_anim_target
                    p.token_anim_target = None
                    p.token_anim_progress = 0.0

    def draw_tokens(self):
        for p in self.players:
            x,y = self._space_coords_for(p.pos)
            # if animating, lerp to target
            if p.token_anim_target is not None:
                tx,ty = self._space_coords_for(p.token_anim_target)
                t = p.token_anim_progress
                x = int(x*(1-t) + tx*t)
                y = int(y*(1-t) + ty*t)
            pygame.draw.circle(self.screen, (255,255,255), (x,y), 18)
            pygame.draw.circle(self.screen, p.color, (x,y), 12)

    def draw_player_boards_and_buttons(self):
        # draw per-player small control buttons inside their slot rect from selection_ui
        font = pygame.font.SysFont(None, 20)
        for pid in range(8):
            rect = self.selection_ui.slot_rect(pid)
            # draw buttons inside rect: Roll/End, Buy/Mortgage, Properties
            btn_w = 80; btn_h = 26
            gap = 6
            x = rect.left + gap
            y = rect.top + gap
            # roll button
            roll_rect = pygame.Rect(x, y, btn_w, btn_h)
            # properties button
            prop_rect = pygame.Rect(x, y + btn_h + gap, btn_w, btn_h)
            buy_rect = pygame.Rect(x, y + 2*(btn_h+gap), btn_w, btn_h)
            # draw them differently depending on current player and ownership
            is_current = (pid == self.current)
            # roll is only enabled for current player
            roll_col = (120,200,120) if is_current else (80,80,80)
            pygame.draw.rect(self.screen, roll_col, roll_rect, border_radius=6)
            pygame.draw.rect(self.screen, (220,220,220), roll_rect, width=1, border_radius=6)
            pygame.draw.rect(self.screen, (100,100,100), prop_rect, border_radius=6)
            pygame.draw.rect(self.screen, (100,100,100), buy_rect, border_radius=6)
            rtxt = font.render("Roll/End" if is_current else "Wait", True, (0,0,0))
            prt = font.render("Props", True, (0,0,0))
            brt = font.render("Buy/Mort", True, (0,0,0))
            self.screen.blit(rtxt, rtxt.get_rect(center=roll_rect.center))
            self.screen.blit(prt, prt.get_rect(center=prop_rect.center))
            self.screen.blit(brt, brt.get_rect(center=buy_rect.center))

    def draw_properties_overlay(self, pid:int):
        # draw centered properties panel for pid
        ow, oh = 360, 280
        w,h = self.screen.get_size()
        r = pygame.Rect(w//2 - ow//2, h//2 - oh//2, ow, oh)
        pygame.draw.rect(self.screen, (28,28,28), r, border_radius=8)
        pygame.draw.rect(self.screen, (180,180,180), r, width=2, border_radius=8)
        font = pygame.font.SysFont(None, 22)
        # rotate text according to player's perspective
        x0, y0 = r.left + 16, r.top + 16
        self.screen.blit(font.render(f"Player {pid+1}", True, (255,255,255)), (x0, y0))
        self.screen.blit(font.render(f"Money: ${self.players[pid].money}", True, (255,255,255)), (x0, y0+28))
        # properties list
        y = y0 + 60
        for prop_idx in self.players[pid].properties:
            if prop_idx < len(self.properties):
                p = self.properties[prop_idx]
                pygame.draw.rect(self.screen, p["color"], pygame.Rect(x0, y, 24, 16))
                self.screen.blit(font.render(p["name"], True, (255,255,255)), (x0+32, y))
                y += 28

    def roll_dice_for_current(self):
        import random
        d1 = random.randint(1,6)
        d2 = random.randint(1,6)
        self.last_roll = (d1,d2)
        steps = d1 + d2
        target = (self.players[self.current].pos + steps) % self.board_spaces
        # animate token
        self.players[self.current].token_anim_target = target
        self.players[self.current].token_anim_progress = 0.0
        # landing logic (auto-buy simplified)
        # if unowned and price exists, allow buy later via buy button

    def draw(self):
        # draw board & UI elements
        self.draw_board()
        self.draw_tokens()
        self.draw_player_boards_and_buttons()
        # draw properties overlays on top of everything
        for pid in range(8):
            if self.properties_open[pid]:
                self.draw_properties_overlay(pid)