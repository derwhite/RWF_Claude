"""
Client fuer die Raider.io "Live Tracking - Boss Attempts" API.

https://raider.io/api#/Live%20Tracking%20-%20Raiding/getApiV1LivetrackingGuildBossattempts

Reales Antwortformat (Stand 08/2026), ermittelt anhand einer echten
API-Response:

{
  "guild": {...},
  "raid": {"name": "The Venomous Abyss", "slug": "the-venomous-abyss", ...},
  "boss": {"name": "The Coiled Altar", "slug": "the-coiled-altar", "ordinal": 6, ...},
  "attempts": [
    {
      "pullStartedAt": "2026-08-26T21:55:20.734Z",
      "overallPercent": 90.45,
      "isSuccess": false,
      "encounter": {"durationMs": 48477}
    },
    ...
  ]
}

Wichtig: Es gibt KEINE Pull-Nummer im Datensatz. Die Nummerierung wird
hier anhand der chronologischen Reihenfolge (pullStartedAt) vergeben.
"""
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

import phases
from config import (
    RAIDERIO_API_KEY,
    RAIDERIO_BASE_URL,
    RAID_SLUG,
    DIFFICULTY,
    BOSS_SLUG,
    PERIOD,
    GUILDS,
    CACHE_TTL_SECONDS,
    TIMEZONE,
)


class RaiderIOError(Exception):
    """Fehler beim Abruf oder Verarbeiten der Raider.io API-Antwort."""


try:
    _LOCAL_TZ = ZoneInfo(TIMEZONE)
except Exception:
    print(f"WARNUNG: Zeitzone '{TIMEZONE}' konnte nicht geladen werden, nutze UTC. "
          f"Falls dies unter Windows passiert: 'pip install tzdata' (siehe requirements.txt).")
    _LOCAL_TZ = timezone.utc


# ---------------------------------------------------------------------------
# Sehr einfacher In-Memory-Cache (Prozess-lokal, kein Redis noetig)
# ---------------------------------------------------------------------------
_cache: dict = {}

# Separater, langlebiger Cache nur fuer Gilden-Logos (aendert sich praktisch
# nie waehrend eines Raid-Tiers). Wird bei jedem erfolgreichen API-Call
# nebenbei befuellt, damit z.B. die Navigation auch ohne eigenen API-Call
# pro Tab ein Icon zeigen kann, sobald eine Gilde einmal geladen wurde.
_guild_logo_cache: dict = {}


def _cache_get(key):
    entry = _cache.get(key)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        return None
    return data


def _cache_set(key, data):
    _cache[key] = (time.time(), data)


def fetch_boss_attempts_raw(guild_key: str) -> dict:
    """Ruft die rohen Boss-Attempt-Daten fuer eine Gilde von der Raider.io API ab."""
    if guild_key not in GUILDS:
        raise RaiderIOError(f"Unbekannte Gilde: {guild_key}")

    cache_key = f"attempts:{guild_key}:{BOSS_SLUG}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    guild_cfg = GUILDS[guild_key]
    params = {
        "raid": RAID_SLUG,
        "boss": BOSS_SLUG,
        "difficulty": DIFFICULTY,
        "region": guild_cfg["region"],
        "realm": guild_cfg["realm"],
        "guild": guild_cfg["guild"],
        "period": PERIOD,
    }
    if RAIDERIO_API_KEY:
        params["access_key"] = RAIDERIO_API_KEY

    url = f"{RAIDERIO_BASE_URL}/live-tracking/guild/boss-attempts"

    try:
        resp = requests.get(url, params=params, timeout=10)
    except requests.RequestException as exc:
        raise RaiderIOError(f"Netzwerkfehler beim Aufruf der Raider.io API: {exc}") from exc

    if resp.status_code == 429:
        raise RaiderIOError("Raider.io API Rate-Limit erreicht (HTTP 429). Bitte kurz warten.")
    if resp.status_code in (401, 403):
        raise RaiderIOError(
            f"Raider.io API hat den Zugriff verweigert (HTTP {resp.status_code}). "
            "API-Key in der .env (RAIDERIO_API_KEY) pruefen."
        )
    if resp.status_code == 404:
        raise RaiderIOError(
            "Raider.io API antwortete mit 404 - pruefe RAID_SLUG/BOSS_SLUG sowie "
            "guild/realm/region in config.py."
        )
    if resp.status_code != 200:
        raise RaiderIOError(
            f"Raider.io API antwortete mit HTTP {resp.status_code}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise RaiderIOError("Antwort der Raider.io API war kein gueltiges JSON.") from exc

    _cache_set(cache_key, data)

    if isinstance(data, dict):
        logo = (data.get("guild") or {}).get("logo")
        if logo:
            _guild_logo_cache[guild_key] = logo

    return data


def get_guild_logo(guild_key: str):
    """Liefert die zuletzt bekannte Logo-URL einer Gilde, falls schon einmal geladen."""
    return _guild_logo_cache.get(guild_key)


def _format_timestamp(value):
    """Formatiert Unix-Timestamps (s oder ms) oder ISO-Strings (UTC) in die
    konfigurierte lokale Zeitzone (TIMEZONE, siehe config.py) als dd.mm.yyyy HH:MM."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            ts = value / 1000 if value > 1e12 else value
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        elif isinstance(value, str):
            v = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            return str(value)
        dt_local = dt.astimezone(_LOCAL_TZ)
        return dt_local.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError, OSError):
        pass
    return str(value)


def _format_duration(seconds):
    """Formatiert eine Sekundenzahl als MM:SS."""
    if seconds is None:
        return None
    seconds = int(round(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"


def _parse_sort_ts(value):
    """Liefert einen sortierbaren Zeit-Wert fuer die chronologische Sortierung."""
    if value is None:
        return 0
    try:
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            v = value.replace("Z", "+00:00")
            return datetime.fromisoformat(v).timestamp()
    except (ValueError, TypeError):
        pass
    return 0


def normalize_attempt(raw: dict, pull_number: int) -> dict:
    """Bildet ein rohes Attempt-Objekt der API auf ein einheitliches Format ab."""
    encounter = raw.get("encounter") or {}
    duration_ms = encounter.get("durationMs")

    normalized = {
        "pull_number": pull_number,
        "percent": raw.get("overallPercent"),
        "is_kill": bool(raw.get("isSuccess")),
        "duration_seconds": round(duration_ms / 1000) if duration_ms is not None else None,
        "duration": _format_duration(duration_ms / 1000) if duration_ms is not None else None,
        "recorded_at": _format_timestamp(raw.get("pullStartedAt")),
        # wipeReason ist aktuell kein Teil der beobachteten API-Antwort,
        # bleibt hier als Fallback falls Raider.io das Feld ergaenzt.
        "wipe_reason": raw.get("wipeReason"),
    }
    if normalized["is_kill"]:
        normalized["percent"] = 0.0
    normalized["raw"] = raw
    return normalized


def _extract_attempts_list(raw_response) -> list:
    """Die API liefert die Liste unter dem Key 'attempts'."""
    if isinstance(raw_response, list):
        return raw_response
    if isinstance(raw_response, dict):
        for key in ("attempts", "pulls", "bossAttempts", "data", "results"):
            value = raw_response.get(key)
            if isinstance(value, list):
                return value
    return []


def get_boss_meta(raw_response: dict) -> dict:
    """Liest Bossname/Raidname/encounterId/Gildenlogo aus der Antwort."""
    if not isinstance(raw_response, dict):
        return {}
    boss = raw_response.get("boss") or {}
    raid = raw_response.get("raid") or {}
    guild = raw_response.get("guild") or {}
    return {
        "boss_name": boss.get("name"),
        "boss_ordinal": boss.get("ordinal"),
        "raid_name": raid.get("name"),
        "encounter_id": boss.get("encounterId"),
        "guild_logo": guild.get("logo"),
    }


def get_attempts(guild_key: str, mode: str, n: int):
    """
    Holt und normalisiert die Boss-Attempts einer Gilde.

    Rueckgabe: (attempts, meta)
      - attempts: Liste normalisierter Pulls, sortiert nach `mode`
      - meta: Zusatzinfos (Bossname, Raidname) fuer die Anzeige

    mode == "last": sortiert nach Pull-Nummer absteigend (neueste zuerst)
    mode == "best": sortiert nach Boss-HP% aufsteigend (beste/niedrigste zuerst)
    """
    raw_response = fetch_boss_attempts_raw(guild_key)
    raw_attempts = _extract_attempts_list(raw_response)

    # Pull-Nummer wird von der API nicht mitgeliefert -> anhand der
    # chronologischen Reihenfolge (pullStartedAt) vergeben.
    raw_attempts_sorted = sorted(raw_attempts, key=lambda a: _parse_sort_ts(a.get("pullStartedAt")))
    attempts = [normalize_attempt(a, pull_number=i + 1) for i, a in enumerate(raw_attempts_sorted)]

    meta = get_boss_meta(raw_response)
    encounter_id = meta.get("encounter_id")
    for a in attempts:
        phase_info = phases.get_phase(encounter_id, a["percent"], a["duration_seconds"])
        a["phase"] = phase_info["label"]
        a["phase_percent"] = phase_info["percent"]

    if mode == "best":
        attempts.sort(
            key=lambda a: (
                a["percent"] if a["percent"] is not None else 100.0,
                -(a["pull_number"] or 0),
            )
        )
    else:  # "last"
        attempts.sort(key=lambda a: (a["pull_number"] or 0), reverse=True)

    return attempts[:n], meta
