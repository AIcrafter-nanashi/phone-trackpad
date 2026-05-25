from dataclasses import dataclass


@dataclass
class Config:
    port: int = 8765
    sensitivity: float = 1.5
    pin_length: int = 4
    lan_only: bool = True
    scroll_speed: float = 3.0
    token_ttl_seconds: int = 3600
