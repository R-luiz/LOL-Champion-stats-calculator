"""Data Dragon static data fetcher for League of Legends.

Downloads champion base stats and item stats from Riot's CDN
(https://ddragon.leagueoflegends.com) and caches them locally.
Used to estimate enemy target stats from their champion + level + items.

Uses stdlib only (urllib + json + pathlib).
"""

import json
import os
import ssl
import urllib.request
from pathlib import Path

from .target import Target

DDRAGON_BASE = "https://ddragon.leagueoflegends.com"
CACHE_DIR = Path.home() / ".cache" / "lol_data"

_ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
_ssl_ctx.check_hostname = True
_ssl_ctx.verify_mode = ssl.CERT_REQUIRED
_ssl_ctx.load_default_certs()


def _fetch_json(url: str, timeout: float = 10.0):
    """GET *url* and return parsed JSON."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as resp:
        return json.loads(resp.read().decode())


def _stat_at_level(base: float, growth: float, level: int) -> float:
    """Compute a champion stat at *level* using the LoL scaling formula.

    Formula: base + growth * (level - 1) * (0.7025 + 0.0175 * (level - 1))
    """
    if level <= 1:
        return base
    n = level - 1
    return base + growth * n * (0.7025 + 0.0175 * n)


class DataDragon:
    """Fetches and caches champion/item static data from Data Dragon.

    Args:
        version: Game version string (e.g. "16.3.1").  If None, the
            latest version is fetched automatically.
    """

    def __init__(self, version: str | None = None):
        if version is None:
            versions = _fetch_json(f"{DDRAGON_BASE}/api/versions.json")
            version = versions[0]
        self.version = version
        self._cache_path = CACHE_DIR / version
        self._champions: dict = {}
        self._items: dict = {}
        self._load()

    def _load(self):
        """Load data from cache or fetch from CDN."""
        champ_file = self._cache_path / "champion.json"
        item_file = self._cache_path / "item.json"

        if champ_file.exists() and item_file.exists():
            with open(champ_file) as f:
                self._champions = json.load(f)
            with open(item_file) as f:
                self._items = json.load(f)
            return

        # Fetch from CDN
        base = f"{DDRAGON_BASE}/cdn/{self.version}/data/en_US"
        champ_data = _fetch_json(f"{base}/champion.json")
        item_data = _fetch_json(f"{base}/item.json")

        self._champions = champ_data["data"]
        self._items = item_data["data"]

        # Cache to disk
        self._cache_path.mkdir(parents=True, exist_ok=True)
        with open(champ_file, "w") as f:
            json.dump(self._champions, f)
        with open(item_file, "w") as f:
            json.dump(self._items, f)

    def champion_stats_at_level(self, name: str, level: int) -> dict:
        """Compute champion HP, armor, MR, AD at *level*.

        Args:
            name: Champion name as it appears in-game (e.g. "Fiora", "Darius").
                  Case-insensitive — matched against ddragon keys.
            level: Champion level (1-18).

        Returns:
            Dict with keys: hp, armor, mr, ad.
        """
        champ = self._find_champion(name)
        if champ is None:
            raise ValueError(f"Champion '{name}' not found in Data Dragon")
        s = champ["stats"]
        return {
            "hp": _stat_at_level(s["hp"], s["hpperlevel"], level),
            "armor": _stat_at_level(s["armor"], s["armorperlevel"], level),
            "mr": _stat_at_level(s["spellblock"], s["spellblockperlevel"], level),
            "ad": _stat_at_level(s["attackdamage"], s["attackdamageperlevel"], level),
        }

    def item_stats(self, item_id: int) -> dict:
        """Return stat bonuses for an item.

        Args:
            item_id: Riot item ID (e.g. 3161 for Spear of Shojin).

        Returns:
            Dict with keys: hp, armor, mr, ad, ap, attack_speed_pct.
            Missing stats default to 0.
        """
        item = self._items.get(str(item_id))
        if item is None:
            return {"hp": 0, "armor": 0, "mr": 0, "ad": 0, "ap": 0,
                    "attack_speed_pct": 0}
        stats = item.get("stats", {})
        return {
            "hp": stats.get("FlatHPPoolMod", 0),
            "armor": stats.get("FlatArmorMod", 0),
            "mr": stats.get("FlatSpellBlockMod", 0),
            "ad": stats.get("FlatPhysicalDamageMod", 0),
            "ap": stats.get("FlatMagicDamageMod", 0),
            "attack_speed_pct": stats.get("PercentAttackSpeedMod", 0) * 100,
        }

    def item_name(self, item_id: int) -> str:
        """Return the display name for an item ID, or '?' if unknown."""
        item = self._items.get(str(item_id))
        return item["name"] if item else "?"

    def estimate_target(self, champion_name: str, level: int,
                        item_ids: list[int]) -> Target:
        """Estimate a Target's defensive stats from champion + level + items.

        Returns base stats at level + item stat bonuses only.
        Rune shard HP is handled separately by live.py calibration.

        Args:
            champion_name: Enemy champion name.
            level: Enemy champion level.
            item_ids: List of item IDs from the scoreboard.

        Returns:
            A Target with estimated armor, mr, max_hp.
        """
        base = self.champion_stats_at_level(champion_name, level)
        bonus_hp = 0.0
        bonus_armor = 0.0
        bonus_mr = 0.0
        for iid in item_ids:
            s = self.item_stats(iid)
            bonus_hp += s["hp"]
            bonus_armor += s["armor"]
            bonus_mr += s["mr"]
        return Target(
            max_hp=base["hp"] + bonus_hp,
            armor=base["armor"] + bonus_armor,
            mr=base["mr"] + bonus_mr,
        )

    def _find_champion(self, name: str):
        """Find champion data by name (case-insensitive)."""
        # ddragon keys are like "Fiora", "Darius", "MasterYi"
        # Try exact key match first
        if name in self._champions:
            return self._champions[name]
        # Case-insensitive search on the 'name' field
        lower = name.lower()
        for key, data in self._champions.items():
            if key.lower() == lower or data.get("name", "").lower() == lower:
                return data
        return None
