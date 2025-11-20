"""Central configuration for ARPi2 game system."""

# Network Configuration
SERVER_IP = "192.168.1.44"
SERVER_PORT = 8765
SERVER_WS = f"ws://{SERVER_IP}:{SERVER_PORT}"

# Display Configuration
WINDOW_SIZE = (1920, 1080)
FPS = 60

# Interaction Configuration
HOVER_TIME_THRESHOLD = 0.9  # seconds to hold for activation

# Player Configuration
MAX_PLAYERS = 8
MIN_PLAYERS = 2

# Player Colors (8 distinct colors)
PLAYER_COLORS = [
    (220, 40, 40),      # Red
    (40, 120, 200),     # Blue
    (40, 200, 120),     # Green
    (255, 200, 60),     # Yellow
    (200, 40, 200),     # Magenta
    (40, 220, 200),     # Cyan
    (255, 120, 60),     # Orange
    (140, 40, 220),     # Purple
]

# UI Colors
class Colors:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    DARK_BG = (18, 18, 28)
    PANEL = (24, 24, 34)
    ACCENT = (240, 200, 80)
    GOLD = (255, 215, 0)
    SHADOW = (10, 10, 10)
    DISABLED = (80, 80, 80)
    DISABLED_TEXT = (160, 160, 160)