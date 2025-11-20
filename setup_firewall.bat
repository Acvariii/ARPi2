@echo off
echo ================================================
echo ARPi2 Server - Windows Firewall Configuration
echo ================================================
echo.
echo This script will add a firewall rule to allow
echo incoming connections on port 8765 for the game server.
echo.
echo You need to run this as Administrator!
echo.
pause

echo.
echo Adding firewall rule...
netsh advfirewall firewall add rule name="ARPi2 Game Server" dir=in action=allow protocol=TCP localport=8765

if %errorlevel% == 0 (
    echo.
    echo ================================================
    echo SUCCESS! Firewall rule added.
    echo ================================================
    echo.
    echo Port 8765 is now open for incoming connections.
    echo You can now run: python game_server_full.py
    echo.
) else (
    echo.
    echo ================================================
    echo FAILED - Run this script as Administrator
    echo ================================================
    echo.
    echo Right-click this file and select "Run as administrator"
    echo.
)

pause
