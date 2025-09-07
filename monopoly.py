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

        # players actually playing (set by launcher when starting the game)
        self.players_selected: List[int] = []

    def _compute_board_rect(self) -> pygame.Rect:
        """Return a centered board rect that avoids covering edge player slots."""
        w,h = self.screen.get_size()
        # leave margin so player slots around edges don't overlap the board
        margin = max(120, int(min(w, h) * 0.12))
        board_w = w - 2*margin
        board_h = h - 2*margin
        # make board square-ish but fit in center
        size = min(board_w, board_h)
        bx = (w - size) // 2
        by = (h - size) // 2
        return pygame.Rect(bx, by, size, size)

    def draw_board(self):
        w,h = self.screen.get_size()
        # background for play area
        pygame.draw.rect(self.screen, (20,80,30), pygame.Rect(0,0,w,h))

        # draw centered board
        board_rect = self._compute_board_rect()
        pygame.draw.rect(self.screen, (200,200,200), board_rect, width=6, border_radius=8)
        inner = board_rect.inflate(-10, -10)
        pygame.draw.rect(self.screen, (24,24,24), inner, border_radius=6)

        # draw 10 spaces per side as simple color blocks
        side_count = 10
        # bottom (positions 0..9) left->right mapped so pos 0 is bottom-right as earlier mapping
        # We'll draw bottom from right to left to match token coords
        # compute sizes
        space_w = inner.width // side_count
        space_h = inner.height // side_count

        # bottom row (pos 0..9): draw from right to left
        for i in range(side_count):
            pos_idx = i  # will map later for numbering if desired
            x = inner.right - (i+1)*space_w
            y = inner.bottom - space_h
            r = pygame.Rect(x, y, space_w, space_h)
            pygame.draw.rect(self.screen, (180,180,180), r, border_radius=2)
            # small index label
            pygame.draw.rect(self.screen, (140,140,140), r.inflate(-6,-6), border_radius=2)

        # left column (10..19) bottom->top
        for i in range(side_count):
            x = inner.left
            y = inner.bottom - (i+1)*space_h - space_h*(0)
            r = pygame.Rect(x, inner.bottom - (i+1)*space_h - space_h*(0), space_w, space_h)
            # rotate rectangles for visual difference
            pygame.draw.rect(self.screen, (200,200,200), pygame.Rect(inner.left, inner.bottom - (i+1)*space_h - space_h + 0, space_w, space_h), border_radius=2)

        # top row (20..29) left->right
        for i in range(side_count):
            x = inner.left + i*space_w
            y = inner.top
            r = pygame.Rect(x, y, space_w, space_h)
            pygame.draw.rect(self.screen, (180,180,180), r, border_radius=2)

        # right column (30..39) top->bottom
        for i in range(side_count):
            x = inner.right - space_w
            y = inner.top + i*space_h
            r = pygame.Rect(x, y, space_w, space_h)
            pygame.draw.rect(self.screen, (200,200,200), r, border_radius=2)

        # draw player slots (edge boards)
        self.selection_ui.draw_slots()

    def _space_coords_for(self, pos:int) -> Tuple[int,int]:
        # map 0..39 to points around board rectangle (consistent with draw_board)
        board = self._compute_board_rect()
        margin = 0
        inner = board.inflate(-10, -10)
        side_count = 10
        space_w = inner.width / side_count
        space_h = inner.height / side_count

        # 0..9 bottom (right to left)
        if pos < 10:
            t = pos / 10.0
            # map 0->right-most cell center
            ix = int(inner.right - (pos + 0.5) * space_w)
            iy = int(inner.bottom - space_h / 2)
            return ix, iy
        elif pos < 20:
            p = pos - 10
            ix = int(inner.left + space_w / 2)
            iy = int(inner.bottom - (p + 0.5) * space_h)
            return ix, iy
        elif pos < 30:
            p = pos - 20
            ix = int(inner.left + (p + 0.5) * space_w)
            iy = int(inner.top + space_h / 2)
            return ix, iy
        else:
            p = pos - 30
            ix = int(inner.right - space_w / 2)
            iy = int(inner.top + (p + 0.5) * space_h)
            return ix, iy

    def update(self, fingertip_meta: List[Dict]):
        # update selection UI hover toggles (still keep selection visible)
        self.selection_ui.update_with_fingertips(fingertip_meta)
        # update hover popup logic for property overlays (closable by hover)
        now = time.time()
        for meta in fingertip_meta:
            px,py = meta["pos"]
            hand = meta["hand"]
            for pid in range(8):
                if not self.properties_open[pid]:
                    continue
                ow, oh = 360, 280
                ow_rect = pygame.Rect(self.screen.get_width()//2 - ow//2, self.screen.get_height()//2 - oh//2, ow, oh)
                if ow_rect.collidepoint((px,py)):
                    key = (pid, hand)
                    if key not in self.popup_hover:
                        self.popup_hover[key] = now
                    elif now - self.popup_hover[key] >= 1.0:
                        self.properties_open[pid] = False
                        self.popup_hover = {k:v for k,v in self.popup_hover.items() if k[0]!=pid}
                else:
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
        # draw each player's token only if that player is in players_selected
        for p in self.players:
            if self.players_selected and p.idx not in self.players_selected:
                continue
            x,y = self._space_coords_for(p.pos)
            if p.token_anim_target is not None:
                tx,ty = self._space_coords_for(p.token_anim_target)
                t = p.token_anim_progress
                x = int(x*(1-t) + tx*t)
                y = int(y*(1-t) + ty*t)
            # draw token shadow + colored core
            pygame.draw.circle(self.screen, (0,0,0), (x+2, y+3), 16)
            pygame.draw.circle(self.screen, p.color, (x, y), 12)

    def draw_player_boards_and_buttons(self):
        # draw per-player large control buttons inside their slot rect from selection_ui
        font = pygame.font.SysFont(None, 20)
        for pid in range(8):
            rect = self.selection_ui.slot_rect(pid)
            # highlight only if player is selected/playing
            is_selected = (self.players_selected and pid in self.players_selected) or (not self.players_selected and self.selection_ui.selected[pid])
            bg_color = (255,255,255) if is_selected else (40,40,40)
            # draw lightly tinted background for player's slot (so "lit up" players show)
            tint = tuple(min(255, c + 40) for c in self.players[pid].color)
            if is_selected:
                pygame.draw.rect(self.screen, tint, rect.inflate(8,8), border_radius=8)
            # draw border for current player
            if pid == self.current:
                pygame.draw.rect(self.screen, (255, 215, 0), rect.inflate(6,6), width=4, border_radius=8)
                # label current
                lbl = font.render("CURRENT", True, (0,0,0))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width()//2, rect.top + 6))

            # large buttons filling most of the slot
            btn_w = max(60, rect.width - 12)
            # stack three tall buttons vertically
            gap = 8
            total_btn_h = rect.height - (gap*4)
            btn_h = max(28, total_btn_h // 3)
            x = rect.left + 6
            y = rect.top + gap

            # Roll/End
            roll_rect = pygame.Rect(x, y, btn_w, btn_h)
            roll_col = (120,200,120) if pid == self.current else (120,120,120)
            pygame.draw.rect(self.screen, roll_col, roll_rect, border_radius=8)
            pygame.draw.rect(self.screen, (220,220,220), roll_rect, width=1, border_radius=8)
            rtxt = font.render("Roll / End", True, (0,0,0))
            self.screen.blit(rtxt, rtxt.get_rect(center=roll_rect.center))

            # Props
            y += btn_h + gap
            prop_rect = pygame.Rect(x, y, btn_w, btn_h)
            pygame.draw.rect(self.screen, (200,200,200), prop_rect, border_radius=8)
            prt = font.render("Properties", True, (0,0,0))
            self.screen.blit(prt, prt.get_rect(center=prop_rect.center))

            # Buy/Mortgage
            y += btn_h + gap
            buy_rect = pygame.Rect(x, y, btn_w, btn_h)
            pygame.draw.rect(self.screen, (200,180,140), buy_rect, border_radius=8)
            brt = font.render("Buy / Mortg.", True, (0,0,0))
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

    def draw(self):
        # draw board & UI elements
        self.draw_board()
        self.draw_tokens()
        self.draw_player_boards_and_buttons()
        # draw properties overlays on top of everything
        for pid in range(8):
            if self.properties_open[pid]:
                self.draw_properties_overlay(pid)