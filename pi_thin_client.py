import asyncio
import websockets
import pygame
import numpy as np
import json
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from config import WINDOW_SIZE, FPS, SERVER_IP, SERVER_PORT


class PiThinClient:
    
    def __init__(self, server_url=None):
        if server_url is None:
            server_url = f"ws://{SERVER_IP}:{SERVER_PORT}"
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        
        pygame.init()
        pygame.mouse.set_visible(True)
        display_flags = pygame.FULLSCREEN | pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode(WINDOW_SIZE, display_flags)
        self.clock = pygame.time.Clock()
        
        self.running = True
        self.last_frame_surface = None
        self.decode_executor = ThreadPoolExecutor(max_workers=2)
        self.decode_queue: Optional[asyncio.Queue] = None
        
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
    
    async def connect(self):
        max_retries = 10
        retry_delay = 3
        
        print(f"\n{'='*60}")
        print(f"Attempting to connect to: {self.server_url}")
        print(f"Make sure the server is running: python game_server_pyglet_complete.py")
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
        print("1. Ensure server is running: python game_server_pyglet_complete.py")
        print(f"2. Check server IP in config.py (currently: {self.server_url})")
        print("3. Check firewall allows port 8765")
        print("4. Ping server: ping <server_ip>")
        print("5. Both devices on same network?")
        print("="*60 + "\n")
        return False
    
    @staticmethod
    def _decode_frame_surface(frame_bytes):
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame_bgr is None:
                return None
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            return frame_rgb.tobytes(), (w, h)
        except Exception as e:
            print(f"Decode error: {e}")
            return None
    
    async def receive_frames(self):
        try:
            async for message in self.websocket:
                try:
                    if isinstance(message, bytes):
                        if self.decode_queue is None:
                            continue
                        try:
                            self.decode_queue.put_nowait(message)
                        except asyncio.QueueFull:
                            # Drop oldest frame to keep latency low
                            try:
                                self.decode_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                            try:
                                self.decode_queue.put_nowait(message)
                            except asyncio.QueueFull:
                                pass
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

    async def decode_loop(self):
        loop = asyncio.get_running_loop()
        while self.running:
            if not self.decode_queue:
                await asyncio.sleep(0.001)
                continue
            try:
                frame_bytes = await self.decode_queue.get()
            except asyncio.CancelledError:
                break
            result = await loop.run_in_executor(self.decode_executor, self._decode_frame_surface, frame_bytes)
            if result is not None:
                try:
                    buffer_bytes, size = result
                    frame_surface = pygame.image.frombuffer(buffer_bytes, size, 'RGB')
                    if size != WINDOW_SIZE:
                        frame_surface = pygame.transform.smoothscale(frame_surface, WINDOW_SIZE)
                    self.last_frame_surface = frame_surface.convert()
                except Exception as e:
                    print(f"Surface error: {e}")
            self.decode_queue.task_done()
    
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
            
            await asyncio.sleep(0.01)
    
    async def render_loop(self):
        while self.running:
            if self.last_frame_surface:
                self.screen.blit(self.last_frame_surface, (0, 0))
            else:
                self.screen.fill((20, 20, 30))
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
        self.decode_queue = asyncio.Queue(maxsize=1)
        
        try:
            await asyncio.gather(
                self.receive_frames(),
                self.decode_loop(),
                self.render_loop(),
                self.handle_input(),
                self.ping_loop()
            )
        except KeyboardInterrupt:
            print("\nShutting down client...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        if self.decode_executor:
            self.decode_executor.shutdown(wait=False)
        if self.decode_queue:
            while not self.decode_queue.empty():
                try:
                    self.decode_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        pygame.quit()


async def main():
    client = PiThinClient()
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
