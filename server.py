import asyncio
import json
import time
import logging
from typing import Set

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
VIEWERS: Set[websockets.WebSocketServerProtocol] = set()

# optional: camera clients set (not strictly needed)
CAMERAS: Set[websockets.WebSocketServerProtocol] = set()

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
    await asyncio.gather(
        *[ws.send(data_str) for ws in list(VIEWERS) if not ws.closed],
        return_exceptions=True,
    )

def process_frame_jpeg(jpeg_bytes: bytes, frame_id: int = 0):
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands_detector.process(img_rgb)

    payload = {
        "type": "hands",
        "frame_id": frame_id,
        "timestamp": time.time(),
        "width": w,
        "height": h,
        "hands": [],
    }

    if results.multi_hand_landmarks:
        for i, (landmarks, handedness) in enumerate(
            zip(results.multi_hand_landmarks, results.multi_handedness)
        ):
            lm = []
            for pt in landmarks.landmark:
                lm.append([pt.x, pt.y, pt.z])
            fingertips = {}
            for name, idx in FINGERTIP_INDICES.items():
                p = landmarks.landmark[idx]
                fingertips[name] = [p.x, p.y, p.z]
            hand_info = {
                "hand_id": i,
                "handedness": handedness.classification[0].label if handedness else None,
                "score": handedness.classification[0].score if handedness else None,
                "landmarks": lm,
                "fingertips": fingertips,
            }
            payload["hands"].append(hand_info)
    return payload

async def handler(ws: websockets.WebSocketServerProtocol, path):
    logger.info("Client connected: %s", ws.remote_address)
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
    async with websockets.serve(handler, "0.0.0.0", 8765, max_size=None, max_queue=None):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())