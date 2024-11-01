from dataclasses import dataclass


@dataclass
class Auth:
    discord_id: int
    token: str
    lichess_username: str
