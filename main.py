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
        from launcher import run_launcher
        run_launcher()
    elif mode == "both":
        from pi_client import start_pi_client
        from launcher import run_launcher
        t = threading.Thread(target=start_pi_client, daemon=True)
        t.start()
        time.sleep(0.3)
        run_launcher()
    else:
        usage()