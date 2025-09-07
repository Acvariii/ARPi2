import sys
import threading
import time

def usage():
    print("Usage: python main.py [pi|launcher|both]")
    sys.exit(1)

if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "both"

    if mode == "pi":
        from pi_client import start_pi_client
        start_pi_client()
    elif mode == "launcher":
        # call the restored monolithic launcher entrypoint
        from game_launcher import run_pygame
        run_pygame()
    elif mode == "both":
        from pi_client import start_pi_client
        from game_launcher import run_pygame
        t = threading.Thread(target=start_pi_client, daemon=True)
        t.start()
        time.sleep(0.3)
        run_pygame()
    else:
        usage()