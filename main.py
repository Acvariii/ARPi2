import sys
import threading
import time

def usage():
    print("Usage: python main.py [pi|launcher|server|both]")
    print("  pi: Run Raspberry Pi camera client")
    print("  launcher: Run game launcher (default)")
    print("  server: Run server with video display")
    print("  both: Run both camera and launcher")
    sys.exit(1)

if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "launcher"

    if mode == "pi":
        from pi_client import start_pi_client
        start_pi_client()
    
    elif mode == "server":
        # Run server with video display
        from video_display import VideoDisplay
        import asyncio
        
        # Start video display
        video = VideoDisplay()
        video.start()
        
        # Import and run server
        from server import main as server_main
        print("Server running with video display. Press Ctrl+C to stop.")
        print("Video window: Press 'q' to quit video display")
        try:
            asyncio.run(server_main())
        except KeyboardInterrupt:
            print("\nShutting down...")
            video.stop()
    
    elif mode == "launcher":
        from launcher import run_pygame
        run_pygame()
    
    elif mode == "both":
        from pi_client import start_pi_client
        from launcher import run_pygame
        
        # Start camera in background
        t = threading.Thread(target=start_pi_client, daemon=True)
        t.start()
        time.sleep(0.5)  # Give camera time to connect
        
        # Run launcher in main thread
        run_pygame()
    
    else:
        usage()