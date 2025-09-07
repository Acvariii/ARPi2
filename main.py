import sys

# simple entrypoint to run either the pi client or the launcher
def usage():
    print("Usage: python main.py [pi|launcher]")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()

    mode = sys.argv[1].lower()
    if mode == "pi":
        # start the pi client
        from pi_client import start_pi_client
        start_pi_client()
    elif mode == "launcher":
        # start the pygame launcher
        from game_launcher import run_launcher
        run_launcher()
    else:
        usage()