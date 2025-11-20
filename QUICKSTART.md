# ARPi2 Quick Start Guide - Thin Client Mode

## First Time Setup

### Step 1: Configure IP Address

1. Find your server PC's IP address:
   - **Windows**: Open Command Prompt, type `ipconfig`, look for IPv4 Address
   - **Linux/Mac**: Open Terminal, type `ifconfig` or `ip addr`
2. Edit `config.py` on BOTH server and Pi:
   ```python
   SERVER_IP = "192.168.1.44"  # Replace with your server's IP
   ```

### Step 2: Setup Windows Firewall (Server PC)

**Option A: Automatic (Recommended)**

1. Right-click `setup_firewall.bat`
2. Select "Run as administrator"
3. Press any key to continue

**Option B: Manual**

1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → Next
5. Select "TCP", enter port `8765` → Next
6. Select "Allow the connection" → Next
7. Check all profiles → Next
8. Name it "ARPi2 Game Server" → Finish

### Step 3: Test Connection (On Raspberry Pi)

```bash
python check_connection.py 192.168.1.44
```

If all checks pass, proceed to Step 4!

## Running the System

### On Server PC (Run this first!):

```bash
cd D:\GitHub\ARPi2
python game_server_full.py
```

You should see:

```
Game server with hand tracking started on ws://0.0.0.0:8765
Rendering at 1920x1080 @ 60 FPS target
```

### On Raspberry Pi:

```bash
cd ~/ARPi2
python pi_thin_client.py
```

You should see:

```
Connecting to server at ws://192.168.1.44:8765...
✓ Connected to game server!
```

## Troubleshooting

### Error: "Connection refused (errno 111)"

- **Cause**: Server not running
- **Fix**: Start server first with `python game_server_full.py`

### Error: "No route to host (errno 113)"

- **Cause**: Firewall blocking connection
- **Fix**: Run `setup_firewall.bat` as administrator on server PC

### Error: "Connection timeout"

- **Cause**: Wrong IP address or not on same network
- **Fix**:
  1. Verify IP in `config.py`
  2. Ensure both devices on same WiFi
  3. Test: `ping 192.168.1.44` from Pi

### Black Screen on Pi

- **Cause**: Not connected to server yet
- **Fix**: Wait for "Connected to game server!" message

### Low FPS on Server (~18 FPS)

- **Cause**: Rendering to display window slows down
- **Fix**: This is normal, frames sent to Pi are still 60 FPS

## Controls

### Hand Tracking

- Point index finger at elements
- Hold for 1 second to activate
- Circular progress indicator shows when activating

### Mouse (Testing)

- Move mouse to position
- Hover for 1 second to activate
- Works on both server and Pi

### Keyboard

- **ESC**: Exit application
- **Text input**: Supported in D&D character creation

## Performance Tips

1. **Use Ethernet cable** instead of WiFi for best performance
2. **Close unnecessary programs** on server PC
3. **Good lighting** for hand tracking
4. **Position camera** 2-3 feet above table, angled down

## Ports Used

| Port | Purpose                                                    |
| ---- | ---------------------------------------------------------- |
| 8765 | Game server + hand tracking                                |
| 5000 | Legacy hand tracking server (not used in thin client mode) |

## Quick Commands

**Check server IP (Windows):**

```cmd
ipconfig | findstr IPv4
```

**Check Pi IP:**

```bash
hostname -I
```

**Test connection:**

```bash
ping 192.168.1.44
```

**Kill stuck process (Pi):**

```bash
pkill -f pi_thin_client
```

## Game Selection

Once connected, you'll see the game launcher:

1. **Monopoly**: Full board game with properties, dice, tokens
2. **Blackjack**: Free-for-all casino game with betting
3. **D&D**: Character creator with races, classes, dice rolling

Hover over a game to select, then choose players!
