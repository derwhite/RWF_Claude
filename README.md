# Race to World First Tracker

Kleine Flask-Website, die den Mythic-Raid-Fortschritt (Boss-Pulls) von
Liquid, Echo und Method über die [Raider.io Live-Tracking-API](https://raider.io/api#/Live%20Tracking%20-%20Raiding/getApiV1LivetrackingGuildBossattempts)
anzeigt.

- `/last/<n>` – die letzten `n` Pulls (neueste zuerst)
- `/best/<n>` – die `n` besten Pulls (niedrigste Boss-HP% zuerst)
- `/last/<n>/compare` bzw. `/best/<n>/compare` – alle Gilden nebeneinander
  in einer Tabelle (Rang 1 = neuester bzw. bester Pull je Gilde)
- Gilde wird per `?guild=liquid|echo|method` gewählt (Tabs in der UI)
- Dark-/Light-Mode per Switch oben rechts

## 1. Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Trage in `.env` mindestens `RAIDERIO_API_KEY` ein. `BOSS_SLUG=latest`
sorgt dafür, dass automatisch der aktuell umkämpfte Boss der jeweiligen
Gilde angezeigt wird – kein manuelles Nachschlagen eines Boss-Slugs nötig.
Falls du stattdessen mal einen konkreten (nicht den aktuellsten) Boss
sehen willst, kannst du `BOSS_SLUG` in der `.env` auf dessen Slug setzen
(z. B. `the-coiled-altar`).

## 2. Lokal starten (Entwicklung)

```bash
python app.py
```

Öffnet auf `http://127.0.0.1:5000`.

## 3. Produktiv starten (waitress)

```bash
python serve.py
```

Startet über `waitress` auf `http://0.0.0.0:8080` (Host/Port über `.env`
änderbar). Für den Live-Betrieb hinter `HOST.de` am besten hinter einen
Reverse Proxy (nginx/Caddy) hängen, der TLS terminiert und an Port 8080
weiterleitet.

## 4. API-Antwortformat

Das Parsing in `raiderio_client.py` basiert auf einer echten Beispiel-
Antwort der API (`pullStartedAt`, `overallPercent`, `isSuccess`,
`encounter.durationMs`, sowie `boss`/`raid`-Metadaten). Eine Pull-Nummer
liefert die API nicht mit – sie wird anhand der chronologischen
Reihenfolge (`pullStartedAt`) serverseitig vergeben.

Sollte Raider.io das Format mal ändern und die Tabelle leere ("–") Werte
zeigen:

1. `DEBUG_ROUTES=true` in `.env` setzen, App neu starten
2. `/debug/<guild-key>` aufrufen (z. B. `/debug/echo`) → zeigt das rohe
   JSON der API
3. Die passenden Feldnamen in `raiderio_client.py` → `normalize_attempt()`
   / `get_boss_meta()` anpassen

Schick mir bei Bedarf einfach den Inhalt von `/debug/<guild>`, dann
passe ich das direkt für dich an.

## 5. Gilden / Raid ändern

Alles Guild- und Raid-bezogene steht zentral in `config.py`
(`GUILDS`, `RAID_SLUG`, `DIFFICULTY`). Neue Gilde hinzufügen = neuer
Eintrag im `GUILDS`-Dict (inkl. Akzentfarbe für die Tabs).

## 6. Phasen-Anzeige (P1/P2/...)

Raider.io liefert keine Phaseninformationen. `phases.py` bietet daher eine
eigene Funktion `get_phase(encounter_id, overall_percent, duration_seconds)`,
die anhand von manuell hinterlegten Grenzwerten (`PHASE_DEFINITIONS`) eine
Phase wie "P1" zurückgibt – wahlweise Prozent-basiert (z. B. P1: 100-70%)
oder Zeit-basiert (z. B. P1: erste 2 Minuten). Die `encounterId` des
aktuellen Bosses steht klein im Seiten-Header (z. B. `#197169`).

```python
# phases.py
PHASE_DEFINITIONS = {
    197169: {
        "mode": "percent",
        "phases": [("P1", 100), ("P2", 70), ("P3", 40)],
    },
}
```

Ohne Eintrag für eine `encounterId` wird einfach keine Phase angezeigt.

## Projektstruktur

```
rtwf-tracker/
├── app.py              Flask-Routen (/last/<n>, /best/<n>, /compare, /debug/<g>)
├── raiderio_client.py   API-Aufruf, Caching, Feld-Normalisierung, Phasen-Zuordnung
├── phases.py             Boss-Phase (P1/P2/...) aus HP%/Dauer ableiten
├── config.py             Gilden, Raid-Konfiguration, .env-Anbindung
├── serve.py              Produktions-Start via waitress
├── requirements.txt
├── pyproject.toml
├── .env.example
├── templates/
│   ├── base.html
│   ├── _nav.html          Gemeinsame Navigation (Gilden-Tabs, Modus, Anzahl)
│   ├── table.html          Einzelgilden-Tabelle
│   ├── compare.html        Alle Gilden nebeneinander
│   └── error.html
└── static/
    ├── style.css           Dark/Light Theme, Boss-HP-Balken, Compare-Tabelle
    └── script.js           Theme-Switch, eigene Anzahl-Eingabe
```
