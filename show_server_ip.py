import socket
import subprocess
import platform

def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return f"Error: {e}"

def get_all_ips():
    """Get all network interfaces and their IPs."""
    ips = []
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            output = result.stdout
            
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if 'IPv4 Address' in line or 'IPv4' in line:
                    ip = line.split(':')[-1].strip()
                    if ip and not ip.startswith('169.'):
                        adapter_name = ""
                        for j in range(i-1, max(0, i-10), -1):
                            if 'adapter' in lines[j].lower():
                                adapter_name = lines[j].strip().rstrip(':')
                                break
                        ips.append((adapter_name, ip))
        else:
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
            output = result.stdout
            
            current_interface = ""
            for line in output.split('\n'):
                if line and not line.startswith(' '):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        current_interface = parts[1].strip()
                elif 'inet ' in line and 'inet6' not in line:
                    ip = line.strip().split()[1].split('/')[0]
                    if not ip.startswith('127.'):
                        ips.append((current_interface, ip))
    except Exception as e:
        ips.append(("Error", str(e)))
    
    return ips

def main():
    print("\n" + "="*70)
    print(" "*20 + "ARPi2 Server Network Information")
    print("="*70)
    
    print("\n📡 PRIMARY IP ADDRESS (use this in config.py):")
    primary_ip = get_local_ip()
    print(f"   {primary_ip}")
    
    print(f"\n🔌 SERVER PORT: 8765")
    
    print(f"\n🌐 WEBSOCKET URL FOR RASPBERRY PI:")
    print(f"   ws://{primary_ip}:8765")
    
    print("\n" + "-"*70)
    print("\n💻 ALL NETWORK INTERFACES:")
    all_ips = get_all_ips()
    if all_ips:
        for adapter, ip in all_ips:
            print(f"   {adapter}: {ip}")
    else:
        print("   No network interfaces found")
    
    print("\n" + "="*70)
    print("\n📝 CONFIGURATION STEPS:")
    print(f"\n1. Edit config.py on BOTH server and Raspberry Pi:")
    print(f'   SERVER_IP = "{primary_ip}"')
    print(f"\n2. Setup firewall (Windows only):")
    print(f"   - Run 'setup_firewall.bat' as administrator")
    print(f"   - OR manually allow port 8765 in Windows Firewall")
    print(f"\n3. On Raspberry Pi, test connection:")
    print(f"   python check_connection.py {primary_ip}")
    print(f"\n4. Start server:")
    print(f"   python game_server_full.py")
    print(f"\n5. On Pi, start client:")
    print(f"   python pi_thin_client.py")
    
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
