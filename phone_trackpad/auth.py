"""PIN authentication and session token management."""

import hmac
import secrets
import time
import uuid
from typing import TypedDict


class AttemptState(TypedDict):
    count: int
    locked_until: float


class AuthManager:
    MAX_FAILED_ATTEMPTS = 5
    LOCK_SECONDS = 60

    def __init__(self, pin_length: int = 4, token_ttl_seconds: int = 3600) -> None:
        self._pin = self.generate_pin(pin_length)
        self.token_ttl_seconds = token_ttl_seconds
        self._tokens: dict[str, float] = {}
        self._ip_attempts: dict[str, AttemptState] = {}

    @staticmethod
    def generate_pin(length: int = 4) -> str:
        if length <= 0:
            raise ValueError("PIN length must be positive")
        return "".join(secrets.choice("0123456789") for _ in range(length))

    def verify_pin(self, input_pin: str) -> bool:
        return hmac.compare_digest(self._pin, str(input_pin))

    def get_pin(self) -> str:
        return self._pin

    def issue_token(self) -> str:
        self.cleanup_expired_tokens()
        token = str(uuid.uuid4())
        self._tokens[token] = time.monotonic() + self.token_ttl_seconds
        return token

    def verify_token(self, token: str) -> bool:
        if not isinstance(token, str):
            return False
        expires_at = self._tokens.get(token)
        if expires_at is None:
            return False
        if time.monotonic() >= expires_at:
            self._tokens.pop(token, None)
            return False
        return True

    def revoke_token(self, token: str) -> None:
        if isinstance(token, str):
            self._tokens.pop(token, None)

    def cleanup_expired_tokens(self) -> None:
        now = time.monotonic()
        expired = [
            token for token, expires_at in self._tokens.items() if now >= expires_at
        ]
        for token in expired:
            self._tokens.pop(token, None)

    @staticmethod
    def _normalize_ip(client_ip: str) -> str:
        if client_ip.lower().startswith("::ffff:"):
            return client_ip[7:]
        return client_ip

    def is_locked(self, client_ip: str) -> bool:
        client_ip = self._normalize_ip(client_ip)
        state = self._ip_attempts.get(client_ip)
        if state is None:
            return False
        locked_until = float(state["locked_until"])
        if locked_until and time.monotonic() < locked_until:
            return True
        if locked_until:
            self._ip_attempts.pop(client_ip, None)
        return False

    def record_failed_attempt(self, client_ip: str) -> None:
        client_ip = self._normalize_ip(client_ip)
        state = self._ip_attempts.setdefault(
            client_ip, {"count": 0, "locked_until": 0.0}
        )
        state["count"] += 1
        if state["count"] >= self.MAX_FAILED_ATTEMPTS:
            state["locked_until"] = time.monotonic() + self.LOCK_SECONDS

    def record_success(self, client_ip: str) -> None:
        self._ip_attempts.pop(self._normalize_ip(client_ip), None)
