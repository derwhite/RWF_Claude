import os
from dotenv import load_dotenv

load_dotenv()

# --- Raider.io API -----------------------------------------------------
RAIDERIO_API_KEY = os.environ.get("RAIDERIO_API_KEY", "")
RAIDERIO_BASE_URL = "https://raider.io/api/v1"

# --- Raid / Boss ---------------------------------------------------------
RAID_SLUG = os.environ.get("RAID_SLUG", "the-venomous-abyss")
DIFFICULTY = os.environ.get("DIFFICULTY", "mythic")

# Slug des Bosses, dessen Pull-Historie angezeigt wird. "latest" laesst
# Raider.io automatisch den aktuell umkaempften/letzten Boss der Gilde waehlen
# - genau das, was fuer den Race-to-World-First-Fortschritt gebraucht wird.
# Kann in der .env auf einen konkreten Boss-Slug gesetzt werden, falls mal
# ein bestimmter (nicht der aktuellste) Boss angezeigt werden soll.
BOSS_SLUG = os.environ.get("BOSS_SLUG", "latest")

# "until_kill" liefert nur die Attempts seit dem letzten Kill (bzw. seit
# Beginn der Progression, falls noch kein Kill vorliegt) - also genau die
# aktuell laufenden Pull-Versuche.
PERIOD = os.environ.get("PERIOD", "until_kill")

# Zeitzone, in der Zeitstempel (Pull-Zeitpunkte) angezeigt werden.
# Liste gueltiger Namen: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Berlin")

# --- Gilden ---------------------------------------------------------------
# "guild"/"realm"/"region" müssen exakt den Raider.io-Slugs entsprechen
# (i.d.R. klein geschrieben, Leerzeichen als Bindestrich).
GUILDS = {
    "liquid": {
        "label": "Liquid",
        "guild": "Liquid",
        "realm": "illidan",
        "region": "us",
        "color": "#0c6dc7",  # Liquid-Blau
    },
    "echo": {
        "label": "Echo",
        "guild": "Echo",
        "realm": "tarren-mill",
        "region": "eu",
        "color": "#d31f3c",  # Echo-Rot
    },
    "method": {
        "label": "Method",
        "guild": "Method",
        "realm": "twisting-nether",
        "region": "eu",
        "color": "#f2a900",  # Method-Gold
    },
}
DEFAULT_GUILD = "liquid"

# --- Tabellen-/Request-Limits ---------------------------------------------
MIN_ENTRIES = 1
MAX_ENTRIES = 200
DEFAULT_ENTRIES = 20

# Kurzes serverseitiges Caching, damit mehrfaches schnelles Neuladen der
# Seite nicht sofort das Raider.io Rate-Limit ausreizt.
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "10"))

# Aktiviert /debug/<guild>, um die rohe API-Antwort einzusehen
# (siehe README, Abschnitt "Feld-Mapping anpassen").
DEBUG_ROUTES = os.environ.get("DEBUG_ROUTES", "false").lower() == "true"
