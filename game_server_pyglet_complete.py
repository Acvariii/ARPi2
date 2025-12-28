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
import io
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from config import WINDOW_SIZE, FPS, HOVER_TIME_THRESHOLD, Colors
from config import PLAYER_COLORS
from core.renderer import PygletRenderer
from games.monopoly import MonopolyGame
from games.blackjack import BlackjackGame
from games.dnd import DnDCharacterCreation


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
        self.player_names: Dict[int, str] = {}
        self.web_cursors: Dict[int, Dict] = {}  # player_idx -> {pos:(x,y), click:bool, t:float}
        self.web_esc_requested = False

        # Web-UI-first mode: do not rely on hand tracking or mouse hover input.
        self.web_ui_only = True

        # Web UI extras
        self.ui_history: List[str] = []
        self._monopoly_last_ownership: Dict[int, int] = {}

        # D&D Web UI state
        self.dnd_dm_seat: Optional[int] = None
        self.dnd_background: Optional[str] = None

        # D&D background (AI-generated, in-memory)
        self._dnd_bg_prompt_cache: str = ""
        self._dnd_bg_sprite = None
        self._dnd_bg_img_size: tuple[int, int] = (0, 0)
        self._dnd_bg_aspect_key: tuple[int, int] = (0, 0)
        self._dnd_bg_lock = threading.Lock()
        self._dnd_bg_pending: Optional[tuple[tuple, bytes, str, int, int]] = None  # (desired_id, bytes, ext, iw, ih)
        self._dnd_bg_inflight_key: Optional[tuple] = None  # desired_id
        self._dnd_bg_desired_key: Optional[tuple] = None  # desired_id
        self._dnd_bg_last_error: str = ""
        self._dnd_bg_last_error_time: float = 0.0
        self._dnd_bg_last_log_key: Optional[tuple] = None
        self._dnd_bg_last_log_state: str = ""
        self._dnd_bg_last_log_time: float = 0.0

        # Optional local (on-device) background generation
        self._dnd_local_model_id: str = str((__import__("os").environ.get("DND_BG_LOCAL_MODEL") or "").strip())
        self._dnd_local_enabled: bool = str((__import__("os").environ.get("DND_BG_LOCAL_ENABLED") or "").strip()).lower() in ("1", "true", "yes")
        self._dnd_local_device: str = str((__import__("os").environ.get("DND_BG_LOCAL_DEVICE") or "cuda").strip())
        self._dnd_local_steps: int = int((__import__("os").environ.get("DND_BG_LOCAL_STEPS") or "24").strip() or 24)
        self._dnd_local_guidance: float = float((__import__("os").environ.get("DND_BG_LOCAL_GUIDANCE") or "3.5").strip() or 3.5)
        self._dnd_local_max_long: int = int((__import__("os").environ.get("DND_BG_LOCAL_MAX_LONG") or "1536").strip() or 1536)
        self._dnd_local_pipe = None
        self._dnd_local_pipe_lock = threading.Lock()

        # Lobby gating
        self.min_connected_players = 2

        # Finish initializing networking/window/rendering.
        self._finish_init()

    def _dnd_prompt_seed(self, prompt: str) -> int:
        p = (prompt or "").strip().encode("utf-8")
        h = hashlib.sha256(p).digest()
        return int.from_bytes(h[:8], "little", signed=False)

    def _pollinations_image_url(self, base: str, prompt: str, w: int, h: int, seed: int, model: str) -> str:
        """Build a Pollinations image URL.

        Notes:
        - Uses the public endpoint (no key required in most cases).
        - If POLLINATIONS_API_KEY env var is set, we pass it as a query param for higher limits.
        """
        safe_prompt = urllib.parse.quote((prompt or "").strip() or "fantasy scene", safe="")
        key = str((__import__("os").environ.get("POLLINATIONS_API_KEY") or "").strip())

        qs = {
            "model": model,
            "width": str(int(w)),
            "height": str(int(h)),
            "seed": str(int(seed) & 0x7FFFFFFF),
            "safe": "true",
            "enhance": "true",
            "nologo": "true",
        }
        if key:
            qs["key"] = key

        if base.endswith("/image"):
            # gen.pollinations.ai/image/<prompt>
            return f"{base}/{safe_prompt}?{urllib.parse.urlencode(qs)}"
        # image.pollinations.ai/prompt/<prompt>
        return f"{base}/prompt/{safe_prompt}?{urllib.parse.urlencode(qs)}"

    def _fetch_image_bytes(self, url: str, timeout_s: float = 30.0) -> tuple[bytes, str]:
        req = urllib.request.Request(url, headers={"User-Agent": "ARPi2/1.0"})
        with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
            content_type = str(getattr(resp, "headers", {}).get("Content-Type", "") or "")
            data = resp.read()

        ext = "png" if "png" in content_type.lower() else "jpg"
        return data, ext

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

    def _http_json(self, url: str, payload: dict, timeout_s: float) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "User-Agent": "ARPi2/1.0",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
            raw = resp.read()
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _sse_wait_complete(self, url: str, timeout_s: float) -> Optional[object]:
        """Read a Gradio SSE stream until 'event: complete' and return parsed JSON from the following data line."""
        req = urllib.request.Request(url, headers={"User-Agent": "ARPi2/1.0", "Accept": "text/event-stream"})
        started = time.time()
        data_buf: Optional[str] = None
        saw_complete = False
        try:
            with urllib.request.urlopen(req, timeout=float(timeout_s)) as resp:
                while True:
                    if (time.time() - started) > float(timeout_s):
                        raise TimeoutError("SSE timeout")
                    line = resp.readline()
                    if not line:
                        break
                    try:
                        s = line.decode("utf-8", errors="ignore").strip("\r\n")
                    except Exception:
                        continue
                    if not s:
                        # event boundary
                        if saw_complete and data_buf is not None:
                            try:
                                return json.loads(data_buf)
                            except Exception:
                                return None
                        continue
                    if s.startswith("event:"):
                        ev = s.split(":", 1)[1].strip()
                        saw_complete = (ev == "complete")
                        continue
                    if s.startswith("data:"):
                        data_buf = s.split(":", 1)[1].strip()
                        continue
        except Exception:
            return None
        return None

    def _gradio_extract_image_url(self, base: str, payload: object) -> Optional[str]:
        """Try to extract an image URL from a Gradio result payload."""
        if payload is None:
            return None

        # Payload is usually a list. Look for a dict with url/path.
        candidates: list[dict] = []
        try:
            if isinstance(payload, dict) and "data" in payload:
                payload = payload.get("data")
            if isinstance(payload, list):
                # Flatten one level
                for item in payload:
                    if isinstance(item, dict):
                        candidates.append(item)
                    elif isinstance(item, list):
                        for sub in item:
                            if isinstance(sub, dict):
                                candidates.append(sub)
        except Exception:
            candidates = []

        for d in candidates:
            try:
                u = d.get("url")
                if isinstance(u, str) and u.startswith("http"):
                    return u
            except Exception:
                pass

        # Fall back to serving by path.
        for d in candidates:
            try:
                p = d.get("path")
                if not isinstance(p, str) or not p:
                    continue
                qp = urllib.parse.quote(p, safe="")
                # Try common Gradio file routes.
                return f"{base}/gradio_api/file={qp}"
            except Exception:
                continue

        return None

    def _gradio_call_infer_image(self, base: str, api_name: str, data: list, timeout_s: float) -> Optional[tuple[bytes, str]]:
        """Call a Gradio /call/<api_name> endpoint and return (bytes, ext) for the generated image."""
        call_url = f"{base}/gradio_api/call/{api_name}"
        start = self._http_json(call_url, {"data": data}, timeout_s=timeout_s)
        event_id = str(start.get("event_id") or "").strip()
        if not event_id:
            return None
        result = self._sse_wait_complete(f"{base}/gradio_api/call/{api_name}/{event_id}", timeout_s=timeout_s)
        img_url = self._gradio_extract_image_url(base, result)
        if not img_url:
            return None
        # The gradio_api/file= URL returns bytes.
        try:
            return self._fetch_image_bytes(img_url, timeout_s=timeout_s)
        except Exception:
            # Some spaces use /file= instead.
            try:
                if "/gradio_api/file=" in img_url:
                    alt = img_url.replace("/gradio_api/file=", "/file=")
                    return self._fetch_image_bytes(alt, timeout_s=timeout_s)
            except Exception:
                return None
        return None

    def _dnd_bg_status(self) -> tuple[str, str]:
        """Return (state, detail) for background generation."""
        try:
            prompt = str(getattr(self, "dnd_background", "") or "").strip()
        except Exception:
            prompt = ""

        with self._dnd_bg_lock:
            desired = self._dnd_bg_desired_key
            inflight = self._dnd_bg_inflight_key
            pending = self._dnd_bg_pending
            last_err = self._dnd_bg_last_error
            last_err_time = float(self._dnd_bg_last_error_time or 0.0)

        if not prompt:
            return "idle", "no prompt"

        # Ready if we have a sprite that matches the prompt.
        try:
            if self._dnd_bg_sprite is not None and str(self._dnd_bg_prompt_cache or "") == prompt:
                return "ready", ""
        except Exception:
            pass

        # Pending decode/apply on main thread.
        if pending is not None:
            return "decoding", ""

        # In-flight network fetch.
        if inflight is not None:
            return "fetching", ""

        # Recently errored; in cooldown.
        cooldown_s = 15.0
        age = float(time.time()) - last_err_time if last_err_time > 0 else 1e9
        if last_err and age < cooldown_s:
            retry_in = max(0, int(cooldown_s - age))
            return "error", f"{last_err} (retry in {retry_in}s)"

        # Otherwise we should be about to start a fetch.
        if desired is not None:
            return "queued", ""
        return "idle", ""

    def _dnd_bg_maybe_log(self, state: str, key: Optional[tuple], message: str):
        """Throttled console logging for background generation."""
        try:
            now = float(time.time())
        except Exception:
            now = 0.0

        # Log if state/key changed, or if it's been a while.
        should_log = False
        if key != self._dnd_bg_last_log_key or state != self._dnd_bg_last_log_state:
            should_log = True
        elif now - float(self._dnd_bg_last_log_time or 0.0) > 10.0:
            should_log = True

        if not should_log:
            return

        self._dnd_bg_last_log_key = key
        self._dnd_bg_last_log_state = state
        self._dnd_bg_last_log_time = now
        try:
            print(message)
        except Exception:
            pass

    def _local_model_ready(self) -> bool:
        if not self._dnd_local_enabled:
            return False
        return bool(self._dnd_local_model_id)

    def _get_local_diffusers_pipe(self):
        """Lazy-load and cache a Diffusers text-to-image pipeline."""
        if self._dnd_local_pipe is not None:
            return self._dnd_local_pipe
        with self._dnd_local_pipe_lock:
            if self._dnd_local_pipe is not None:
                return self._dnd_local_pipe

            model_id = str(self._dnd_local_model_id or "").strip()
            if not model_id:
                raise RuntimeError("DND_BG_LOCAL_MODEL is not set")

            # Import lazily so the server can run without these deps unless enabled.
            import torch  # type: ignore
            from diffusers import AutoPipelineForText2Image  # type: ignore

            dtype = torch.float16
            try:
                pipe = AutoPipelineForText2Image.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    use_safetensors=True,
                )
            except Exception:
                # Some models require variant or other settings; fall back.
                pipe = AutoPipelineForText2Image.from_pretrained(model_id)

            device = str(self._dnd_local_device or "cuda")
            try:
                pipe = pipe.to(device)
            except Exception:
                # If CUDA isn't available, fall back to CPU.
                pipe = pipe.to("cpu")

            # Enable attention slicing to reduce VRAM spikes.
            try:
                pipe.enable_attention_slicing()
            except Exception:
                pass
            try:
                pipe.enable_vae_slicing()
            except Exception:
                pass

            self._dnd_local_pipe = pipe
            return pipe

    def _local_generate_image_bytes(self, prompt: str, iw: int, ih: int, seed: int, timeout_s: float) -> tuple[bytes, str]:
        """Generate an image locally using a pre-trained Diffusers model.

        Returns (bytes, ext). No disk writes.
        """
        started = time.time()
        prompt = str(prompt or "").strip() or "fantasy scene"
        iw = int(max(512, iw))
        ih = int(max(512, ih))
        # Diffusion models generally want multiples of 8.
        iw = int(iw // 8 * 8)
        ih = int(ih // 8 * 8)

        pipe = self._get_local_diffusers_pipe()

        import torch  # type: ignore
        from PIL import Image  # type: ignore

        device = getattr(pipe, "device", None)
        gen_device = "cpu"
        try:
            if device is not None and hasattr(device, "type"):
                gen_device = device.type
        except Exception:
            gen_device = "cpu"

        generator = torch.Generator(device=gen_device).manual_seed(int(seed) & 0x7FFFFFFF)
        steps = max(8, int(self._dnd_local_steps))
        guidance = float(self._dnd_local_guidance)

        # Keep an eye on timeout; we can't hard-cancel generation, but we can at least avoid hanging forever.
        if float(time.time() - started) > float(timeout_s):
            raise TimeoutError("Local generation timed out before start")

        out = pipe(
            prompt=prompt,
            width=iw,
            height=ih,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator,
        )

        images = getattr(out, "images", None)
        if not images:
            raise RuntimeError("Local model returned no images")
        img = images[0]
        if not isinstance(img, Image.Image):
            raise RuntimeError("Local model output was not a PIL image")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90, optimize=True)
        return buf.getvalue(), "jpg"

    def _start_dnd_bg_fetch_if_needed(self, desired_id: tuple, prompt: str, seed: int, aspect_w: int, aspect_h: int):
        """Start background generation if not already in-flight.

        Tries multiple endpoints and models in parallel, first success wins.
        Also tries high resolution first, then falls back to smaller sizes.
        """
        with self._dnd_bg_lock:
            if self._dnd_bg_inflight_key == desired_id:
                return
            self._dnd_bg_inflight_key = desired_id

        prompt_short = (prompt or "")[:120]
        self._dnd_bg_maybe_log(
            "fetching",
            desired_id,
            f"[DND BG] Generating (multi-endpoint) seed={seed} prompt='{prompt_short}'",
        )

        # Provider list: keyless public endpoints. Each entry is a dict with a callable runner.
        providers: list[dict] = [
            {
                "name": "hf-flux-schnell",
                "kind": "gradio-call",
                "base": "https://black-forest-labs-flux-1-schnell.hf.space",
                "api": "infer",
                "max_long": 1024,
            },
            {
                "name": "hf-flux-dev",
                "kind": "gradio-call",
                "base": "https://black-forest-labs-flux-1-dev.hf.space",
                "api": "infer",
                "max_long": 1024,
            },
            # Pollinations as an additional option (may be down/blocked).
            {
                "name": "pollinations-image",
                "kind": "pollinations",
                "base": "https://image.pollinations.ai",
                "model": "flux",
                "max_long": 2048,
            },
            {
                "name": "pollinations-gen",
                "kind": "pollinations",
                "base": "https://gen.pollinations.ai/image",
                "model": "flux",
                "max_long": 2048,
            },
        ]

        # Only include local generation if explicitly enabled.
        try:
            if self._local_model_ready():
                providers.insert(
                    0,
                    {
                        "name": "local-diffusers",
                        "kind": "local-diffusers",
                        "max_long": int(self._dnd_local_max_long or 1536),
                    },
                )
        except Exception:
            pass

        # Compute target resolutions: best first, then fall back.
        # Use the framebuffer aspect but cap the long side to keep latency reasonable.
        def sized(long_side: int) -> tuple[int, int]:
            long_side = int(max(512, long_side))
            if aspect_w >= aspect_h:
                iw = long_side
                ih = max(512, int(long_side * float(aspect_h) / float(max(1, aspect_w))))
            else:
                ih = long_side
                iw = max(512, int(long_side * float(aspect_w) / float(max(1, aspect_h))))
            # Keep dimensions even for some decoders.
            iw = int(iw // 2 * 2)
            ih = int(ih // 2 * 2)
            return iw, ih

        # "Best" here means close to screen size, but capped.
        best_long = int(min(2048, max(aspect_w, aspect_h)))
        size_plan = [
            sized(best_long),
            sized(min(1536, best_long)),
            sized(min(1024, best_long)),
        ]

        def worker():
            try:
                last_exc: Optional[Exception] = None
                winner = threading.Event()
                winner_lock = threading.Lock()

                def attempt(url: str, iw: int, ih: int, model: str, timeout_s: float):
                    nonlocal last_exc
                    if winner.is_set():
                        return
                    try:
                        data, ext = self._fetch_image_bytes(url, timeout_s=timeout_s)
                        if winner.is_set():
                            return
                        with winner_lock:
                            if winner.is_set():
                                return
                            # Ensure we're still targeting the same prompt.
                            with self._dnd_bg_lock:
                                if self._dnd_bg_desired_key != desired_id:
                                    return
                                self._dnd_bg_pending = (desired_id, data, ext, int(iw), int(ih))
                                if self._dnd_bg_inflight_key == desired_id:
                                    self._dnd_bg_inflight_key = None
                            winner.set()
                            self._dnd_bg_maybe_log(
                                "downloaded",
                                desired_id,
                                f"[DND BG] Downloaded {len(data)} bytes ({ext}) at {iw}x{ih} via {model}.",
                            )
                    except Exception as e:
                        last_exc = e

                def attempt_provider(provider: dict, iw: int, ih: int, timeout_s: float):
                    nonlocal last_exc
                    if winner.is_set():
                        return
                    try:
                        kind = str(provider.get("kind") or "")
                        name = str(provider.get("name") or "provider")
                        base = str(provider.get("base") or "").rstrip("/")

                        if kind == "pollinations":
                            model = str(provider.get("model") or "flux")
                            url = self._pollinations_image_url(base, prompt, iw, ih, seed, model=model)
                            attempt(url, iw, ih, f"{name}:{model}", timeout_s)
                            return

                        if kind == "local-diffusers":
                            if not self._local_model_ready():
                                raise RuntimeError("Local model disabled or DND_BG_LOCAL_MODEL not set")
                            img_bytes, ext = self._local_generate_image_bytes(prompt, iw, ih, seed, timeout_s=timeout_s)

                            if winner.is_set():
                                return
                            with winner_lock:
                                if winner.is_set():
                                    return
                                with self._dnd_bg_lock:
                                    if self._dnd_bg_desired_key != desired_id:
                                        return
                                    self._dnd_bg_pending = (desired_id, img_bytes, ext, int(iw), int(ih))
                                    if self._dnd_bg_inflight_key == desired_id:
                                        self._dnd_bg_inflight_key = None
                                winner.set()
                                self._dnd_bg_maybe_log(
                                    "downloaded",
                                    desired_id,
                                    f"[DND BG] Generated {len(img_bytes)} bytes ({ext}) at {iw}x{ih} via local model.",
                                )
                            return

                        if kind == "gradio-call":
                            api_name = str(provider.get("api") or "infer")
                            # Data format for these FLUX spaces:
                            # [prompt, seed, randomize_seed, width, height, steps, (optionally guidance)]
                            # We supply seed and set randomize_seed=False.
                            steps = 28 if max(iw, ih) >= 1024 else 24
                            # FLUX schnell expects: [prompt, seed, randomize, width, height, steps]
                            # FLUX dev often expects: [prompt, seed, randomize, width, height, guidance, steps]
                            if "flux-dev" in name:
                                data = [prompt, int(seed) & 0x7FFFFFFF, False, int(iw), int(ih), 3.5, int(steps)]
                            else:
                                data = [prompt, int(seed) & 0x7FFFFFFF, False, int(iw), int(ih), int(steps)]
                            res = self._gradio_call_infer_image(base, api_name, data, timeout_s=timeout_s)
                            if res is None:
                                raise RuntimeError(f"{name} returned no image")
                            img_bytes, ext = res

                            if winner.is_set():
                                return
                            with winner_lock:
                                if winner.is_set():
                                    return
                                with self._dnd_bg_lock:
                                    if self._dnd_bg_desired_key != desired_id:
                                        return
                                    self._dnd_bg_pending = (desired_id, img_bytes, ext, int(iw), int(ih))
                                    if self._dnd_bg_inflight_key == desired_id:
                                        self._dnd_bg_inflight_key = None
                                winner.set()
                                self._dnd_bg_maybe_log(
                                    "downloaded",
                                    desired_id,
                                    f"[DND BG] Downloaded {len(img_bytes)} bytes ({ext}) at {iw}x{ih} via {name}.",
                                )
                            return

                        raise RuntimeError(f"Unknown provider kind: {kind}")
                    except Exception as e:
                        last_exc = e

                # Try size tiers; for each size, race endpoints/models.
                for (iw, ih) in size_plan:
                    if winner.is_set():
                        break

                    timeout_s = 30.0 if max(iw, ih) >= 1536 else 22.0

                    threads: list[threading.Thread] = []
                    for provider in providers:
                        # Clamp size per provider
                        try:
                            max_long = int(provider.get("max_long") or 1024)
                        except Exception:
                            max_long = 1024
                        ciw, cih = int(iw), int(ih)
                        if max(ciw, cih) > max_long:
                            scale = float(max_long) / float(max(ciw, cih))
                            ciw = int(max(512, int(ciw * scale)) // 2 * 2)
                            cih = int(max(512, int(cih * scale)) // 2 * 2)

                        t = threading.Thread(target=attempt_provider, args=(provider, ciw, cih, timeout_s), daemon=True)
                        threads.append(t)
                        t.start()

                    # Wait for a winner or all attempts for this tier to complete.
                    # Give it a bit of slack beyond per-request timeout.
                    tier_deadline = time.time() + timeout_s + 8.0
                    while time.time() < tier_deadline:
                        if winner.is_set():
                            break
                        alive = any(t.is_alive() for t in threads)
                        if not alive:
                            break
                        time.sleep(0.1)

                    # If no winner in this tier, move on (threads are daemonic; they may finish later).
                    if winner.is_set():
                        break

                if winner.is_set():
                    return

                # All failed.
                raise last_exc or RuntimeError("All background endpoints failed")
            except Exception as e:
                with self._dnd_bg_lock:
                    if self._dnd_bg_inflight_key == desired_id:
                        self._dnd_bg_inflight_key = None
                    self._dnd_bg_last_error = str(e)
                    self._dnd_bg_last_error_time = float(time.time())
                self._dnd_bg_maybe_log(
                    "error",
                    desired_id,
                    f"[DND BG] ERROR fetching background (all endpoints): {e}",
                )

        threading.Thread(target=worker, daemon=True).start()

    def _pump_dnd_bg_pending(self, draw_w: int, draw_h: int):
        pending = None
        with self._dnd_bg_lock:
            if self._dnd_bg_pending is not None:
                pending = self._dnd_bg_pending
                self._dnd_bg_pending = None

        if pending is None:
            return

        desired_id, data, ext, iw, ih = pending
        try:
            # Decode using pyglet without touching disk.
            buf = io.BytesIO(data)
            img = pyglet.image.load(f"bg.{ext}", file=buf)
            self._dnd_bg_sprite = pyglet.sprite.Sprite(img, x=0, y=0)

            # Smooth scaling (helps when a 1024px image is scaled to 1080p).
            try:
                self._set_sprite_smoothing(self._dnd_bg_sprite)
            except Exception:
                pass

            if iw > 0 and ih > 0:
                self._dnd_bg_img_size = (iw, ih)

            # Center and preserve aspect ratio.
            try:
                self._layout_dnd_bg_sprite(draw_w, draw_h)
            except Exception:
                pass

            # Cache identity for skip logic.
            try:
                self._dnd_bg_prompt_cache = str(desired_id[0])
            except Exception:
                self._dnd_bg_prompt_cache = ""
            self._dnd_bg_aspect_key = (int(draw_w // 64), int(draw_h // 64))

            self._dnd_bg_maybe_log(
                "ready",
                desired_id,
                f"[DND BG] Applied background sprite ({iw}x{ih}).",
            )
        except Exception as e:
            with self._dnd_bg_lock:
                self._dnd_bg_last_error = str(e)
                self._dnd_bg_last_error_time = float(time.time())

            self._dnd_bg_maybe_log(
                "error",
                desired_id,
                f"[DND BG] ERROR decoding/applying background: {e}",
            )

    def _ensure_dnd_background_sprite(self, draw_w: int, draw_h: int):
        """Ensure a cached sprite exists for the current prompt and aspect ratio."""
        prompt = str(getattr(self, "dnd_background", "") or "").strip()
        if not prompt:
            prompt = "fantasy scene"

        # Apply completed downloads (sprite creation must happen on main thread).
        try:
            self._pump_dnd_bg_pending(draw_w, draw_h)
        except Exception:
            pass

        # Regenerate only when prompt changes or the aspect ratio bucket changes.
        aspect_key = (int(draw_w // 64), int(draw_h // 64))
        if prompt == self._dnd_bg_prompt_cache and aspect_key == self._dnd_bg_aspect_key and self._dnd_bg_sprite is not None:
            # Update scale in case resolution changed.
            try:
                self._set_sprite_smoothing(self._dnd_bg_sprite)
                self._layout_dnd_bg_sprite(draw_w, draw_h)
            except Exception:
                pass
            return

        seed = self._dnd_prompt_seed(prompt)
        desired_id = (prompt, aspect_key, int(seed), "pollinations")
        with self._dnd_bg_lock:
            self._dnd_bg_desired_key = desired_id

        # Avoid hammering the service if it just errored (rate limits are common).
        cooldown_s = 15.0
        try:
            last_err_age = float(time.time()) - float(self._dnd_bg_last_error_time or 0.0)
        except Exception:
            last_err_age = 1e9

        if last_err_age < cooldown_s:
            return

        try:
            self._start_dnd_bg_fetch_if_needed(desired_id, prompt, int(seed), int(draw_w), int(draw_h))
        except Exception:
            return

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

        # Player selection is handled via Web UI (button-driven), so hide in-window selection UIs.
        setattr(self.monopoly_game, "web_ui_only_player_select", True)
        setattr(self.blackjack_game, "web_ui_only_player_select", True)
        # Board-only rendering in the Pyglet window (no panels). Web UI shows actions/info.
        setattr(self.monopoly_game, "board_only_mode", True)
        setattr(self.blackjack_game, "board_only_mode", True)
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
        if self.state == "dnd_creation":
            return getattr(self.dnd_creation, "game", None) or self.dnd_creation
        return None

    def _get_player_select_snapshot(self, game):
        if not hasattr(game, "selection_ui"):
            return None
        selected = list(getattr(game.selection_ui, "selected", []))
        slots = []
        dm_seat = self.dnd_dm_seat if self.state == "dnd_creation" else None
        for i in range(8):
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
        snap = {
            "server_state": self.state,
            "history": list(getattr(self, "ui_history", [])),
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
                if isinstance(seat, int) and seat >= 0 and self.state == "monopoly":
                    mg = getattr(self, "monopoly_game", None)
                    if mg is not None and hasattr(mg, "handle_player_quit"):
                        mg.handle_player_quit(seat)
                if isinstance(seat, int) and seat >= 0 and self.state == "blackjack":
                    bg = getattr(self, "blackjack_game", None)
                    if bg is not None and hasattr(bg, "close_web_result"):
                        bg.close_web_result(seat)
            except Exception:
                pass

            self.ui_client_player[client_id] = -1
            self.ui_client_ready[client_id] = False
            self.ui_client_vote.pop(client_id, None)
            self.ui_client_end_game[client_id] = False
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
            if key not in ("monopoly", "blackjack", "d&d", "dnd"):
                return
            # Only ready+seated clients may vote.
            seat = self.ui_client_player.get(client_id, -1)
            if not (isinstance(seat, int) and seat >= 0):
                return
            if not bool(self.ui_client_ready.get(client_id, False)):
                return
            self.ui_client_vote[client_id] = "d&d" if key == "dnd" else key
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

                char = Character(name=name, player_color=tuple(PLAYER_COLORS[seat % len(PLAYER_COLORS)]))
                char.race = race
                char.char_class = char_class
                try:
                    char.alignment = random.choice(list(ALIGNMENTS))
                except Exception:
                    char.alignment = ""
                char.abilities = abilities
                try:
                    char.skills = list(CLASS_SKILLS.get(char_class, []))
                except Exception:
                    char.skills = []
                try:
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
                return

            if msg_type == "dnd_dm_set_background":
                if seat is None or not (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat):
                    return
                bg = str(data.get("background") or "").strip()
                if not bg:
                    return
                self.dnd_background = bg
                try:
                    self._dnd_bg_prompt_cache = ""
                    self._dnd_bg_sprite = None
                    self._dnd_bg_img_size = (0, 0)
                    self._dnd_bg_aspect_key = (0, 0)
                    with self._dnd_bg_lock:
                        self._dnd_bg_pending = None
                        self._dnd_bg_inflight_key = None
                        self._dnd_bg_desired_key = None
                except Exception:
                    pass
                self._log_history(f"DM set background: {bg}")
                return

            if msg_type == "dnd_dm_generate_background":
                if seat is None or not (isinstance(self.dnd_dm_seat, int) and seat == self.dnd_dm_seat):
                    return
                prompt = str(data.get("prompt") or "").strip()
                flavors = [
                    "misty",
                    "storm-lit",
                    "moonlit",
                    "ancient",
                    "crumbling",
                    "enchanted",
                    "shadowy",
                    "bloodstained",
                    "quiet",
                    "windswept",
                ]
                places = [
                    "tavern",
                    "forest",
                    "dungeon corridor",
                    "ruined temple",
                    "cavern",
                    "city alley",
                    "crypt",
                    "mountain pass",
                    "wizard tower",
                ]
                try:
                    flavor = random.choice(flavors)
                    place = random.choice(places)
                except Exception:
                    flavor = "mysterious"
                    place = "scene"
                bg = f"{flavor} {place}"
                if prompt:
                    bg = f"{prompt} · {bg}"
                self.dnd_background = bg
                try:
                    self._dnd_bg_prompt_cache = ""
                    self._dnd_bg_sprite = None
                    self._dnd_bg_img_size = (0, 0)
                    self._dnd_bg_aspect_key = (0, 0)
                    with self._dnd_bg_lock:
                        self._dnd_bg_pending = None
                        self._dnd_bg_inflight_key = None
                        self._dnd_bg_desired_key = None
                except Exception:
                    pass
                self._log_history(f"DM generated background: {bg}")
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
            return

    async def handle_ui_client(self, websocket):
        client_id = f"ui:{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.ui_clients[client_id] = websocket
        self.ui_client_player.setdefault(client_id, -1)
        self.ui_client_ready.setdefault(client_id, False)
        self.ui_client_end_game.setdefault(client_id, False)
        print(f"UI client connected: {client_id}")

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
            print(f"UI client disconnected: {client_id}")
    
    def _create_game_buttons(self):
        """Create game selection buttons"""
        games = ["Monopoly", "Blackjack", "D&D"]
        buttons = []
        for i, game in enumerate(games):
            btn_rect = (
                WINDOW_SIZE[0] // 2 - 150,
                WINDOW_SIZE[1] // 2 - 180 + i * 120,
                300, 90
            )
            buttons.append({"text": game, "rect": btn_rect, "key": game.lower()})
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
        for g in (getattr(self, "monopoly_game", None), getattr(self, "blackjack_game", None), getattr(self, "dnd_creation", None)):
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
        elif self.state == "dnd_creation":
            self.dnd_creation.update(dt)
    
    def _handle_menu_input(self, fingertip_meta: List[Dict]):
        """Handle menu input"""
        # Web-UI-only: game selection is controlled from the Web UI.
        # Keep this as a no-op to avoid accidental local state changes.
        self.hover_states.clear()
        return
    
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

            label = f"{seat + 1}. {name}"
            tags = []
            tags.append("Ready" if ready else "Not ready")
            if not connected:
                tags.append("Disconnected")
            label = f"{label}  ({', '.join(tags)})"

            y = start_y + i * row_h
            col = PLAYER_COLORS[seat % len(PLAYER_COLORS)]
            # Color dot to the left of the centered text
            dot_x = center_x - 240
            self.renderer.draw_circle(col, (dot_x, y), 8)
            self.renderer.draw_circle(Colors.WHITE, (dot_x, y), 8, width=2)

            self.renderer.draw_text(
                label,
                center_x - 220, y,
                font_name='Arial', font_size=18,
                color=col,
                anchor_x='left', anchor_y='center'
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
            h_panel = int(WINDOW_SIZE[1] * 0.10)
            v_panel = int(WINDOW_SIZE[0] * 0.12)
            base_x = v_panel + 26
            base_y = h_panel + 26
            players = sorted(set(self.ui_client_player.values()))
            for i, pidx in enumerate(players):
                pos = (base_x, base_y + i * 24)
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
