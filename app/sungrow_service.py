import json
import os
import time
from typing import Any, Dict, Optional

from pysolarcloud import Auth, Server
from pysolarcloud.plants import Plants

from .config import Settings

# Persist cache/plant-id mapping across restarts (and rebuilds) using add-on persistent storage.
STATE_FILE = os.getenv("STATE_FILE", "/data/cache.json")


def _server_from_str(s: str) -> Server:
    normalized = s.strip().lower()
    if normalized in ("europe", "eu"):
        return Server.Europe
    if normalized in ("asia", "cn", "china"):
        return Server.Asia
    if normalized in ("australia", "au"):
        return Server.Australia
    if normalized in ("northamerica", "na", "us", "usa"):
        return Server.NorthAmerica
    return Server.Europe


class SungrowService:
    """
    Sungrow iSolarCloud bridge:
    - OAuth start URL
    - OAuth callback exchanges code for tokens (persisted to /data/tokens.json)
    - Resolve plant IDs by plant name
    - Fetch realtime plant data with caching (persisted to /data/cache.json)
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        # pysolarcloud auth client
        self.auth = Auth(
            _server_from_str(settings.server),
            settings.app_key,
            settings.secret_key,
            settings.app_id,
        )
        self.plants_api = Plants(self.auth)

        self._plant_ids_by_name: Dict[str, str] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Dict[str, float] = {}

        # Restore tokens/cache from persistent storage (best effort)
        self._load_tokens()
        self._load_local_state()

    # -----------------------------
    # OAuth helpers
    # -----------------------------
    def auth_url(self) -> str:
        return self.auth.auth_url(self.settings.redirect_uri)

    async def authorize_with_code(self, code: str) -> None:
        await self.auth.async_authorize(code, self.settings.redirect_uri)
        self._save_tokens()
        await self._resolve_plants()
        self._save_local_state()

    # -----------------------------
    # Plant resolution
    # -----------------------------
    async def _resolve_plants(self) -> None:
        plants = await self.plants_api.async_get_plants()
        self._plant_ids_by_name = {p["ps_name"]: str(p["ps_id"]) for p in plants}
        self._save_local_state()

    async def get_plant_id(self, plant_name: str) -> str:
        if plant_name not in self._plant_ids_by_name:
            await self._resolve_plants()
        plant_id = self._plant_ids_by_name.get(plant_name)
        if not plant_id:
            known = sorted(self._plant_ids_by_name.keys())
            raise RuntimeError(f"Plant '{plant_name}' not found. Known: {known}")
        return plant_id

    # -----------------------------
    # Normalization helpers
    # -----------------------------
    @staticmethod
    def _compact_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
        # Keep only fields that have a value
        return {k: v for k, v in raw.items() if v and v.get("value") is not None}

    @staticmethod
    def _val(compact: Dict[str, Any], key: str) -> Optional[Any]:
        m = compact.get(key)
        return None if not m else m.get("value")

    @staticmethod
    def _unit(compact: Dict[str, Any], key: str) -> Optional[str]:
        m = compact.get(key)
        return None if not m else m.get("unit")

    def _normalize_plant_realtime(
        self,
        plant_name: str,
        plant_id: str,
        raw: Dict[str, Any],
        now: float,
    ) -> Dict[str, Any]:
        compact = self._compact_raw(raw)

        out: Dict[str, Any] = {
            "plant_name": plant_name,
            "plant_id": plant_id,
            "timestamp_unix": int(now),

            # Power (W)
            "power_w": self._val(compact, "power"),
            "power_unit": self._unit(compact, "power"),  # usually "W"

            # Some plants expose inverter-side AC power separately (W)
            "inverter_ac_power_w": self._val(compact, "inverter_ac_power"),
            "inverter_ac_power_unit": self._unit(compact, "inverter_ac_power"),

            # Energy (your account returns Wh) -> use *_wh consistently
            "daily_yield_wh": self._val(compact, "daily_yield"),
            "daily_yield_unit": self._unit(compact, "daily_yield"),  # likely "Wh"
            "total_yield_wh": self._val(compact, "total_yield"),
            "total_yield_unit": self._unit(compact, "total_yield"),  # likely "Wh"

            # Keep compact raw for debugging / extra fields
            "raw": compact,
        }

        # drop None values to keep JSON clean
        return {k: v for k, v in out.items() if v is not None}

    # -----------------------------
    # API methods
    # -----------------------------
    async def get_realtime_for_plant(self, plant_name: str) -> Dict[str, Any]:
        """
        Fetch realtime for one plant (uses cache).
        Note: main app uses get_realtime_all() for efficiency,
        but keeping this is useful for debugging.
        """
        ttl = self.settings.cache_ttl_seconds
        now = time.time()

        if plant_name in self._cache and (now - self._cache_ts.get(plant_name, 0.0)) < ttl:
            return self._cache[plant_name]

        plant_id = await self.get_plant_id(plant_name)
        data_map = await self.plants_api.async_get_realtime_data([plant_id])
        raw = data_map.get(plant_id, {})

        normalized = self._normalize_plant_realtime(plant_name, plant_id, raw, now)

        self._cache[plant_name] = normalized
        self._cache_ts[plant_name] = now
        self._save_local_state()
        return normalized

    async def get_realtime_all(self) -> Dict[str, Any]:
        """
        Fetch realtime for BOTH plants (single Sungrow API call), cached.
        This is what /realtime, /sg/realtime and /sh/realtime should use.
        """
        ttl = self.settings.cache_ttl_seconds
        now = time.time()
        cache_key = "__ALL__"

        if cache_key in self._cache and (now - self._cache_ts.get(cache_key, 0.0)) < ttl:
            return self._cache[cache_key]

        sg_id = await self.get_plant_id(self.settings.sg_plant_name)
        sh_id = await self.get_plant_id(self.settings.sh_plant_name)

        data_map = await self.plants_api.async_get_realtime_data([sg_id, sh_id])

        sg_norm = self._normalize_plant_realtime(
            self.settings.sg_plant_name, sg_id, data_map.get(sg_id, {}), now
        )
        sh_norm = self._normalize_plant_realtime(
            self.settings.sh_plant_name, sh_id, data_map.get(sh_id, {}), now
        )

        result = {
            "timestamp_unix": int(now),
            "plants": {"sg": sg_norm, "sh": sh_norm},
        }

        self._cache[cache_key] = result
        self._cache_ts[cache_key] = now
        self._save_local_state()
        return result

    # -----------------------------
    # Token persistence (OAuth)
    # -----------------------------
    def _extract_tokens(self) -> Optional[Any]:
        """
        pysolarcloud's Auth stores tokens internally.
        Attribute names can differ between versions; we try common ones.
        """
        for attr in ("token", "tokens", "_token", "_tokens"):
            if hasattr(self.auth, attr):
                return getattr(self.auth, attr)
        return None

    def _inject_tokens(self, tokens: Any) -> None:
        for attr in ("token", "tokens", "_token", "_tokens"):
            if hasattr(self.auth, attr):
                try:
                    setattr(self.auth, attr, tokens)
                    return
                except Exception:
                    continue

    def _load_tokens(self) -> None:
        try:
            with open(self.settings.token_file, "r", encoding="utf-8") as f:
                tokens = json.load(f)
            if tokens:
                self._inject_tokens(tokens)
        except Exception:
            pass

    def _save_tokens(self) -> None:
        try:
            tokens = self._extract_tokens()
            if tokens is None:
                return
            with open(self.settings.token_file, "w", encoding="utf-8") as f:
                json.dump(tokens, f, indent=2)
        except Exception:
            pass

    # -----------------------------
    # Local state (cache + plant-id mapping)
    # -----------------------------
    def _load_local_state(self) -> None:
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                obj = json.load(f)
            self._cache = obj.get("cache", {})
            self._cache_ts = obj.get("cache_ts", {})
            self._plant_ids_by_name = obj.get("plant_ids_by_name", {})
        except Exception:
            pass

    def _save_local_state(self) -> None:
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "cache": self._cache,
                        "cache_ts": self._cache_ts,
                        "plant_ids_by_name": self._plant_ids_by_name,
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass
