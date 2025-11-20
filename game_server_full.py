import asyncio
import websockets
import pygame
import cv2
import numpy as np
import json
import base64
import time
from typing import Dict, List, Optional
from io import BytesIO
import mediapipe as mp

from launcher import GameLauncher
from config import WINDOW_SIZE, FPS


class HandTrackingServer:
    
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=8,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.fingertip_data = []
    
    def process_frame(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        
        fingertips = []
        
        if results.multi_hand_landmarks:
            h, w = frame_bgr.shape[:2]
            
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                index_tip = hand_landmarks.landmark[8]
                
                x = int(index_tip.x * WINDOW_SIZE[0])
                y = int(index_tip.y * WINDOW_SIZE[1])
                
                fingertips.append({
                    "pos": (x, y),
                    "hand": hand_idx,
                    "name": f"hand_{hand_idx}"
                })
        
        return fingertips


class GameServerWithTracking:
    
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        pygame.init()
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption("ARPi2 Game Server")
        pygame.mouse.set_visible(True)
        self.clock = pygame.time.Clock()
        
        self.launcher = None
        self.hand_tracker = HandTrackingServer()
        self.fingertip_data = []
        self.running = True
        
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        self.last_keyboard_event = None
    
    async def handle_client(self, websocket, path):
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        print(f"Client connected: {client_id}")
        self.clients[client_id] = websocket
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "camera_frame":
                        await self.process_camera_frame(data, client_id)
                    elif msg_type == "keyboard":
                        self.last_keyboard_event = data
                    elif msg_type == "mouse":
                        mouse_pos = tuple(data.get("pos", [0, 0]))
                        mouse_meta = {"pos": mouse_pos, "hand": -2, "name": "remote_mouse"}
                        if mouse_meta not in self.fingertip_data:
                            self.fingertip_data.append(mouse_meta)
                    elif msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                
                except json.JSONDecodeError:
                    print(f"Invalid JSON from {client_id}")
                except Exception as e:
                    print(f"Error processing message from {client_id}: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {client_id}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def process_camera_frame(self, data, client_id):
        try:
            frame_base64 = data.get("frame", "")
            if not frame_base64:
                return
            
            frame_bytes = base64.b64decode(frame_base64)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame_bgr is not None:
                self.fingertip_data = self.hand_tracker.process_frame(frame_bgr)
        
        except Exception as e:
            print(f"Error processing camera frame: {e}")
    
    async def game_loop(self):
        self.launcher = GameLauncher()
        self.launcher.screen = self.screen
        
        def get_combined_fingertips():
            combined = list(self.fingertip_data)
            mouse_pos = pygame.mouse.get_pos()
            combined.append({"pos": mouse_pos, "hand": -1, "name": "mouse"})
            return combined
        
        self.launcher.get_fingertip_meta = get_combined_fingertips
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        print("ESC pressed - shutting down server...")
                        self.running = False
            
            if self.last_keyboard_event:
                key = self.last_keyboard_event.get("key")
                unicode_char = self.last_keyboard_event.get("unicode", "")
                
                event = pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode_char)
                
                if self.launcher.current_game and hasattr(self.launcher.current_game, 'handle_text_input'):
                    self.launcher.current_game.handle_text_input(event)
                
                self.last_keyboard_event = None
            
            self.screen.fill((0, 0, 0))
            
            combined_fingertips = get_combined_fingertips()
            
            if self.launcher.state == "menu":
                self.launcher.handle_menu_state(combined_fingertips)
            elif self.launcher.state == "player_select":
                self.launcher.handle_player_select_state(combined_fingertips)
            elif self.launcher.state in ["monopoly_playing", "blackjack_playing", "dnd_playing"]:
                current_event = None
                if self.last_keyboard_event:
                    key = self.last_keyboard_event.get("key")
                    unicode_char = self.last_keyboard_event.get("unicode", "")
                    current_event = pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode_char)
                    self.last_keyboard_event = None
                
                self.launcher.handle_game_state(combined_fingertips, current_event)
            
            # Draw visible mouse cursor
            mouse_pos = pygame.mouse.get_pos()
            pygame.draw.circle(self.screen, (255, 255, 255), mouse_pos, 10, 2)
            pygame.draw.circle(self.screen, (0, 200, 255), mouse_pos, 3)
            
            pygame.display.update()
            
            # Only encode/broadcast if there are connected clients
            if self.clients:
                frame_data = await self.encode_frame()
                await self.broadcast_frame(frame_data)
            
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_time >= 1.0:
                self.current_fps = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time
                print(f"Server FPS: {self.current_fps:.1f} | Hands tracked: {len(self.fingertip_data)}")
            
            await asyncio.sleep(1.0 / FPS)
    
    async def encode_frame(self) -> str:
        # Fast frame capture using surfarray
        frame_array = pygame.surfarray.pixels3d(self.screen)
        frame_bgr = cv2.cvtColor(np.transpose(frame_array, (1, 0, 2)), cv2.COLOR_RGB2BGR)
        
        # Lower quality for faster encoding (clients only need video feed)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        result, encoded_img = cv2.imencode('.jpg', frame_bgr, encode_param)
        
        if result:
            return base64.b64encode(encoded_img.tobytes()).decode('utf-8')
        return ""
    
    async def broadcast_frame(self, frame_data: str):
        if not self.clients:
            return
        
        message = json.dumps({
            "type": "game_frame",
            "frame": frame_data,
            "fps": self.current_fps,
            "hands": len(self.fingertip_data)
        })
        
        disconnected = []
        for client_id, websocket in self.clients.items():
            try:
                await websocket.send(message)
            except:
                disconnected.append(client_id)
        
        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def start(self):
        server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"Game server with hand tracking started on ws://{self.host}:{self.port}")
        print(f"Rendering at {WINDOW_SIZE[0]}x{WINDOW_SIZE[1]} @ {FPS} FPS target")
        
        game_task = asyncio.create_task(self.game_loop())
        
        await asyncio.gather(server.wait_closed(), game_task)
    
    def stop(self):
        self.running = False
        if self.hand_tracker and hasattr(self.hand_tracker, 'hands'):
            self.hand_tracker.hands.close()
        pygame.quit()


async def main():
    server = GameServerWithTracking(host="0.0.0.0", port=8765)
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()


if __name__ == "__main__":
    asyncio.run(main())
