"""
Client fuer die Raider.io "Live Tracking - Boss Attempts" API.

https://raider.io/api#/Live%20Tracking%20-%20Raiding/getApiV1LivetrackingGuildBossattempts
"""
import time
from datetime import datetime, timezone

import requests

from config import (
    RAIDERIO_API_KEY,
    RAIDERIO_BASE_URL,
    RAID_SLUG,
    DIFFICULTY,
    BOSS_SLUG,
    GUILDS,
    CACHE_TTL_SECONDS,
)


class RaiderIOError(Exception):
    """Fehler beim Abruf oder Verarbeiten der Raider.io API-Antwort."""


# ---------------------------------------------------------------------------
# Sehr einfacher In-Memory-Cache (Prozess-lokal, kein Redis noetig)
# ---------------------------------------------------------------------------
_cache: dict = {}


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

    if not BOSS_SLUG:
        raise RaiderIOError(
            "Kein BOSS_SLUG konfiguriert. Bitte BOSS_SLUG in der .env setzen "
            "(siehe README.md, Abschnitt 'Boss-Slug herausfinden')."
        )

    cache_key = f"attempts:{guild_key}:{BOSS_SLUG}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    guild_cfg = GUILDS[guild_key]
    params = {
        "raidSlug": RAID_SLUG,
        "bossSlug": BOSS_SLUG,
        "difficulty": DIFFICULTY,
        "region": guild_cfg["region"],
        "realm": guild_cfg["realm"],
        "guild": guild_cfg["guild"],
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
            "Raider.io API antwortete mit 404 - pruefe RAID_SLUG, BOSS_SLUG, "
            "sowie guild/realm/region in config.py."
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
    return data


# ---------------------------------------------------------------------------
# WICHTIG - Feld-Mapping
# ---------------------------------------------------------------------------
# Raider.io stellt fuer die Live-Tracking-Endpunkte keine maschinenlesbare
# Swagger-/OpenAPI-Datei bereit (die Doku-Seite ist eine JS-App). Die unten
# gelisteten Kandidaten-Keys decken die in der Praxis gebraeuchlichen
# Namensvarianten ab. Falls die Tabelle nach dem ersten Start leere Werte
# ("-") zeigt:
#
#   1. In der .env DEBUG_ROUTES=true setzen und den Server neu starten
#   2. /debug/<guild-key> aufrufen (z.B. /debug/liquid) -> zeigt rohes JSON
#   3. Die tatsaechlichen Feldnamen unten in _CANDIDATE_KEYS ergaenzen
#
# Das ist der einzige Ort im Code, der bei abweichenden Feldnamen angepasst
# werden muss.
_CANDIDATE_KEYS = {
    "pull_number": ["pullNumber", "pull_number", "attemptNumber", "attempt_number", "number"],
    "percent": [
        "healthPercent",
        "health_percent",
        "percent",
        "bestPercent",
        "best_percent",
        "pullPercent",
        "bossPercent",
    ],
    "is_kill": ["isKill", "is_kill", "kill", "isDefeated", "defeated"],
    "duration_seconds": ["durationSeconds", "duration_seconds", "duration", "fightLength", "length"],
    "recorded_at": [
        "recordedAt",
        "recorded_at",
        "pulledAt",
        "pulled_at",
        "createdAt",
        "created_at",
        "timestamp",
        "startedAt",
    ],
    "wipe_reason": ["wipeReason", "wipe_reason", "deathReason", "killReason"],
}


def _first_present(raw: dict, keys: list):
    for k in keys:
        if k in raw and raw[k] is not None:
            return raw[k]
    return None


def _format_timestamp(value):
    """Formatiert Unix-Timestamps (s oder ms) oder ISO-Strings als dd.mm.yyyy HH:MM."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            ts = value / 1000 if value > 1e12 else value
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%d.%m.%Y %H:%M")
        if isinstance(value, str):
            v = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v)
            return dt.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError, OSError):
        pass
    return str(value)


def normalize_attempt(raw: dict) -> dict:
    """Bildet ein rohes Attempt-Objekt der API auf ein einheitliches Format ab."""
    normalized = {
        "pull_number": _first_present(raw, _CANDIDATE_KEYS["pull_number"]),
        "percent": _first_present(raw, _CANDIDATE_KEYS["percent"]),
        "is_kill": bool(_first_present(raw, _CANDIDATE_KEYS["is_kill"])),
        "duration_seconds": _first_present(raw, _CANDIDATE_KEYS["duration_seconds"]),
        "recorded_at": _format_timestamp(_first_present(raw, _CANDIDATE_KEYS["recorded_at"])),
        "wipe_reason": _first_present(raw, _CANDIDATE_KEYS["wipe_reason"]),
    }
    if normalized["is_kill"]:
        normalized["percent"] = 0.0
    normalized["raw"] = raw
    return normalized


def _extract_attempts_list(raw_response) -> list:
    """Die API kann die Liste direkt oder unter einem Wrapper-Key liefern."""
    if isinstance(raw_response, list):
        return raw_response
    if isinstance(raw_response, dict):
        for key in ("attempts", "pulls", "bossAttempts", "data", "results"):
            value = raw_response.get(key)
            if isinstance(value, list):
                return value
    return []


def get_attempts(guild_key: str, mode: str, n: int) -> list:
    """
    Holt und normalisiert die Boss-Attempts einer Gilde.

    mode == "last": sortiert nach Pull-Nummer absteigend (neueste zuerst)
    mode == "best": sortiert nach Boss-HP% aufsteigend (beste/niedrigste zuerst)
    """
    raw_response = fetch_boss_attempts_raw(guild_key)
    raw_attempts = _extract_attempts_list(raw_response)
    attempts = [normalize_attempt(a) for a in raw_attempts]

    if mode == "best":
        attempts.sort(
            key=lambda a: (
                a["percent"] if a["percent"] is not None else 100.0,
                -(a["pull_number"] or 0),
            )
        )
    else:  # "last"
        attempts.sort(key=lambda a: (a["pull_number"] or 0), reverse=True)

    return attempts[:n]
