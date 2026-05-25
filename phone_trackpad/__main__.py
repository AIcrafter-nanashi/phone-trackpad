"""Command-line entry point for Phone Trackpad."""

import argparse
import asyncio
import sys

from phone_trackpad.auth import AuthManager
from phone_trackpad.config import Config
from phone_trackpad.mouse_controller import MouseController
from phone_trackpad.qr_generator import generate_and_display_qr, get_lan_ips
from phone_trackpad.server import TrackpadServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use an iPhone as a Windows trackpad.")
    parser.add_argument("--port", type=int, default=8765, help="HTTP/WebSocket port")
    parser.add_argument(
        "--sensitivity", type=float, default=1.5, help="Pointer movement multiplier"
    )
    parser.add_argument("--no-qr", action="store_true", help="Do not display a QR code")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(port=args.port, sensitivity=args.sensitivity)
    auth_manager = AuthManager(config.pin_length, config.token_ttl_seconds)
    mouse_controller = MouseController(config.sensitivity, config.scroll_speed)
    server = TrackpadServer(config, auth_manager, mouse_controller)

    urls = [f"http://{ip}:{config.port}/" for ip in get_lan_ips()]
    print("Phone Trackpad is available at:")
    for url in urls:
        print(f"  {url}")
    print(f"PIN: {auth_manager.get_pin()}")
    print("Keep this terminal open while controlling the computer.")
    if not args.no_qr:
        generate_and_display_qr(urls[0])

    if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nPhone Trackpad stopped.")


if __name__ == "__main__":
    main()
