import asyncio
import cv2
import numpy as np
import websockets
import json
import time
import threading

SERVER_WS = "ws://192.168.1.79:8765"  # <-- replace SERVER_IP with your Windows machine IP
CAM_INDEX = 0
WIDTH = 1280
HEIGHT = 720
FPS = 60
JPEG_QUALITY = 75

# Receiver task: prints JSON payloads or renders a small preview with fingertip overlays
async def receiver(ws):
    async for message in ws:
        try:
            data = json.loads(message)
            # minimal handling: print number of hands
            if data.get("type") == "hands":
                print(f"[{time.strftime('%H:%M:%S')}] hands: {len(data.get('hands', []))}")
        except Exception:
            pass

async def send_frames(ws):
    cap = cv2.VideoCapture(CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    frame_id = 0
    if not cap.isOpened():
        print("Failed to open camera")
        return
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue
            # encode to JPEG
            _, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            await ws.send(buf.tobytes())
            frame_id += 1
            await asyncio.sleep(0)  # yield
    finally:
        cap.release()

async def main():
    async with websockets.connect(SERVER_WS, max_size=None) as ws:
        # register as camera
        await ws.send("camera")
        # run send and recv concurrently
        await asyncio.gather(send_frames(ws), receiver(ws))

if __name__ == "__main__":
    asyncio.run(main())