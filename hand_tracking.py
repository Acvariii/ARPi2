import asyncio
import json
import threading
import time
from typing import List, Dict, Optional
import websockets

class HandTracker:
    """Manages WebSocket connection to hand tracking server and provides hand data."""
    
    def __init__(self, server_ws: str = "ws://192.168.1.79:8765"):
        self.server_ws = server_ws
        self._shared = {"hands": [], "w": 1280, "h": 720, "ts": 0.0}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """Start the hand tracking receiver thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the hand tracking receiver thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run_async_loop(self):
        """Run async loop in this thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._recv_loop())
        except Exception as e:
            print(f"Hand tracker error: {e}")

    async def _recv_loop(self):
        """Async loop to receive hand data from server."""
        while self._running:
            try:
                async with websockets.connect(self.server_ws, max_size=None) as ws:
                    await ws.send("viewer")
                    async for msg in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(msg)
                        except Exception:
                            continue
                        
                        if data.get("type") == "hands":
                            with self._lock:
                                self._shared["hands"] = data.get("hands", [])
                                self._shared["w"] = data.get("width", self._shared["w"])
                                self._shared["h"] = data.get("height", self._shared["h"])
                                self._shared["ts"] = time.time()
            except Exception as e:
                if self._running:
                    print(f"Connection lost, retrying in 2s: {e}")
                    await asyncio.sleep(2)

    def get_hands_snapshot(self) -> Dict:
        """Return a copy of the latest hands data."""
        with self._lock:
            return {
                "hands": list(self._shared.get("hands", [])),
                "w": self._shared.get("w", 1280),
                "h": self._shared.get("h", 720),
                "ts": self._shared.get("ts", 0.0),
            }

    def get_fingertips_for_screen(self, screen_w: int, screen_h: int) -> List[Dict]:
        """Convert normalized fingertip coords to screen space."""
        snap = self.get_hands_snapshot()
        result = []
        for h in snap.get("hands", []):
            hand_id = h.get("hand_id", 0)
            fps = h.get("fingertips", {})
            for name, v in fps.items():
                nx, ny = v[0], v[1]
                sx = int(nx * screen_w)
                sy = int(ny * screen_h)
                result.append({"pos": (sx, sy), "hand": hand_id, "name": name})
        return result


# Module-level instance for backward compatibility
_global_tracker: Optional[HandTracker] = None

def start_ws_thread(server_ws: str = "ws://192.168.1.79:8765"):
    """Start global hand tracker (for backward compatibility)."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = HandTracker(server_ws)
    _global_tracker.start()
    return _global_tracker

def get_hands_snapshot() -> Dict:
    """Get hands from global tracker."""
    if _global_tracker is None:
        return {"hands": [], "w": 1280, "h": 720, "ts": 0.0}
    return _global_tracker.get_hands_snapshot()

def fingertip_meta_for_screen(screen_w: int, screen_h: int) -> List[Dict]:
    """Get fingertips from global tracker."""
    if _global_tracker is None:
        return []
    return _global_tracker.get_fingertips_for_screen(screen_w, screen_h)