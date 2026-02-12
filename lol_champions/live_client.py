"""Live Client Data API client for League of Legends.

Communicates with the in-game client at https://127.0.0.1:2999 to read
real-time player stats, items, abilities, and runes.  Only available
while a game is in progress.  No authentication required.

Uses stdlib only (urllib + ssl + json).
"""

import json
import ssl
import urllib.request
import urllib.error

BASE_URL = "https://127.0.0.1:2999/liveclientdata"

# Reusable SSL context — the game client uses a self-signed certificate.
_ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _get(endpoint: str, timeout: float = 2.0) -> dict | list:
    """GET *endpoint* and return parsed JSON."""
    url = f"{BASE_URL}/{endpoint}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as resp:
        return json.loads(resp.read().decode())


def is_game_active() -> bool:
    """Return True if a League game is currently running."""
    try:
        _get("gamestats", timeout=1.0)
        return True
    except (urllib.error.URLError, OSError):
        return False


def get_active_player() -> dict:
    """Full data for the active player (stats, abilities, runes, level).

    Returns a dict with keys: ``abilities``, ``championStats``,
    ``currentGold``, ``fullRunes``, ``level``, ``riotId``, etc.
    """
    return _get("activeplayer")


def get_player_list() -> list:
    """Scoreboard data for all 10 players.

    Each entry has: ``championName``, ``level``, ``items``, ``scores``,
    ``runes``, ``summonerSpells``, ``team``, ``isDead``, etc.
    """
    return _get("playerlist")


def get_game_stats() -> dict:
    """Game metadata: ``gameMode``, ``gameTime``, ``mapName``."""
    return _get("gamestats")


def get_active_player_name() -> str:
    """Return the active player's Riot ID (name#tag)."""
    return _get("activeplayername")
