# ARPi2 Web UI Controller

This project now includes a tiny **local-hosted website** that lets phones/tablets control:
- Main menu game selection
- Player selection (toggle players + start)
- In-game popup/panel buttons (Monopoly/Blackjack)

It uses:
- A local HTTP server for the static site (`web_ui/`) on port **8000**
- The existing WebSocket server on port **8765** with a dedicated UI path: **`/ui`**

## Run

1) Start the server on the Windows machine:

```powershell
python game_server_pyglet_complete.py
```

2) On a phone/tablet connected to the same network, open:

- `http://<SERVER_IP>:8000`

3) Enter:
- Host/IP: the server IP (same one the Pi client uses)
- Player slot: Player 1-8
- Name: optional

Then press **Connect**.

## Notes

- The WebSocket endpoint for the web UI is `ws://<SERVER_IP>:8765/ui`.
- The Pi thin client can still connect to `ws://<SERVER_IP>:8765/` for video.
- Player 8 (DM) is treated as always selected in the selection screen.
