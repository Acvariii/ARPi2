import socket
import sys

def check_connection(server_ip, port=8765):
    print(f"\n{'='*60}")
    print(f"ARPi2 Server Connection Diagnostic")
    print(f"{'='*60}\n")
    
    print(f"Testing connection to: {server_ip}:{port}\n")
    
    print("Step 1: Testing basic network connectivity...")
    try:
        import subprocess
        import platform
        
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        result = subprocess.run(['ping', param, '1', server_ip], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        if result.returncode == 0:
            print(f"✓ Server {server_ip} is reachable via ping")
        else:
            print(f"✗ Cannot ping server {server_ip}")
            print("  - Check if server is online")
            print("  - Check if both devices are on same network")
            return False
    except Exception as e:
        print(f"✗ Ping test failed: {e}")
    
    print("\nStep 2: Testing port connectivity...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    
    try:
        result = sock.connect_ex((server_ip, port))
        if result == 0:
            print(f"✓ Port {port} is OPEN and accepting connections")
            print("  Server is running and accessible!")
            sock.close()
            return True
        else:
            print(f"✗ Port {port} is CLOSED or filtered")
            print("  Possible causes:")
            print(f"  - Server not running (start with: python game_server_pyglet_complete.py)")
            print(f"  - Firewall blocking port {port}")
            print(f"  - Server listening on different port")
            sock.close()
            return False
    except socket.timeout:
        print(f"✗ Connection timeout - Server not responding")
        print("  - Check firewall settings")
        print("  - Ensure server is running")
        sock.close()
        return False
    except socket.gaierror:
        print(f"✗ Cannot resolve hostname/IP: {server_ip}")
        print("  - Check IP address is correct")
        sock.close()
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sock.close()
        return False
    
    print(f"\n{'='*60}\n")


def get_local_ip():
    print("Your Raspberry Pi IP address:")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"  {local_ip}")
    except Exception as e:
        print(f"  Could not determine: {e}")
    print()


if __name__ == "__main__":
    print("\nUsage: python check_connection.py <server_ip>")
    print("Example: python check_connection.py 192.168.1.44\n")
    
    get_local_ip()
    
    if len(sys.argv) > 1:
        server_ip = sys.argv[1]
        success = check_connection(server_ip)
        
        if success:
            print("✓ All checks passed! You can now run:")
            print("  python pi_thin_client.py")
        else:
            print("✗ Connection issues detected. Fix the above problems first.")
            print("\nQuick fixes:")
            print("1. On server PC, run: python game_server_pyglet_complete.py")
            print("2. Windows Firewall: Allow Python through firewall")
            print("3. Check both devices on same WiFi network")
    else:
        print("Please provide server IP address as argument")
        print("Example: python check_connection.py 192.168.1.44")
