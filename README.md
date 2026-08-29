# Race to World First Tracker

Kleine Flask-Website, die den Mythic-Raid-Fortschritt (Boss-Pulls) von
Liquid, Echo und Method über die [Raider.io Live-Tracking-API](https://raider.io/api#/Live%20Tracking%20-%20Raiding/getApiV1LivetrackingGuildBossattempts)
anzeigt.

- `/last/<n>` – die letzten `n` Pulls (neueste zuerst)
- `/best/<n>` – die `n` besten Pulls (niedrigste Boss-HP% zuerst)
- Gilde wird per `?guild=liquid|echo|method` gewählt (Tabs in der UI)
- Dark-/Light-Mode per Switch oben rechts

## 1. Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Trage in `.env` mindestens `RAIDERIO_API_KEY` und `BOSS_SLUG` ein.

## 2. Boss-Slug herausfinden

Die Live-Tracking-API braucht den exakten `bossSlug` des Bosses, dessen
Pulls du sehen willst (aktuell also vermutlich der letzte/umkämpfte Boss
von "The Venomous Abyss"). Zwei einfache Wege, ihn herauszufinden:

1. Öffne die Guild-Live-Tracking-Seite der Gilde auf raider.io im Browser
   (z. B. über die Gildensuche → Reiter "Raid Progress" → aktueller Boss)
   und schau im Netzwerk-Tab der Browser-DevTools nach dem Request an
   `.../live-tracking/guild/boss-attempts` – der Query-Parameter
   `bossSlug` steht direkt in der URL.
2. Alternativ: `DEBUG_ROUTES=true` in der `.env` setzen, App starten und
   `/debug/liquid` (o. ä.) aufrufen – falls `BOSS_SLUG` schon (auch nur
   testweise) gesetzt ist, siehst du dort die rohe API-Antwort inkl.
   aller vorhandenen Felder.

Trage den gefundenen Slug in `.env` unter `BOSS_SLUG` ein.

## 3. Lokal starten (Entwicklung)

```bash
python app.py
```

Öffnet auf `http://127.0.0.1:5000`.

## 4. Produktiv starten (waitress)

```bash
python serve.py
```

Startet über `waitress` auf `http://0.0.0.0:8080` (Host/Port über `.env`
änderbar). Für den Live-Betrieb hinter `HOST.de` am besten hinter einen
Reverse Proxy (nginx/Caddy) hängen, der TLS terminiert und an Port 8080
weiterleitet.

## 5. Wichtiger Hinweis zum API-Antwortformat

Raider.io stellt für die Live-Tracking-Endpunkte keine maschinenlesbare
OpenAPI-Spezifikation bereit (die Doku-Seite ist eine reine JS-App), daher
basiert das Parsing der Pull-Daten in `raiderio_client.py`
(`_CANDIDATE_KEYS`) auf den in der Praxis gebräuchlichen Feldnamen
(`pullNumber`, `healthPercent`, `isKill`, `durationSeconds`,
`recordedAt`, ...). Sollte deine Antwort andere Feldnamen verwenden und
die Tabelle leere ("–") Werte zeigen:

1. `DEBUG_ROUTES=true` in `.env` setzen, App neu starten
2. `/debug/<guild-key>` aufrufen (z. B. `/debug/echo`) → zeigt das rohe
   JSON der API
3. Die passenden Feldnamen in `raiderio_client.py` → `_CANDIDATE_KEYS`
   ergänzen

Das ist die einzige Stelle im Code, die bei abweichenden Feldnamen
angepasst werden muss – der Rest (Sortierung, Rendering, Caching)
funktioniert unabhängig davon.

Schick mir bei Bedarf einfach den Inhalt von `/debug/<guild>`, dann
passe ich das Mapping direkt für dich an.

## 6. Gilden / Raid ändern

Alles Guild- und Raid-bezogene steht zentral in `config.py`
(`GUILDS`, `RAID_SLUG`, `DIFFICULTY`). Neue Gilde hinzufügen = neuer
Eintrag im `GUILDS`-Dict (inkl. Akzentfarbe für die Tabs).

## Projektstruktur

```
rtwf-tracker/
├── app.py              Flask-Routen (/last/<n>, /best/<n>, /debug/<g>)
├── raiderio_client.py   API-Aufruf, Caching, Feld-Normalisierung
├── config.py             Gilden, Raid-Konfiguration, .env-Anbindung
├── serve.py              Produktions-Start via waitress
├── requirements.txt
├── .env.example
├── templates/
│   ├── base.html
│   ├── table.html         Haupttabelle inkl. Tabs/Umschalter
│   └── error.html
└── static/
    ├── style.css           Dark/Light Theme, Boss-HP-Balken
    └── script.js           Theme-Switch, eigene Anzahl-Eingabe
```
