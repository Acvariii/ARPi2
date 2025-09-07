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

# connected viewers (receive JSON hand data)
VIEWERS: Set[Any] = set()

# optional: camera clients set (not strictly needed)
CAMERAS: Set[Any] = set()

FINGERTIP_INDICES = {
    "thumb": 4,
    "index": 8,
    "middle": 12,
    "ring": 16,
    "pinky": 20,
}

async def broadcast(data_str: str):
    if not VIEWERS:
        return

    async def send_safe(ws, data):
        try:
            await ws.send(data)
        except Exception:
            # remove viewers that raised (closed/invalid)
            VIEWERS.discard(ws)

    tasks = []
    for ws in list(VIEWERS):
        # prefer not to access attributes that may not exist on all connection types
        is_closed = getattr(ws, "closed", None)
        is_open = getattr(ws, "open", None)
        # If we can determine it's closed, skip; otherwise try sending (send_safe will drop invalids)
        if is_closed is True:
            VIEWERS.discard(ws)
            continue
        if is_open is False:
            VIEWERS.discard(ws)
            continue
        tasks.append(send_safe(ws, data_str))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

def process_frame_jpeg(jpeg_bytes: bytes, frame_id: int = 0):
    # Decode JPEG
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]

    # Pad to square to avoid the NORM_RECT without IMAGE_DIMENSIONS warning.
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
                # pt.x/pt.y are relative to the padded square
                # convert to pixels in padded space, then to pixels in original image,
                # then normalize relative to original width/height.
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
    """WebSocket handler compatible with websockets 11+.

    The library now calls handlers with a single connection object.
    """
    ws = connection
    logger.info("Client connected: %s", getattr(ws, 'remote_address', None))
    try:
        async for message in ws:
            # binary frames from camera clients
            if isinstance(message, (bytes, bytearray)):
                payload = process_frame_jpeg(message)
                if payload:
                    data_str = json.dumps(payload)
                    await broadcast(data_str)
            else:
                # text messages - simple protocol:
                txt = message.strip().lower()
                if txt == "viewer":
                    VIEWERS.add(ws)
                    logger.info("Registered viewer: %s", ws.remote_address)
                    await ws.send(json.dumps({"type": "info", "message": "viewer_registered"}))
                elif txt == "camera":
                    CAMERAS.add(ws)
                    logger.info("Registered camera: %s", ws.remote_address)
                    await ws.send(json.dumps({"type": "info", "message": "camera_registered"}))
                elif txt == "ping":
                    await ws.send("pong")
                else:
                    # echo back unknown commands
                    await ws.send(json.dumps({"type": "info", "message": "unknown_command", "command": txt}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        VIEWERS.discard(ws)
        CAMERAS.discard(ws)
        logger.info("Client disconnected: %s", ws.remote_address)

async def main():
    logger.info("Starting WebSocket server on :8765")
    async with websockets.serve(handler, "192.168.1.79", 8765, max_size=None, max_queue=None):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())