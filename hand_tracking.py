import asyncio
import json
import threading
import time
from typing import List, Dict
import websockets

# shared snapshot updated by the ws thread
_shared = {"hands": [], "w": 1280, "h": 720, "ts": 0.0}
_lock = threading.Lock()


async def _recv_loop(server_ws: str):
    async with websockets.connect(server_ws, max_size=None) as ws:
        await ws.send("viewer")
        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue
            if data.get("type") == "hands":
                with _lock:
                    _shared["hands"] = data.get("hands", [])
                    _shared["w"] = data.get("width", _shared["w"])
                    _shared["h"] = data.get("height", _shared["h"])
                    _shared["ts"] = time.time()


def start_ws_thread(server_ws: str = "ws://192.168.1.79:8765"):
    """Start a background thread that keeps the shared hand snapshot updated."""
    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_recv_loop(server_ws))
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def get_hands_snapshot() -> Dict:
    """Return a shallow copy of the latest hands payload."""
    with _lock:
        return {
            "hands": list(_shared.get("hands", [])),
            "w": _shared.get("w", 1280),
            "h": _shared.get("h", 720),
            "ts": _shared.get("ts", 0.0),
        }


def fingertip_meta_for_screen(screen_w: int, screen_h: int) -> List[Dict]:
    """Convert the stored normalized fingertip coords into screen-space fingertip meta:
    returns list of {'pos': (x_px, y_px), 'hand': hand_id, 'slot_key': optional}
    """
    snap = get_hands_snapshot()
    out = []
    for h in snap.get("hands", []):
        hand_id = h.get("hand_id", 0)
        fps = h.get("fingertips", {})
        for name, v in fps.items():
            nx, ny = v[0], v[1]
            sx = int(nx * screen_w)
            sy = int(ny * screen_h)
            out.append({"pos": (sx, sy), "hand": hand_id, "name": name})
    return out