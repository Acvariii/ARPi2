"""
ARPi2 Game Server - Pyglet/OpenGL Version (Clean & Organized)
High-performance OpenGL-accelerated game server with complete UI
All games include player selection and player panels matching Pygame version
"""
import asyncio
import websockets
import pyglet
from pyglet import gl
import cv2
import numpy as np
import json
import time
import ctypes
from typing import Dict, List
import mediapipe as mp
from concurrent.futures import ThreadPoolExecutor

from config import WINDOW_SIZE, FPS, HOVER_TIME_THRESHOLD, Colors
from core.renderer import PygletRenderer
from games.monopoly import MonopolyGame
from games.blackjack import BlackjackGame
from games.dnd import DnDCharacterCreation


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
    """OpenGL-accelerated game server using Pyglet with complete UI"""
    
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Thread pools for CPU-intensive operations
        self.hand_worker_count = 2
        self.encode_worker_count = 2
        self.hand_executor = ThreadPoolExecutor(max_workers=self.hand_worker_count)
        self.encode_executor = ThreadPoolExecutor(max_workers=self.encode_worker_count)
        self.latest_hand_frame = None
        self.hand_frame_event = None
        
        # Create Pyglet window with OpenGL - Fullscreen
        config = pyglet.gl.Config(double_buffer=True, sample_buffers=1, samples=4)
        self.window = pyglet.window.Window(
            fullscreen=True,
            caption="ARPi2 Game Server - Pyglet/OpenGL (Complete UI)",
            config=config,
            vsync=True
        )
        
        # Update window size to actual screen size
        global WINDOW_SIZE
        WINDOW_SIZE = (self.window.width, self.window.height)
        
        # Setup OpenGL state
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        
        # Renderer - use actual window size for fullscreen
        self.renderer = PygletRenderer(self.window.width, self.window.height)
        
        # Hand tracking
        self.hand_tracker = HandTrackingServer()
        self.fingertip_data = []
        self.running = True
        
        # FPS tracking
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Frame broadcasting
        self.last_broadcast_time = time.time()
        self.broadcast_fps = 60  # Send 60 frames per second to clients
        self.broadcasting = False  # Flag to prevent overlapping broadcasts
        
        # GPU capture buffers (double-buffered PBOs)
        self.capture_width = self.window.width
        self.capture_height = self.window.height
        self.capture_stride = self.capture_width * 3
        self.capture_buffer_size = self.capture_stride * self.capture_height
        self.capture_pbos = (gl.GLuint * 2)()
        gl.glGenBuffers(2, self.capture_pbos)
        for idx in range(2):
            gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.capture_pbos[idx])
            gl.glBufferData(gl.GL_PIXEL_PACK_BUFFER, self.capture_buffer_size, None, gl.GL_STREAM_READ)
        gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)
        self.capture_pbo_index = 0
        self.capture_ready = False

        # Input state
        self.last_keyboard_event = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.esc_pressed = False  # Track ESC key presses
        
        # Game state
        self.state = "menu"  # menu, monopoly, blackjack, dnd_creation
        
        # Menu buttons
        self.game_buttons = self._create_game_buttons()
        self.hover_states = {}
        
        # Game instances - use actual window size for fullscreen
        self.dnd_creation = DnDCharacterCreation(self.window.width, self.window.height, self.renderer)
        self.monopoly_game = MonopolyGame(self.window.width, self.window.height, self.renderer)
        self.blackjack_game = BlackjackGame(self.window.width, self.window.height, self.renderer)
        
        # Setup event handlers
        self.window.on_draw = self.on_draw
        self.window.on_mouse_motion = self.on_mouse_motion
        self.window.on_key_press = self.on_key_press
        self.window.on_close = self.on_close
        
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
        """Pyglet draw callback"""
        self.window.clear()
        
        # Clear renderer cache for new frame
        self.renderer.clear_cache()
        
        if self.state == "menu":
            self._draw_menu()
        elif self.state == "monopoly":
            self.monopoly_game.draw()
        elif self.state == "blackjack":
            self.blackjack_game.draw()
        elif self.state == "dnd_creation":
            self.dnd_creation.draw()
        
        # Draw all batched shapes (board, panels, popups)
        self.renderer.draw_all()
        
        # Draw game-specific immediate elements (tokens on top of board, under popups)
        if self.state == "monopoly" and hasattr(self.monopoly_game, 'draw_immediate'):
            self.monopoly_game.draw_immediate()
        elif self.state == "blackjack" and hasattr(self.blackjack_game, 'draw_immediate'):
            self.blackjack_game.draw_immediate()
        
        # Draw popup batch again so popups appear on top of immediate elements
        if self.state == "monopoly" and self.monopoly_game.popup.active:
            # Create new batch for popup only
            popup_renderer = self.monopoly_game.renderer
            popup_renderer.clear_cache()
            popup_renderer.draw_rect((0, 0, 0, 50), (0, 0, self.monopoly_game.width, self.monopoly_game.height))
            self.monopoly_game.popup.draw(popup_renderer)
            popup_renderer.draw_all()
        
        # Draw cursors AFTER everything else so they're on top
        self._draw_cursors()
        
        # Update FPS counter
        self._update_fps()
    
    def on_mouse_motion(self, x, y, dx, dy):
        """Handle mouse motion (for testing without hand tracking)"""
        # Convert from OpenGL coordinates (bottom-left origin) to Pygame coordinates (top-left origin)
        self.mouse_x = x
        self.mouse_y = WINDOW_SIZE[1] - y
    
    def on_key_press(self, symbol, modifiers):
        """Handle keyboard input"""
        if symbol == pyglet.window.key.ESCAPE:
            if self.state == "menu":
                print("ESC pressed in menu - Exiting server...")
                self.running = False
                pyglet.app.exit()
                self.window.close()
            else:
                print("ESC pressed in game - Returning to menu...")
                self.esc_pressed = True
    
    def on_close(self):
        """Handle window close event"""
        print("Window closed - Exiting server...")
        self.running = False
        pyglet.app.exit()
        return True
    
    def update(self, dt: float):
        """Update game state"""
        # Get fingertip data (or use mouse for testing)
        if self.fingertip_data:
            fingertip_meta = self.fingertip_data
        else:
            # Use mouse position for testing
            fingertip_meta = [{"pos": (self.mouse_x, self.mouse_y), "hand": -1, "name": "mouse"}]
        
        # Inject ESC key if pressed
        if self.esc_pressed:
            fingertip_meta = ['ESC'] + fingertip_meta
            self.esc_pressed = False
        
        # Handle input based on state
        if self.state == "menu":
            self._handle_menu_input(fingertip_meta)
        elif self.state == "monopoly":
            should_exit = self.monopoly_game.handle_input(fingertip_meta)
            if should_exit:
                print("Exiting Monopoly to menu")
                self.state = "menu"
                self.monopoly_game.state = "player_select"
                self.monopoly_game.selection_ui.reset()
            self.monopoly_game.update(dt)
        elif self.state == "blackjack":
            should_exit = self.blackjack_game.handle_input(fingertip_meta)
            if should_exit:
                print("Exiting Blackjack to menu")
                self.state = "menu"
                self.blackjack_game.state = "player_select"
                self.blackjack_game.selection_ui.reset()
            self.blackjack_game.update(dt)
        elif self.state == "dnd_creation":
            should_exit = self.dnd_creation.handle_input(fingertip_meta)
            if should_exit:
                print("Exiting D&D to menu")
                self.state = "menu"
            self.dnd_creation.update(dt)
    
    def _handle_menu_input(self, fingertip_meta: List[Dict]):
        """Handle menu input"""
        current_time = time.time()
        active_hovers = set()
        
        for meta in fingertip_meta:
            pos = meta["pos"]
            
            for i, btn in enumerate(self.game_buttons):
                btn_rect = btn["rect"]
                if (btn_rect[0] <= pos[0] <= btn_rect[0] + btn_rect[2] and
                    btn_rect[1] <= pos[1] <= btn_rect[1] + btn_rect[3]):
                    key = f"game_{i}"
                    active_hovers.add(key)
                    
                    if key not in self.hover_states:
                        self.hover_states[key] = {"start_time": current_time, "pos": pos}
                    
                    hover_duration = current_time - self.hover_states[key]["start_time"]
                    if hover_duration >= HOVER_TIME_THRESHOLD:
                        game_key = btn["key"]
                        if game_key == "monopoly":
                            self.state = "monopoly"
                            self.monopoly_game.state = "player_select"
                        elif game_key == "blackjack":
                            self.state = "blackjack"
                            self.blackjack_game.state = "player_select"
                        elif game_key == "d&d":
                            self.state = "dnd_creation"
                        del self.hover_states[key]
        
        # Remove stale hovers
        for key in list(self.hover_states.keys()):
            if key not in active_hovers:
                del self.hover_states[key]
    
    def _draw_menu(self):
        """Draw main menu"""
        # Background
        self.renderer.draw_rect((25, 35, 25), (0, 0, WINDOW_SIZE[0], WINDOW_SIZE[1]))
        
        # Panel
        panel_rect = (80, 60, WINDOW_SIZE[0] - 160, WINDOW_SIZE[1] - 120)
        self.renderer.draw_rect(Colors.PANEL, panel_rect)
        
        # Title
        self.renderer.draw_text(
            "ARPi2 Game Launcher",
            WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 90,
            font_name='Arial', font_size=64,
            color=Colors.WHITE,
            anchor_x='center', anchor_y='center'
        )
        
        # Subtitle
        self.renderer.draw_text(
            "Pyglet/OpenGL - Complete UI with Player Selection",
            WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] - 150,
            font_name='Arial', font_size=24,
            color=(200, 200, 200),
            anchor_x='center', anchor_y='center'
        )
        
        # Game buttons
        for i, btn in enumerate(self.game_buttons):
            x, y, w, h = btn["rect"]
            
            # Button background
            self.renderer.draw_rect((80, 100, 120), (x, y, w, h))
            self.renderer.draw_rect((150, 170, 190), (x, y, w, h), width=3)
            
            # Button text
            self.renderer.draw_text(
                btn["text"],
                x + w // 2, y + h // 2,
                font_name='Arial', font_size=40,
                color=Colors.WHITE,
                anchor_x='center', anchor_y='center'
            )
        
        # Hover indicators
        current_time = time.time()
        for key, state in self.hover_states.items():
            hover_duration = current_time - state["start_time"]
            progress = min(1.0, hover_duration / HOVER_TIME_THRESHOLD)
            pos = state["pos"]
            self.renderer.draw_circular_progress((pos[0] + 28, pos[1] - 28), 20, progress, Colors.ACCENT, thickness=6)
    
    def _draw_cursors(self):
        """Draw cursor for each fingertip - uses immediate drawing to be on top"""
        if self.fingertip_data:
            for meta in self.fingertip_data:
                pos = meta["pos"]
                self.renderer.draw_circle_immediate(Colors.ACCENT, pos, 8)
                self.renderer.draw_circle_immediate(Colors.WHITE, pos, 8, width=2)
        else:
            # Draw mouse cursor - blue dot on top of everything
            self.renderer.draw_circle_immediate((100, 150, 255), (self.mouse_x, self.mouse_y), 8)
            self.renderer.draw_circle_immediate((255, 255, 255), (self.mouse_x, self.mouse_y), 8, width=2)
    
    def _update_fps(self):
        """Update FPS counter"""
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            """print(f"Server FPS: {self.current_fps:.1f} | Hands tracked: {len(self.fingertip_data)}")"""
    
    async def broadcast_frame(self):
        """Capture screen and broadcast to all clients with GPU/CPU overlap"""
        if self.broadcasting:
            return
        
        self.broadcasting = True
        try:
            width = self.capture_width
            height = self.capture_height
            bytes_per_frame = self.capture_buffer_size
            current_index = self.capture_pbo_index
            next_index = (current_index + 1) % 2
            frame_bytes = None
            
            # Kick off asynchronous GPU read into current PBO
            gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.capture_pbos[current_index])
            gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, ctypes.c_void_p(0))
            
            # Map the previously used PBO to access completed pixel data
            if self.capture_ready:
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, self.capture_pbos[next_index])
                ptr = gl.glMapBuffer(gl.GL_PIXEL_PACK_BUFFER, gl.GL_READ_ONLY)
                if ptr:
                    frame_bytes = ctypes.string_at(ptr, bytes_per_frame)
                    gl.glUnmapBuffer(gl.GL_PIXEL_PACK_BUFFER)
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)
            else:
                # Skip first frame (no data yet)
                gl.glBindBuffer(gl.GL_PIXEL_PACK_BUFFER, 0)
                self.capture_ready = True
            
            # Advance PBO index for next call
            self.capture_pbo_index = next_index
            
            if not frame_bytes:
                return
            
            loop = asyncio.get_running_loop()
            
            def encode_frame():
                arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                arr = arr.reshape((height, width, 3))
                arr = np.flip(arr, axis=0)  # Flip vertically
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                result, encoded = cv2.imencode('.jpg', arr, encode_param)
                if result:
                    return encoded.tobytes()
                return None
            
            encoded_bytes = await loop.run_in_executor(self.encode_executor, encode_frame)
            if not encoded_bytes or not self.clients:
                return
            
            disconnected = []
            send_tasks = []
            for client_id, websocket in list(self.clients.items()):
                send_tasks.append((client_id, websocket.send(encoded_bytes)))
            
            results = await asyncio.gather(*[task for _, task in send_tasks], return_exceptions=True)
            for (client_id, _), result in zip(send_tasks, results):
                if isinstance(result, Exception):
                    disconnected.append(client_id)
            
            for client_id in disconnected:
                if client_id in self.clients:
                    del self.clients[client_id]
        except Exception as e:
            print(f"Error broadcasting frame: {e}")
        finally:
            self.broadcasting = False

    async def hand_tracking_loop(self):
        if self.hand_frame_event is None:
            self.hand_frame_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        while self.running:
            await self.hand_frame_event.wait()
            frame_bytes = self.latest_hand_frame
            self.latest_hand_frame = None
            self.hand_frame_event.clear()
            if not frame_bytes:
                continue

            def process_camera_frame():
                try:
                    nparr = np.frombuffer(frame_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        return self.hand_tracker.process_frame(frame)
                except Exception as e:
                    print(f"Error in hand tracking: {e}")
                return None

            try:
                fingertips = await loop.run_in_executor(self.hand_executor, process_camera_frame)
                if fingertips is not None:
                    self.fingertip_data = fingertips
            except Exception as e:
                print(f"Hand tracking processing error: {e}")
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.clients[client_id] = websocket
        print(f"Client connected: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    if isinstance(message, bytes):
                        self.latest_hand_frame = bytes(message)
                        if self.hand_frame_event:
                            self.hand_frame_event.set()
                        continue

                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                    elif msg_type == "keyboard":
                        # could handle keyboard inputs if needed
                        pass
                    elif msg_type == "mouse":
                        pass
                except Exception as e:
                    print(f"Error processing message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {client_id}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def start_server(self):
        """Start WebSocket server"""
        # Use lambda to properly wrap the handler for websockets 14.0+
        async def handler(websocket):
            await self.handle_client(websocket, websocket.request.path)
        
        server = await websockets.serve(handler, self.host, self.port)
        print(f"Server started on ws://{self.host}:{self.port}")
        print("Press ESC to exit")
        
        await server.wait_closed()
    
    def run(self):
        """Run the game server"""
        print("Starting Pyglet/OpenGL Game Server...")
        print("This version includes complete UI with player selection and panels")
        
        # Schedule update function
        pyglet.clock.schedule_interval(self.update, 1.0 / FPS)
        
        # Run asyncio event loop with Pyglet
        async def main():
            # Start server and hand tracking loop
            self.hand_frame_event = asyncio.Event()
            hand_task = asyncio.create_task(self.hand_tracking_loop())
            server_task = asyncio.create_task(self.start_server())
            
            try:
                # Run Pyglet in async context
                while self.running and len(pyglet.app.windows) > 0:
                    pyglet.clock.tick()
                    
                    for window in list(pyglet.app.windows):
                        if window and not window.has_exit:
                            window.switch_to()
                            window.dispatch_events()
                            window.dispatch_event('on_draw')
                            window.flip()
                    
                    # Broadcast frames to clients at specified FPS (non-blocking)
                    current_time = time.time()
                    if current_time - self.last_broadcast_time >= (1.0 / self.broadcast_fps):
                        if self.clients:  # Only broadcast if we have clients
                            # Fire and forget - don't await
                            asyncio.create_task(self.broadcast_frame())
                        self.last_broadcast_time = current_time
                    
                    await asyncio.sleep(0.001)  # Small sleep to prevent CPU spinning
            finally:
                # Cancel server task
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
                # Cancel hand tracking loop
                hand_task.cancel()
                try:
                    await hand_task
                except asyncio.CancelledError:
                    pass
                print("Server shut down successfully")
        
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nServer stopped by user")
        except Exception as e:
            # Ignore the flip error during shutdown
            if "'NoneType' object has no attribute 'flip'" not in str(e):
                print(f"\nServer error: {e}")
        finally:
            self.running = False
            # Close window if still open
            try:
                if self.window and not self.window.has_exit:
                    self.window.close()
            except:
                pass
            # Stop worker pools
            self.hand_executor.shutdown(wait=False)
            self.encode_executor.shutdown(wait=False)
            if hasattr(self, "capture_pbos"):
                try:
                    gl.glDeleteBuffers(2, self.capture_pbos)
                except Exception:
                    pass
        print("Cleanup complete")


if __name__ == "__main__":
    server = PygletGameServer()
    server.run()
