import sys
import threading
import time

# simple entrypoint to run either the pi client or the launcher
def usage():
    print("Usage: python main.py [pi|launcher|both]")
    sys.exit(1)

if __name__ == "__main__":
    # default: run both client and launcher
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "both"

    if mode == "pi":
        # start the pi client only
        from pi_client import start_pi_client
        start_pi_client()
    elif mode == "launcher":
        # start the pygame launcher only
        from game_launcher import run_launcher
        run_launcher()
    elif mode == "both":
        # start pi client in a background thread, run launcher in main thread
        from pi_client import start_pi_client
        from game_launcher import run_launcher

        t = threading.Thread(target=start_pi_client, daemon=True)
        t.start()
        # small delay to allow the client to connect before UI appears
        time.sleep(0.3)
        run_launcher()
    else:
        usage()