import asyncio
import json
import threading
import time
import cv2
import numpy as np
import websockets
from typing import Optional, Dict, List
from config import SERVER_WS

class VideoDisplay:
    """Displays camera feed with hand tracking overlays in a separate thread."""

    def __init__(self, server_ws: str = SERVER_WS, window_name: str = "Hand Tracking"):
        self.server_ws = server_ws
        self.window_name = window_name
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_hands: List[Dict] = []
        self.frame_width = 1280
        self.frame_height = 720
        self.running = False
        self.lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._display_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the video display in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the video display."""
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._display_thread is not None:
            self._display_thread.join(timeout=2.0)
        cv2.destroyAllWindows()

    def _run_async_loop(self):
        """Run the async websocket loop in this thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_main())
        except Exception as e:
            print(f"Video display error: {e}")
        finally:
            loop.close()

    async def _async_main(self):
        """Main async loop for receiving frames and hand data."""
        async with websockets.connect(self.server_ws, max_size=None) as ws:
            await ws.send("viewer")
            
            self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
            self._display_thread.start()
            
            async for msg in ws:
                if not self.running:
                    break
                    
                if isinstance(msg, bytes):
                    # Received frame
                    arr = np.frombuffer(msg, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        with self.lock:
                            self.latest_frame = frame
                            self.frame_height, self.frame_width = frame.shape[:2]
                else:
                    # Received JSON (hand data)
                    try:
                        data = json.loads(msg)
                        if data.get("type") == "hands":
                            with self.lock:
                                self.latest_hands = data.get("hands", [])
                                self.frame_width = data.get("width", self.frame_width)
                                self.frame_height = data.get("height", self.frame_height)
                    except Exception:
                        pass

    def _display_loop(self):
        """Display frames with overlays in OpenCV window."""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 960, 540)
        
        while self.running:
            with self.lock:
                frame = self.latest_frame.copy() if self.latest_frame is not None else None
                hands = self.latest_hands.copy()
                w, h = self.frame_width, self.frame_height
            
            if frame is not None:
                # Draw hand overlays
                for hand in hands:
                    fingertips = hand.get("fingertips", {})
                    handedness = hand.get("handedness", "Unknown")
                    hand_id = hand.get("hand_id", 0)
                    
                    # Choose color based on hand
                    if handedness == "Left":
                        hand_color = (100, 180, 250)  # Blue for left
                    else:
                        hand_color = (250, 180, 100)  # Orange for right
                    
                    for name, coords in fingertips.items():
                        x = int(coords[0] * w)
                        y = int(coords[1] * h)
                        
                        # Draw circles around fingertip
                        cv2.circle(frame, (x, y), 30, (255, 255, 255), 2)
                        cv2.circle(frame, (x, y), 20, hand_color, -1)
                        cv2.circle(frame, (x, y), 6, (0, 0, 0), -1)
                        
                        # Draw label
                        label = f"{handedness[0]}{hand_id}:{name}"
                        cv2.putText(frame, label, (x + 35, y), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Draw hand count
                hand_count_text = f"Hands: {len(hands)}"
                cv2.putText(frame, hand_count_text, (10, 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                cv2.imshow(self.window_name, frame)
            else:
                # Show blank frame with message
                blank = np.zeros((540, 960, 3), dtype=np.uint8)
                cv2.putText(blank, "Waiting for camera feed...", (250, 270),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.imshow(self.window_name, blank)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
                break
            elif key == ord('h'):
                # Toggle hands display (could be extended)
                pass
        
        cv2.destroyWindow(self.window_name)