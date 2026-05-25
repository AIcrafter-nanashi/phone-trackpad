# Phone Trackpad

Phone Trackpad turns an iPhone browser into a touchpad and text-input remote
for a Windows computer on the same local network. The desktop process serves a
mobile web UI and receives authenticated WebSocket control messages on one
port.

## Features

- One-finger pointer movement and tap-to-left-click.
- Two-finger scrolling and two-finger tap-to-right-click.
- Dedicated left and right click buttons.
- Text entry pasted through the Windows clipboard, including Japanese text.
- Random PIN authentication, one-hour session tokens, and per-client-IP
  lockout after repeated PIN failures.
- QR-code startup display and automatic browser reconnection.
- RFC1918 local-network access restriction by default.

## Requirements

- Windows 10 or later with Python 3.9 or later.
- An iPhone and the Windows PC connected to the same trusted Wi-Fi network.
- A desktop session where `pyautogui` can control the mouse and keyboard.
- `websockets` 14.0 or later (installed by the commands below).

## Installation

From this source directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

On some Windows setups, `pyautogui` may also require its Windows helper
dependencies such as `pygetwindow`; installing through `pip` normally resolves
them automatically.

## Start The Server

```powershell
phone-trackpad
# or:
python -m phone_trackpad --port 8765 --sensitivity 2.0
```

Use `--no-qr` if an image viewer must not be opened. At startup the terminal
prints each detected local URL and a four-digit PIN. Scan the QR code or open
one of those URLs on the iPhone, then enter the displayed PIN.

## Windows Firewall

Run PowerShell as Administrator and allow inbound TCP access only from the
local subnet on a Private network profile. Adjust the port if you start the
server with another `--port` value.

```powershell
New-NetFirewallRule -DisplayName "Phone Trackpad (Private LAN)" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 `
  -Profile Private -RemoteAddress LocalSubnet
```

To remove this rule later:

```powershell
Remove-NetFirewallRule -DisplayName "Phone Trackpad (Private LAN)"
```

## Screen Description

The first screen contains a PIN field and Connect button. After authentication,
the screen changes to a dark full-height trackpad area with a connection dot at
the top, a Keyboard toggle, and Left Click and Right Click buttons below the
pad. Opening Keyboard reveals a text box and Send button.

## Controls

| Gesture or control | Result |
| --- | --- |
| Drag one finger on the pad | Move pointer |
| Tap one finger on the pad | Left click |
| Drag two fingers on the pad | Scroll |
| Tap two fingers on the pad | Right click |
| Keyboard / Send | Paste entered text on the PC |

## Security Notes

- Use this server only on a trusted private network. It uses HTTP/WebSocket
  without TLS; the PIN and control traffic aren't encrypted on the LAN.
- HTTP UI and WebSocket connections are limited to RFC1918 private IP ranges
  and loopback addresses, but this is not a substitute for a firewall.
- Five failed PIN attempts from one client IP lock that IP's authentication for
  60 seconds. IPv4-mapped IPv6 addresses are treated as their IPv4 address.
- Authenticated session tokens expire after 3600 seconds and are revoked when
  their WebSocket connection ends.
- `pyautogui.FAILSAFE` is disabled to support edge-of-screen trackpad control.
  Stop the process with `Ctrl+C` in its terminal when remote control should end.
- `pyautogui.PAUSE` is set to `0.0` so each remote input event is applied
  without PyAutoGUI's default delay.
- Text input copies phone-provided content to the PC clipboard and pastes it
  into whichever desktop application currently has focus.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
