import asyncio
import websockets
import pygame
import cv2
import numpy as np
import json
import base64
import time
from typing import Optional
from io import BytesIO

from config import WINDOW_SIZE, FPS, SERVER_IP, SERVER_PORT


class PiThinClient:
    
    def __init__(self, server_url=None):
        if server_url is None:
            server_url = f"ws://{SERVER_IP}:{SERVER_PORT}"
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        
        pygame.init()
        pygame.mouse.set_visible(True)
        self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.FULLSCREEN | pygame.NOFRAME)
        self.clock = pygame.time.Clock()
        
        self.camera = cv2.VideoCapture(0)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        self.running = True
        self.last_frame = None
        
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
    
    async def connect(self):
        max_retries = 10
        retry_delay = 3
        
        print(f"\n{'='*60}")
        print(f"Attempting to connect to: {self.server_url}")
        print(f"Make sure the server is running: python game_server_full.py")
        print(f"{'='*60}\n")
        
        for attempt in range(max_retries):
            try:
                print(f"[{attempt + 1}/{max_retries}] Connecting to {self.server_url}...")
                self.websocket = await websockets.connect(
                    self.server_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                )
                print("✓ Connected to game server!")
                return True
            except ConnectionRefusedError:
                print(f"✗ Connection refused - Is the server running?")
            except OSError as e:
                if "113" in str(e) or "No route to host" in str(e):
                    print(f"✗ No route to host - Check firewall and network settings")
                elif "111" in str(e):
                    print(f"✗ Connection refused - Server not running on port 8765")
                else:
                    print(f"✗ Network error: {e}")
            except Exception as e:
                print(f"✗ Connection error: {e}")
            
            if attempt < max_retries - 1:
                print(f"   Retrying in {retry_delay} seconds...\n")
                await asyncio.sleep(retry_delay)
        
        print("\n" + "="*60)
        print("❌ Failed to connect to server")
        print("\nTroubleshooting:")
        print("1. Ensure server is running: python game_server_full.py")
        print(f"2. Check server IP in config.py (currently: {self.server_url})")
        print("3. Check firewall allows port 8765")
        print("4. Ping server: ping <server_ip>")
        print("5. Both devices on same network?")
        print("="*60 + "\n")
        return False
    
    async def send_camera_frame(self):
        ret, frame = self.camera.read()
        if not ret:
            return
        
        # Keep original resolution for quality
        frame_small = cv2.resize(frame, (640, 480))
        
        # Good quality
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        result, encoded_img = cv2.imencode('.jpg', frame_small, encode_param)
        
        if result:
            frame_bytes = encoded_img.tobytes()
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')
            
            message = json.dumps({
                "type": "camera_frame",
                "frame": frame_base64,
                "timestamp": time.time()
            })
            
            try:
                await self.websocket.send(message)
            except:
                pass
    
    async def receive_frames(self):
        try:
            async for message in self.websocket:
                try:
                    if isinstance(message, bytes):
                        nparr = np.frombuffer(message, np.uint8)
                        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame_bgr is not None:
                            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                            frame_surface = pygame.surfarray.make_surface(
                                np.transpose(frame_rgb, (1, 0, 2))
                            )
                            if frame_surface.get_size() != WINDOW_SIZE:
                                frame_surface = pygame.transform.scale(frame_surface, WINDOW_SIZE)
                            self.last_frame = frame_surface
                        continue
                    
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "pong":
                        pass
                
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"Error processing frame: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
            self.running = False
    
    async def handle_input(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    print("Quit event received - shutting down client...")
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        print("ESC pressed - shutting down client...")
                        self.running = False
                    else:
                        try:
                            await self.websocket.send(json.dumps({
                                "type": "keyboard",
                                "key": event.key,
                                "unicode": event.unicode
                            }))
                        except:
                            pass
                elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEMOTION:
                    try:
                        mouse_pos = pygame.mouse.get_pos()
                        await self.websocket.send(json.dumps({
                            "type": "mouse",
                            "pos": mouse_pos,
                            "buttons": pygame.mouse.get_pressed()
                        }))
                    except:
                        pass
            
            await asyncio.sleep(0.01)
    
    async def render_loop(self):
        while self.running:
            self.screen.fill((20, 20, 30))
            
            if self.last_frame:
                self.screen.blit(self.last_frame, (0, 0))
            else:
                font = pygame.font.SysFont("Arial", 48)
                text = font.render("Connecting to server...", True, (255, 255, 255))
                text_rect = text.get_rect(center=(WINDOW_SIZE[0]//2, WINDOW_SIZE[1]//2))
                self.screen.blit(text, text_rect)
            
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_time >= 1.0:
                self.current_fps = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time
            
            font_small = pygame.font.SysFont("Arial", 16)
            fps_text = font_small.render(f"Pi FPS: {self.current_fps:.1f}", True, (0, 255, 0))
            self.screen.blit(fps_text, (10, 10))
            
            pygame.display.flip()
            self.clock.tick(FPS)
            
            await asyncio.sleep(0)
    
    async def camera_loop(self):
        while self.running:
            await self.send_camera_frame()
            await asyncio.sleep(1.0 / 60)  # 60 FPS for fast hand tracking
    
    async def ping_loop(self):
        while self.running:
            try:
                await self.websocket.send(json.dumps({"type": "ping"}))
            except:
                pass
            await asyncio.sleep(5)
    
    async def run(self):
        if not await self.connect():
            print("Could not connect to server. Exiting.")
            return
        
        try:
            await asyncio.gather(
                self.receive_frames(),
                self.render_loop(),
                self.camera_loop(),
                self.handle_input(),
                self.ping_loop()
            )
        except KeyboardInterrupt:
            print("\nShutting down client...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        self.running = False
        if self.camera:
            self.camera.release()
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        pygame.quit()


async def main():
    client = PiThinClient()
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
