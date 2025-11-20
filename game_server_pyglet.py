"""
ARPi2 Game Server - Pyglet/OpenGL Version
High-performance OpenGL-accelerated game server for 60 FPS at 1920x1080
"""
import asyncio
import websockets
import pyglet
from pyglet import gl
import cv2
import numpy as np
import json
import base64
import time
from typing import Dict, List, Optional
import mediapipe as mp

from config import WINDOW_SIZE, FPS, HOVER_TIME_THRESHOLD, Colors
from pyglet_renderer import PygletRenderer, TextCache
from dnd_pyglet import DnDCharacterCreation
from monopoly_pyglet import MonopolyPyglet
from blackjack_pyglet import BlackjackPyglet


class HandTrackingServer:
    """MediaPipe hand tracking processor"""
    
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
        """Process camera frame and extract fingertip positions"""
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


class PygletGameServer:
    """OpenGL-accelerated game server using Pyglet"""
    
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Create Pyglet window with OpenGL
        config = pyglet.gl.Config(double_buffer=True, sample_buffers=1, samples=4)
        self.window = pyglet.window.Window(
            width=WINDOW_SIZE[0],
            height=WINDOW_SIZE[1],
            caption="ARPi2 Game Server (Pyglet/OpenGL)",
            config=config,
            vsync=True  # Enable VSync for smooth 60 FPS
        )
        
        # Setup OpenGL state
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        
        # Renderer
        self.renderer = PygletRenderer(WINDOW_SIZE[0], WINDOW_SIZE[1])
        self.text_cache = TextCache()
        
        # Hand tracking
        self.hand_tracker = HandTrackingServer()
        self.fingertip_data = []
        self.running = True
        
        # FPS tracking
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Input state
        self.last_keyboard_event = None
        self.mouse_x = 0
        self.mouse_y = 0
        
        # Game state
        self.game_state = "menu"  # menu, player_select, monopoly, blackjack, dnd, dnd_creation
        self.selected_game = None
        
        # Menu buttons
        self.game_buttons = self._create_game_buttons()
        self.hover_states = {}  # Track hover progress for buttons
        
        # Game instances
        self.dnd_creation = DnDCharacterCreation(WINDOW_SIZE[0], WINDOW_SIZE[1], self.renderer)
        self.monopoly_game = MonopolyPyglet(WINDOW_SIZE[0], WINDOW_SIZE[1], self.renderer)
        self.blackjack_game = BlackjackPyglet(WINDOW_SIZE[0], WINDOW_SIZE[1], self.renderer)
        self.selected_players = []  # Track which players are selected
        self.current_player_creating = 0  # Track which player is creating character
        
        # Setup event handlers
        self.window.on_draw = self.on_draw
        self.window.on_mouse_motion = self.on_mouse_motion
        self.window.on_key_press = self.on_key_press
        
        print(f"Pyglet/OpenGL game server initialized")
        print(f"OpenGL Version: {gl.gl_info.get_version()}")
        print(f"OpenGL Renderer: {gl.gl_info.get_renderer()}")
    
    def _create_game_buttons(self):
        """Create game selection buttons"""
        games = ["Monopoly", "Blackjack", "D&D"]
        buttons = []
        for i, game in enumerate(games):
            btn_rect = (
                WINDOW_SIZE[0] // 2 - 150,
                WINDOW_SIZE[1] // 2 - 180 + i * 120,
                300, 90
            )
            buttons.append({"text": game, "rect": btn_rect, "key": game.lower()})
        return buttons
    
    def on_draw(self):
        """Pyglet draw callback - called every frame"""
        self.window.clear()
        self.renderer.clear_cache()
        
        # Draw based on game state
        if self.game_state == "menu":
            self.draw_menu()
        elif self.game_state == "player_select":
            self.draw_player_select()
        elif self.game_state == "dnd_creation":
            self.dnd_creation.draw()
        elif self.game_state == "monopoly":
            self.monopoly_game.draw()
        elif self.game_state == "blackjack":
            self.blackjack_game.draw()
        else:
            # Draw game placeholder
            self.renderer.draw_text(
                f"Game: {self.selected_game}",
                WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2,
                font_size=48, anchor_x='center', anchor_y='center',
                color=(255, 255, 255)
            )
        
        # Draw FPS counter
        self.renderer.draw_text(
            f'FPS: {self.current_fps:.1f}',
            10, 30,
            font_size=24,
            color=(255, 255, 255)
        )
        
        # Draw all batched elements
        self.renderer.draw_all()
        
        # Draw cursor last (not batched for immediate feedback)
        self.draw_cursor()
    
    def draw_menu(self):
        """Draw main menu"""
        # Panel background
        panel_rect = (80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
        self.renderer.draw_rect((45, 50, 55), panel_rect)
        
        # Title
        self.renderer.draw_text(
            "Game Launcher",
            WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 100,
            font_name='Arial', font_size=64,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='top'
        )
        
        # Game buttons
        fingertips = self.get_combined_fingertips()
        current_time = time.time()
        
        for btn in self.game_buttons:
            rect = btn["rect"]
            text = btn["text"]
            key = btn["key"]
            
            # Check hover
            hovering = False
            for meta in fingertips:
                px, py = meta["pos"]
                if (rect[0] <= px <= rect[0] + rect[2] and
                    rect[1] <= py <= rect[1] + rect[3]):
                    hovering = True
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": (px, py)}
                    
                    # Check if hover threshold reached
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        self.selected_game = key
                        self.game_state = "player_select"
                        self.hover_states.clear()
                    break
            
            if not hovering and key in self.hover_states:
                del self.hover_states[key]
            
            # Draw button
            bg_color = (80, 120, 180) if hovering else (60, 80, 120)
            border_color = (150, 200, 255) if hovering else (100, 150, 200)
            
            self.renderer.draw_rect(bg_color, rect)
            self.renderer.draw_rect(border_color, rect, width=3)
            
            # Button text
            self.renderer.draw_text(
                text,
                rect[0] + rect[2] // 2, rect[1] + rect[3] // 2 + 10,
                font_size=36,
                color=(255, 255, 255),
                anchor_x='center', anchor_y='center'
            )
            
            # Draw hover progress
            if key in self.hover_states:
                hover_duration = current_time - self.hover_states[key]["start_time"]
                progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
                px, py = self.hover_states[key]["pos"]
                self.renderer.draw_circular_progress(
                    (px, py - 28), 20, progress,
                    (100, 200, 255), thickness=6
                )
    
    def draw_player_select(self):
        """Draw player selection screen"""
        # Panel background
        panel_rect = (80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
        self.renderer.draw_rect((45, 50, 55), panel_rect)
        
        # Title
        self.renderer.draw_text(
            f"Select Players - {self.selected_game.title()}",
            WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 100,
            font_name='Arial', font_size=48,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        # Add Start Game button for each game type
        start_rect = (WINDOW_SIZE[0] // 2 - 150, WINDOW_SIZE[1] // 2, 300, 80)
        
        if self.selected_game == "d&d":
            button_text = "Create Character"
            button_color = (80, 150, 80)
        elif self.selected_game == "monopoly":
            button_text = "Start Monopoly"
            button_color = (80, 100, 150)
        elif self.selected_game == "blackjack":
            button_text = "Start Blackjack"
            button_color = (150, 80, 80)
        else:
            button_text = "Start Game"
            button_color = (80, 80, 80)
        
        self.renderer.draw_rect(button_color, start_rect)
        self.renderer.draw_rect((120, 200, 120), start_rect, width=3)
        
        self.renderer.draw_text(
            button_text,
            WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2 + 40,
            font_size=32,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        # Check if start button clicked
        fingertips = self.get_combined_fingertips()
        for meta in fingertips:
            px, py = meta["pos"]
            if (start_rect[0] <= px <= start_rect[0] + start_rect[2] and
                start_rect[1] <= py <= start_rect[1] + start_rect[3]):
                if "start_btn" not in self.hover_states:
                    self.hover_states["start_btn"] = {"start_time": time.time(), "pos": (px, py)}
                
                hover_duration = time.time() - self.hover_states["start_btn"]["start_time"]
                if hover_duration >= HOVER_TIME_THRESHOLD:
                    # Start the selected game
                    self.selected_players = [0]  # For now, just player 0
                    
                    if self.selected_game == "d&d":
                        self.current_player_creating = 0
                        self.dnd_creation.start_creation(0)
                        self.game_state = "dnd_creation"
                    elif self.selected_game == "monopoly":
                        self.monopoly_game.start_game([0, 1])
                        self.game_state = "monopoly"
                    elif self.selected_game == "blackjack":
                        self.blackjack_game.start_game([0, 1])
                        self.game_state = "blackjack"
                    
                    self.hover_states.clear()
                
                progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
                self.renderer.draw_circular_progress(
                    (px, py - 28), 20, progress,
                    (100, 200, 255), thickness=6
                )
                break
        else:
            if "start_btn" in self.hover_states:
                del self.hover_states["start_btn"]
        
        # Placeholder - just show a back button
        back_rect = (WINDOW_SIZE[0] // 2 - 100, 100, 200, 60)
        self.renderer.draw_rect((120, 60, 60), back_rect)
        self.renderer.draw_rect((200, 100, 100), back_rect, width=2)
        
        self.renderer.draw_text(
            "Back to Menu",
            WINDOW_SIZE[0] // 2, 130,
            font_size=24,
            color=(255, 255, 255),
            anchor_x='center', anchor_y='center'
        )
        
        # Check if back button clicked
        fingertips = self.get_combined_fingertips()
        for meta in fingertips:
            px, py = meta["pos"]
            if (back_rect[0] <= px <= back_rect[0] + back_rect[2] and
                back_rect[1] <= py <= back_rect[1] + back_rect[3]):
                if "back_btn" not in self.hover_states:
                    self.hover_states["back_btn"] = {"start_time": time.time(), "pos": (px, py)}
                
                hover_duration = time.time() - self.hover_states["back_btn"]["start_time"]
                if hover_duration >= HOVER_TIME_THRESHOLD:
                    self.game_state = "menu"
                    self.selected_game = None
                    self.hover_states.clear()
                
                progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
                self.renderer.draw_circular_progress(
                    (px, py - 28), 20, progress,
                    (100, 200, 255), thickness=6
                )
                break
        else:
            if "back_btn" in self.hover_states:
                del self.hover_states["back_btn"]
    
    def draw_cursor(self):
        """Draw mouse cursor as a circle"""
        # mouse_y is already in pygame coordinates, convert to OpenGL
        y_opengl = WINDOW_SIZE[1] - self.mouse_y
        
        # Draw filled circle
        circle = pyglet.shapes.Circle(
            self.mouse_x, y_opengl, 8,
            color=(0, 220, 255),
            batch=None
        )
        circle.draw()
    
    def on_mouse_motion(self, x, y, dx, dy):
        """Handle mouse movement"""
        self.mouse_x = x
        # Convert from OpenGL coordinates (bottom-left) to pygame coordinates (top-left)
        self.mouse_y = WINDOW_SIZE[1] - y
    
    def on_key_press(self, symbol, modifiers):
        """Handle keyboard input"""
        if symbol == pyglet.window.key.ESCAPE:
            print("ESC pressed - shutting down server...")
            self.running = False
            self.window.close()
            return pyglet.event.EVENT_HANDLED
    
    def get_combined_fingertips(self) -> List[Dict]:
        """Get all fingertip data including mouse"""
        combined = list(self.fingertip_data)
        # Add mouse position
        combined.append({
            "pos": (self.mouse_x, self.mouse_y),
            "hand": -1,
            "name": "mouse"
        })
        return combined
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connections"""
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
        """Process incoming camera frame for hand tracking"""
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
    
    async def encode_frame(self) -> str:
        """Capture and encode current frame for streaming to clients"""
        # Capture OpenGL framebuffer
        buffer = pyglet.image.get_buffer_manager().get_color_buffer()
        image_data = buffer.get_image_data()
        
        # Convert to numpy array
        data = np.frombuffer(image_data.get_data(), dtype=np.uint8)
        data = data.reshape((WINDOW_SIZE[1], WINDOW_SIZE[0], 4))
        
        # Flip vertically (OpenGL origin is bottom-left)
        data = np.flipud(data)
        
        # Convert RGBA to BGR for JPEG
        frame_bgr = cv2.cvtColor(data, cv2.COLOR_RGBA2BGR)
        
        # Encode as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        result, encoded_img = cv2.imencode('.jpg', frame_bgr, encode_param)
        
        if result:
            return base64.b64encode(encoded_img.tobytes()).decode('utf-8')
        return ""
    
    async def broadcast_frame(self, frame_data: str):
        """Broadcast frame to all connected clients"""
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
    
    def update(self, dt):
        """Update game state (called every frame)"""
        # Update FPS counter
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            print(f"Server FPS: {self.current_fps:.1f} | Hands tracked: {len(self.fingertip_data)}")
        
        # Update game-specific logic
        fingertips = self.get_combined_fingertips()
        
        if self.game_state == "dnd_creation":
            self.dnd_creation.update(dt)
            creation_complete = self.dnd_creation.handle_input(fingertips)
            
            if creation_complete:
                print(f"Character creation complete for player {self.current_player_creating}")
                self.game_state = "menu"
                self.selected_game = None
                self.selected_players = []
        
        elif self.game_state == "monopoly":
            self.monopoly_game.update(dt)
            exit_to_menu = self.monopoly_game.handle_input(fingertips)
            
            if exit_to_menu:
                print("Exiting Monopoly to menu")
                self.game_state = "menu"
                self.selected_game = None
                self.selected_players = []
        
        elif self.game_state == "blackjack":
            self.blackjack_game.update(dt)
            exit_to_menu = self.blackjack_game.handle_input(fingertips)
            
            if exit_to_menu:
                print("Exiting Blackjack to menu")
                self.game_state = "menu"
                self.selected_game = None
                self.selected_players = []
    
    async def async_update(self, dt):
        """Async update for network operations"""
        # Only encode/broadcast if there are clients
        if self.clients:
            frame_data = await self.encode_frame()
            await self.broadcast_frame(frame_data)
    
    def run(self):
        """Start the Pyglet game loop"""
        # Schedule update callback
        pyglet.clock.schedule_interval(self.update, 1.0 / FPS)
        
        # Schedule async network update
        async def async_loop():
            while self.running:
                await self.async_update(1.0 / FPS)
                await asyncio.sleep(1.0 / FPS)
        
        # Run Pyglet event loop
        pyglet.app.run()
    
    async def start(self):
        """Start WebSocket server and game loop"""
        # Start WebSocket server
        server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"Game server with hand tracking started on ws://{self.host}:{self.port}")
        print(f"Rendering at {WINDOW_SIZE[0]}x{WINDOW_SIZE[1]} @ {FPS} FPS target")
        
        # Run Pyglet in a separate thread or use async integration
        # For now, we'll use pyglet.app.run() which blocks
        
        # Create async task for network
        async def network_loop():
            while self.running:
                if self.clients:
                    frame_data = await self.encode_frame()
                    await self.broadcast_frame(frame_data)
                await asyncio.sleep(1.0 / 30)  # 30 FPS streaming
        
        network_task = asyncio.create_task(network_loop())
        
        # Run Pyglet game loop (this blocks)
        self.run()
        
        # Cleanup
        await network_task
        server.close()
        await server.wait_closed()


async def main():
    """Main entry point"""
    server = PygletGameServer(host="0.0.0.0", port=8765)
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.running = False
        if server.hand_tracker and hasattr(server.hand_tracker, 'hands'):
            server.hand_tracker.hands.close()


if __name__ == "__main__":
    # Note: Pyglet doesn't work well with asyncio.run() due to event loop conflicts
    # We'll need to integrate them properly
    print("Starting Pyglet/OpenGL Game Server...")
    print("This is a work in progress - integrating Pyglet with asyncio...")
    
    # For now, just run the server without asyncio
    server = PygletGameServer(host="0.0.0.0", port=8765)
    
    # Schedule FPS update
    def update(dt):
        server.update(dt)
    
    pyglet.clock.schedule_interval(update, 1.0 / FPS)
    
    print(f"Server started on ws://{server.host}:{server.port}")
    print("Press ESC to exit")
    
    pyglet.app.run()
