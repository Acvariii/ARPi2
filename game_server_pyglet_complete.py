"""
ARPi2 Game Server - Pyglet/OpenGL Version (Clean & Organized)
High-performance OpenGL-accelerated game server with complete UI
All games include player selection and player panels matching Pygame version
"""
import asyncio
import random
import websockets
import pyglet
from pyglet import gl
from pyglet.math import Mat4
import cv2
import numpy as np
import json
import time
import ctypes
import threading
import http.server
import socketserver
import functools
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import math
import re

from config import WINDOW_SIZE, FPS, HOVER_TIME_THRESHOLD, Colors
from config import PLAYER_COLORS
from core.renderer import PygletRenderer
from games.monopoly import MonopolyGame
from games.blackjack import BlackjackGame
from games.uno import UnoGame
from games.exploding_kittens import ExplodingKittensGame
from games.texas_holdem import TexasHoldemGame
from games.cluedo import CluedoGame
from games.risk import RiskGame
from games.dnd import DnDCharacterCreation

from core.popup_system import UniversalPopup

from server.dnd_dice import CenterDiceRollDisplay
from server.dnd_character_creation import (
    _dnd_background_questions,
    _dnd_generate_background_text,
    _dnd_pick_additional_skills,
    _dnd_starting_loadout,
)


def _stable_rng_seed(*parts: object) -> int:
    """Return a stable 64-bit seed for random.Random from arbitrary inputs."""
    s = "|".join(str(p) for p in parts if p is not None)
    h = hashlib.sha256(s.encode("utf-8", errors="ignore")).digest()
    return int.from_bytes(h[:8], "little", signed=False)

class PygletGameServer:
    """OpenGL-accelerated game server using Pyglet with complete UI"""
    
    def __init__(self, host="0.0.0.0", port=8765):
        global WINDOW_SIZE
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.ui_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.ui_client_player: Dict[str, int] = {}
        self.ui_client_name: Dict[str, str] = {}
        self.ui_client_ready: Dict[str, bool] = {}
        self.ui_client_vote: Dict[str, str] = {}
        self.ui_client_end_game: Dict[str, bool] = {}
        self.ui_client_music_mute_vote: Dict[str, bool] = {}
        self.player_names: Dict[int, str] = {}
        self.web_cursors: Dict[int, Dict] = {}  # player_idx -> {pos:(x,y), click:bool, t:float}
        self.web_esc_requested = False

        # Audio (Pyglet)
        self._audio_inited = False
        self._bg_player = None
        self._bg_track: Optional[str] = None
        self._bg_volume = 0.35
        self._sfx_cache: Dict[str, object] = {}
        self._music_muted = False
        self._last_music_state: Optional[str] = None
        self._bg_restart_in_progress: bool = False

        # Draw SFX tracking (detect deck size drops)
        self._last_deck_state: Optional[str] = None
        self._last_deck_counts: Dict[str, int] = {}

        # Web-UI-first mode: do not rely on hand tracking or mouse hover input.
        self.web_ui_only = True

        # Web UI extras
        self.ui_history: List[str] = []
        self._monopoly_last_ownership: Dict[int, int] = {}

        # D&D Web UI state
        self.dnd_dm_seat: Optional[int] = None
        self.dnd_background: Optional[str] = None

        # D&D dice roll overlays (centered visible dice animation)
        self._dnd_dice_display = CenterDiceRollDisplay()
        self._dnd_dice_lock = threading.Lock()
        self._dnd_dice_pending: List[tuple[int, int, int]] = []  # (seat, sides, result)

        # D&D background (local file selection only; no external APIs)
        self._dnd_bg_prompt_cache: str = ""  # stores "file:<name>" when loaded
        self._dnd_bg_sprite = None
        self._dnd_bg_img_size: tuple[int, int] = (0, 0)
        self._dnd_bg_aspect_key: tuple[int, int] = (0, 0)
        self._dnd_bg_last_error: str = ""
        self._dnd_bg_last_error_time: float = 0.0

        # D&D local background files (games/dnd/backgrounds)
        self._dnd_bg_files_cache: List[str] = []
        self._dnd_bg_files_cache_time: float = 0.0

        # Lobby gating
        self.min_connected_players = 2

        # Finish initializing networking/window/rendering.
        self._finish_init()

    def _sounds_dir(self) -> Path:
        return (Path(__file__).parent / "sounds").resolve()

    def _audio_init(self) -> None:
        if bool(getattr(self, "_audio_inited", False)):
            return
        try:
            self._bg_player = self._create_bg_player()
        except Exception:
            self._bg_player = None
        self._sfx_cache = {}
        self._audio_inited = True

    def _create_bg_player(self):
        p = pyglet.media.Player()
        try:
            p.volume = float(getattr(self, "_bg_volume", 0.35))
        except Exception:
            pass
        try:
            p.push_handlers(on_eos=lambda: self._on_bg_eos())
        except Exception:
            pass
        return p

    def _on_bg_eos(self) -> None:
        # Defensive fallback: some platforms/codecs don't loop reliably.
        if bool(getattr(self, "_bg_restart_in_progress", False)):
            return
        self._bg_restart_in_progress = True
        try:
            track = (getattr(self, "_bg_track", None) or "").strip() or None
            if track is None:
                return
            if bool(getattr(self, "_music_muted", False)):
                return

            p = getattr(self, "_bg_player", None)
            if p is None:
                return

            # Looping is more reliable with non-streaming sources (seekable).
            src = self._audio_load(track, streaming=False)
            if src is None:
                return

            try:
                group = pyglet.media.SourceGroup(src.audio_format, None)
                group.loop = True
                group.queue(src)
                p.queue(group)
            except Exception:
                try:
                    p.queue(src)
                except Exception:
                    return

            # Belt-and-braces loop hint.
            try:
                p.eos_action = pyglet.media.Player.EOS_LOOP
            except Exception:
                pass

            try:
                p.play()
            except Exception:
                return
        finally:
            self._bg_restart_in_progress = False

    def _audio_load(self, filename: str, streaming: bool = False):
        try:
            self._audio_init()
        except Exception:
            return None
        name = (filename or "").strip()
        if not name:
            return None
        path = self._sounds_dir() / name
        try:
            if not path.exists():
                return None
        except Exception:
            return None
        try:
            return pyglet.media.load(str(path), streaming=bool(streaming))
        except Exception:
            return None

    def _play_sfx(self, filename: str) -> None:
        # One-shot sound effect.
        try:
            self._audio_init()
        except Exception:
            return
        src = self._sfx_cache.get(filename)
        if src is None:
            src = self._audio_load(filename, streaming=False)
            if src is None:
                return
            self._sfx_cache[filename] = src
        try:
            src.play()
        except Exception:
            return

    def _stop_bg_music(self) -> None:
        try:
            p = getattr(self, "_bg_player", None)
            if p is None:
                return
            try:
                p.pause()
            except Exception:
                pass
            try:
                p.delete()
            except Exception:
                pass
        except Exception:
            pass
        try:
            self._bg_player = self._create_bg_player()
        except Exception:
            self._bg_player = None

    def _set_bg_music(self, filename: Optional[str]) -> None:
        # Looping background music.
        try:
            self._audio_init()
        except Exception:
            return

        want = (filename or "").strip() or None
        if want == getattr(self, "_bg_track", None):
            return
        self._bg_track = want

        # Always stop old track when switching.
        self._stop_bg_music()
        if want is None:
            return
        if bool(getattr(self, "_music_muted", False)):
            return

        # Prefer non-streaming sources for looping reliability.
        src = self._audio_load(want, streaming=False)
        if src is None:
            return

        p = getattr(self, "_bg_player", None)
        if p is None:
            return

        # Prefer SourceGroup looping; fallback to eos_action + on_eos restart if needed.
        try:
            group = pyglet.media.SourceGroup(src.audio_format, None)
            group.loop = True
            group.queue(src)
            p.queue(group)
        except Exception:
            try:
                p.queue(src)
                try:
                    p.eos_action = pyglet.media.Player.EOS_LOOP
                except Exception:
                    pass
            except Exception:
                return

        # Belt-and-braces: set loop action even when SourceGroup is used.
        try:
            p.eos_action = pyglet.media.Player.EOS_LOOP
        except Exception:
            pass

        try:
            p.play()
        except Exception:
            return

    def _desired_bg_track_for_state(self, state: str) -> Optional[str]:
        st = str(state or "").strip()
        if st == "menu":
            return "LobbyBG.mp3"
        if st == "blackjack":
            return "BlackjackBG.mp3"
        if st == "exploding_kittens":
            return "ExplodingKittensBG.mp3"
        if st == "uno":
            return "UnoBG.mp3"
        if st == "monopoly":
            return "MonopolyBG.mp3"
        if st == "texas_holdem":
            return "TexasHoldemBG.mp3"
        if st == "cluedo":
            return "CluedoBG.mp3"
        if st == "risk":
            return "RiskBG.mp3"
        return None

    def _eligible_music_vote_client_ids(self) -> List[str]:
        eligible: List[str] = []
        for cid, seat in (self.ui_client_player or {}).items():
            if cid not in (self.ui_clients or {}):
                continue
            if isinstance(seat, int) and seat >= 0:
                eligible.append(cid)
        return eligible

    def _music_vote_counts(self) -> tuple[int, int, bool]:
        eligible = self._eligible_music_vote_client_ids()
        total = len(eligible)
        required = max(1, (total // 2) + 1)
        votes = sum(1 for cid in eligible if bool(self.ui_client_music_mute_vote.get(cid, False)))
        muted = votes >= required
        return votes, required, muted

    def _recompute_music_mute(self) -> None:
        votes, required, muted = self._music_vote_counts()
        prev = bool(getattr(self, "_music_muted", False))
        self._music_muted = bool(muted)
        if prev != self._music_muted:
            desired = self._desired_bg_track_for_state(self.state)
            if self._music_muted:
                self._stop_bg_music()
            else:
                # Force restart even if the desired track matches the previous track.
                self._bg_track = None
                self._set_bg_music(desired)

    def _audio_tick(self) -> None:
        # Keep background music in sync with server state and vote mute.
        try:
            self._audio_init()
        except Exception:
            return
        try:
            self._recompute_music_mute()
        except Exception:
            pass

        st = str(getattr(self, "state", "") or "")
        if st != getattr(self, "_last_music_state", None):
            self._last_music_state = st
            self._set_bg_music(self._desired_bg_track_for_state(st))

        # Defensive: if playback stopped for any reason, restart the desired track.
        try:
            if not bool(getattr(self, "_music_muted", False)):
                desired = self._desired_bg_track_for_state(str(getattr(self, "state", "") or ""))
                if desired:
                    p = getattr(self, "_bg_player", None)
                    playing = bool(getattr(p, "playing", False)) if p is not None else False
                    if not playing:
                        # Force restart even if the desired track matches the previous track.
                        self._bg_track = None
                        self._set_bg_music(desired)
        except Exception:
            pass

    def _current_deck_count_for_state(self) -> Optional[tuple[str, int]]:
        st = str(getattr(self, "state", "") or "")
        try:
            if st == "uno":
                g = getattr(self, "uno_game", None)
                return ("uno", int(len(getattr(g, "draw_pile", []) or [])))
            if st == "exploding_kittens":
                g = getattr(self, "exploding_kittens_game", None)
                return ("exploding_kittens", int(len(getattr(g, "draw_pile", []) or [])))
            if st == "blackjack":
                g = getattr(self, "blackjack_game", None)
                return ("blackjack", int(len(getattr(g, "deck", []) or [])))
        except Exception:
            return None
        return None

    def _maybe_play_flip_on_deck_change(self) -> None:
        info = self._current_deck_count_for_state()
        if not info:
            self._last_deck_state = str(getattr(self, "state", "") or "")
            return

        key, current = info
        st = str(getattr(self, "state", "") or "")

        # On state change, seed baseline without playing sounds.
        if st != getattr(self, "_last_deck_state", None):
            self._last_deck_state = st
            self._last_deck_counts[key] = int(current)
            return

        last = self._last_deck_counts.get(key)
        if isinstance(last, int) and int(current) < int(last):
            try:
                self._play_sfx("FlipCard.mp3")
            except Exception:
                pass
        self._last_deck_counts[key] = int(current)

    def _dnd_backgrounds_dir(self) -> Path:
        return (Path(__file__).parent / "games" / "dnd" / "backgrounds").resolve()

    def _list_dnd_background_files(self) -> List[str]:
        """Return available local background image filenames (no paths)."""
        try:
            now = float(time.time())
        except Exception:
            now = 0.0
        # Cache briefly to avoid filesystem churn during UI polling.
        if now and (now - float(self._dnd_bg_files_cache_time or 0.0)) < 1.0:
            return list(self._dnd_bg_files_cache or [])

        bg_dir = self._dnd_backgrounds_dir()
        out: List[str] = []
        try:
            if bg_dir.exists() and bg_dir.is_dir():
                exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
                for p in bg_dir.iterdir():
                    try:
                        if not p.is_file():
                            continue
                        if p.suffix.lower() not in exts:
                            continue
                        out.append(p.name)
                    except Exception:
                        continue
        except Exception:
            out = []
        out.sort(key=lambda s: s.lower())
        self._dnd_bg_files_cache = list(out)
        self._dnd_bg_files_cache_time = now
        return list(out)

    def _set_sprite_smoothing(self, sprite_obj) -> None:
        """Force linear texture filtering to reduce pixelation when scaling."""
        if sprite_obj is None:
            return
        try:
            tex = sprite_obj.image.get_texture()
            tex.min_filter = gl.GL_LINEAR
            tex.mag_filter = gl.GL_LINEAR
        except Exception:
            pass

    def _layout_dnd_bg_sprite(self, draw_w: int, draw_h: int) -> None:
        """Center the background sprite while preserving aspect ratio (letterboxing)."""
        spr = getattr(self, "_dnd_bg_sprite", None)
        if spr is None:
            return

        try:
            iw, ih = self._dnd_bg_img_size
        except Exception:
            iw, ih = 0, 0

        if iw <= 0 or ih <= 0:
            try:
                tex = spr.image.get_texture()
                iw, ih = int(getattr(tex, "width", 0)), int(getattr(tex, "height", 0))
            except Exception:
                iw, ih = 0, 0

        if iw <= 0 or ih <= 0:
            return

        scale = min(float(draw_w) / float(iw), float(draw_h) / float(ih))
        scaled_w = float(iw) * scale
        scaled_h = float(ih) * scale
        x = (float(draw_w) - scaled_w) * 0.5
        y = (float(draw_h) - scaled_h) * 0.5

        try:
            spr.x = float(x)
            spr.y = float(y)
            spr.scale = float(scale)
        except Exception:
            try:
                spr.x = float(x)
                spr.y = float(y)
                spr.scale_x = float(scale)
                spr.scale_y = float(scale)
            except Exception:
                pass

    def _queue_dnd_dice_roll(self, seat: int, sides: int, result: int) -> None:
        try:
            s = int(seat)
            sd = int(sides)
            r = int(result)
        except Exception:
            return
        with self._dnd_dice_lock:
            self._dnd_dice_pending.append((s, sd, r))

    def _pump_dnd_dice_pending(self) -> None:
        """Drain queued dice roll events and add them to the animated display.

        This runs on the Pyglet/update thread to avoid cross-thread mutation during draw.
        """
        with self._dnd_dice_lock:
            pending = list(self._dnd_dice_pending)
            self._dnd_dice_pending.clear()
        if not pending:
            return

        for seat, sides, result in pending:
            try:
                name = "DM" if (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat) else self._player_display_name(seat)
                color = tuple(PLAYER_COLORS[int(seat) % len(PLAYER_COLORS)])
                self._dnd_dice_display.enqueue(name, int(sides), int(result), color=color)
            except Exception:
                continue
    def _ensure_dnd_background_sprite(self, draw_w: int, draw_h: int):
        """Ensure a cached sprite exists for the selected local background file."""
        bg = str(getattr(self, "dnd_background", "") or "").strip()

        if not bg:
            return

        # If the background matches a local file, load from disk and do NOT call external APIs.
        try:
            files = set(self._list_dnd_background_files() or [])
        except Exception:
            files = set()
        if bg in files:
            aspect_key = (int(draw_w // 64), int(draw_h // 64))
            want = f"file:{bg}"
            if want == self._dnd_bg_prompt_cache and aspect_key == self._dnd_bg_aspect_key and self._dnd_bg_sprite is not None:
                try:
                    self._set_sprite_smoothing(self._dnd_bg_sprite)
                    self._layout_dnd_bg_sprite(draw_w, draw_h)
                except Exception:
                    pass
                return

            try:
                bg_dir = self._dnd_backgrounds_dir()
                path = (bg_dir / bg).resolve()
                # Safety: ensure the resolved path stays inside the backgrounds dir.
                if bg_dir not in path.parents and path != bg_dir:
                    raise RuntimeError("Invalid background path")

                img = pyglet.image.load(str(path))
                self._dnd_bg_sprite = pyglet.sprite.Sprite(img, x=0, y=0)
                self._set_sprite_smoothing(self._dnd_bg_sprite)
                self._dnd_bg_img_size = (int(getattr(img, "width", 0) or 0), int(getattr(img, "height", 0) or 0))
                self._dnd_bg_prompt_cache = want
                self._dnd_bg_aspect_key = aspect_key
                self._layout_dnd_bg_sprite(draw_w, draw_h)
                return
            except Exception as e:
                self._dnd_bg_last_error = str(e)
                self._dnd_bg_last_error_time = float(time.time())
                try:
                    print(f"[DND BG] ERROR loading local background '{bg}': {e}")
                except Exception:
                    pass
                return

        # Unknown background value (not in local file list). Ignore.
        return

    def _finish_init(self):
        global WINDOW_SIZE
        # UI seat assignment: clients can be unseated (-1) until they choose.
        # ui_client_player maps client_id -> seat index (0..7) or -1.

        # Render settings
        self.render_board_only = True

        self.http_server_port = 8000
        self._httpd = None
        self._http_thread = None

        # Thread pool for CPU-intensive operations (JPEG encoding)
        self.encode_worker_count = 2
        self.encode_executor = ThreadPoolExecutor(max_workers=self.encode_worker_count)

        # Create Pyglet window with OpenGL.
        # Deployment target is 1080p, so lock the window to the configured WINDOW_SIZE
        # (1920x1080 by default). This keeps rendering/layout consistent and avoids
        # borders from running a smaller window on a larger display.
        target_w, target_h = int(WINDOW_SIZE[0]), int(WINDOW_SIZE[1])
        try:
            from pyglet import display as pyglet_display
            display = pyglet_display.get_display()
            screen = display.get_default_screen()
        except Exception:
            screen = None

        use_exclusive_fullscreen = False
        try:
            if screen is not None:
                sw = int(getattr(screen, "width", 0))
                sh = int(getattr(screen, "height", 0))
                use_exclusive_fullscreen = (sw == target_w and sh == target_h)
        except Exception:
            use_exclusive_fullscreen = False

        config = pyglet.gl.Config(double_buffer=True, sample_buffers=1, samples=4)
        if use_exclusive_fullscreen:
            # True fullscreen: avoids Windows work-area/taskbar margins.
            self.window = pyglet.window.Window(
                width=target_w,
                height=target_h,
                fullscreen=True,
                screen=screen,
                caption="ARPi2 Game Server - Pyglet/OpenGL (Complete UI)",
                config=config,
                vsync=True,
            )
        else:
            # Dev fallback: fixed-size borderless window.
            self.window = pyglet.window.Window(
                width=target_w,
                height=target_h,
                fullscreen=False,
                style=pyglet.window.Window.WINDOW_STYLE_BORDERLESS,
                caption="ARPi2 Game Server - Pyglet/OpenGL (Complete UI)",
                config=config,
                vsync=True,
            )
            try:
                self.window.set_location(0, 0)
            except Exception:
                pass

        # Keep WINDOW_SIZE aligned to the created window size.
        WINDOW_SIZE = (self.window.width, self.window.height)

        # Setup OpenGL state
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)

        # Renderer - use actual window size
        self.renderer = PygletRenderer(self.window.width, self.window.height)
        
        self.running = True
        
        # FPS tracking
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Frame broadcasting
        self.last_broadcast_time = time.time()
        self.broadcast_fps = 60  # Send 60 frames per second to clients
        self.broadcasting = False  # Flag to prevent overlapping broadcasts
        
        # GPU capture buffers (double-buffered PBOs)
        # Use framebuffer size if available (HiDPI correctness).
        try:
            fb_w, fb_h = self.window.get_framebuffer_size()
        except Exception:
            fb_w, fb_h = self.window.width, self.window.height
        self.capture_width = int(fb_w)
        self.capture_height = int(fb_h)
        self.capture_stride = self.capture_width * 3
        self.capture_buffer_size = self.capture_stride * self.capture_height
        self.capture_pbos = (gl.GLuint * 2)()
        gl.glGenBuffers(2, self.capture_pbos)
        for idx in range(2):
            gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.capture_pbos[idx])
            gl.glBufferData(gl.GL_PIXEL_PACK_BUFFER, self.capture_buffer_size, None, gl.GL_STREAM_READ)
        gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)
        self.capture_pbo_index = 0
        self.capture_ready = False

        # Input state (web UI + keyboard only)
        self.last_keyboard_event = None
        self.esc_pressed = False  # Track ESC key presses
        
        # Game state
        self.state = "menu"  # menu, monopoly, blackjack, dnd_creation
        
        # Menu buttons
        self.game_buttons = self._create_game_buttons()
        self.hover_states = {}
        
        # Game instances - use actual window size for fullscreen
        self.dnd_creation = DnDCharacterCreation(self.window.width, self.window.height, self.renderer)
        self.monopoly_game = MonopolyGame(self.window.width, self.window.height, self.renderer)
        self.blackjack_game = BlackjackGame(self.window.width, self.window.height, self.renderer)
        self.uno_game = UnoGame(self.window.width, self.window.height, self.renderer)
        self.exploding_kittens_game = ExplodingKittensGame(self.window.width, self.window.height, self.renderer)
        self.texas_holdem_game = TexasHoldemGame(self.window.width, self.window.height, self.renderer)
        self.cluedo_game = CluedoGame(self.window.width, self.window.height, self.renderer)
        self.risk_game = RiskGame(self.window.width, self.window.height, self.renderer)

        # Universal (server-managed) end-of-game vote popup state
        self._endgame_vote_token: Optional[str] = None
        self._endgame_votes_by_seat: Dict[int, str] = {}

        # Provide seat->name to games that can render player names on the board.
        try:
            if hasattr(self.uno_game, "set_name_provider"):
                self.uno_game.set_name_provider(self._player_display_name)
        except Exception:
            pass

        try:
            if hasattr(self.exploding_kittens_game, "set_name_provider"):
                self.exploding_kittens_game.set_name_provider(self._player_display_name)
        except Exception:
            pass

        try:
            if hasattr(self.texas_holdem_game, "set_name_provider"):
                self.texas_holdem_game.set_name_provider(self._player_display_name)
        except Exception:
            pass

        try:
            if hasattr(self.cluedo_game, "set_name_provider"):
                self.cluedo_game.set_name_provider(self._player_display_name)
        except Exception:
            pass

        try:
            if hasattr(self.risk_game, "set_name_provider"):
                self.risk_game.set_name_provider(self._player_display_name)
        except Exception:
            pass

        # Player selection is handled via Web UI (button-driven), so hide in-window selection UIs.
        setattr(self.monopoly_game, "web_ui_only_player_select", True)
        setattr(self.blackjack_game, "web_ui_only_player_select", True)
        setattr(self.uno_game, "web_ui_only_player_select", True)
        setattr(self.exploding_kittens_game, "web_ui_only_player_select", True)
        setattr(self.texas_holdem_game, "web_ui_only_player_select", True)
        setattr(self.cluedo_game, "web_ui_only_player_select", True)
        setattr(self.risk_game, "web_ui_only_player_select", True)
        # Board-only rendering in the Pyglet window (no panels). Web UI shows actions/info.
        setattr(self.monopoly_game, "board_only_mode", True)
        setattr(self.blackjack_game, "board_only_mode", True)
        setattr(self.uno_game, "board_only_mode", True)
        setattr(self.exploding_kittens_game, "board_only_mode", True)
        setattr(self.texas_holdem_game, "board_only_mode", True)
        setattr(self.cluedo_game, "board_only_mode", True)
        setattr(self.risk_game, "board_only_mode", True)
        if hasattr(self.dnd_creation, "game"):
            setattr(self.dnd_creation.game, "web_ui_only_player_select", True)
            setattr(self.dnd_creation.game, "web_ui_only_char_creation", True)
        
        # Setup event handlers
        self.window.on_draw = self.on_draw
        # Mouse motion is legacy / debugging only; web-UI-only mode doesn't use it.
        # self.window.on_mouse_motion = self.on_mouse_motion
        self.window.on_key_press = self.on_key_press
        self.window.on_close = self.on_close
        
        print(f"Pyglet/OpenGL game server initialized")
        print(f"OpenGL Version: {gl.gl_info.get_version()}")
        print(f"OpenGL Renderer: {gl.gl_info.get_renderer()}")
        print(f"Web UI: http://{self.host}:{self.http_server_port}")

        # Audio must be initialized after Pyglet is ready.
        try:
            self._audio_init()
        except Exception:
            pass

    def _log_history(self, msg: str) -> None:
        text = (msg or "").strip()
        if not text:
            return
        self.ui_history.append(text)
        # Intentionally unbounded: user requested ALL history.

    def _player_display_name(self, player_idx: int) -> str:
        try:
            pidx = int(player_idx)
        except Exception:
            return "Player"
        name = (self.player_names.get(pidx) or "").strip()
        if name:
            return name
        return f"Player {pidx + 1}"

    def _update_monopoly_history(self) -> None:
        if self.state != "monopoly":
            return
        mg = getattr(self, "monopoly_game", None)
        if mg is None:
            return
        if getattr(mg, "state", None) != "playing":
            return

        props = getattr(mg, "properties", None) or []
        current: Dict[int, int] = {}
        for i, prop in enumerate(props):
            owner = getattr(prop, "owner", None)
            if owner is None:
                continue
            try:
                current[int(i)] = int(owner)
            except Exception:
                continue

        prev = getattr(self, "_monopoly_last_ownership", {}) or {}
        for idx, new_owner in current.items():
            old_owner = prev.get(idx)
            if old_owner == new_owner:
                continue
            name = str(getattr(props[idx], "data", {}).get("name", f"Property {idx}"))
            if old_owner is None:
                buyer = self._player_display_name(new_owner)
                self._log_history(f"{buyer} bought {name}")
            else:
                buyer = self._player_display_name(new_owner)
                self._log_history(f"{name} transferred to {buyer}")

        self._monopoly_last_ownership = current

    def _get_taken_player_slots(self) -> List[int]:
        taken = set()
        for p in self.ui_client_player.values():
            if isinstance(p, int) and 0 <= p <= 7:
                taken.add(p)
        return sorted(taken)

    def _get_available_player_slots(self) -> List[int]:
        taken = set(self._get_taken_player_slots())
        return [i for i in range(8) if i not in taken]

    def _try_set_client_seat(self, client_id: str, desired_slot: int) -> bool:
        """Assign a seat to a UI client. Prevents two clients from sharing a slot."""
        try:
            slot = int(desired_slot)
        except Exception:
            return False
        if slot < 0 or slot > 7:
            return False

        current = self.ui_client_player.get(client_id, -1)
        if current == slot:
            return True

        for other_id, other_slot in self.ui_client_player.items():
            if other_id == client_id:
                continue
            if other_slot == slot:
                return False

        self.ui_client_player[client_id] = slot
        # Keep in-game player_select selection aligned to current seating.
        self._sync_player_select_from_seats()
        return True

    def _try_auto_assign_client_seat(self, client_id: str) -> bool:
        """Assign the first available seat to a client if they are unseated."""
        current = self.ui_client_player.get(client_id, -1)
        if isinstance(current, int) and current >= 0:
            return True
        available = self._get_available_player_slots()
        if not available:
            return False
        ok = self._try_set_client_seat(client_id, available[0])
        if ok:
            self._sync_player_select_from_seats()
        return ok

    def _sync_player_select_from_seats(self) -> None:
        """In web-UI-only mode, derive selected players from current seating.

        This prevents stale/ghost selections when a client changes seats.
        """
        game = self._get_active_game()
        if game is None:
            return
        if getattr(game, "state", None) != "player_select":
            return
        if not hasattr(game, "selection_ui"):
            return

        selected = getattr(game.selection_ui, "selected", None)
        if not isinstance(selected, list) or not selected:
            return

        seated = set()
        for cid, seat in (self.ui_client_player or {}).items():
            if cid not in (self.ui_clients or {}):
                continue
            if isinstance(seat, int) and 0 <= seat <= 7:
                seated.add(seat)

        for i in range(min(8, len(selected))):
            selected[i] = i in seated

        if self.state == "dnd_creation":
            dm = getattr(self, "dnd_dm_seat", None)
            if not (isinstance(dm, int) and dm in seated):
                self.dnd_dm_seat = None
                try:
                    if hasattr(game, "set_dm_player_idx"):
                        game.set_dm_player_idx(None)
                    else:
                        game.dm_player_idx = None
                except Exception:
                    pass

    def _ensure_player_slot_selected(self, player_idx: int) -> None:
        """Ensure a player's slot is marked selected in the active game's player_select UI.

        This keeps the in-game selection state consistent with the server-authoritative
        seating, while remaining a no-op in the menu or when a game has no selection UI.
        """
        try:
            pidx = int(player_idx)
        except Exception:
            return
        if pidx < 0 or pidx > 7:
            return

        game = self._get_active_game()
        if game is None:
            return
        if getattr(game, "state", None) != "player_select":
            return
        if not hasattr(game, "selection_ui"):
            return

        selected = getattr(game.selection_ui, "selected", None)
        if not isinstance(selected, list) or not selected:
            return
        if pidx >= len(selected):
            return

        # Keep behavior compatible, but also ensure we clear stale selections.
        self._sync_player_select_from_seats()

    def _get_lobby_players_snapshot(self) -> List[Dict]:
        players = []
        for client_id, ws in self.ui_clients.items():
            seat = self.ui_client_player.get(client_id, -1)
            if not isinstance(seat, int):
                seat = -1
            name = self.ui_client_name.get(client_id, "")
            ready = bool(self.ui_client_ready.get(client_id, False))
            vote = self.ui_client_vote.get(client_id)
            if vote is not None:
                vote = str(vote)
            players.append({
                "client_id": client_id,
                "seat": seat,
                "name": name,
                "ready": ready,
                "vote": vote,
                "connected": True,
            })
        # stable ordering: seated first, then by seat, then by client_id
        players.sort(key=lambda p: (p["seat"] < 0, p["seat"], p["client_id"]))
        return players

    def _lobby_all_ready(self) -> bool:
        # Only count seated clients.
        seated_clients = [cid for cid, seat in self.ui_client_player.items() if isinstance(seat, int) and seat >= 0]
        if len(seated_clients) < int(getattr(self, "min_connected_players", 2)):
            return False
        return all(bool(self.ui_client_ready.get(cid, False)) for cid in seated_clients)

    def _reset_lobby(self) -> None:
        # Keep names/seats, but require ready + votes again
        for cid in list(self.ui_client_ready.keys()):
            self.ui_client_ready[cid] = False
        self.ui_client_vote = {}
        # Clear End Game consensus votes whenever we return to lobby.
        for cid in list(self.ui_client_end_game.keys()):
            self.ui_client_end_game[cid] = False

    def _required_end_game_client_ids(self) -> List[str]:
        """Return the UI client IDs that must press End Game to exit.

        Prefer active in-game players when available; otherwise fall back to all seated clients.
        """
        # Determine the relevant seat set for the active game.
        seats: List[int] = []
        try:
            game = self._get_active_game()
            if game is not None:
                ap = getattr(game, "active_players", None)
                if isinstance(ap, list) and ap:
                    seats = [int(s) for s in ap if isinstance(s, int) or (isinstance(s, (str, float)) and str(s).isdigit())]
        except Exception:
            seats = []

        required: List[str] = []
        for cid, seat in (self.ui_client_player or {}).items():
            if cid not in (self.ui_clients or {}):
                continue
            if not (isinstance(seat, int) and seat >= 0):
                continue
            if seats and seat not in seats:
                continue
            required.append(cid)

        # If we couldn't find active players, require all seated/connected clients.
        if not required:
            for cid, seat in (self.ui_client_player or {}).items():
                if cid not in (self.ui_clients or {}):
                    continue
                if isinstance(seat, int) and seat >= 0:
                    required.append(cid)
        return required

    def _maybe_end_game(self) -> None:
        if self.state == "menu":
            return
        required = self._required_end_game_client_ids()
        if not required:
            return
        if all(bool(self.ui_client_end_game.get(cid, False)) for cid in required):
            self._log_history("Game ended (all players pressed End Game)")
            self.state = "menu"
            self._reset_lobby()

    def _maybe_apply_vote_result(self) -> None:
        if self.state != "menu":
            return
        if not self._lobby_all_ready():
            return

        # Count votes from ready+seated clients only
        counts: Dict[str, int] = {}
        voters = 0
        for cid, seat in self.ui_client_player.items():
            if not (isinstance(seat, int) and seat >= 0):
                continue
            if not bool(self.ui_client_ready.get(cid, False)):
                continue
            voters += 1
            key = self.ui_client_vote.get(cid)
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1

        if voters <= 0:
            return

        # Strict majority wins (> 50%). For 2 players, requires unanimity.
        for key, n in counts.items():
            if n > voters / 2:
                self._apply_game_selection(key)
                self.ui_client_vote = {}
                return

    def _apply_game_selection(self, key: str) -> None:
        if self.state != "menu":
            return
        if key == "monopoly":
            self.state = "monopoly"
            self.monopoly_game.state = "player_select"
            self.monopoly_game.selection_ui.reset()
        elif key == "blackjack":
            self.state = "blackjack"
            self.blackjack_game.state = "player_select"
            self.blackjack_game.selection_ui.reset()
        elif key == "uno":
            self.state = "uno"
            self.uno_game.state = "player_select"
            self.uno_game.selection_ui.reset()
        elif key == "exploding_kittens":
            self.state = "exploding_kittens"
            self.exploding_kittens_game.state = "player_select"
            self.exploding_kittens_game.selection_ui.reset()
        elif key == "texas_holdem":
            self.state = "texas_holdem"
            self.texas_holdem_game.state = "player_select"
            self.texas_holdem_game.selection_ui.reset()
        elif key == "cluedo":
            self.state = "cluedo"
            self.cluedo_game.state = "player_select"
            self.cluedo_game.selection_ui.reset()
        elif key == "risk":
            self.state = "risk"
            self.risk_game.state = "player_select"
            self.risk_game.selection_ui.reset()
        elif key in ("d&d", "dnd"):
            self.state = "dnd_creation"
            self.dnd_dm_seat = None
            self.dnd_background = None
            # Reset the underlying D&D session.
            try:
                sess = getattr(self.dnd_creation, "game", None)
                if sess is not None:
                    sess.state = "player_select"
                    if hasattr(sess, "selection_ui"):
                        sess.selection_ui.reset()
                    try:
                        sess.active_players = []
                        sess.characters = {}
                        sess.character_creators = {}
                    except Exception:
                        pass
                    try:
                        if hasattr(sess, "set_dm_player_idx"):
                            sess.set_dm_player_idx(None)
                        else:
                            sess.dm_player_idx = None
                    except Exception:
                        pass
            except Exception:
                pass

    def _start_http_server(self):
        web_root_base = Path(__file__).parent / "web_ui"
        dist_root = web_root_base / "dist"
        web_root = dist_root if (dist_root / "index.html").exists() else web_root_base
        if not web_root.exists():
            print(f"Web UI folder missing: {web_root}")
            return

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(web_root))
        try:
            # ThreadingMixIn is built-in via ThreadingTCPServer; good enough for static files
            self._httpd = socketserver.ThreadingTCPServer((self.host, self.http_server_port), handler)
            self._httpd.daemon_threads = True
        except OSError as e:
            print(f"Failed to start Web UI HTTP server on port {self.http_server_port}: {e}")
            return

        def serve():
            try:
                self._httpd.serve_forever(poll_interval=0.25)
            except Exception as e:
                print(f"Web UI HTTP server stopped: {e}")

        self._http_thread = threading.Thread(target=serve, daemon=True)
        self._http_thread.start()

    def _get_active_game(self):
        if self.state == "monopoly":
            return self.monopoly_game
        if self.state == "blackjack":
            return self.blackjack_game
        if self.state == "uno":
            return self.uno_game
        if self.state == "exploding_kittens":
            return self.exploding_kittens_game
        if self.state == "texas_holdem":
            return self.texas_holdem_game
        if self.state == "cluedo":
            return self.cluedo_game
        if self.state == "risk":
            return self.risk_game
        if self.state == "dnd_creation":
            return getattr(self.dnd_creation, "game", None) or self.dnd_creation
        return None

    def _get_player_select_snapshot(self, game):
        if not hasattr(game, "selection_ui"):
            return None
        selected = list(getattr(game.selection_ui, "selected", []))
        slots = []
        dm_seat = self.dnd_dm_seat if self.state == "dnd_creation" else None
        slot_count = 6 if self.state == "cluedo" else 8
        for i in range(slot_count):
            name = self.player_names.get(i) or f"Player {i + 1}"
            if self.state == "dnd_creation" and isinstance(dm_seat, int) and i == dm_seat:
                name = f"{name} (DM)"
            slots.append({
                "player_idx": i,
                "label": name,
                "selected": bool(selected[i]) if i < len(selected) else False,
            })

        # Start requirements vary per game
        start_enabled = False
        if self.state == "monopoly":
            start_enabled = sum(1 for s in slots if s["selected"]) >= 2
        elif self.state == "blackjack":
            start_enabled = sum(1 for s in slots if s["selected"]) >= 1
        elif self.state == "uno":
            start_enabled = sum(1 for s in slots if s["selected"]) >= 2
        elif self.state == "exploding_kittens":
            start_enabled = sum(1 for s in slots if s["selected"]) >= 2
        elif self.state == "texas_holdem":
            start_enabled = sum(1 for s in slots if s["selected"]) >= 2
        elif self.state == "cluedo":
            sel_count = sum(1 for s in slots if s["selected"])
            start_enabled = sel_count >= 3 and sel_count <= 6
        elif self.state == "risk":
            start_enabled = sum(1 for s in slots if s["selected"]) >= 2
        elif self.state == "dnd_creation":
            sel_count = sum(1 for s in slots if s["selected"])
            start_enabled = sel_count >= 2 and isinstance(dm_seat, int) and any(
                s["selected"] and s["player_idx"] == dm_seat for s in slots
            )

        out = {"slots": slots, "start_enabled": start_enabled}
        if self.state == "dnd_creation":
            out["dm_player_idx"] = dm_seat
        return out

    def _get_popup_snapshot(self, game, player_idx: int):
        if not hasattr(game, "popup"):
            return {"active": False}

        popup = game.popup
        if not getattr(popup, "active", False):
            return {"active": False}

        # Only show the popup to the owning player (if defined)
        popup_player = getattr(popup, "player_idx", None)
        if popup_player is not None and popup_player != player_idx:
            return {"active": False}

        def _rgb_to_hex(rgb):
            try:
                r, g, b = rgb
                return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            except Exception:
                return None

        lines = []
        line_items = []
        for entry in getattr(popup, "text_lines", []) or []:
            if isinstance(entry, (list, tuple)) and len(entry) >= 1:
                text = str(entry[0])
                lines.append(text)
                color = None
                if len(entry) >= 3 and isinstance(entry[2], (list, tuple)) and len(entry[2]) == 3:
                    color = _rgb_to_hex(entry[2])
                line_items.append({"text": text, "color": color})

        buttons = []
        if hasattr(game, "buttons") and player_idx in getattr(game, "buttons", {}):
            for btn_id, btn in game.buttons[player_idx].items():
                text = getattr(btn, "text", "")
                enabled = bool(getattr(btn, "enabled", True))
                if text:
                    # When a popup is active, only expose popup-specific buttons.
                    # This avoids showing core panel actions (Roll/End/Build/etc.) inside
                    # a popup snapshot, which can lead to confusing or unsafe actions.
                    if isinstance(btn_id, str) and btn_id.startswith("popup_"):
                        buttons.append({"id": btn_id, "text": text, "enabled": enabled})

        # Server-managed popups may provide Web UI buttons directly via popup.data.
        if not buttons:
            try:
                pdata = getattr(popup, "data", None) or {}
                pbtns = pdata.get("buttons")
                if isinstance(pbtns, list):
                    for b in pbtns:
                        if not isinstance(b, dict):
                            continue
                        bid = b.get("id")
                        if not (isinstance(bid, str) and bid.startswith("popup_")):
                            continue
                        txt = str(b.get("text") or "")
                        if not txt:
                            continue
                        en = bool(b.get("enabled", True))
                        buttons.append({"id": bid, "text": txt, "enabled": en})
            except Exception:
                pass

        trade = None
        trade_select = None
        deed_detail = None
        try:
            popup_type = getattr(popup, "popup_type", "") or ""

            def _hex(c):
                if isinstance(c, str) and c:
                    return c
                try:
                    r, g, b = c
                    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                except Exception:
                    return None

            def _prop_card(prop_idx: int) -> Dict:
                prop = getattr(game, "properties", [None])[prop_idx]
                data = getattr(prop, "data", {}) or {}
                name = str(data.get("name", ""))
                mortgaged = bool(getattr(prop, "is_mortgaged", False))
                houses = int(getattr(prop, "houses", 0) or 0)
                return {
                    "idx": int(prop_idx),
                    "name": name,
                    "color": _hex(data.get("color")),
                    "mortgaged": mortgaged,
                    "houses": houses,
                    "tradable": (not mortgaged) and houses == 0,
                }

            if self.state == "monopoly" and popup_type.startswith("trade_"):
                initiator_seat = getattr(game, "trade_initiator", None)
                partner_seat = getattr(game, "trade_partner", None)
                if isinstance(initiator_seat, int) and isinstance(partner_seat, int):
                    initiator = getattr(game, "players", [None] * 8)[initiator_seat]
                    partner = getattr(game, "players", [None] * 8)[partner_seat]

                    initiator_props = []
                    partner_props = []
                    try:
                        for pidx in list(getattr(initiator, "properties", []) or []):
                            initiator_props.append(_prop_card(int(pidx)))
                    except Exception:
                        initiator_props = []
                    try:
                        for pidx in list(getattr(partner, "properties", []) or []):
                            partner_props.append(_prop_card(int(pidx)))
                    except Exception:
                        partner_props = []

                    offer = getattr(game, "trade_offer", {}) or {}
                    request = getattr(game, "trade_request", {}) or {}
                    trade = {
                        "initiator": int(initiator_seat),
                        "partner": int(partner_seat),
                        "offer": {
                            "money": int(offer.get("money", 0) or 0),
                            "properties": [int(x) for x in (offer.get("properties", []) or [])],
                        },
                        "request": {
                            "money": int(request.get("money", 0) or 0),
                            "properties": [int(x) for x in (request.get("properties", []) or [])],
                        },
                        "initiator_assets": {
                            "money": int(getattr(initiator, "money", 0) or 0),
                            "properties": initiator_props,
                        },
                        "partner_assets": {
                            "money": int(getattr(partner, "money", 0) or 0),
                            "properties": partner_props,
                        },
                    }

            # Trade partner selection: expose the currently highlighted partner's assets.
            if self.state == "monopoly" and popup_type == "trade_select":
                initiator_seat = getattr(game, "trade_initiator", None)
                try:
                    scroll_pos = int(getattr(game, "trade_scroll_index", 0) or 0)
                except Exception:
                    scroll_pos = 0

                active_players = list(getattr(game, "active_players", []) or [])
                players = list(getattr(game, "players", [None] * 8) or [])

                if isinstance(initiator_seat, int) and active_players:
                    candidate_positions: List[int] = []
                    for pos, seat in enumerate(active_players):
                        try:
                            seat_i = int(seat)
                        except Exception:
                            continue
                        if seat_i == initiator_seat:
                            continue
                        if not (0 <= seat_i < len(players)):
                            continue
                        p = players[seat_i]
                        if p is None:
                            continue
                        if bool(getattr(p, "is_bankrupt", False)):
                            continue
                        candidate_positions.append(pos)

                    if candidate_positions:
                        if scroll_pos not in candidate_positions:
                            scroll_pos = candidate_positions[0]
                        partner_seat = int(active_players[scroll_pos])
                        partner = players[partner_seat] if 0 <= partner_seat < len(players) else None

                        partner_props: List[Dict] = []
                        try:
                            for pidx in list(getattr(partner, "properties", []) or []):
                                partner_props.append(_prop_card(int(pidx)))
                        except Exception:
                            partner_props = []

                        trade_select = {
                            "initiator": int(initiator_seat),
                            "partner": int(partner_seat),
                            "partner_name": self._player_display_name(partner_seat),
                            "choice_index": int(candidate_positions.index(scroll_pos) + 1),
                            "choice_count": int(len(candidate_positions)),
                            "partner_assets": {
                                "money": int(getattr(partner, "money", 0) or 0) if partner is not None else 0,
                                "properties": partner_props,
                            },
                        }

            # Mortgage/Deeds detail: expose structured property details for rich UI rendering.
            if self.state == "monopoly" and popup_type == "mortgage":
                try:
                    prop_idx = int((getattr(popup, "data", {}) or {}).get("prop_idx"))
                except Exception:
                    prop_idx = None

                player_obj = (getattr(popup, "data", {}) or {}).get("player")

                if isinstance(prop_idx, int) and hasattr(game, "properties"):
                    prop = getattr(game, "properties", [None])[prop_idx]
                    data = getattr(prop, "data", {}) or {}
                    prop_type = str(data.get("type", ""))
                    group = data.get("group")
                    mortgage_value = int(data.get("mortgage_value", 0) or 0)
                    unmortgage_cost = int(mortgage_value * 1.1)
                    rent_tiers = data.get("rent")
                    if not isinstance(rent_tiers, list):
                        rent_tiers = None

                    owned_in_group = None
                    try:
                        if player_obj is not None and group is not None:
                            owned = 0
                            for pidx in list(getattr(player_obj, "properties", []) or []):
                                try:
                                    pidx_i = int(pidx)
                                except Exception:
                                    continue
                                p2 = getattr(game, "properties", [None])[pidx_i]
                                d2 = getattr(p2, "data", {}) or {}
                                if d2.get("group") == group:
                                    owned += 1
                            owned_in_group = int(owned)
                    except Exception:
                        owned_in_group = None

                    scroll_index = None
                    scroll_total = None
                    try:
                        if player_obj is not None:
                            props = list(getattr(player_obj, "properties", []) or [])
                            scroll_total = int(len(props))
                            scroll_index = int(getattr(game, "mortgage_scroll_index", 0) or 0) + 1
                    except Exception:
                        scroll_index = None
                        scroll_total = None

                    deed_detail = {
                        "idx": int(prop_idx),
                        "name": str(data.get("name", "")),
                        "type": prop_type,
                        "group": str(group) if group is not None else None,
                        "color": _hex(data.get("color")),
                        "price": int(data.get("price", 0) or 0),
                        "mortgage_value": mortgage_value,
                        "unmortgage_cost": unmortgage_cost,
                        "house_cost": int(data.get("house_cost", 0) or 0),
                        "rent_tiers": [int(x or 0) for x in rent_tiers] if rent_tiers is not None else None,
                        "mortgaged": bool(getattr(prop, "is_mortgaged", False)) if prop is not None else False,
                        "houses": int(getattr(prop, "houses", 0) or 0) if prop is not None else 0,
                        "owned_in_group": owned_in_group,
                        "scroll_index": scroll_index,
                        "scroll_total": scroll_total,
                        "player_money": int(getattr(player_obj, "money", 0) or 0) if player_obj is not None else None,
                    }
        except Exception:
            trade = None
            trade_select = None
            deed_detail = None

        return {
            "active": True,
            "popup_type": getattr(popup, "popup_type", ""),
            "lines": lines,
            "line_items": line_items,
            "buttons": buttons,
            "trade": trade,
            "trade_select": trade_select,
            "deed_detail": deed_detail,
        }

    def _get_panel_buttons_snapshot(self, game, player_idx: int):
        if not hasattr(game, "buttons"):
            return []

        def _monopoly_current_turn_seat() -> Optional[int]:
            """Best-effort current turn seat for Monopoly.

            This is used for UI gating; if we cannot determine it confidently,
            we return None and the UI will default to a safe disabled state.
            """
            try:
                ap = getattr(game, "active_players", None)
                cpi = getattr(game, "current_player_idx", None)
                if not isinstance(ap, list) or not ap:
                    return None
                try:
                    idx = int(cpi)
                except Exception:
                    idx = 0
                if idx < 0:
                    idx = 0
                if idx >= len(ap):
                    idx = 0
                return int(ap[idx])
            except Exception:
                return None

        # Monopoly UX: never show non-current players an enabled Action/Build button.
        # Also, when current turn cannot be determined, default to a safe disabled state.
        curr_turn_seat = _monopoly_current_turn_seat() if self.state == "monopoly" else None

        btns = []
        player_buttons = getattr(game, "buttons", {}).get(player_idx)
        if not player_buttons:
            return []
        for btn_id, btn in player_buttons.items():
            # Popup-only buttons are rendered in the dedicated popup snapshot/UI.
            # Avoid duplicating them in the normal panel button list.
            if isinstance(btn_id, str) and btn_id.startswith("popup_"):
                continue
            text = getattr(btn, "text", "")
            enabled = bool(getattr(btn, "enabled", True))

            if self.state == "monopoly":
                # If we can't determine whose turn it is, avoid showing actionable
                # End Turn/Roll/Build for anyone (server will still enforce).
                if not isinstance(curr_turn_seat, int):
                    if btn_id == "action":
                        text = "Roll"
                        enabled = False
                    elif btn_id == "build":
                        enabled = False
                elif player_idx != curr_turn_seat:
                    if btn_id == "action":
                        # Always show Roll (disabled) for non-current players.
                        text = "Roll"
                        enabled = False
                    elif btn_id == "build":
                        enabled = False

            if text:
                btns.append({"id": btn_id, "text": text, "enabled": enabled})
        return btns

    def get_ui_snapshot(self, player_idx: int):
        # Audio snapshot (music mute vote)
        my_client_id = None
        try:
            for cid, seat in (self.ui_client_player or {}).items():
                if cid not in (self.ui_clients or {}):
                    continue
                if isinstance(seat, int) and seat == player_idx:
                    my_client_id = cid
                    break
        except Exception:
            my_client_id = None

        try:
            mute_votes, mute_required, music_muted = self._music_vote_counts()
        except Exception:
            mute_votes, mute_required, music_muted = 0, 1, False

        snap = {
            "server_state": self.state,
            "history": list(getattr(self, "ui_history", [])),
            "audio": {
                "music_muted": bool(music_muted),
                "mute_votes": int(mute_votes),
                "mute_required": int(mute_required),
                "you_voted_mute": bool(self.ui_client_music_mute_vote.get(my_client_id, False)) if my_client_id else False,
            },
            "palette": {
                "player_colors": [
                    "#ff4d4d",  # Player 1
                    "#4d79ff",  # Player 2
                    "#4dff88",  # Player 3
                    "#ffd24d",  # Player 4
                    "#b84dff",  # Player 5
                    "#4dfff0",  # Player 6
                    "#ff4dd2",  # Player 7
                    "#c7ff4d",  # Player 8
                ]
            },
            "available_player_slots": self._get_available_player_slots(),
            "taken_player_slots": self._get_taken_player_slots(),
            "your_player_slot": int(player_idx) if isinstance(player_idx, int) else player_idx,
            "lobby": {
                "players": self._get_lobby_players_snapshot(),
                "all_ready": self._lobby_all_ready(),
                "votes": {},
                "seated_count": sum(1 for s in self.ui_client_player.values() if isinstance(s, int) and s >= 0),
                "min_players": int(getattr(self, "min_connected_players", 2)),
            },
        }

        # End Game consensus state (in-game only)
        if self.state != "menu":
            # Determine this client's pressed state by matching player_idx -> client_id.
            pressed = False
            try:
                # Find client id whose seat matches player_idx.
                for cid, seat in (self.ui_client_player or {}).items():
                    if cid not in (self.ui_clients or {}):
                        continue
                    if isinstance(seat, int) and seat == player_idx:
                        pressed = bool(self.ui_client_end_game.get(cid, False))
                        break
            except Exception:
                pressed = False

            required_ids = self._required_end_game_client_ids()
            snap["end_game"] = {
                "pressed": pressed,
                "pressed_count": sum(1 for cid in required_ids if bool(self.ui_client_end_game.get(cid, False))),
                "required_count": len(required_ids),
            }

        # Vote counts (menu only)
        if self.state == "menu":
            counts: Dict[str, int] = {}
            for cid, key in (self.ui_client_vote or {}).items():
                if not key:
                    continue
                if not bool(self.ui_client_ready.get(cid, False)):
                    continue
                counts[key] = counts.get(key, 0) + 1
            snap["lobby"]["votes"] = counts

        # Include cursor positions for drawing dots in the web UI trackpad
        cursors = []
        now = time.time()
        for pidx, cur in (self.web_cursors or {}).items():
            pos = cur.get("pos")
            if not pos:
                continue
            col = PLAYER_COLORS[int(pidx) % len(PLAYER_COLORS)]
            # Normalize to 0..1 in top-left origin
            x_norm = float(pos[0]) / float(max(1, WINDOW_SIZE[0]))
            y_norm = float(pos[1]) / float(max(1, WINDOW_SIZE[1]))
            cursors.append({
                "player_idx": int(pidx),
                "name": self.player_names.get(int(pidx)) or f"Player {int(pidx) + 1}",
                "color": [int(col[0]), int(col[1]), int(col[2])],
                "x": max(0.0, min(1.0, x_norm)),
                "y": max(0.0, min(1.0, y_norm)),
                "age_ms": int((now - float(cur.get("t", now))) * 1000),
            })
        snap["cursors"] = cursors
        if self.state == "menu":
            snap["menu_games"] = [{"key": b["key"], "label": b["text"]} for b in self.game_buttons]
            return snap

        game = self._get_active_game()
        if game is None:
            return snap

        # Game-specific info for the Web UI
        if self.state == "monopoly":
            try:
                mg = self.monopoly_game
                players = []
                for pidx in getattr(mg, "active_players", []) or []:
                    try:
                        pidx_int = int(pidx)
                    except Exception:
                        continue
                    if pidx_int < 0 or pidx_int > 7:
                        continue
                    p = getattr(mg, "players", [None] * 8)[pidx_int]
                    if p is None:
                        continue
                    props = []
                    for prop_idx in getattr(p, "properties", []) or []:
                        try:
                            prop_i = int(prop_idx)
                        except Exception:
                            continue
                        if prop_i < 0 or prop_i >= len(getattr(mg, "properties", []) or []):
                            continue
                        prop = mg.properties[prop_i]
                        props.append({
                            "idx": prop_i,
                            "name": str(getattr(prop, "data", {}).get("name", "")),
                        })

                    players.append({
                        "player_idx": pidx_int,
                        "name": self.player_names.get(pidx_int) or f"Player {pidx_int + 1}",
                        "money": int(getattr(p, "money", 0)),
                        "jail_free_cards": int(getattr(p, "get_out_of_jail_cards", 0)),
                        "properties": props,
                    })

                ownership: Dict[str, int] = {}
                for i, prop in enumerate(getattr(mg, "properties", []) or []):
                    owner = getattr(prop, "owner", None)
                    if owner is None:
                        continue
                    try:
                        ownership[str(i)] = int(owner)
                    except Exception:
                        continue

                snap["monopoly"] = {
                    "players": players,
                    "ownership": ownership,
                    "current_turn_seat": None,
                    "current_turn_name": None,
                }

                # Provide current turn info for UI clarity.
                try:
                    active_players = getattr(mg, "active_players", None)
                    current_player_idx = getattr(mg, "current_player_idx", None)
                    if isinstance(active_players, list) and isinstance(current_player_idx, int):
                        if 0 <= current_player_idx < len(active_players):
                            seat = int(active_players[current_player_idx])
                            snap["monopoly"]["current_turn_seat"] = seat
                            snap["monopoly"]["current_turn_name"] = self.player_names.get(seat) or f"Player {seat + 1}"
                except Exception:
                    pass
            except Exception:
                pass

        if self.state == "blackjack":
            try:
                bg = self.blackjack_game
                summary = None
                try:
                    if hasattr(bg, "get_status_summary"):
                        summary = bg.get_status_summary()
                except Exception:
                    summary = None

                snap["blackjack"] = {
                    "state": str(getattr(bg, "state", "")),
                    "phase_text": (summary or {}).get("phase_text"),
                    "ready_count": (summary or {}).get("ready_count"),
                    "required_count": (summary or {}).get("required_count"),
                    "your_chips": None,
                    "your_current_bet": 0,
                    "your_total_bet": 0,
                    "your_hand": [],
                    "your_hand_value": None,
                    "result_popup": None,
                }

                if isinstance(player_idx, int) and 0 <= player_idx <= 7:
                    p = getattr(bg, "players", [None] * 8)[player_idx]
                    if p is not None:
                        try:
                            snap["blackjack"]["your_chips"] = int(getattr(p, "chips", 0) or 0)
                        except Exception:
                            snap["blackjack"]["your_chips"] = None
                        try:
                            snap["blackjack"]["your_current_bet"] = int(getattr(p, "current_bet", 0) or 0)
                        except Exception:
                            snap["blackjack"]["your_current_bet"] = 0

                        total_bet = 0
                        try:
                            for h in list(getattr(p, "hands", []) or []):
                                total_bet += int(getattr(h, "bet", 0) or 0)
                        except Exception:
                            total_bet = 0
                        if total_bet == 0:
                            total_bet = int(snap["blackjack"]["your_current_bet"] or 0)
                        snap["blackjack"]["your_total_bet"] = int(total_bet)

                        # Show only the requesting player's own hand cards.
                        hand_cards = []
                        hand_value = None
                        try:
                            hand = None
                            if hasattr(p, "get_current_hand"):
                                hand = p.get_current_hand()
                            if hand is None:
                                # Fallback: first hand
                                hs = list(getattr(p, "hands", []) or [])
                                hand = hs[0] if hs else None
                            if hand is not None:
                                cards = list(getattr(hand, "cards", []) or [])
                                hand_cards = [str(c) for c in cards]
                                if hasattr(hand, "value"):
                                    hand_value = int(hand.value())
                        except Exception:
                            hand_cards = []
                            hand_value = None
                        snap["blackjack"]["your_hand"] = hand_cards
                        snap["blackjack"]["your_hand_value"] = hand_value

                        # Must-close Web UI result popup for this player (if any)
                        try:
                            if hasattr(bg, "get_web_result_popup"):
                                snap["blackjack"]["result_popup"] = bg.get_web_result_popup(player_idx)
                        except Exception:
                            snap["blackjack"]["result_popup"] = None
            except Exception:
                pass

        if self.state == "uno":
            try:
                ug = self.uno_game
                snap["uno"] = {
                    "state": str(getattr(ug, "state", "")),
                    "active_players": list(getattr(ug, "active_players", []) or []),
                    "current_turn_seat": getattr(ug, "current_turn_seat", None),
                    "direction": int(getattr(ug, "direction", 1) or 1),
                    "current_color": getattr(ug, "current_color", None),
                    "top_card": None,
                    "hand_counts": {},
                    "your_hand": [],
                    "winner": getattr(ug, "winner", None),
                    "awaiting_color": False,
                    "next_round_ready": {},
                    "next_round_ready_count": 0,
                    "next_round_total": 0,
                }

                try:
                    st = ug.get_public_state(player_idx) if hasattr(ug, "get_public_state") else None
                except Exception:
                    st = None
                if isinstance(st, dict):
                    for k in (
                        "state",
                        "active_players",
                        "current_turn_seat",
                        "direction",
                        "current_color",
                        "top_card",
                        "hand_counts",
                        "your_hand",
                        "winner",
                        "awaiting_color",
                        "next_round_ready",
                        "next_round_ready_count",
                        "next_round_total",
                    ):
                        if k in st:
                            snap["uno"][k] = st.get(k)

                # Ensure consistent types
                try:
                    if isinstance(snap["uno"].get("hand_counts"), dict):
                        snap["uno"]["hand_counts"] = {str(k): int(v or 0) for k, v in snap["uno"]["hand_counts"].items()}
                except Exception:
                    snap["uno"]["hand_counts"] = {}
            except Exception:
                pass

        if self.state == "exploding_kittens":
            try:
                ekg = self.exploding_kittens_game
                snap["exploding_kittens"] = {
                    "state": str(getattr(ekg, "state", "")),
                    "active_players": list(getattr(ekg, "active_players", []) or []),
                    "eliminated_players": list(getattr(ekg, "eliminated_players", []) or []),
                    "current_turn_seat": getattr(ekg, "current_turn_seat", None),
                    "pending_draws": int(getattr(ekg, "pending_draws", 1) or 1),
                    "deck_count": int(len(getattr(ekg, "draw_pile", []) or [])),
                    "discard_top": None,
                    "last_event": None,
                    "last_event_age_ms": 0,
                    "hand_counts": {},
                    "your_hand": [],
                    "awaiting_favor_target": False,
                    "nope_active": False,
                    "nope_count": 0,
                    "winner": getattr(ekg, "winner", None),
                }

                try:
                    st = ekg.get_public_state(player_idx) if hasattr(ekg, "get_public_state") else None
                except Exception:
                    st = None
                if isinstance(st, dict):
                    for k in (
                        "state",
                        "active_players",
                        "eliminated_players",
                        "current_turn_seat",
                        "pending_draws",
                        "deck_count",
                        "discard_top",
                        "last_event",
                        "last_event_age_ms",
                        "hand_counts",
                        "your_hand",
                        "awaiting_favor_target",
                        "nope_active",
                        "nope_count",
                        "winner",
                    ):
                        if k in st:
                            snap["exploding_kittens"][k] = st.get(k)

                try:
                    if isinstance(snap["exploding_kittens"].get("hand_counts"), dict):
                        snap["exploding_kittens"]["hand_counts"] = {
                            str(k): int(v or 0) for k, v in snap["exploding_kittens"]["hand_counts"].items()
                        }
                except Exception:
                    snap["exploding_kittens"]["hand_counts"] = {}
            except Exception:
                pass

        if self.state == "texas_holdem":
            try:
                tg = self.texas_holdem_game
                st = tg.get_public_state(player_idx) if hasattr(tg, "get_public_state") else None
                if isinstance(st, dict):
                    snap["texas_holdem"] = st
            except Exception:
                pass

        if self.state == "cluedo":
            try:
                cg = self.cluedo_game
                st = cg.get_public_state(player_idx) if hasattr(cg, "get_public_state") else None
                if isinstance(st, dict):
                    snap["cluedo"] = st
            except Exception:
                pass

        if self.state == "risk":
            try:
                rg = self.risk_game
                st = rg.get_public_state(player_idx) if hasattr(rg, "get_public_state") else None
                if isinstance(st, dict):
                    snap["risk"] = st
            except Exception:
                pass

        if self.state == "dnd_creation":
            try:
                dg = getattr(self.dnd_creation, "game", None)
                dm_seat = self.dnd_dm_seat
                dnd_state = str(getattr(dg, "state", "")) if dg is not None else ""

                selected_seats: List[int] = []
                try:
                    if dg is not None and getattr(dg, "state", None) == "player_select" and hasattr(dg, "selection_ui"):
                        sel = list(getattr(dg.selection_ui, "selected", []) or [])
                        selected_seats = [i for i, s in enumerate(sel[:8]) if s]
                    else:
                        selected_seats = [int(x) for x in (getattr(dg, "active_players", []) or [])]
                except Exception:
                    selected_seats = []

                try:
                    from games.dnd.models import Character, RACES, CLASSES
                except Exception:
                    Character = None
                    RACES = []
                    CLASSES = []

                monsters = []
                try:
                    from games.dnd.data import MONSTERS
                    monsters = sorted([str(k) for k in (MONSTERS or {}).keys()])
                except Exception:
                    monsters = []

                players = []
                for seat in range(8):
                    has_saved = False
                    try:
                        if Character is not None:
                            has_saved = bool(Character.character_exists(seat))
                    except Exception:
                        has_saved = False

                    char = None
                    try:
                        if dg is not None:
                            char = (getattr(dg, "characters", {}) or {}).get(seat)
                    except Exception:
                        char = None

                    try:
                        if char is not None and hasattr(char, "normalize_inventory"):
                            char.normalize_inventory()
                    except Exception:
                        pass

                    players.append({
                        "player_idx": seat,
                        "selected": bool(seat in set(selected_seats)),
                        "is_dm": bool(isinstance(dm_seat, int) and seat == dm_seat),
                        "has_saved": bool(has_saved),
                        "has_character": bool(char is not None),
                        "name": getattr(char, "name", "") if char is not None else "",
                        "race": getattr(char, "race", "") if char is not None else "",
                        "char_class": getattr(char, "char_class", "") if char is not None else "",
                        "hp": int(getattr(char, "current_hp", 0) or 0) if char is not None else 0,
                        "ac": int(getattr(char, "armor_class", 0) or 0) if char is not None else 0,
                        "abilities": dict(getattr(char, "abilities", {}) or {}) if char is not None else {},
                        "skills": list(getattr(char, "skills", []) or []) if char is not None else [],
                        "background": str(getattr(char, "background", "") or "") if char is not None else "",
                        "feats": list(getattr(char, "feats", []) or []) if char is not None else [],
                        "features": list(getattr(char, "features", []) or []) if char is not None else [],
                        "inventory": list(getattr(char, "inventory", []) or []) if char is not None else [],
                        "equipment": dict(getattr(char, "equipment", {}) or {}) if char is not None else {},
                    })

                enemies = []
                try:
                    for idx, e in enumerate(list(getattr(dg, "enemies", []) or [])):
                        enemies.append({
                            "enemy_idx": int(idx),
                            "name": str(getattr(e, "name", "")),
                            "hp": int(getattr(e, "current_hp", 0) or 0),
                            "max_hp": int(getattr(e, "max_hp", 0) or 0),
                            "ac": int(getattr(e, "armor_class", 0) or 0),
                            "cr": float(getattr(e, "cr", 0) or 0),
                        })
                except Exception:
                    enemies = []

                snap["dnd"] = {
                    "state": dnd_state,
                    "dm_player_idx": dm_seat,
                    "background": self.dnd_background,
                    "background_files": self._list_dnd_background_files(),
                    "background_questions": _dnd_background_questions(),
                    "in_combat": bool(getattr(dg, "in_combat", False)) if dg is not None else False,
                    "races": list(RACES) if isinstance(RACES, list) else [],
                    "classes": list(CLASSES) if isinstance(CLASSES, list) else [],
                    "monsters": monsters,
                    "players": players,
                    "enemies": enemies,
                }
            except Exception:
                pass

        game_state = getattr(game, "state", None)
        if game_state == "player_select":
            ps = self._get_player_select_snapshot(game)
            if ps:
                snap["player_select"] = ps

        popup = self._get_popup_snapshot(game, player_idx)
        snap["popup"] = popup
        # Avoid duplicate action sets (e.g., Buy/Pass showing twice): when a popup is active
        # for this player, the popup's buttons are authoritative.
        if popup.get("active"):
            snap["panel_buttons"] = []
        else:
            snap["panel_buttons"] = self._get_panel_buttons_snapshot(game, player_idx)
        return snap

    async def ui_broadcast_loop(self):
        while self.running:
            if self.ui_clients:
                to_remove = []
                tasks = []
                for client_id, ws in list(self.ui_clients.items()):
                    pidx = self.ui_client_player.get(client_id, -1)
                    if isinstance(pidx, int) and pidx >= 0:
                        self._ensure_player_slot_selected(pidx)
                    payload = {"type": "snapshot", "data": self.get_ui_snapshot(pidx)}
                    tasks.append((client_id, ws.send(json.dumps(payload))))
                results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)
                for (client_id, _), res in zip(tasks, results):
                    if isinstance(res, Exception):
                        to_remove.append(client_id)
                for client_id in to_remove:
                    self.ui_clients.pop(client_id, None)
                    self.ui_client_player.pop(client_id, None)
                    self.ui_client_name.pop(client_id, None)
                    self.ui_client_ready.pop(client_id, None)
                    self.ui_client_vote.pop(client_id, None)
                if to_remove:
                    self._sync_player_select_from_seats()
            await asyncio.sleep(0.1)

    def _apply_ui_action(self, client_id: str, data: Dict):
        msg_type = data.get("type")

        if msg_type == "quit":
            # Player leaves the current session: release seat and clear lobby state.
            seat = self.ui_client_player.get(client_id, -1)

            # If a player quits mid-game, apply game-specific cleanup.
            try:
                if isinstance(seat, int) and seat >= 0:
                    # Monopoly already has bespoke quit logic; do not change it.
                    if self.state == "monopoly":
                        mg = getattr(self, "monopoly_game", None)
                        if mg is not None and hasattr(mg, "handle_player_quit"):
                            mg.handle_player_quit(seat)
                    else:
                        g = self._get_active_game()
                        if g is not None and hasattr(g, "handle_player_quit"):
                            g.handle_player_quit(seat)

                    # Blackjack has per-seat result popups; ensure quitters don't block progression.
                    if self.state == "blackjack":
                        bg = getattr(self, "blackjack_game", None)
                        if bg is not None and hasattr(bg, "close_web_result"):
                            bg.close_web_result(seat)
            except Exception:
                pass

            self.ui_client_player[client_id] = -1
            self.ui_client_ready[client_id] = False
            self.ui_client_vote.pop(client_id, None)
            self.ui_client_end_game[client_id] = False
            self.ui_client_music_mute_vote.pop(client_id, None)
            self._recompute_music_mute()
            self._sync_player_select_from_seats()

            who = None
            try:
                if isinstance(seat, int) and seat >= 0:
                    who = self.player_names.get(seat) or f"Player {seat + 1}"
            except Exception:
                who = None
            self._log_history(f"{who or 'A player'} quit")
            return

        if msg_type == "end_game":
            if self.state == "menu":
                return
            # Only seated clients can participate.
            seat = self.ui_client_player.get(client_id, -1)
            if not (isinstance(seat, int) and seat >= 0):
                return
            pressed = bool(data.get("pressed", True))
            self.ui_client_end_game[client_id] = pressed
            self._maybe_end_game()
            return

        if msg_type == "hello":
            name = (data.get("name") or "").strip()
            if name:
                self.ui_client_name[client_id] = name[:24]
            # Back-compat: older clients may include player_idx inside hello.
            if "player_idx" in data:
                try:
                    desired = int(data.get("player_idx"))
                except Exception:
                    desired = -1
                if 0 <= desired <= 7:
                    if self._try_set_client_seat(client_id, desired):
                        if name:
                            self.player_names[desired] = name[:24]
                        return
            # New flow: hello only sets the name; seat chosen via set_seat.
            # If unseated, auto-assign a seat now.
            if self._try_auto_assign_client_seat(client_id):
                seat = self.ui_client_player.get(client_id, -1)
                if isinstance(seat, int) and seat >= 0 and name:
                    self.player_names[seat] = name[:24]
            self.ui_client_end_game.setdefault(client_id, False)
            return

        if msg_type == "vote_music_mute":
            # Only seated clients can vote.
            seat = self.ui_client_player.get(client_id, -1)
            if not (isinstance(seat, int) and seat >= 0):
                return
            cur = bool(self.ui_client_music_mute_vote.get(client_id, False))
            self.ui_client_music_mute_vote[client_id] = not cur
            self._recompute_music_mute()
            return

        if msg_type == "set_seat":
            try:
                desired = int(data.get("player_idx"))
            except Exception:
                return
            ok = self._try_set_client_seat(client_id, desired)
            if ok:
                name = (data.get("name") or "").strip() or self.ui_client_name.get(client_id, "")
                if name:
                    self.player_names[desired] = name[:24]
            return

        if msg_type == "set_ready":
            ready = bool(data.get("ready"))
            self.ui_client_ready[client_id] = ready
            return

        if msg_type == "vote_game":
            # Only allow voting when everyone is ready and we are still in menu.
            if self.state != "menu":
                return
            if not self._lobby_all_ready():
                return
            key = data.get("key")
            if not isinstance(key, str):
                return
            key = key.strip()
            # Back-compat alias
            if key == "dnd":
                key = "d&d"
            try:
                allowed_keys = {str(b.get("key")) for b in (self.game_buttons or []) if b and b.get("key")}
            except Exception:
                allowed_keys = set()
            if key not in allowed_keys:
                return
            # Only ready+seated clients may vote.
            seat = self.ui_client_player.get(client_id, -1)
            if not (isinstance(seat, int) and seat >= 0):
                return
            if not bool(self.ui_client_ready.get(client_id, False)):
                return
            self.ui_client_vote[client_id] = key
            self._maybe_apply_vote_result()
            return

        if msg_type in ("pointer", "tap"):
            pidx = self.ui_client_player.get(client_id, 0)
            try:
                x = float(data.get("x"))
                y = float(data.get("y"))
            except Exception:
                return
            # Web UI sends normalized 0..1 in screen space (top-left origin)
            x = max(0.0, min(1.0, x))
            y = max(0.0, min(1.0, y))
            px = int(x * WINDOW_SIZE[0])
            py = int(y * WINDOW_SIZE[1])
            click = bool(data.get("click")) or (msg_type == "tap")
            self.web_cursors[pidx] = {"pos": (px, py), "click": click, "t": time.time()}
            return

        if msg_type in ("esc", "back"):
            self.web_esc_requested = True
            return

        if msg_type == "select_game" and self.state == "menu":
            # Deprecated in favor of voting; ignore.
            return

        game = self._get_active_game()
        if game is None:
            return

        # Web UI: allow decreasing Blackjack bet during betting phase.
        if self.state == "blackjack" and msg_type == "blackjack_adjust_bet":
            pidx = self.ui_client_player.get(client_id, -1)
            if not (isinstance(pidx, int) and pidx >= 0):
                return
            try:
                amount = int(data.get("amount", 0) or 0)
            except Exception:
                amount = 0
            if amount <= 0:
                return
            try:
                bg = self.blackjack_game
                if str(getattr(bg, "state", "")) != "betting":
                    return
                player = getattr(bg, "players", [None] * 8)[pidx]
                if player is None:
                    return
                # Don't allow modifying once ready.
                if bool(getattr(player, "is_ready", False)):
                    return
                if hasattr(bg, "adjust_current_bet"):
                    bg.adjust_current_bet(pidx, -amount)
                else:
                    cur = int(getattr(player, "current_bet", 0) or 0)
                    setattr(player, "current_bet", max(0, cur - amount))
                    if hasattr(bg, "_show_betting_for_all_players"):
                        bg._show_betting_for_all_players()
            except Exception:
                return
            return

        # Web UI: close the must-close Blackjack win/lose popup.
        if self.state == "blackjack" and msg_type == "blackjack_close_result":
            pidx = self.ui_client_player.get(client_id, -1)
            if not (isinstance(pidx, int) and pidx >= 0):
                return
            try:
                bg = self.blackjack_game
                if hasattr(bg, "close_web_result"):
                    bg.close_web_result(pidx)
            except Exception:
                return
            return

        # Web-UI-first Monopoly trade editing (drag/drop + +/- money)
        if self.state == "monopoly" and msg_type in ("trade_adjust_money", "trade_set_property"):
            pidx = self.ui_client_player.get(client_id, -1)
            if not (isinstance(pidx, int) and pidx >= 0):
                return
            popup = getattr(game, "popup", None)
            if not getattr(popup, "active", False):
                return
            popup_type = str(getattr(popup, "popup_type", "") or "")
            if popup_type != "trade_web_edit":
                return
            initiator_seat = getattr(game, "trade_initiator", None)
            partner_seat = getattr(game, "trade_partner", None)
            if not (isinstance(initiator_seat, int) and isinstance(partner_seat, int)):
                return
            if pidx != initiator_seat:
                return

            if msg_type == "trade_adjust_money":
                side = data.get("side")
                try:
                    delta = int(data.get("delta"))
                except Exception:
                    return
                if side not in ("offer", "request"):
                    return
                offer = getattr(game, "trade_offer", {}) or {}
                request = getattr(game, "trade_request", {}) or {}
                try:
                    initiator_money = int(getattr(getattr(game, "players", [None] * 8)[initiator_seat], "money", 0) or 0)
                except Exception:
                    initiator_money = 0
                try:
                    partner_money = int(getattr(getattr(game, "players", [None] * 8)[partner_seat], "money", 0) or 0)
                except Exception:
                    partner_money = 0

                if side == "offer":
                    cur = int(offer.get("money", 0) or 0)
                    nxt = max(0, cur + delta)
                    nxt = min(nxt, max(0, initiator_money))
                    offer["money"] = nxt
                    game.trade_offer = offer
                else:
                    cur = int(request.get("money", 0) or 0)
                    nxt = max(0, cur + delta)
                    nxt = min(nxt, max(0, partner_money))
                    request["money"] = nxt
                    game.trade_request = request

                # Refresh popup state
                if hasattr(game, "_show_trade_web_edit"):
                    game._show_trade_web_edit()
                return

            if msg_type == "trade_set_property":
                side = data.get("side")
                try:
                    prop_idx = int(data.get("prop_idx"))
                except Exception:
                    return
                included = bool(data.get("included"))
                if side not in ("offer", "request"):
                    return

                props = getattr(game, "properties", []) or []
                if prop_idx < 0 or prop_idx >= len(props):
                    return
                prop = props[prop_idx]
                mortgaged = bool(getattr(prop, "is_mortgaged", False))
                houses = int(getattr(prop, "houses", 0) or 0)
                if mortgaged or houses > 0:
                    return

                initiator = getattr(game, "players", [None] * 8)[initiator_seat]
                partner = getattr(game, "players", [None] * 8)[partner_seat]
                initiator_owned = set(getattr(initiator, "properties", []) or [])
                partner_owned = set(getattr(partner, "properties", []) or [])

                if side == "offer":
                    if prop_idx not in initiator_owned:
                        return
                    offer = getattr(game, "trade_offer", {}) or {}
                    offer_props = list(offer.get("properties", []) or [])
                    if included and prop_idx not in offer_props:
                        offer_props.append(prop_idx)
                    if (not included) and prop_idx in offer_props:
                        offer_props.remove(prop_idx)
                    offer["properties"] = offer_props
                    game.trade_offer = offer
                else:
                    if prop_idx not in partner_owned:
                        return
                    request = getattr(game, "trade_request", {}) or {}
                    req_props = list(request.get("properties", []) or [])
                    if included and prop_idx not in req_props:
                        req_props.append(prop_idx)
                    if (not included) and prop_idx in req_props:
                        req_props.remove(prop_idx)
                    request["properties"] = req_props
                    game.trade_request = request

                if hasattr(game, "_show_trade_web_edit"):
                    game._show_trade_web_edit()
                return

        # Player selection controls
        if msg_type == "set_player_selected" and getattr(game, "state", None) == "player_select":
            try:
                pidx = int(data.get("player_idx"))
                selected = bool(data.get("selected"))
            except Exception:
                return
            if not hasattr(game, "selection_ui"):
                return
            if 0 <= pidx < len(game.selection_ui.selected):
                game.selection_ui.selected[pidx] = selected
            return

        if msg_type == "dnd_set_dm" and self.state == "dnd_creation" and getattr(game, "state", None) == "player_select":
            seat = self.ui_client_player.get(client_id, -1)
            if not (isinstance(seat, int) and 0 <= seat <= 7):
                return
            try:
                selected = list(getattr(game.selection_ui, "selected", []) or [])
                if seat >= len(selected) or not bool(selected[seat]):
                    return
            except Exception:
                return
            self.dnd_dm_seat = seat
            try:
                if hasattr(game, "set_dm_player_idx"):
                    game.set_dm_player_idx(seat)
                else:
                    game.dm_player_idx = seat
            except Exception:
                pass
            self._log_history(f"{self._player_display_name(seat)} set themselves as DM")
            return

        if msg_type == "start_game" and getattr(game, "state", None) == "player_select":
            if not hasattr(game, "selection_ui"):
                return
            selected_indices = [i for i, s in enumerate(game.selection_ui.selected) if s]
            if self.state == "monopoly" and len(selected_indices) >= 2:
                game.start_game(selected_indices)
            elif self.state == "blackjack" and len(selected_indices) >= 1:
                game.start_game(selected_indices)
            elif self.state == "uno" and len(selected_indices) >= 2:
                game.start_game(selected_indices)
            elif self.state == "exploding_kittens" and len(selected_indices) >= 2:
                game.start_game(selected_indices)
            elif self.state == "texas_holdem" and len(selected_indices) >= 2:
                game.start_game(selected_indices)
            elif self.state == "cluedo" and len(selected_indices) >= 3 and len(selected_indices) <= 6:
                game.start_game(selected_indices)
            elif self.state == "risk" and len(selected_indices) >= 2:
                game.start_game(selected_indices)
            elif self.state == "dnd_creation":
                dm = self.dnd_dm_seat
                if len(selected_indices) >= 2 and isinstance(dm, int) and dm in selected_indices:
                    try:
                        if hasattr(game, "set_dm_player_idx"):
                            game.set_dm_player_idx(dm)
                        else:
                            game.dm_player_idx = dm
                    except Exception:
                        pass
                    game.start_game(selected_indices)
            return

        # D&D web character creation/load + basic actions
        if self.state == "dnd_creation":
            seat = self.ui_client_player.get(client_id, -1)
            if not (isinstance(seat, int) and 0 <= seat <= 7):
                seat = None

            if msg_type == "dnd_load_character":
                if seat is None:
                    return
                try:
                    from games.dnd.models import Character
                    char = Character.load_from_file(seat)
                except Exception:
                    char = None
                if char is None:
                    return
                try:
                    if hasattr(game, "set_character"):
                        game.set_character(seat, char)
                    else:
                        game.characters[seat] = char
                    if hasattr(game, "maybe_advance_from_char_creation"):
                        game.maybe_advance_from_char_creation()
                except Exception:
                    pass
                self._log_history(f"{self._player_display_name(seat)} loaded a character")
                return

            if msg_type == "dnd_create_character":
                if seat is None:
                    return
                if isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat:
                    return

                race = str(data.get("race") or "").strip()
                char_class = str(data.get("char_class") or "").strip()
                name = str(data.get("name") or "").strip()
                try:
                    from games.dnd.models import (
                        Character,
                        RACES,
                        CLASSES,
                        ALIGNMENTS,
                        ABILITY_SCORES,
                        generate_character_name,
                        CLASS_SKILLS,
                    )
                except Exception:
                    return
                if race not in RACES or char_class not in CLASSES:
                    return

                # Optional Web UI point-buy abilities
                abilities_from_ui = data.get("abilities")
                abilities = None
                if isinstance(abilities_from_ui, dict):
                    try:
                        parsed: Dict[str, int] = {}
                        for a in ABILITY_SCORES:
                            if a not in abilities_from_ui:
                                raise ValueError("missing")
                            v = int(abilities_from_ui.get(a))
                            parsed[a] = v

                        # 5e point-buy: scores 8..15, costs 0,1,2,3,4,5,7,9
                        cost_map = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
                        total_cost = 0
                        for a, v in parsed.items():
                            if v < 8 or v > 15:
                                raise ValueError("range")
                            if v not in cost_map:
                                raise ValueError("cost")
                            total_cost += cost_map[v]
                        if total_cost > 27:
                            raise ValueError("budget")
                        abilities = parsed
                    except Exception:
                        abilities = None

                if abilities is None:
                    def roll_ability() -> int:
                        rolls = [random.randint(1, 6) for _ in range(4)]
                        rolls.sort()
                        return int(sum(rolls[1:]))

                    abilities = {a: roll_ability() for a in ABILITY_SCORES}
                if not name:
                    name = generate_character_name(race, char_class)

                # Background questionnaire answers (optional)
                raw_answers = data.get("background_answers")
                bg_answers: Dict[str, str] = {}
                if isinstance(raw_answers, dict):
                    for k, v in raw_answers.items():
                        kid = str(k or "").strip()
                        if not kid:
                            continue
                        bg_answers[kid] = str(v or "").strip()

                char = Character(name=name, player_color=tuple(PLAYER_COLORS[seat % len(PLAYER_COLORS)]))
                char.race = race
                char.char_class = char_class
                try:
                    char.alignment = random.choice(list(ALIGNMENTS))
                except Exception:
                    char.alignment = ""
                char.abilities = abilities
                try:
                    base_skills = list(CLASS_SKILLS.get(char_class, []))
                except Exception:
                    base_skills = []
                # Keep the class baseline (up to 2), then add 2 background-influenced skills.
                try:
                    seed_hint = f"seat:{seat}|cid:{client_id}"
                    rng = random.Random(_stable_rng_seed(name, race, char_class, seed_hint))
                    extra_skills = _dnd_pick_additional_skills(char_class, bg_answers, rng)
                except Exception:
                    extra_skills = []
                merged_skills: List[str] = []
                for s in (base_skills[:2] + list(extra_skills or [])):
                    s = str(s or "").strip()
                    if not s:
                        continue
                    if s not in merged_skills:
                        merged_skills.append(s)
                char.skills = merged_skills

                # Starting items / equipment based on class
                try:
                    loadout_items, equip_map = _dnd_starting_loadout(char_class)
                except Exception:
                    loadout_items, equip_map = ([], {})
                try:
                    for it in list(loadout_items or []):
                        char.add_item(it)
                except Exception:
                    pass
                try:
                    # Resolve "__auto:Name" placeholders to actual item IDs
                    name_to_id: Dict[str, str] = {}
                    for it in list(getattr(char, "inventory", []) or []):
                        if not isinstance(it, dict):
                            continue
                        nm = str(it.get("name") or "").strip()
                        iid = str(it.get("id") or "").strip()
                        if nm and iid and nm not in name_to_id:
                            name_to_id[nm] = iid
                    char.equipment = dict(getattr(char, "equipment", {}) or {})
                    for slot, ref in (equip_map or {}).items():
                        sslot = str(slot or "").strip()
                        if not sslot:
                            continue
                        r = str(ref or "").strip()
                        if r.startswith("__auto:"):
                            nm = r.replace("__auto:", "", 1).strip()
                            iid = name_to_id.get(nm)
                            if iid:
                                char.equipment[sslot] = iid
                        else:
                            # If a raw item id was provided
                            if r:
                                char.equipment[sslot] = r
                except Exception:
                    pass

                # Background narrative + feats + features
                try:
                    bg_text, feats, features = _dnd_generate_background_text(name, race, char_class, bg_answers, seed_hint=f"seat:{seat}")
                    char.background = bg_text
                    char.background_answers = bg_answers
                    char.feats = list(feats or [])
                    char.features = list(features or [])
                except Exception:
                    try:
                        char.background_answers = bg_answers
                    except Exception:
                        pass
                try:
                    # Derived stats should reflect equipped gear.
                    if hasattr(char, "update_derived_stats"):
                        char.update_derived_stats(reset_current_hp=True)
                    else:
                        char.calculate_hp()
                        char.calculate_ac()
                except Exception:
                    pass

                try:
                    char.save_to_file(seat)
                except Exception:
                    pass
                try:
                    if hasattr(game, "set_character"):
                        game.set_character(seat, char)
                    else:
                        game.characters[seat] = char
                    if hasattr(game, "maybe_advance_from_char_creation"):
                        game.maybe_advance_from_char_creation()
                except Exception:
                    pass
                self._log_history(f"{self._player_display_name(seat)} created a character: {name}")
                return

            if msg_type == "dnd_roll_dice":
                if seat is None:
                    return
                try:
                    sides = int(data.get("sides"))
                except Exception:
                    return
                if sides not in (4, 6, 8, 10, 12, 20):
                    return
                result = random.randint(1, sides)
                self._log_history(f"{self._player_display_name(seat)} rolled d{sides}: {result}")
                try:
                    self._queue_dnd_dice_roll(seat, sides, result)
                except Exception:
                    pass
                return

            if msg_type == "dnd_dm_set_background_file":
                if seat is None or not (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat):
                    return
                bg_file = str(data.get("background_file") or "").strip()
                if not bg_file:
                    return
                try:
                    allowed = set(self._list_dnd_background_files() or [])
                except Exception:
                    allowed = set()
                if bg_file not in allowed:
                    return
                self.dnd_background = bg_file
                try:
                    self._dnd_bg_prompt_cache = ""
                    self._dnd_bg_sprite = None
                    self._dnd_bg_img_size = (0, 0)
                    self._dnd_bg_aspect_key = (0, 0)
                except Exception:
                    pass
                self._log_history(f"DM set local background: {bg_file}")
                return

            if msg_type == "dnd_dm_give_item":
                if seat is None or not (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat):
                    return
                try:
                    target = int(data.get("target_player_idx"))
                except Exception:
                    return
                if target < 0 or target > 7:
                    return
                try:
                    char = (getattr(game, "characters", {}) or {}).get(target)
                    if char is None:
                        return
                    raw_item = data.get("item")
                    if isinstance(raw_item, dict):
                        item_obj = raw_item
                    else:
                        item_name = str(raw_item or "").strip()
                        if not item_name:
                            return
                        item_obj = {"name": item_name, "kind": "misc"}

                    try:
                        if hasattr(char, "add_item"):
                            char.add_item(item_obj)
                        else:
                            inv = list(getattr(char, "inventory", []) or [])
                            inv.append(item_obj)
                            char.inventory = inv
                    except Exception:
                        return
                    try:
                        char.save_to_file(target)
                    except Exception:
                        pass
                except Exception:
                    return
                try:
                    given_name = str((item_obj or {}).get("name") or "item")
                except Exception:
                    given_name = "item"
                self._log_history(f"DM gave {given_name} to {self._player_display_name(target)}")
                return

            if msg_type == "dnd_use_item":
                if seat is None:
                    return
                item_id = str(data.get("item_id") or "").strip()
                if not item_id:
                    return
                try:
                    char = (getattr(game, "characters", {}) or {}).get(seat)
                    if char is None:
                        return
                    ok = bool(getattr(char, "use_item", lambda _id: False)(item_id))
                    if ok:
                        try:
                            char.save_to_file(seat)
                        except Exception:
                            pass
                        self._log_history(f"{self._player_display_name(seat)} used an item")
                except Exception:
                    return
                return

            if msg_type == "dnd_equip_item":
                if seat is None:
                    return
                item_id = str(data.get("item_id") or "").strip()
                if not item_id:
                    return
                try:
                    char = (getattr(game, "characters", {}) or {}).get(seat)
                    if char is None:
                        return
                    ok = bool(getattr(char, "equip_item", lambda _id: False)(item_id))
                    if ok:
                        try:
                            char.save_to_file(seat)
                        except Exception:
                            pass
                        self._log_history(f"{self._player_display_name(seat)} equipped gear")
                except Exception:
                    return
                return

            if msg_type == "dnd_unequip_slot":
                if seat is None:
                    return
                slot = str(data.get("slot") or "").strip()
                if not slot:
                    return
                try:
                    char = (getattr(game, "characters", {}) or {}).get(seat)
                    if char is None:
                        return
                    ok = bool(getattr(char, "unequip_slot", lambda _s: False)(slot))
                    if ok:
                        try:
                            char.save_to_file(seat)
                        except Exception:
                            pass
                        self._log_history(f"{self._player_display_name(seat)} unequipped {slot}")
                except Exception:
                    return
                return

            if msg_type == "dnd_dm_spawn_enemy":
                if seat is None or not (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat):
                    return
                try:
                    from games.dnd.data import MONSTERS
                except Exception:
                    MONSTERS = {}
                monster_name = str(data.get("monster") or "").strip()
                if not monster_name:
                    try:
                        monster_name = random.choice(list(MONSTERS.keys())) if MONSTERS else ""
                    except Exception:
                        monster_name = ""
                if not monster_name:
                    return
                try:
                    if hasattr(game, "_spawn_enemy"):
                        game._spawn_enemy(monster_name)
                        self._log_history(f"DM spawned enemy: {monster_name}")
                    else:
                        self._log_history(f"DM spawn enemy requested: {monster_name}")
                except Exception:
                    return
                return

            if msg_type == "dnd_dm_adjust_enemy_hp":
                if seat is None or not (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat):
                    return
                try:
                    enemy_idx = int(data.get("enemy_idx"))
                    delta = int(data.get("delta"))
                except Exception:
                    return
                if delta == 0:
                    return
                try:
                    enemies = list(getattr(game, "enemies", []) or [])
                    if enemy_idx < 0 or enemy_idx >= len(enemies):
                        return
                    enemy = enemies[enemy_idx]
                    if delta < 0:
                        # negative delta means damage
                        if hasattr(enemy, "take_damage"):
                            enemy.take_damage(abs(delta))
                        else:
                            enemy.current_hp = max(0, int(getattr(enemy, "current_hp", 0) or 0) - abs(delta))
                    else:
                        if hasattr(enemy, "heal"):
                            enemy.heal(delta)
                        else:
                            enemy.current_hp = min(
                                int(getattr(enemy, "max_hp", 0) or 0),
                                int(getattr(enemy, "current_hp", 0) or 0) + delta,
                            )
                    self._log_history(f"DM adjusted {getattr(enemy, 'name', 'enemy')} HP ({delta:+d})")
                except Exception:
                    return
                return

            if msg_type == "dnd_dm_remove_enemy":
                if seat is None or not (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat):
                    return
                try:
                    enemy_idx = int(data.get("enemy_idx"))
                except Exception:
                    return
                try:
                    enemies = list(getattr(game, "enemies", []) or [])
                    if enemy_idx < 0 or enemy_idx >= len(enemies):
                        return
                    removed = enemies.pop(enemy_idx)
                    game.enemies = enemies
                    # End combat if no enemies remain.
                    try:
                        if not enemies:
                            game.in_combat = False
                            if getattr(game, "state", None) == "combat":
                                game.state = "gameplay"
                    except Exception:
                        pass
                    self._log_history(f"DM removed enemy: {getattr(removed, 'name', 'enemy')}")
                except Exception:
                    return
                return

        # Popup / panel button clicks
        if msg_type == "click_button":
            btn_id = data.get("id")
            if not isinstance(btn_id, str):
                return
            pidx = self.ui_client_player.get(client_id, -1)
            if not (isinstance(pidx, int) and pidx >= 0):
                return

            # Universal end-of-game vote popup (server-managed)
            try:
                if btn_id.startswith("popup_") and self._handle_endgame_vote_click(int(pidx), btn_id):
                    return
            except Exception:
                pass
            if self.state == "monopoly":
                # Enforce turn/popup ownership server-side.
                if getattr(game.popup, "active", False):
                    try:
                        popup_owner = getattr(game.popup, "player_idx", None)
                    except Exception:
                        popup_owner = None

                    # If a popup is active for this player, only allow popup buttons.
                    if isinstance(popup_owner, int) and popup_owner == pidx:
                        if btn_id == "popup_close":
                            try:
                                if str(getattr(game.popup, "popup_type", "") or "") == "mortgage":
                                    game.popup.hide()
                                    if hasattr(game, "_restore_default_buttons"):
                                        game._restore_default_buttons(pidx)
                            except Exception:
                                pass
                        elif btn_id == "popup_cancel":
                            try:
                                if str(getattr(game.popup, "popup_type", "") or "") == "trade_select":
                                    game.popup.hide()
                                    if hasattr(game, "_restore_default_buttons"):
                                        game._restore_default_buttons(pidx)
                                    # Reset trade state.
                                    try:
                                        game.trade_initiator = None
                                        game.trade_partner = None
                                        game.trade_offer = {"money": 0, "properties": []}
                                        game.trade_request = {"money": 0, "properties": []}
                                    except Exception:
                                        pass
                                    try:
                                        game.trade_mode = None
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        elif btn_id.startswith("popup_"):
                            game._handle_popup_button_click(btn_id)
                        return

                if btn_id in ("action", "props", "build"):
                    # Only the current-turn player may perform turn actions.
                    curr_seat = None
                    try:
                        ap = getattr(game, "active_players", None)
                        cpi = getattr(game, "current_player_idx", None)
                        if isinstance(ap, list) and ap:
                            try:
                                idx = int(cpi)
                            except Exception:
                                idx = 0
                            if idx < 0 or idx >= len(ap):
                                idx = 0
                            curr_seat = int(ap[idx])
                    except Exception:
                        curr_seat = None

                    if btn_id in ("action", "build") and isinstance(curr_seat, int) and pidx != curr_seat:
                        return

                    game._handle_click(pidx, btn_id)
            elif self.state == "blackjack":
                game._handle_popup_click(pidx, btn_id)
            elif self.state == "uno":
                if hasattr(game, "handle_click"):
                    game.handle_click(pidx, btn_id)
            elif self.state == "exploding_kittens":
                if hasattr(game, "handle_click"):
                    game.handle_click(pidx, btn_id)
            elif self.state == "texas_holdem":
                if hasattr(game, "handle_click"):
                    game.handle_click(pidx, btn_id)
            elif self.state == "cluedo":
                if hasattr(game, "handle_click"):
                    if btn_id == "roll":
                        try:
                            self._play_sfx("RollDice.mp3")
                        except Exception:
                            pass
                    game.handle_click(pidx, btn_id)
            elif self.state == "risk":
                if hasattr(game, "handle_click"):
                    if btn_id == "attack":
                        try:
                            self._play_sfx("SwordSlice.mp3")
                        except Exception:
                            pass
                    game.handle_click(pidx, btn_id)
            return

    async def handle_ui_client(self, websocket):
        client_id = f"ui:{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.ui_clients[client_id] = websocket
        self.ui_client_player.setdefault(client_id, -1)
        self.ui_client_ready.setdefault(client_id, False)
        self.ui_client_end_game.setdefault(client_id, False)
        print(f"UI client connected: {client_id}")

        if self.state == "menu":
            try:
                self._play_sfx("HeartbeatReady.mp3")
            except Exception:
                pass

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    continue
                try:
                    data = json.loads(message)
                except Exception:
                    continue
                try:
                    self._apply_ui_action(client_id, data)
                except Exception as e:
                    print(f"UI action error: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.ui_clients.pop(client_id, None)
            self.ui_client_player.pop(client_id, None)
            self.ui_client_name.pop(client_id, None)
            self.ui_client_ready.pop(client_id, None)
            self.ui_client_vote.pop(client_id, None)
            self.ui_client_end_game.pop(client_id, None)
            self.ui_client_music_mute_vote.pop(client_id, None)
            try:
                self._recompute_music_mute()
            except Exception:
                pass
            print(f"UI client disconnected: {client_id}")
    
    def _create_game_buttons(self):
        """Create game selection buttons"""
        games = [
            ("Monopoly", "monopoly"),
            ("Blackjack", "blackjack"),
            ("Uno", "uno"),
            ("Exploding Kittens", "exploding_kittens"),
            ("Texas Hold'em", "texas_holdem"),
            ("Cluedo", "cluedo"),
            ("Risk", "risk"),
            ("D&D", "d&d"),
        ]
        buttons = []
        for i, (label, key) in enumerate(games):
            btn_rect = (
                WINDOW_SIZE[0] // 2 - 150,
                WINDOW_SIZE[1] // 2 - 180 + i * 120,
                300, 90
            )
            buttons.append({"text": label, "rect": btn_rect, "key": key})
        return buttons
    
    def on_draw(self):
        """Pyglet draw callback"""
        # Ensure the viewport matches the actual framebuffer.
        # With Windows DPI scaling, the framebuffer can be larger than window.width/height.
        # If the viewport stays at the logical size, you get big black borders.
        try:
            fb_w, fb_h = self.window.get_framebuffer_size()
        except Exception:
            fb_w, fb_h = self.window.width, self.window.height
        draw_w, draw_h = int(fb_w), int(fb_h)
        try:
            self.window.viewport = (0, 0, draw_w, draw_h)
        except Exception:
            pass
        try:
            gl.glViewport(0, 0, draw_w, draw_h)
        except Exception:
            pass

        # Critical for HiDPI/DPI scaling: pyglet.shapes uses window.projection/view.
        # If projection stays in logical window units while the viewport is framebuffer-sized,
        # drawings appear letterboxed with a border. Force projection to framebuffer units.
        try:
            self.window.projection = Mat4.orthogonal_projection(0, draw_w, 0, draw_h, -1, 1)
            self.window.view = Mat4()
        except Exception:
            pass

        # Drive ALL drawing/layout off framebuffer dimensions to avoid DPI scaling margins.
        # (On 1080p @ 100% DPI, framebuffer == window size so this is a no-op.)
        try:
            self.renderer.width = draw_w
            self.renderer.height = draw_h
        except Exception:
            pass
        try:
            global WINDOW_SIZE
            WINDOW_SIZE = (draw_w, draw_h)
        except Exception:
            pass

        # Keep active games in sync with the draw size.
        # Many layouts use game.width/game.height; update them dynamically.
        for g in (
            getattr(self, "monopoly_game", None),
            getattr(self, "blackjack_game", None),
            getattr(self, "uno_game", None),
            getattr(self, "exploding_kittens_game", None),
            getattr(self, "texas_holdem_game", None),
            getattr(self, "cluedo_game", None),
            getattr(self, "risk_game", None),
            getattr(self, "dnd_creation", None),
        ):
            if g is None:
                continue
            try:
                setattr(g, "width", draw_w)
                setattr(g, "height", draw_h)
            except Exception:
                pass

        self.window.clear()
        
        # Clear renderer cache for new frame
        self.renderer.clear_cache()
        
        if self.state == "menu":
            self._draw_menu()
        elif self.state == "monopoly":
            self.monopoly_game.draw()
        elif self.state == "blackjack":
            self.blackjack_game.draw()
        elif self.state == "uno":
            self.uno_game.draw()
        elif self.state == "exploding_kittens":
            self.exploding_kittens_game.draw()
        elif self.state == "texas_holdem":
            self.texas_holdem_game.draw()
        elif self.state == "cluedo":
            self.cluedo_game.draw()
        elif self.state == "risk":
            self.risk_game.draw()
        elif self.state == "dnd_creation":
            # Web UI drives D&D fully; keep the server window clean/fullscreen,
            # but reflect the chosen background + encounter.
            try:
                # Draw AI-generated background image (in-memory, no disk).
                try:
                    self._ensure_dnd_background_sprite(draw_w, draw_h)
                    if self._dnd_bg_sprite is not None:
                        self._dnd_bg_sprite.draw()
                    else:
                        self.renderer.draw_rect((12, 12, 12), (0, 0, draw_w, draw_h))
                except Exception:
                    self.renderer.draw_rect((12, 12, 12), (0, 0, draw_w, draw_h))

                # Slight dark overlay for readability.
                self.renderer.draw_rect((0, 0, 0), (0, 0, draw_w, draw_h), alpha=70)

                bg = str(getattr(self, "dnd_background", "") or "").strip()
                if not bg:
                    bg = "(no background set)"

                # Header
                self.renderer.draw_text(
                    "D&D (Web UI)",
                    24,
                    28,
                    font_size=20,
                    color=(230, 230, 230),
                    anchor_x="left",
                    anchor_y="top",
                )
                self.renderer.draw_text(
                    f"Background: {bg}",
                    24,
                    58,
                    font_size=16,
                    color=(200, 200, 200),
                    anchor_x="left",
                    anchor_y="top",
                )

                # Background generation status
                try:
                    state, detail = self._dnd_bg_status()
                except Exception:
                    state, detail = "", ""
                status_text = ""
                if state:
                    if state == "ready":
                        status_text = "BG: ready"
                    elif state == "fetching":
                        status_text = "BG: generating… (fetching)"
                    elif state == "decoding":
                        status_text = "BG: generating… (decoding)"
                    elif state == "queued":
                        status_text = "BG: generating…"
                    elif state == "error":
                        status_text = "BG: error"
                    else:
                        status_text = f"BG: {state}"
                if detail:
                    status_text = f"{status_text} · {detail}" if status_text else detail
                if status_text:
                    self.renderer.draw_text(
                        status_text,
                        24,
                        82,
                        font_size=12,
                        color=(190, 190, 190),
                        anchor_x="left",
                        anchor_y="top",
                    )

                # Encounter overlay (top-right)
                dg = None
                try:
                    dg = getattr(getattr(self, "dnd_creation", None), "game", None)
                except Exception:
                    dg = None
                try:
                    enemies = list(getattr(dg, "enemies", []) or []) if dg is not None else []
                except Exception:
                    enemies = []

                panel_w = min(420, max(320, draw_w // 3))
                panel_x = draw_w - panel_w - 24
                panel_y = 28
                card_h = 86
                gap = 10

                self.renderer.draw_text(
                    "Encounter",
                    panel_x,
                    panel_y,
                    font_size=18,
                    color=(230, 230, 230),
                    anchor_x="left",
                    anchor_y="top",
                )

                if not enemies:
                    self.renderer.draw_text(
                        "No enemies",
                        panel_x,
                        panel_y + 30,
                        font_size=14,
                        color=(180, 180, 180),
                        anchor_x="left",
                        anchor_y="top",
                    )
                else:
                    y = panel_y + 34
                    for e in enemies[:6]:
                        name = str(getattr(e, "name", "") or "Enemy")
                        hp = int(getattr(e, "current_hp", 0) or 0)
                        max_hp = int(getattr(e, "max_hp", 0) or 0)
                        ac = int(getattr(e, "armor_class", 0) or 0)
                        cr = getattr(e, "cr", 0) or 0
                        try:
                            cr_f = float(cr)
                        except Exception:
                            cr_f = 0.0

                        self.renderer.draw_rect((30, 30, 30), (panel_x, y, panel_w, card_h), alpha=220)
                        self.renderer.draw_rect((90, 90, 90), (panel_x, y, panel_w, card_h), width=1, alpha=220)
                        self.renderer.draw_text(
                            name,
                            panel_x + 12,
                            y + 14,
                            font_size=15,
                            color=(235, 235, 235),
                            anchor_x="left",
                            anchor_y="top",
                        )
                        self.renderer.draw_text(
                            f"HP {hp}/{max_hp}  ·  AC {ac}  ·  CR {cr_f:g}",
                            panel_x + 12,
                            y + 36,
                            font_size=12,
                            color=(200, 200, 200),
                            anchor_x="left",
                            anchor_y="top",
                        )

                        bar_x = panel_x + 12
                        bar_y = y + 58
                        bar_w = panel_w - 24
                        bar_h = 10
                        self.renderer.draw_rect((70, 70, 70), (bar_x, bar_y, bar_w, bar_h), alpha=220)
                        pct = (hp / max_hp) if max_hp > 0 else 0.0
                        pct = max(0.0, min(1.0, pct))
                        self.renderer.draw_rect((180, 60, 60), (bar_x, bar_y, int(bar_w * pct), bar_h), alpha=230)

                        y += card_h + gap

                # Dice roll animations (per seat)
                try:
                    self._dnd_dice_display.draw(self.renderer)
                except Exception:
                    pass
            except Exception:
                pass
        
        # Draw all batched shapes (board, panels, popups)
        self.renderer.draw_all()
        
        # Draw game-specific immediate elements (tokens on top of board, under popups)
        if self.state == "monopoly" and hasattr(self.monopoly_game, 'draw_immediate'):
            self.monopoly_game.draw_immediate()
        elif self.state == "blackjack" and hasattr(self.blackjack_game, 'draw_immediate'):
            self.blackjack_game.draw_immediate()
        
        # Draw popup batch again so popups appear on top of immediate elements
        if (not self.render_board_only) and self.state == "monopoly" and self.monopoly_game.popup.active:
            # Create new batch for popup only
            popup_renderer = self.monopoly_game.renderer
            popup_renderer.clear_cache()
            # Dim the UI around the board, but keep the board readable (property names).
            # Draw 4 rectangles around the board area rather than one full-screen overlay.
            try:
                bx, by, bw, bh = getattr(self.monopoly_game, "board_rect", (0, 0, 0, 0))
            except Exception:
                bx, by, bw, bh = (0, 0, 0, 0)
            w, h = int(self.monopoly_game.width), int(self.monopoly_game.height)
            dim = (0, 0, 0, 50)
            if bw > 0 and bh > 0:
                # Top
                if by > 0:
                    popup_renderer.draw_rect(dim, (0, 0, w, by))
                # Bottom
                bottom_y = by + bh
                if bottom_y < h:
                    popup_renderer.draw_rect(dim, (0, bottom_y, w, h - bottom_y))
                # Left
                if bx > 0:
                    popup_renderer.draw_rect(dim, (0, by, bx, bh))
                # Right
                right_x = bx + bw
                if right_x < w:
                    popup_renderer.draw_rect(dim, (right_x, by, w - right_x, bh))
            else:
                popup_renderer.draw_rect(dim, (0, 0, w, h))
            self.monopoly_game.popup.draw(popup_renderer)
            popup_renderer.draw_all()
        
        # If we only want the board in the Pyglet window, mask out the player UI panel regions.
        # IMPORTANT: do not apply this mask in the menu (it creates a fake "border").
        if self.render_board_only:
            active_game = None
            if self.state == "monopoly":
                active_game = self.monopoly_game
            elif self.state == "blackjack":
                active_game = self.blackjack_game
            elif self.state == "dnd_creation":
                active_game = self.dnd_creation

            if active_game is None:
                # Menu or unknown state: no masking.
                self._draw_cursors()
                self._update_fps()
                return

            # If the active game supports true board-only rendering, do not mask.
            if getattr(active_game, "board_only_mode", False):
                # Still draw cursors and FPS overlay.
                self._draw_cursors()
                self._update_fps()
                return

            h_panel = int(WINDOW_SIZE[1] * 0.10)
            v_panel = int(WINDOW_SIZE[0] * 0.12)
            w = int(WINDOW_SIZE[0])
            h = int(WINDOW_SIZE[1])
            # top
            self.renderer.draw_rect((0, 0, 0), (0, 0, w, h_panel))
            # bottom
            self.renderer.draw_rect((0, 0, 0), (0, h - h_panel, w, h_panel))
            # left
            self.renderer.draw_rect((0, 0, 0), (0, h_panel, v_panel, h - 2 * h_panel))
            # right
            self.renderer.draw_rect((0, 0, 0), (w - v_panel, h_panel, v_panel, h - 2 * h_panel))
            # Ensure mask draws immediately
            self.renderer.draw_all()

        # Dice overlay should appear above all UI layers.
        if self.state == "dnd_creation":
            try:
                self._dnd_dice_display.draw(self.renderer)
            except Exception:
                pass

        # Draw cursors AFTER everything else (and after the mask) so they're visible
        self._draw_cursors()
        
        # Update FPS counter
        self._update_fps()
    
    def on_key_press(self, symbol, modifiers):
        """Handle keyboard input"""
        if symbol == pyglet.window.key.ESCAPE:
            if self.state == "menu":
                print("ESC pressed in menu - Exiting server...")
                self.running = False
                pyglet.app.exit()
                self.window.close()
            else:
                print("ESC pressed in game - Returning to menu...")
                self.esc_pressed = True
    
    def on_close(self):
        """Handle window close event"""
        print("Window closed - Exiting server...")
        self.running = False
        pyglet.app.exit()
        return True
    
    def update(self, dt: float):
        """Update game state"""
        self._audio_tick()
        self._maybe_play_flip_on_deck_change()
        # Web UI history feed (log only on deltas)
        self._update_monopoly_history()

        # Web-UI-only: handle ESC centrally (no in-window input handling).
        if self.web_esc_requested:
            self.esc_pressed = True
            self.web_esc_requested = False

        if self.esc_pressed:
            self.esc_pressed = False
            if self.state == "menu":
                print("ESC pressed in menu - Exiting server...")
                self.running = False
                pyglet.app.exit()
                try:
                    self.window.close()
                except Exception:
                    pass
                return

            # In-game ESC returns to menu.
            print("ESC pressed in game - Returning to menu...")
            self.state = "menu"
            self._reset_lobby()
            try:
                self.monopoly_game.state = "player_select"
                self.monopoly_game.selection_ui.reset()
            except Exception:
                pass
            try:
                self.blackjack_game.state = "player_select"
                self.blackjack_game.selection_ui.reset()
            except Exception:
                pass
            try:
                self.uno_game.state = "player_select"
                self.uno_game.selection_ui.reset()
            except Exception:
                pass
            try:
                self.exploding_kittens_game.state = "player_select"
                self.exploding_kittens_game.selection_ui.reset()
            except Exception:
                pass
            try:
                self.texas_holdem_game.state = "player_select"
                self.texas_holdem_game.selection_ui.reset()
            except Exception:
                pass
            try:
                self.cluedo_game.state = "player_select"
                self.cluedo_game.selection_ui.reset()
            except Exception:
                pass
            try:
                sess = getattr(self.dnd_creation, "game", None)
                if sess is not None:
                    sess.state = "player_select"
                    if hasattr(sess, "selection_ui"):
                        sess.selection_ui.reset()
                    try:
                        sess.active_players = []
                        sess.characters = {}
                        sess.character_creators = {}
                    except Exception:
                        pass
                    try:
                        if hasattr(sess, "set_dm_player_idx"):
                            sess.set_dm_player_idx(None)
                        else:
                            sess.dm_player_idx = None
                    except Exception:
                        pass
                self.dnd_dm_seat = None
                self.dnd_background = None
                try:
                    with self._dnd_dice_lock:
                        self._dnd_dice_pending.clear()
                    self._dnd_dice_display.clear()
                except Exception:
                    pass
            except Exception:
                pass
            return

        # Web pointer cursors are optional (purely visual); expire stale cursors.
        if self.web_cursors:
            now = time.time()
            for pidx, cur in list(self.web_cursors.items()):
                if now - float(cur.get("t", now)) > 10.0:
                    del self.web_cursors[pidx]
        
        # Web-UI-only: no in-window input handling (no hover/click processing).
        if self.state == "menu":
            self._maybe_apply_vote_result()
        elif self.state == "monopoly":
            self.monopoly_game.update(dt)
        elif self.state == "blackjack":
            self.blackjack_game.update(dt)
        elif self.state == "uno":
            self.uno_game.update(dt)
        elif self.state == "exploding_kittens":
            self.exploding_kittens_game.update(dt)
        elif self.state == "texas_holdem":
            self.texas_holdem_game.update(dt)
        elif self.state == "cluedo":
            self.cluedo_game.update(dt)
            # Allow games to request a return-to-lobby flow (same as pressing ESC).
            try:
                if bool(getattr(self.cluedo_game, "request_return_to_lobby", False)):
                    self.cluedo_game.request_return_to_lobby = False
                    self.web_esc_requested = True
            except Exception:
                pass
        elif self.state == "dnd_creation":
            self.dnd_creation.update(dt)
            try:
                self._pump_dnd_dice_pending()
                self._dnd_dice_display.update(dt)
            except Exception:
                pass

        # Server-managed lifecycle behaviors
        if self.state != "menu":
            self._maybe_auto_start_active_game()
            self._maybe_show_endgame_vote_popup()
    
    def _handle_menu_input(self, fingertip_meta: List[Dict]):
        """Handle menu input"""
        # Web-UI-only: game selection is controlled from the Web UI.
        # Keep this as a no-op to avoid accidental local state changes.
        self.hover_states.clear()
        return

    def _active_connected_seats(self) -> List[int]:
        seats: List[int] = []
        for cid, seat in (self.ui_client_player or {}).items():
            if cid not in (self.ui_clients or {}):
                continue
            if isinstance(seat, int) and 0 <= seat <= 7 and seat not in seats:
                seats.append(int(seat))
        seats.sort()
        return seats

    def _maybe_auto_start_active_game(self) -> None:
        """Skip redundant in-game player selection; auto-start using seated clients."""
        game = self._get_active_game()
        if game is None:
            return
        if getattr(game, "state", None) != "player_select":
            return

        seats = self._active_connected_seats()
        if not seats:
            return

        # Per-game minimums.
        min_players = 2
        if self.state == "blackjack":
            min_players = 1
        elif self.state == "cluedo":
            min_players = 3
        elif self.state == "dnd_creation":
            min_players = 2

        if len(seats) < int(min_players):
            return

        # D&D: choose a default DM (lowest seat) if not set.
        if self.state == "dnd_creation":
            try:
                dm = getattr(self, "dnd_dm_seat", None)
                if not (isinstance(dm, int) and dm in seats):
                    dm = int(seats[0])
                    self.dnd_dm_seat = dm
                if hasattr(game, "set_dm_player_idx"):
                    game.set_dm_player_idx(dm)
                else:
                    setattr(game, "dm_player_idx", dm)
            except Exception:
                pass

        try:
            game.start_game(list(seats))
            self._log_history(f"Auto-started {self.state} with {len(seats)} players")
        except Exception:
            return

    def _endgame_participant_seats(self, game) -> List[int]:
        """Return seats who participated in the game, including eliminated when present."""
        seats: List[int] = []

        try:
            ap = getattr(game, "active_players", None)
            if isinstance(ap, list):
                for s in ap:
                    try:
                        si = int(s)
                    except Exception:
                        continue
                    if 0 <= si <= 7 and si not in seats:
                        seats.append(si)
        except Exception:
            pass

        # Include eliminated players when available (requested behavior).
        for attr in ("eliminated_players", "eliminated"):
            try:
                elim = getattr(game, attr, None)
                if isinstance(elim, list):
                    for s in elim:
                        try:
                            si = int(s)
                        except Exception:
                            continue
                        if 0 <= si <= 7 and si not in seats:
                            seats.append(si)
            except Exception:
                continue

        seats.sort()
        return seats

    def _is_game_over(self, game) -> bool:
        try:
            if getattr(game, "winner", None) is not None:
                return True
        except Exception:
            pass

        # Monopoly
        try:
            if str(getattr(game, "state", "")) == "winner" and getattr(game, "winner_idx", None) is not None:
                return True
        except Exception:
            pass

        # Blackjack
        try:
            if str(getattr(game, "state", "")) == "game_over":
                return True
        except Exception:
            pass

        # Texas Hold'em (terminal showdown)
        try:
            if str(getattr(game, "state", "")) == "showdown":
                sd = getattr(game, "last_showdown", None)
                if isinstance(sd, dict) and str(sd.get("reason") or "") == "Not enough players with chips":
                    return True
        except Exception:
            pass

        return False

    def _endgame_token(self, game) -> str:
        parts = [str(self.state)]
        for attr in ("game_id", "hand_id", "_web_round_id"):
            try:
                v = getattr(game, attr, None)
            except Exception:
                v = None
            if v is not None:
                parts.append(f"{attr}:{v}")
        for attr in ("winner", "winner_idx"):
            try:
                v = getattr(game, attr, None)
            except Exception:
                v = None
            if v is not None:
                parts.append(f"{attr}:{v}")
        return "|".join(parts)

    def _ensure_game_popup(self, game) -> None:
        if hasattr(game, "popup"):
            return
        try:
            setattr(game, "popup", UniversalPopup())
        except Exception:
            pass

    def _set_endgame_popup_text(self, game, eligible_seats: List[int]) -> None:
        popup = getattr(game, "popup", None)
        if popup is None:
            return

        votes_again = sum(1 for v in (self._endgame_votes_by_seat or {}).values() if v == "again")
        votes_lobby = sum(1 for v in (self._endgame_votes_by_seat or {}).values() if v == "lobby")
        total = int(len(eligible_seats))
        required = (total // 2) + 1 if total > 0 else 1

        winner_text = ""
        try:
            w = getattr(game, "winner", None)
            if isinstance(w, int):
                winner_text = f"Winner: {self._player_display_name(int(w))}"
        except Exception:
            winner_text = ""
        try:
            if not winner_text and str(getattr(game, "state", "")) == "winner":
                w = getattr(game, "winner_idx", None)
                if isinstance(w, int):
                    winner_text = f"Winner: {self._player_display_name(int(w))}"
        except Exception:
            pass

        lines = [("Game finished", 18, (220, 220, 220))]
        if winner_text:
            lines.append((winner_text, 18, (255, 255, 255)))
        lines.append((f"Votes (need {required}): Play again {votes_again} · Lobby {votes_lobby}", 16, (200, 200, 200)))
        popup.text_lines = lines

        # Provide popup buttons via popup.data so we don't need to mutate game.buttons.
        popup.data = {
            "buttons": [
                {"id": "popup_0", "text": "Play again", "enabled": True},
                {"id": "popup_1", "text": "Return to lobby", "enabled": True},
            ]
        }

    def _maybe_show_endgame_vote_popup(self) -> None:
        game = self._get_active_game()
        if game is None:
            return

        if not self._is_game_over(game):
            self._endgame_vote_token = None
            self._endgame_votes_by_seat = {}
            return

        self._ensure_game_popup(game)
        popup = getattr(game, "popup", None)
        if popup is None:
            return

        # Don't override other game popups.
        if bool(getattr(popup, "active", False)) and str(getattr(popup, "popup_type", "")) not in ("", "end_game_vote"):
            return

        token = self._endgame_token(game)
        if token != self._endgame_vote_token:
            self._endgame_vote_token = token
            self._endgame_votes_by_seat = {}

        participants = self._endgame_participant_seats(game)
        if not participants:
            participants = self._active_connected_seats()
        eligible = [s for s in self._active_connected_seats() if s in set(participants)]
        if not eligible:
            eligible = list(participants)

        popup.active = True
        popup.player_idx = None
        popup.popup_type = "end_game_vote"
        self._set_endgame_popup_text(game, eligible)

    def _handle_endgame_vote_click(self, seat: int, btn_id: str) -> bool:
        """Return True if handled."""
        game = self._get_active_game()
        if game is None:
            return False

        popup = getattr(game, "popup", None)
        if popup is None:
            return False

        if not (bool(getattr(popup, "active", False)) and str(getattr(popup, "popup_type", "")) == "end_game_vote"):
            return False

        if not self._is_game_over(game):
            return False

        participants = self._endgame_participant_seats(game)
        if not participants:
            participants = self._active_connected_seats()
        if int(seat) not in set(participants):
            return True  # handled (ignore)

        eligible = [s for s in self._active_connected_seats() if s in set(participants)]
        if not eligible:
            eligible = list(participants)

        choice = None
        if btn_id == "popup_0":
            choice = "again"
        elif btn_id == "popup_1":
            choice = "lobby"
        else:
            return False

        self._endgame_votes_by_seat[int(seat)] = str(choice)

        votes_again = sum(1 for v in (self._endgame_votes_by_seat or {}).values() if v == "again")
        votes_lobby = sum(1 for v in (self._endgame_votes_by_seat or {}).values() if v == "lobby")
        total = int(len(eligible))
        required = (total // 2) + 1 if total > 0 else 1

        self._set_endgame_popup_text(game, eligible)

        if votes_again >= required:
            try:
                popup.hide()
            except Exception:
                try:
                    popup.active = False
                except Exception:
                    pass
            try:
                game.start_game(list(participants))
            except Exception:
                pass
            self._endgame_votes_by_seat = {}
            self._endgame_vote_token = None
            return True

        if votes_lobby >= required:
            try:
                popup.hide()
            except Exception:
                try:
                    popup.active = False
                except Exception:
                    pass
            self._endgame_votes_by_seat = {}
            self._endgame_vote_token = None
            self.web_esc_requested = True
            return True

        return True
    
    def _draw_menu(self):
        """Draw main menu"""
        # Background (fill the whole screen)
        # Use renderer dimensions to avoid any mismatch with WINDOW_SIZE.
        w, h = int(getattr(self.renderer, "width", WINDOW_SIZE[0])), int(getattr(self.renderer, "height", WINDOW_SIZE[1]))
        # Slight overscan to avoid 1-2px borders from coordinate/driver rounding.
        self.renderer.draw_rect(Colors.DARK_BG, (-4, -4, w + 8, h + 8))
        # Subtle accents (no external assets)
        self.renderer.draw_rect(Colors.ACCENT, (-4, -4, w + 8, int(h * 0.22) + 8), alpha=10)
        self.renderer.draw_rect(Colors.WHITE, (-4, int(h * 0.78), w + 8, int(h * 0.22) + 8), alpha=5)
        self.renderer.draw_circle(Colors.ACCENT, (int(w * 0.18), int(h * 0.30)), int(min(w, h) * 0.24), alpha=8)
        self.renderer.draw_circle(Colors.ACCENT, (int(w * 0.84), int(h * 0.70)), int(min(w, h) * 0.30), alpha=6)

        center_x = w // 2
        
        # Title
        title_x = center_x
        title_y = int(h * 0.18)
        self.renderer.draw_text(
            "ARPi2 Game Launcher",
            title_x, title_y,
            font_name='Arial', font_size=64,
            color=Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )
        
        # Subtitle
        self.renderer.draw_text(
            "Use the Web UI to vote/select a game",
            title_x, title_y - 56,
            font_name='Arial', font_size=24,
            color=(200, 200, 200),
            anchor_x='center', anchor_y='center'
        )

        # Lobby status (Web UI players)
        try:
            lobby_players = self._get_lobby_players_snapshot() or []
        except Exception:
            lobby_players = []

        lobby_y = int(h * 0.44)
        self.renderer.draw_text(
            "Lobby",
            center_x, lobby_y,
            font_name='Arial', font_size=22,
            color=Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )

        # Player list (centered under Lobby, each with seat color)
        list_top_y = lobby_y + 18
        row_h = 26
        max_rows = 8
        entries = (lobby_players or [])[:max_rows]
        total_h = len(entries) * row_h
        start_y = int(list_top_y + 46)

        for i, entry in enumerate(entries):
            try:
                seat = int(entry.get("seat", -1))
            except Exception:
                continue
            if seat < 0 or seat > 7:
                continue
            name = (entry.get("name") or f"Player {seat + 1}").strip()
            ready = bool(entry.get("ready", False))
            connected = bool(entry.get("connected", True))

            label = f"{name}"
            tags = []
            tags.append("Ready" if ready else "Not ready")
            if not connected:
                tags.append("Disconnected")
            label = f"{label}  ({', '.join(tags)})"

            y = start_y + i * row_h
            col = PLAYER_COLORS[seat % len(PLAYER_COLORS)]
            # Color dot and centered label
            dot_x = center_x - 190
            self.renderer.draw_circle(col, (dot_x, y), 8)
            self.renderer.draw_circle(Colors.WHITE, (dot_x, y), 8, width=2)

            self.renderer.draw_text(
                label,
                center_x, y,
                font_name='Arial', font_size=18,
                color=col,
                anchor_x='center', anchor_y='center'
            )

        # If no one is seated yet, show a centered hint.
        if not entries:
            self.renderer.draw_text(
                "Waiting for players to join…",
                center_x, int(h * 0.56),
                font_name='Arial', font_size=20,
                color=(200, 200, 200),
                anchor_x='center', anchor_y='center'
            )
        
        # No in-window game buttons (web UI controls selection)
    
    def _draw_cursors(self):
        """Draw cursor for each fingertip - uses immediate drawing to be on top"""
        if self.web_cursors:
            # Draw all connected web cursors (one dot per player)
            for pidx, cur in self.web_cursors.items():
                pos = cur.get("pos")
                if not pos:
                    continue
                color = PLAYER_COLORS[pidx % len(PLAYER_COLORS)]
                self.renderer.draw_circle_immediate(color, pos, 9)
                self.renderer.draw_circle_immediate(Colors.WHITE, pos, 9, width=2)
            return

        # Web UI is button-driven; if players are connected but not sending pointer data,
        # still show a small per-player dot inside the playable area so you can see who is connected.
        if self.ui_clients:
            # Put these dots in the bottom-left corner so they don't clutter the top-left
            # of every game's board view.
            base_x = 26
            base_y = int(WINDOW_SIZE[1] - 26)
            players = sorted(set(self.ui_client_player.values()))
            for i, pidx in enumerate(players):
                pos_y = base_y - i * 24
                if pos_y < 18:
                    break
                pos = (base_x, pos_y)
                color = PLAYER_COLORS[pidx % len(PLAYER_COLORS)]
                self.renderer.draw_circle_immediate(color, pos, 9)
                self.renderer.draw_circle_immediate(Colors.WHITE, pos, 9, width=2)
            return

        # No legacy cursor rendering in web-ui-only mode.
        return
    
    def _update_fps(self):
        """Update FPS counter"""
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            """print(f"Server FPS: {self.current_fps:.1f}")"""
    
    async def broadcast_frame(self):
        """Capture screen and broadcast to all clients with GPU/CPU overlap"""
        if self.broadcasting:
            return
        
        self.broadcasting = True
        try:
            width = self.capture_width
            height = self.capture_height
            bytes_per_frame = self.capture_buffer_size
            current_index = self.capture_pbo_index
            next_index = (current_index + 1) % 2
            frame_bytes = None
            
            # Kick off asynchronous GPU read into current PBO
            gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.capture_pbos[current_index])
            gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, ctypes.c_void_p(0))
            
            # Map the previously used PBO to access completed pixel data
            if self.capture_ready:
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.capture_pbos[next_index])
                ptr = gl.glMapBuffer(gl.GL_PIXEL_PACK_BUFFER, gl.GL_READ_ONLY)
                if ptr:
                    frame_bytes = ctypes.string_at(ptr, bytes_per_frame)
                    gl.glUnmapBuffer(gl.GL_PIXEL_PACK_BUFFER)
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)
            else:
                # Skip first frame (no data yet)
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)
                self.capture_ready = True
            
            # Advance PBO index for next call
            self.capture_pbo_index = next_index
            
            if not frame_bytes:
                return
            
            loop = asyncio.get_running_loop()
            
            def encode_frame():
                arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                arr = arr.reshape((height, width, 3))
                arr = np.flip(arr, axis=0)  # Flip vertically
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                result, encoded = cv2.imencode('.jpg', arr, encode_param)
                if result:
                    return encoded.tobytes()
                return None
            
            encoded_bytes = await loop.run_in_executor(self.encode_executor, encode_frame)
            if not encoded_bytes or not self.clients:
                return
            
            disconnected = []
            send_tasks = []
            for client_id, websocket in list(self.clients.items()):
                send_tasks.append((client_id, websocket.send(encoded_bytes)))
            
            results = await asyncio.gather(*[task for _, task in send_tasks], return_exceptions=True)
            for (client_id, _), result in zip(send_tasks, results):
                if isinstance(result, Exception):
                    disconnected.append(client_id)
            
            for client_id in disconnected:
                if client_id in self.clients:
                    del self.clients[client_id]
        except Exception as e:
            print(f"Error broadcasting frame: {e}")
        finally:
            self.broadcasting = False

    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients[client_id] = websocket
        print(f"Client connected: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    if isinstance(message, bytes):
                        # Pi camera upload is no longer used for input; ignore binary uploads.
                        continue

                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    elif msg_type == "keyboard":
                        # could handle keyboard inputs if needed
                        pass
                    elif msg_type == "mouse":
                        pass
                except Exception as e:
                    print(f"Error processing message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {client_id}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def start_server(self):
        """Start WebSocket server"""
        async def handler(websocket):
            path = websocket.request.path
            if path == "/ui":
                await self.handle_ui_client(websocket)
            else:
                await self.handle_client(websocket, path)

        server = await websockets.serve(handler, self.host, self.port)
        print(f"Server started on ws://{self.host}:{self.port}")
        print("Press ESC to exit")
        
        await server.wait_closed()
    
    def run(self):
        """Run the game server"""
        print("Starting Pyglet/OpenGL Game Server...")
        print("This version includes complete UI with player selection and panels")

        # Start local Web UI (static files)
        self._start_http_server()
        
        # Schedule update function
        pyglet.clock.schedule_interval(self.update, 1.0 / FPS)
        
        # Run asyncio event loop with Pyglet
        async def main():
            # Start server
            server_task = asyncio.create_task(self.start_server())
            ui_task = asyncio.create_task(self.ui_broadcast_loop())
            
            try:
                # Run Pyglet in async context
                while self.running and len(pyglet.app.windows) > 0:
                    pyglet.clock.tick()
                    
                    for window in list(pyglet.app.windows):
                        if window and not window.has_exit:
                            window.switch_to()
                            window.dispatch_events()
                            window.dispatch_event('on_draw')
                            window.flip()
                    
                    # Broadcast frames to clients at specified FPS (non-blocking)
                    current_time = time.time()
                    if current_time - self.last_broadcast_time >= (1.0 / self.broadcast_fps):
                        if self.clients:  # Only broadcast if we have clients
                            # Fire and forget - don't await
                            asyncio.create_task(self.broadcast_frame())
                        self.last_broadcast_time = current_time
                    
                    await asyncio.sleep(0.001)  # Small sleep to prevent CPU spinning
            finally:
                # Cancel server task
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
                # Cancel UI broadcast
                ui_task.cancel()
                try:
                    await ui_task
                except asyncio.CancelledError:
                    pass
                print("Server shut down successfully")
        
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nServer stopped by user")
        except Exception as e:
            # Ignore the flip error during shutdown
            if "'NoneType' object has no attribute 'flip'" not in str(e):
                print(f"\nServer error: {e}")
        finally:
            self.running = False
            # Stop HTTP server
            if self._httpd is not None:
                try:
                    self._httpd.shutdown()
                    self._httpd.server_close()
                except Exception:
                    pass
            # Close window if still open
            try:
                if self.window and not self.window.has_exit:
                    self.window.close()
            except:
                pass
            # Stop worker pool
            self.encode_executor.shutdown(wait=False)
            if hasattr(self, "capture_pbos"):
                try:
                    gl.glDeleteBuffers(2, self.capture_pbos)
                except Exception:
                    pass
        print("Cleanup complete")


if __name__ == "__main__":
    server = PygletGameServer()
    server.run()
