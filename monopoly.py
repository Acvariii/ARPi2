import time
import math
import random
import pygame
from typing import List, Dict, Tuple, Optional

from ui_elements import PlayerSelectionUI, HOVER_TIME_THRESHOLD

# Minimal 40-space description (name + optional display color)
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
        # movement path: list of target spaces to step through
        self.move_path: List[int] = []
        self.move_start: float = 0.0
        self.move_per_space: float = 0.25  # seconds per space (4 spaces/sec)
        self.move_from: Optional[int] = None
        self._open_after_move = False

class MonopolyGame:
    def __init__(self, screen: pygame.Surface, hand_to_screen_fn):
        self.screen = screen
        self.hand_to_screen = hand_to_screen_fn
        self.selection_ui = PlayerSelectionUI(screen)
        # create 8 players with a vibrant palette
        vibrant = [(220,40,40),(40,220,40),(40,70,220),(255,200,60),(200,40,200),(40,220,200),(255,120,60),(140,40,220)]
        self.players = [Player(i, vibrant[i]) for i in range(8)]
        self.players_selected: List[int] = []
        self.current = 0
        self.properties = PROPERTY_SPACES.copy()
        self.board_spaces = 40
        self.owners: List[Optional[int]] = [None] * self.board_spaces
        # hover / popup tracking
        self.button_hover: Dict[str, float] = {}
        self.button_hover_pos: Dict[str, Tuple[int,int]] = {}
        self.popup_hover: Dict[str, float] = {}
        self.properties_open: Dict[int, bool] = {i: False for i in range(8)}
        # dice state
        self.dice_state: Dict = {"rolling": False, "start": 0.0, "end": 0.0, "d1": 0, "d2": 0, "pid": None}
        self.last_roll = (0,0)
        # cached button rects
        self._last_button_rects: Dict[int, Dict[str, pygame.Rect]] = {}

    # geometry helpers
    def _compute_board_rect(self) -> pygame.Rect:
        w,h = self.screen.get_size()
        margin = max(120, int(min(w, h) * 0.12))
        size = min(w - 2*margin, h - 2*margin)
        bx = (w - size) // 2
        by = (h - size) // 2
        return pygame.Rect(bx, by, size, size)

    def _space_rect_for(self, idx:int, inner:pygame.Rect, side_count:int=10) -> pygame.Rect:
        space_w = inner.width // side_count
        space_h = inner.height // side_count
        if idx < 10:
            i = idx
            x = inner.right - (i+1)*space_w
            y = inner.bottom - space_h
            return pygame.Rect(x, y, space_w, space_h)
        if idx < 20:
            i = idx - 10
            x = inner.left
            y = inner.bottom - (i+1)*space_h - 0
            return pygame.Rect(x, y, space_w, space_h)
        if idx < 30:
            i = idx - 20
            x = inner.left + i*space_w
            y = inner.top
            return pygame.Rect(x, y, space_w, space_h)
        i = idx - 30
        x = inner.right - space_w
        y = inner.top + i*space_h
        return pygame.Rect(x, y, space_w, space_h)

    def _space_coords_for(self, pos:int) -> Tuple[int,int]:
        board = self._compute_board_rect()
        inner = board.inflate(-10, -10)
        side_count = 10
        space_w = inner.width / side_count
        space_h = inner.height / side_count
        if pos < 10:
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
        rect = self.selection_ui.slot_rect(pid)
        pos = self.selection_ui.positions[pid]
        gap = 8; xpad = 6; ypad = 6
        rects: Dict[str, pygame.Rect] = {}
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
        self._last_button_rects[pid] = rects
        return rects

    # popup overlay rect anchored to player's slot so it doesn't cover board center
    def _properties_overlay_rect(self, pid:int, ow:int=360, oh:int=280) -> pygame.Rect:
        screen_w, screen_h = self.screen.get_size()
        slot = self.selection_ui.slot_rect(pid)
        if slot.top == 0:
            x = max(16, min(screen_w - ow - 16, slot.centerx - ow//2)); y = slot.bottom + 8
        elif slot.bottom == screen_h:
            x = max(16, min(screen_w - ow - 16, slot.centerx - ow//2)); y = slot.top - oh - 8
        elif slot.left == 0:
            x = slot.right + 8; y = max(16, min(screen_h - oh - 16, slot.centery - oh//2))
        else:
            x = slot.left - ow - 8; y = max(16, min(screen_h - oh - 16, slot.centery - oh//2))
        return pygame.Rect(int(x), int(y), ow, oh)

    # update loop: fingertip hover -> open/close popups, trigger roll -> animate dice & movement
    def update(self, fingertip_meta: List[Dict]):
        self.selection_ui.update_with_fingertips(fingertip_meta)
        now = time.time()

        # first handle popups (hover to close) and block underlying buttons for that player
        for pid in list(self.players_selected):
            if self.properties_open.get(pid):
                orect = self._properties_overlay_rect(pid)
                for meta in fingertip_meta:
                    pos = meta.get("pos"); hand = meta.get("hand")
                    if not pos:
                        continue
                    key = f"popup:{pid}:{hand}"
                    if orect.collidepoint(pos):
                        if key not in self.popup_hover:
                            self.popup_hover[key] = now
                        else:
                            if (now - self.popup_hover[key]) >= HOVER_TIME_THRESHOLD:
                                self.properties_open[pid] = False
                                # clear popup hover keys for this pid
                                for k in list(self.popup_hover.keys()):
                                    if k.startswith(f"popup:{pid}:"):
                                        self.popup_hover.pop(k, None)
                    else:
                        if key in self.popup_hover:
                            self.popup_hover.pop(key, None)
                # skip processing buttons for this pid while popup open
                continue

            rects = self._player_button_rects(pid)
            for meta in fingertip_meta:
                pos = meta.get("pos"); hand = meta.get("hand")
                if not pos:
                    continue
                for key_name, r in rects.items():
                    hkey = f"{pid}:{key_name}:{hand}"
                    if r.collidepoint(pos):
                        if hkey not in self.button_hover:
                            self.button_hover[hkey] = now
                            self.button_hover_pos[hkey] = pos
                        else:
                            self.button_hover_pos[hkey] = pos
                            elapsed = now - self.button_hover[hkey]
                            if elapsed >= HOVER_TIME_THRESHOLD:
                                if key_name == "roll" and pid == self.current and not self.dice_state["rolling"]:
                                    dur = random.uniform(2.0, 4.0)
                                    self.dice_state.update({"rolling": True, "start": now, "end": now + dur, "d1": 0, "d2": 0, "pid": pid})
                                elif key_name == "buy":
                                    if pid == self.current:
                                        self.properties_open[pid] = True
                                elif key_name == "props":
                                    if pid == self.current:
                                        self.properties_open[pid] = True
                                # when triggering a popup, clear button hovers for that pid/key to avoid immediate retrigger
                                if self.properties_open.get(pid):
                                    for k in list(self.button_hover.keys()):
                                        if k.startswith(f"{pid}:"):
                                            self.button_hover.pop(k, None)
                                            self.button_hover_pos.pop(k, None)
                                # clear this hover key
                                for k in list(self.button_hover.keys()):
                                    if k.startswith(f"{pid}:{key_name}:"):
                                        self.button_hover.pop(k, None)
                                        self.button_hover_pos.pop(k, None)
                    else:
                        if hkey in self.button_hover:
                            self.button_hover.pop(hkey, None)
                        if hkey in self.button_hover_pos:
                            self.button_hover_pos.pop(hkey, None)

        # complete dice rolling and build movement path
        if self.dice_state.get("rolling"):
            if now >= self.dice_state["end"]:
                d1 = random.randint(1,6); d2 = random.randint(1,6)
                self.dice_state.update({"d1": d1, "d2": d2, "rolling": False})
                pid = self.dice_state["pid"]
                if pid is not None:
                    steps = d1 + d2
                    start_pos = self.players[pid].pos
                    path = [ (start_pos + i) % self.board_spaces for i in range(1, steps+1) ]
                    self.players[pid].move_path = path
                    self.players[pid].move_start = now
                    self.players[pid].move_from = start_pos
                    # mark popup to open after move if landing on an ownable property
                    target = path[-1]
                    self.players[pid]._open_after_move = False
                    if 0 <= target < len(self.properties):
                        spec = self.properties[target]
                        if spec.get("color") is not None and self.owners[target] is None:
                            self.players[pid]._open_after_move = True
                    self.last_roll = (d1, d2)
                    # rotate current to next selected player immediately after starting move
                    if self.players_selected:
                        try:
                            idx_in = self.players_selected.index(pid)
                            self.current = self.players_selected[(idx_in + 1) % len(self.players_selected)]
                        except ValueError:
                            pass

        # process movement completion
        for p in self.players:
            if p.move_path:
                elapsed = now - p.move_start
                per = p.move_per_space
                total_time = per * len(p.move_path)
                if elapsed >= total_time:
                    p.pos = p.move_path[-1]
                    p.move_path = []
                    p.move_start = 0.0
                    if getattr(p, "_open_after_move", False):
                        self.properties_open[p.idx] = True
                        p._open_after_move = False

    # ---- drawing ----
    def _draw_rotated_text(self, surf:pygame.Surface, text:str, rect:pygame.Rect, angle:int, font:pygame.font.Font, color=(255,255,255)):
        txt = font.render(text, True, color)
        if angle != 0:
            txt = pygame.transform.rotate(txt, angle)
        trect = txt.get_rect(center=rect.center)
        surf.blit(txt, trect)

    def draw_board(self):
        w,h = self.screen.get_size()
        pygame.draw.rect(self.screen, (20,80,30), pygame.Rect(0,0,w,h))
        board_rect = self._compute_board_rect()
        pygame.draw.rect(self.screen, (200,200,200), board_rect, width=6, border_radius=8)
        inner = board_rect.inflate(-10, -10)
        pygame.draw.rect(self.screen, (24,24,24), inner, border_radius=6)

        side_count = 10
        font_small = pygame.font.SysFont(None, 14)
        for idx in range(40):
            r = self._space_rect_for(idx, inner, side_count=side_count)
            pygame.draw.rect(self.screen, (180,180,180) if idx%2==0 else (200,200,200), r, border_radius=2)
            inner_r = r.inflate(-4, -4)
            spec = self.properties[idx] if idx < len(self.properties) else {"name": f"Space {idx}", "color": None}
            color = spec.get("color")
            if color:
                if idx < 10:
                    bar = pygame.Rect(r.left+2, r.top+2, r.width-4, int(r.height*0.18))
                elif idx < 20:
                    bar = pygame.Rect(r.left+2, r.top+2, int(r.width*0.18), r.height-4)
                elif idx < 30:
                    bar = pygame.Rect(r.left+2, r.bottom - int(r.height*0.18) - 2, r.width-4, int(r.height*0.18))
                else:
                    bar = pygame.Rect(r.right - int(r.width*0.18) - 2, r.top+2, int(r.width*0.18), r.height-4)
                pygame.draw.rect(self.screen, color, bar, border_radius=2)

            # determine angle facing outward
            angle = 0
            if r.top == inner.top:
                angle = 180
            elif r.left == inner.left:
                angle = 270
            elif r.right == inner.right:
                angle = 90
            else:
                angle = 0
            name = spec.get("name","")
            if len(name) > 18:
                parts = name.split(" ")
                mid = len(parts)//2
                line1 = " ".join(parts[:mid])
                line2 = " ".join(parts[mid:])
                surf1 = font_small.render(line1, True, (0,0,0))
                surf2 = font_small.render(line2, True, (0,0,0))
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

        # draw only the player slots (edge boards) on top so they don't obscure the board center
        for pid in range(len(self.selection_ui.positions)):
            if self.players_selected:
                if pid not in self.players_selected:
                    continue
            # draw slot using selection_ui helper which avoids painting full-screen background
            try:
                self.selection_ui.draw_slot(pid)
            except Exception:
                pass

    def draw_tokens(self):
        static_by_space: Dict[int, List[Player]] = {}
        moving_players: List[Player] = []
        for p in self.players:
            if self.players_selected and p.idx not in self.players_selected:
                continue
            if p.move_path:
                moving_players.append(p)
            else:
                static_by_space.setdefault(p.pos, []).append(p)

        for space, plist in static_by_space.items():
            cx, cy = self._space_coords_for(space)
            n = len(plist)
            if n == 1:
                p = plist[0]
                pygame.draw.circle(self.screen, (0,0,0), (cx+2, cy+3), 12)
                pygame.draw.circle(self.screen, p.color, (cx, cy), 8)
            else:
                radius = 18
                for k, p in enumerate(plist):
                    angle = 2 * math.pi * k / n
                    px = int(cx + math.cos(angle) * radius)
                    py = int(cy + math.sin(angle) * radius)
                    pygame.draw.circle(self.screen, (0,0,0), (px+2, py+3), 10)
                    pygame.draw.circle(self.screen, p.color, (px, py), 6)

        for p in moving_players:
            elapsed = time.time() - p.move_start
            per = p.move_per_space
            step = int(elapsed // per)
            frac = (elapsed % per) / per if per > 0 else 1.0
            if step >= len(p.move_path):
                sx, sy = self._space_coords_for(p.move_path[-1])
                px, py = sx, sy
            else:
                prev_space = p.move_from if step == 0 else p.move_path[step-1]
                next_space = p.move_path[step]
                sx, sy = self._space_coords_for(prev_space)
                ex, ey = self._space_coords_for(next_space)
                jump = math.sin(frac * math.pi) * 10
                px = int(sx*(1-frac) + ex*frac)
                py = int(sy*(1-frac) + ey*frac - jump)
            pygame.draw.circle(self.screen, (0,0,0), (px+2, py+3), 12)
            pygame.draw.circle(self.screen, p.color, (px, py), 8)

    def draw_player_boards_and_buttons(self):
        font = pygame.font.SysFont(None, 20)
        for pid in list(self.players_selected):
            rect = self.selection_ui.slot_rect(pid)
            pos = self.selection_ui.positions[pid]
            base_col = self.players[pid].color
            washed = tuple(min(255, int(c * 0.75 + 180 * 0.25)) for c in base_col)
            pygame.draw.rect(self.screen, washed, rect.inflate(8,8), border_radius=8)
            if pid == self.current:
                pygame.draw.rect(self.screen, (255,215,0), rect.inflate(6,6), width=4, border_radius=8)
                lbl = font.render("CURRENT", True, (0,0,0))
                self.screen.blit(lbl, (rect.centerx - lbl.get_width()//2, rect.top + 6))
            rects = self._player_button_rects(pid)
            for key_name, brect in rects.items():
                if key_name == "roll":
                    col = tuple(min(255, int(c*0.7 + 220*0.3)) for c in base_col) if pid == self.current else tuple(min(255, int(c*0.6 + 200*0.4)) for c in base_col)
                elif key_name == "props":
                    col = tuple(min(255, int(c*0.8 + 200*0.2)) for c in base_col)
                else:
                    col = tuple(min(255, int(c*0.85 + 190*0.15)) for c in base_col)
                pygame.draw.rect(self.screen, col, brect, border_radius=8)
                pygame.draw.rect(self.screen, (60,60,60), brect, width=1, border_radius=8)
                label_text = "Roll" if key_name == "roll" else ("Properties" if key_name == "props" else "Buy / Mortg.")
                txtsurf = font.render(label_text, True, (0,0,0))
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

        # draw hover progress arcs for button hovers
        now = time.time()
        ACCENT = (240, 200, 80)
        for key, start in list(self.button_hover.items()):
            pos = self.button_hover_pos.get(key)
            if not pos:
                continue
            elapsed = now - start
            progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
            px, py = pos
            arc_rect = pygame.Rect(px + 28 - 20, py - 28 - 20, 40, 40)
            pygame.draw.circle(self.screen, (60, 60, 60), arc_rect.center, 20)
            start_ang = -math.pi / 2
            end_ang = start_ang + progress * 2 * math.pi
            pygame.draw.arc(self.screen, ACCENT, arc_rect, start_ang, end_ang, 6)

        # draw dice at board center
        board_rect = self._compute_board_rect()
        cx, cy = board_rect.centerx, board_rect.centery
        font_small = pygame.font.SysFont(None, 18)
        if self.dice_state.get("rolling"):
            for i in range(2):
                face = random.randint(1,6)
                dx = (i*48) - 24
                dr = pygame.Rect(cx + dx - 22, cy - 22, 44, 44)
                pygame.draw.rect(self.screen, (255,255,255), dr, border_radius=6)
                ftxt = font_small.render(str(face), True, (0,0,0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))
        elif self.dice_state.get("d1", 0) and self.dice_state.get("d2", 0):
            d1 = self.dice_state.get("d1", 0); d2 = self.dice_state.get("d2", 0)
            for i, val in enumerate([d1, d2]):
                dx = (i*48) - 24
                dr = pygame.Rect(cx + dx - 22, cy - 22, 44, 44)
                pygame.draw.rect(self.screen, (255,255,255), dr, border_radius=6)
                ftxt = font_small.render(str(val), True, (0,0,0))
                self.screen.blit(ftxt, ftxt.get_rect(center=dr.center))

    def draw_properties_overlay(self, pid:int):
        ow, oh = 360, 280
        r = self._properties_overlay_rect(pid, ow=ow, oh=oh)
        pygame.draw.rect(self.screen, (28,28,28), r, border_radius=8)
        pygame.draw.rect(self.screen, (180,180,180), r, width=2, border_radius=8)
        font = pygame.font.SysFont(None, 22)
        x0, y0 = r.left + 16, r.top + 16
        self.screen.blit(font.render(f"Player {pid+1}", True, (255,255,255)), (x0, y0))
        self.screen.blit(font.render(f"Money: ${self.players[pid].money}", True, (255,255,255)), (x0, y0+28))
        y = y0 + 60
        for prop_idx in self.players[pid].properties:
            if prop_idx < len(self.properties):
                p = self.properties[prop_idx]
                pygame.draw.rect(self.screen, p["color"] or (120,120,120), pygame.Rect(x0, y, 24, 16))
                self.screen.blit(font.render(p["name"], True, (255,255,255)), (x0+32, y))
                y += 28

        # draw hover-close progress for this overlay
        now = time.time()
        for k, start in list(self.popup_hover.items()):
            try:
                prefix, spid, hand = k.split(":")
                if prefix != "popup": continue
                if int(spid) != pid: continue
                # attempt to get finger pos from selection_ui.get_hover_progress or fallback to center
                hover_pos = None
                for meta in getattr(self.selection_ui, "get_hover_progress", lambda: [])():
                    if meta.get("slot") == pid:
                        hover_pos = meta.get("pos"); break
                if hover_pos:
                    px, py = hover_pos
                else:
                    px, py = r.center
                elapsed = now - start
                progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
                arc_rect = pygame.Rect(px + 28 - 20, py - 28 - 20, 40, 40)
                pygame.draw.circle(self.screen, (60, 60, 60), arc_rect.center, 20)
                start_ang = -math.pi / 2
                end_ang = start_ang + progress * 2 * math.pi
                pygame.draw.arc(self.screen, (240,200,80), arc_rect, start_ang, end_ang, 6)
            except Exception:
                pass

    def draw(self):
        # draw main layers
        self.draw_board()
        self.draw_tokens()
        self.draw_player_boards_and_buttons()
        # popups above buttons & board
        for pid in range(len(self.players)):
            if self.properties_open.get(pid):
                self.draw_properties_overlay(pid)

        # draw selection-slot hover progress indicators (if selection_ui provides them)
        try:
            for h in self.selection_ui.get_hover_progress():
                px, py = h.get("pos", (0, 0))
                progress = h.get("progress", 0.0)
                off_x, off_y = 28, -28
                arc_rect = pygame.Rect(px + off_x - 20, py + off_y - 20, 40, 40)
                pygame.draw.circle(self.screen, (60, 60, 60), arc_rect.center, 20)
                start_ang = -math.pi / 2
                end_ang = start_ang + progress * 2 * math.pi
                pygame.draw.arc(self.screen, (240, 200, 80), arc_rect, start_ang, end_ang, 6)
        except Exception:
            pass

        # game-level button hover arcs (follow finger)
        now = time.time()
        ACCENT = (240, 200, 80)
        for key, start in list(self.button_hover.items()):
            pos = self.button_hover_pos.get(key)
            if not pos:
                continue
            elapsed = now - start
            progress = min(1.0, max(0.0, elapsed / HOVER_TIME_THRESHOLD))
            px, py = pos
            arc_rect = pygame.Rect(px + 28 - 20, py - 28 - 20, 40, 40)
            pygame.draw.circle(self.screen, (60, 60, 60), arc_rect.center, 20)
            start_ang = -math.pi / 2
            end_ang = start_ang + progress * 2 * math.pi
            pygame.draw.arc(self.screen, ACCENT, arc_rect, start_ang, end_ang, 6)

        # draw fingertips (combine selection_ui hover_pos and game-level hover_pos)
        try:
            pts = set()
            for v in getattr(self.selection_ui, "hover_pos", {}).values():
                if v:
                    pts.add((int(v[0]), int(v[1])))
            for v in self.button_hover_pos.values():
                if v:
                    pts.add((int(v[0]), int(v[1])))
            for (px, py) in pts:
                pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 20)
                try:
                    col = self.selection_ui.closest_player_color((px, py))
                except Exception:
                    col = (200, 200, 200)
                pygame.draw.circle(self.screen, col, (px, py), 14)
                pygame.draw.circle(self.screen, (0, 0, 0), (px, py), 4)
        except Exception:
            pass