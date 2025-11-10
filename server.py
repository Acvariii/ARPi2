import asyncio
import json
import time
import logging
from typing import Set, Any

import cv2
import numpy as np
import websockets
import mediapipe as mp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hand-server")

# MediaPipe
mp_hands = mp.solutions.hands
hands_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=8,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

# connected viewers (receive both frames and JSON hand data)
VIEWERS: Set[Any] = set()

# camera clients set
CAMERAS: Set[Any] = set()

FINGERTIP_INDICES = {
    "index": 8,
}

# Video display instance
_video_display = None

async def broadcast_json(data_str: str):
    """Broadcast JSON hand data to all viewers."""
    if not VIEWERS:
        return

    async def send_safe(ws, data):
        try:
            await ws.send(data)
        except Exception:
            VIEWERS.discard(ws)

    tasks = []
    for ws in list(VIEWERS):
        is_closed = getattr(ws, "closed", None)
        is_open = getattr(ws, "open", None)
        if is_closed is True:
            VIEWERS.discard(ws)
            continue
        if is_open is False:
            VIEWERS.discard(ws)
            continue
        tasks.append(send_safe(ws, data_str))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def broadcast_frame(frame_bytes: bytes):
    """Broadcast raw frame to all viewers."""
    if not VIEWERS:
        return

    async def send_safe(ws, data):
        try:
            await ws.send(data)
        except Exception:
            VIEWERS.discard(ws)

    tasks = []
    for ws in list(VIEWERS):
        is_closed = getattr(ws, "closed", None)
        is_open = getattr(ws, "open", None)
        if is_closed is True:
            VIEWERS.discard(ws)
            continue
        if is_open is False:
            VIEWERS.discard(ws)
            continue
        tasks.append(send_safe(ws, frame_bytes))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

def process_frame_jpeg(jpeg_bytes: bytes, frame_id: int = 0):
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]

    pad_size = max(w, h)
    pad_x = (pad_size - w) // 2
    pad_y = (pad_size - h) // 2
    square = np.zeros((pad_size, pad_size, 3), dtype=img.dtype)
    square[pad_y:pad_y + h, pad_x:pad_x + w] = img

    img_rgb = cv2.cvtColor(square, cv2.COLOR_BGR2RGB)
    results = hands_detector.process(img_rgb)

    payload = {
        "type": "hands",
        "frame_id": frame_id,
        "timestamp": time.time(),
        "width": w,
        "height": h,
        "hands": [],
    }

    def clamp01(v):
        return max(0.0, min(1.0, v))

    if results and results.multi_hand_landmarks:
        for i, (landmarks, handedness) in enumerate(
            zip(results.multi_hand_landmarks, results.multi_handedness)
        ):
            lm = []
            fingertips = {}
            for pt in landmarks.landmark:
                px = pt.x * pad_size - pad_x
                py = pt.y * pad_size - pad_y
                nx = clamp01(px / w)
                ny = clamp01(py / h)
                lm.append([nx, ny, pt.z])
            for name, idx in FINGERTIP_INDICES.items():
                p = landmarks.landmark[idx]
                px = p.x * pad_size - pad_x
                py = p.y * pad_size - pad_y
                nx = clamp01(px / w)
                ny = clamp01(py / h)
                fingertips[name] = [nx, ny, p.z]
            hand_info = {
                "hand_id": i,
                "handedness": handedness.classification[0].label if handedness else None,
                "score": handedness.classification[0].score if handedness else None,
                "landmarks": lm,
                "fingertips": fingertips,
            }
            payload["hands"].append(hand_info)
    return payload

async def handler(connection):
    ws = connection
    logger.info("Client connected: %s", getattr(ws, 'remote_address', None))
    
    # Auto-start video display when first camera connects
    global _video_display
    
    try:
        async for message in ws:
            if isinstance(message, (bytes, bytearray)):
                # Broadcast frame to viewers first (for video display)
                await broadcast_frame(message)
                
                # Then process for hand tracking and broadcast JSON
                payload = process_frame_jpeg(message)
                if payload:
                    data_str = json.dumps(payload)
                    await broadcast_json(data_str)
            else:
                txt = message.strip().lower()
                if txt == "viewer":
                    VIEWERS.add(ws)
                    logger.info("Registered viewer: %s", ws.remote_address)
                    await ws.send(json.dumps({"type": "info", "message": "viewer_registered"}))
                elif txt == "camera":
                    CAMERAS.add(ws)
                    logger.info("Registered camera: %s", ws.remote_address)
                    
                    # Start video display when first camera connects
                    if _video_display is None and len(CAMERAS) == 1:
                        try:
                            from video_display import VideoDisplay
                            _video_display = VideoDisplay()
                            _video_display.start()
                            logger.info("Video display started automatically")
                        except Exception as e:
                            logger.error(f"Failed to start video display: {e}")
                    
                    await ws.send(json.dumps({"type": "info", "message": "camera_registered"}))
                elif txt == "ping":
                    await ws.send("pong")
                else:
                    await ws.send(json.dumps({"type": "info", "message": "unknown_command", "command": txt}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        VIEWERS.discard(ws)
        was_camera = ws in CAMERAS
        CAMERAS.discard(ws)
        
        # Stop video display when last camera disconnects
        if was_camera and len(CAMERAS) == 0 and _video_display is not None:
            logger.info("Last camera disconnected, stopping video display")
            _video_display.stop()
            _video_display = None
        
        logger.info("Client disconnected: %s", ws.remote_address)

async def main():
    logger.info("Starting WebSocket server on :8765")
    async with websockets.serve(handler, "192.168.1.79", 8765, max_size=None, max_queue=None):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())