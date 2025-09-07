import time
import math
import random
import pygame
from typing import List, Dict, Tuple, Optional
from ui_elements import PlayerSelectionUI

# full property list for 40 spaces (name + display color for properties; None for non-property)
PROPERTY_SPACES = [
    {"name": "Go", "color": None},
    {"name": "Mediterranean Ave", "color": (139,69,19)},
    {"name": "Community Chest", "color": None},
    {"name": "Baltic Ave", "color": (139,69,19)},
    {"name": "Income Tax", "color": None},
    {"name": "Reading RR", "color": (80,80,80)},
    {"name": "Oriental Ave", "color": (173,216,230)},
    {"name": "Chance", "color": None},
    {"name": "Vermont Ave", "color": (173,216,230)},
    {"name": "Connecticut Ave", "color": (173,216,230)},
    {"name": "Jail / Just Visiting", "color": None},
    {"name": "St. Charles Pl", "color": (255,192,203)},
    {"name": "Electric Co.", "color": (200,200,200)},
    {"name": "States Ave", "color": (255,192,203)},
    {"name": "Virginia Ave", "color": (255,192,203)},
    {"name": "Pennsylvania RR", "color": (80,80,80)},
    {"name": "St. James Pl", "color": (255,165,0)},
    {"name": "Community Chest", "color": None},
    {"name": "Tennessee Ave", "color": (255,165,0)},
    {"name": "New York Ave", "color": (255,165,0)},
    {"name": "Free Parking", "color": None},
    {"name": "Kentucky Ave", "color": (255,105,180)},
    {"name": "Chance", "color": None},
    {"name": "Indiana Ave", "color": (255,105,180)},
    {"name": "Illinois Ave", "color": (255,105,180)},
    {"name": "B. & O. RR", "color": (80,80,80)},
    {"name": "Atlantic Ave", "color": (255,215,0)},
    {"name": "Ventnor Ave", "color": (255,215,0)},
    {"name": "Water Works", "color": (200,200,200)},
    {"name": "Marvin Gardens", "color": (255,215,0)},
    {"name": "Go To Jail", "color": None},
    {"name": "Pacific Ave", "color": (34,139,34)},
    {"name": "North Carolina Ave", "color": (34,139,34)},
    {"name": "Community Chest", "color": None},
    {"name": "Pennsylvania Ave", "color": (34,139,34)},
    {"name": "Short Line RR", "color": (80,80,80)},
    {"name": "Chance", "color": None},
    {"name": "Park Place", "color": (25,25,112)},
    {"name": "Luxury Tax", "color": None},
    {"name": "Boardwalk", "color": (25,25,112)},
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
        # replace with more vibrant palette (keep in sync with ui_elements if desired)
        vibrant = [(220,40,40),(40,220,40),(40,70,220),(255,200,60),(200,40,200),(40,220,200),(255,120,60),(140,40,220)]
        for i,p in enumerate(self.players):
            p.color = vibrant[i]
        self.current = 0
        self.properties = PROPERTY_SPACES.copy()
        self.board_spaces = 40
        self.last_roll = (0,0)
        self.selection_ui = PlayerSelectionUI(screen)
        # per-player UI overlays
        self.properties_open = [False]*8
        # hover popup state for property overlay closure
        self.popup_hover = {}  # key (player, hand) -> start_time

        # players actually playing (set by launcher when starting the game)
        self.players_selected: List[int] = []
        # property ownership: None==bank, otherwise player idx
        self.owners: List[Optional[int]] = [None] * self.board_spaces
        # dice rolling state
        self.dice_state: Dict = {"rolling": False, "start": 0.0, "end": 0.0, "d1": 0, "d2": 0, "pid": None}
        # hover timers for per-player buttons (keyed by "pid:button:hand")
        self.button_hover: Dict[str, float] = {}
        # cached last computed button rects (computed in helper)
        self._last_button_rects: Dict[int, Dict[str, pygame.Rect]] = {}

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

    def _space_rect_for(self, idx:int, inner:pygame.Rect, side_count:int=10) -> pygame.Rect:
        """Return the rect for space idx inside inner rect (10 per side)."""
        space_w = inner.width // side_count
        space_h = inner.height // side_count
        # bottom row (0..9) right->left
        if idx < 10:
            i = idx
            x = inner.right - (i+1)*space_w
            y = inner.bottom - space_h
            return pygame.Rect(x, y, space_w, space_h)
        # left column (10..19) bottom->top
        if idx < 20:
            i = idx - 10
            x = inner.left
            y = inner.bottom - (i+1)*space_h - (space_h * 0)
            return pygame.Rect(x, y, space_w, space_h)
        # top row (20..29) left->right
        if idx < 30:
            i = idx - 20
            x = inner.left + i*space_w
            y = inner.top
            return pygame.Rect(x, y, space_w, space_h)
        # right column (30..39) top->bottom
        i = idx - 30
        x = inner.right - space_w
        y = inner.top + i*space_h
        return pygame.Rect(x, y, space_w, space_h)

    def _draw_rotated_text(self, surf:pygame.Surface, text:str, rect:pygame.Rect, angle:int, font:pygame.font.Font, color=(255,255,255)):
        txt = font.render(text, True, color)
        if angle != 0:
            txt = pygame.transform.rotate(txt, angle)
        trect = txt.get_rect(center=rect.center)
        surf.blit(txt, trect)

    def draw_board(self):
        w,h = self.screen.get_size()
        # background for play area
        pygame.draw.rect(self.screen, (20,80,30), pygame.Rect(0,0,w,h))

        # draw centered board
        board_rect = self._compute_board_rect()
        pygame.draw.rect(self.screen, (200,200,200), board_rect, width=6, border_radius=8)
        inner = board_rect.inflate(-10, -10)
        pygame.draw.rect(self.screen, (24,24,24), inner, border_radius=6)

        # draw 10 spaces per side (full 40-space board)
        side_count = 10
        font_small = pygame.font.SysFont(None, 14)
        for idx in range(40):
            r = self._space_rect_for(idx, inner, side_count=side_count)
            # background
            pygame.draw.rect(self.screen, (180,180,180) if idx%2==0 else (200,200,200), r, border_radius=2)
            # inner panel for name
            inner_r = r.inflate(-4, -4)
            pygame.draw.rect(self.screen, (140,140,140), inner_r, border_radius=2)

            # draw color bar for property groups (at the edge adjacent to board center)
            spec = self.properties[idx]
            color = spec.get("color")
            if color:
                # color bar anchored to inner edge (towards board center)
                # determine side to place bar: for bottom/bottom-right spaces place bar at top of rect,
                # for top spaces place bar at bottom, left column place bar at right, right column place bar at left.
                if idx < 10:  # bottom row
                    bar = pygame.Rect(r.left+2, r.top+2, r.width-4, int(r.height*0.18))
                elif idx < 20:  # left column
                    bar = pygame.Rect(r.left+2, r.top+2, int(r.width*0.18), r.height-4)
                elif idx < 30:  # top row
                    bar = pygame.Rect(r.left+2, r.bottom - int(r.height*0.18) - 2, r.width-4, int(r.height*0.18))
                else:  # right column
                    bar = pygame.Rect(r.right - int(r.width*0.18) - 2, r.top+2, int(r.width*0.18), r.height-4)
                pygame.draw.rect(self.screen, color, bar, border_radius=2)

            # draw name rotated to face outside players
            # determine angle: bottom side texts read normally (0), top side upside down (180),
            # left side rotated 90 (270) so it faces left player, right side rotated 90 (90) to face right player.
            angle = 0
            # center of space to determine side
            cx, cy = r.center
            if r.top == inner.top:  # top row
                angle = 180
            elif r.bottom == inner.bottom:  # bottom row
                angle = 0
            elif r.left == inner.left:  # left column
                angle = 270
            else:  # right column
                angle = 90

            # render name (truncate if too long)
            name = spec.get("name","")
            # split multi-word into up-to-two-line label for small spaces
            if len(name) > 18:
                # try to break on spaces
                parts = name.split(" ")
                mid = len(parts)//2
                line1 = " ".join(parts[:mid])
                line2 = " ".join(parts[mid:])
                # render two lines
                surf1 = font_small.render(line1, True, (0,0,0))
                surf2 = font_small.render(line2, True, (0,0,0))
                # combine into one surface
                combined_h = surf1.get_height() + surf2.get_height()
                combined = pygame.Surface((max(surf1.get_width(), surf2.get_width()), combined_h), pygame.SRCALPHA)
                combined.blit(surf1, (0,0))
                combined.blit(surf2, (0,surf1.get_height()))
                if angle != 0:
                    combined = pygame.transform.rotate(combined, angle)
                crect = combined.get_rect(center=inner_r.center)
                self.screen.blit(combined, crect)
            else:
                self._draw_rotated_text(self.screen, name, inner_r, angle, font_small, color=(0,0,0))

        # draw player slots (edge boards) on top of board so they are not obscured
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

    def _player_button_rects(self, pid: int) -> Dict[str, pygame.Rect]:
        """Return precomputed rects for Roll/Props/Buy buttons for a given player slot."""
        rect = self.selection_ui.slot_rect(pid)
        pos = self.selection_ui.positions[pid]
        gap = 8
        xpad = 6
        ypad = 6
        rects = {}
        if pos[1] == 0 or pos[1] == self.screen.get_height():
            total_w = rect.width - xpad*2
            btn_w = max(60, (total_w - gap*2)//3)
            btn_h = max(32, rect.height - ypad*2)
            start_x = rect.left + xpad + (total_w - (btn_w*3 + gap*2))//2
            y = rect.top + ypad
            for i, key in enumerate(["roll", "props", "buy"]):
                bx = start_x + i*(btn_w + gap)
                rects[key] = pygame.Rect(bx, y, btn_w, btn_h)
        else:
            btn_w = max(60, rect.width - 12)
            total_btn_h = rect.height - (gap*4)
            btn_h = max(28, total_btn_h // 3)
            x = rect.left + 6
            y = rect.top + gap
            rects["roll"] = pygame.Rect(x, y, btn_w, btn_h)
            rects["props"] = pygame.Rect(x, y + btn_h + gap, btn_w, btn_h)
            rects["buy"] = pygame.Rect(x, y + 2*(btn_h + gap), btn_w, btn_h)
        # cache for update/draw consistency
        self._last_button_rects[pid] = rects
        return rects

    def update(self, fingertip_meta: List[Dict]):
        # update selection hover toggles (keep selection visible in game)
        self.selection_ui.update_with_fingertips(fingertip_meta)
        now = time.time()
        # update hover timers for buttons (only consider playing players)
        for pid in list(self.players_selected):
            rects = self._player_button_rects(pid)
            for meta in fingertip_meta:
                pos = meta.get("pos")
                hand = meta.get("hand")
                if not pos:
                    continue
                # roll button hover handling (only allow current player to roll)
                for key_name, r in rects.items():
                    if r.collidepoint(pos):
                        hkey = f"{pid}:{key_name}:{hand}"
                        if hkey not in self.button_hover:
                            self.button_hover[hkey] = now
                        else:
                            if (now - self.button_hover[hkey]) >= 1.0:
                                # trigger action
                                if key_name == "roll" and pid == self.current and not self.dice_state["rolling"]:
                                    # start dice animation for 2-4s
                                    dur = random.uniform(2.0, 4.0)
                                    self.dice_state.update({"rolling": True, "start": now, "end": now + dur, "d1": 0, "d2": 0, "pid": pid})
                                elif key_name == "buy":
                                    # open property overlay for current player if on a property
                                    if pid == self.current:
                                        self.properties_open[pid] = True
                                elif key_name == "props":
                                    if pid == self.current:
                                        self.properties_open[pid] = True
                    else:
                        # clear any hover for that hand/key if moved away
                        hkey = f"{pid}:{key_name}:{hand}"
                        if hkey in self.button_hover:
                            self.button_hover.pop(hkey, None)

        # handle dice finish
        if self.dice_state.get("rolling"):
            if now >= self.dice_state["end"]:
                # finalize dice
                d1 = random.randint(1,6)
                d2 = random.randint(1,6)
                self.dice_state.update({"d1": d1, "d2": d2, "rolling": False})
                pid = self.dice_state["pid"]
                if pid is not None:
                    steps = d1 + d2
                    target = (self.players[pid].pos + steps) % self.board_spaces
                    self.players[pid].token_anim_target = target
                    self.players[pid].token_anim_progress = 0.0
                    self.last_roll = (d1, d2)
                    # if landed on an ownable property and unowned -> open buy overlay
                    if 0 <= target < len(self.properties):
                        spec = self.properties[target]
                        if spec.get("color") is not None and self.owners[target] is None:
                            # open property buy overlay for current
                            self.properties_open[pid] = True
                    # advance current to next selected player after move (simple turn rotate)
                    # find next index in self.players_selected
                    if self.players_selected:
                        try:
                            idx_in_list = self.players_selected.index(pid)
                            next_idx = (idx_in_list + 1) % len(self.players_selected)
                            self.current = self.players_selected[next_idx]
                        except ValueError:
                            pass

        # animate tokens as before
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
        # draw only players that are actually playing to keep board clean
        font = pygame.font.SysFont(None, 20)
        for pid in list(self.players_selected):
            rect = self.selection_ui.slot_rect(pid)
            pos = self.selection_ui.positions[pid]
            # tinted bg using player color slightly washed for UI elements
            base_col = self.players[pid].color
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in base_col)
            pygame.draw.rect(self.screen, washed, rect.inflate(8,8), border_radius=8)

            # current player highlight
            if pid == self.current:
                pygame.draw.rect(self.screen, (255,215,0), rect.inflate(6,6), width=4, border_radius=8)
                lbl = font.render("CURRENT", True, (0,0,0))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width()//2, rect.top + 6))

            # compute button rects (ensures update/draw use same layout)
            rects = self._player_button_rects(pid)
            # draw buttons using player-washed color
            for key_name, brect in rects.items():
                if key_name == "roll":
                    col = tuple(min(255, int(c*0.7 + 220*0.3)) for c in base_col) if pid == self.current else tuple(min(255, int(c*0.6 + 200*0.4)) for c in base_col)
                elif key_name == "props":
                    col = tuple(min(255, int(c*0.8 + 200*0.2)) for c in base_col)
                else:
                    col = tuple(min(255, int(c*0.85 + 190*0.15)) for c in base_col)
                pygame.draw.rect(self.screen, col, brect, border_radius=8)
                pygame.draw.rect(self.screen, (60,60,60), brect, width=1, border_radius=8)
                # label orientation
                label_text = "Roll" if key_name == "roll" else ("Properties" if key_name == "props" else "Buy / Mortg.")
                txtsurf = font.render(label_text, True, (0,0,0))
                # rotate text to face player
                angle_text = 0
                if pos[1] == 0:
                    angle_text = 180
                elif pos[1] == self.screen.get_height():
                    angle_text = 0
                elif pos[0] == 0:
                    angle_text = 270
                else:
                    angle_text = 90
                if angle_text != 0:
                    txtsurf = pygame.transform.rotate(txtsurf, angle_text)
                self.screen.blit(txtsurf, txtsurf.get_rect(center=brect.center))

        # if dice rolling show animated dice near center
        if self.dice_state.get("rolling"):
            cx, cy = self.screen.get_width()//2, self.screen.get_height()//2
            t = time.time()
            # draw two dice with rapidly changing faces
            for i in range(2):
                face = random.randint(1,6)
                dx = (i*48) - 24
                dr = pygame.Rect(cx + dx - 22, cy - 22, 44, 44)
                pygame.draw.rect(self.screen, (255,255,255), dr, border_radius=6)
                ftxt = font.render(str(face), True, (0,0,0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))
        elif self.dice_state.get("d1", 0) and self.dice_state.get("d2", 0):
            # show last roll result briefly
            cx, cy = self.screen.get_width()//2, self.screen.get_height()//2
            d1 = self.dice_state.get("d1", 0)
            d2 = self.dice_state.get("d2", 0)
            for i, val in enumerate([d1, d2]):
                dx = (i*48) - 24
                dr = pygame.Rect(cx + dx - 22, cy - 22, 44, 44)
                pygame.draw.rect(self.screen, (255,255,255), dr, border_radius=6)
                ftxt = font.render(str(val), True, (0,0,0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))
        # end draw_player_boards_and_buttons

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