"""Combined HTTP and WebSocket server for the phone trackpad."""

import asyncio
from http import HTTPStatus
import ipaddress
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import websockets
from websockets.exceptions import ConnectionClosed

from phone_trackpad.screen_streamer import ScreenStreamer


class TrackpadServer:
    ALLOWED_NETWORKS = tuple(
        ipaddress.ip_network(network)
        for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")
    )

    def __init__(self, config: Any, auth_manager: Any, mouse_controller: Any) -> None:
        self.config = config
        self.auth_manager = auth_manager
        self.mouse_controller = mouse_controller
        self.screen_streamer = ScreenStreamer()
        self.sessions: dict[Any, str] = {}
        self.index_path = Path(__file__).with_name("static") / "index.html"

    async def process_request(self, connection: Any, request: Any) -> Any:
        """Serve the UI and restrict requests to local network clients."""
        request_path = urlsplit(request.path).path

        if self.config.lan_only and not self._is_lan_client(connection):
            return self._http_response(
                connection, HTTPStatus.FORBIDDEN, "LAN access only.\n"
            )

        if request.headers.get("Upgrade", "").lower() == "websocket":
            if request_path in ("/", "/ws"):
                return None
            return self._http_response(
                connection, HTTPStatus.NOT_FOUND, "WebSocket endpoint not found.\n"
            )

        if request_path == "/":
            try:
                body = self.index_path.read_text(encoding="utf-8")
            except OSError:
                return self._http_response(
                    connection, HTTPStatus.INTERNAL_SERVER_ERROR, "UI not available.\n"
                )
            return self._http_response(
                connection, HTTPStatus.OK, body, "text/html; charset=utf-8"
            )

        return self._http_response(connection, HTTPStatus.NOT_FOUND, "Not found.\n")

    @staticmethod
    def _http_response(
        connection: Any,
        status: HTTPStatus,
        body: str,
        content_type: str = "text/plain; charset=utf-8",
    ) -> Any:
        response = connection.respond(status, body)
        del response.headers["Content-Type"]
        response.headers["Content-Type"] = content_type
        response.headers["Cache-Control"] = "no-store"
        return response

    async def handler(self, websocket: Any) -> None:
        if self.config.lan_only and not self._is_lan_client(websocket):
            await self._send(websocket, {"type": "error", "message": "LAN access only"})
            await websocket.close(code=1008, reason="LAN access only")
            return

        try:
            async for raw_message in websocket:
                try:
                    message = json.loads(raw_message)
                except (json.JSONDecodeError, TypeError):
                    await self._error(websocket, "Invalid JSON")
                    continue

                if not isinstance(message, dict):
                    await self._error(websocket, "Invalid message")
                    continue

                if websocket not in self.sessions:
                    await self._handle_auth(websocket, message)
                    continue

                await self._handle_operation(websocket, message)
        except ConnectionClosed:
            pass
        finally:
            self.screen_streamer.unsubscribe(websocket)
            token = self.sessions.pop(websocket, None)
            if token is not None:
                self.auth_manager.revoke_token(token)
                await self.broadcast_status()

    async def _handle_auth(self, websocket: Any, message: dict[str, Any]) -> None:
        if message.get("type") != "auth":
            await self._error(websocket, "Unauthorized")
            return

        client_ip = self._client_ip(websocket)
        if self.auth_manager.is_locked(client_ip):
            await self._send(
                websocket,
                {"type": "auth_result", "success": False, "message": "Try again later"},
            )
            return

        if not self.auth_manager.verify_pin(str(message.get("pin", ""))):
            self.auth_manager.record_failed_attempt(client_ip)
            error = (
                "Try again later"
                if self.auth_manager.is_locked(client_ip)
                else "Invalid PIN"
            )
            await self._send(
                websocket, {"type": "auth_result", "success": False, "message": error}
            )
            return

        self.auth_manager.record_success(client_ip)
        token = self.auth_manager.issue_token()
        self.sessions[websocket] = token
        await self._send(
            websocket, {"type": "auth_result", "success": True, "token": token}
        )
        await self.broadcast_status()

    async def _handle_operation(self, websocket: Any, message: dict[str, Any]) -> None:
        expected_token = self.sessions.get(websocket)
        token = message.get("token")
        if token != expected_token or not self.auth_manager.verify_token(token):
            old_token = self.sessions.pop(websocket, None)
            if old_token is not None:
                self.auth_manager.revoke_token(old_token)
            await self._send(
                websocket,
                {
                    "type": "error",
                    "message": "Session expired. Please re-authenticate.",
                    "reauth": True,
                },
            )
            await self.broadcast_status()
            return

        operation = message.get("type")
        try:
            if operation == "move":
                dx = self._number(message.get("dx"), limit=500.0)
                dy = self._number(message.get("dy"), limit=500.0)
                self.mouse_controller.move(dx, dy)
            elif operation == "left_click":
                self.mouse_controller.left_click()
            elif operation == "right_click":
                self.mouse_controller.right_click()
            elif operation == "scroll":
                dy = self._number(message.get("dy"), limit=100.0)
                self.mouse_controller.scroll(dy)
            elif operation == "type":
                text = message.get("text")
                if not isinstance(text, str) or len(text) > 10000:
                    raise ValueError("Invalid text")
                self.mouse_controller.type_text(text)
            elif operation == "key_press":
                key = message.get("key")
                if not isinstance(key, str):
                    raise ValueError("Invalid key")
                self.mouse_controller.key_press(key)
            elif operation == "set_sensitivity":
                value = self._number(message.get("value"), limit=10.0)
                self.mouse_controller.sensitivity = max(0.1, value)
            elif operation == "start_stream":
                if self.screen_streamer.available:
                    fps = self._number(message.get("fps", 5), limit=60.0)
                    scale = self._number(message.get("scale", 0.35), limit=1.0)
                    quality = int(self._number(message.get("quality", 25), limit=80.0))
                    self.screen_streamer.fps = max(1.0, fps)
                    self.screen_streamer.scale = max(0.1, scale)
                    self.screen_streamer.quality = max(10, quality)
                    self.screen_streamer.subscribe(websocket)
                    print(
                        f"[Screen] Streaming started — {self._client_ip(websocket)} "
                        f"(fps={self.screen_streamer.fps:.0f} scale={self.screen_streamer.scale} "
                        f"quality={self.screen_streamer.quality})"
                    )
                else:
                    await self._send(websocket, {
                        "type": "error",
                        "message": "Screen capture unavailable. Run: pip install mss",
                    })
            elif operation == "stop_stream":
                self.screen_streamer.unsubscribe(websocket)
                print(f"[Screen] Streaming stopped — {self._client_ip(websocket)}")
            elif operation == "ping":
                await self._send(websocket, {"type": "pong"})
            else:
                await self._error(websocket, "Unknown operation")
        except (TypeError, ValueError):
            await self._error(websocket, "Invalid payload")
        except Exception:
            await self._error(websocket, "Operation failed")

    async def broadcast_status(self) -> None:
        message = {
            "type": "status",
            "connected": bool(self.sessions),
            "client_count": len(self.sessions),
        }
        disconnected: list[Any] = []
        for websocket in list(self.sessions):
            try:
                await self._send(websocket, message)
            except ConnectionClosed:
                disconnected.append(websocket)
        for websocket in disconnected:
            token = self.sessions.pop(websocket, None)
            if token is not None:
                self.auth_manager.revoke_token(token)

    def _is_lan_client(self, websocket: Any) -> bool:
        remote = getattr(websocket, "remote_address", None)
        if not remote:
            return False
        host = remote[0] if isinstance(remote, tuple) else str(remote)
        return self._is_lan_address(host)

    @classmethod
    def _is_lan_address(cls, ip: str) -> bool:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return False
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if address.is_loopback:
            return True
        return any(address in network for network in cls.ALLOWED_NETWORKS)

    @staticmethod
    def _client_ip(websocket: Any) -> str:
        remote = getattr(websocket, "remote_address", None)
        if not remote:
            return ""
        return remote[0] if isinstance(remote, tuple) else str(remote)

    @staticmethod
    def _number(value: Any, limit: float) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite input")
        return max(-limit, min(limit, number))

    @staticmethod
    async def _send(websocket: Any, message: dict[str, Any]) -> None:
        await websocket.send(json.dumps(message, ensure_ascii=False))

    async def _error(self, websocket: Any, message: str) -> None:
        await self._send(websocket, {"type": "error", "message": message})

    async def start(self) -> None:
        async with websockets.serve(
            self.handler,
            "0.0.0.0",
            self.config.port,
            process_request=self.process_request,
        ):
            await asyncio.Future()
