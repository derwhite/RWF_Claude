from flask import Flask, render_template, redirect, url_for, abort, jsonify, request

from config import (
    GUILDS,
    DEFAULT_GUILD,
    MIN_ENTRIES,
    MAX_ENTRIES,
    DEFAULT_ENTRIES,
    DEBUG_ROUTES,
    BOSS_SLUG,
    RAID_SLUG,
    DIFFICULTY,
)
from raiderio_client import get_attempts, fetch_boss_attempts_raw, RaiderIOError

app = Flask(__name__)


def _clamp_n(n: int) -> int:
    return max(MIN_ENTRIES, min(MAX_ENTRIES, n))


def _resolve_guild(guild_key: str) -> str:
    key = (guild_key or DEFAULT_GUILD).lower()
    if key not in GUILDS:
        abort(404, description=f"Unbekannte Gilde '{key}'.")
    return key


@app.route("/")
def index():
    return redirect(url_for("table_view", mode="last", n=DEFAULT_ENTRIES))


@app.route("/<any(last,best):mode>/<int:n>")
def table_view(mode, n):
    n = _clamp_n(n)
    guild_key = _resolve_guild(request.args.get("guild"))

    error = None
    attempts = []
    meta = {}
    try:
        attempts, meta = get_attempts(guild_key, mode, n)
    except RaiderIOError as exc:
        error = str(exc)

    return render_template(
        "table.html",
        mode=mode,
        n=n,
        guild_key=guild_key,
        guilds=GUILDS,
        guild=GUILDS[guild_key],
        attempts=attempts,
        meta=meta,
        error=error,
        raid_slug=RAID_SLUG,
        difficulty=DIFFICULTY,
        boss_slug=BOSS_SLUG,
        debug_routes=DEBUG_ROUTES,
    )


@app.route("/<any(last,best):mode>/<int:n>/compare")
def compare_view(mode, n):
    n = _clamp_n(n)

    columns = []
    for key, g in GUILDS.items():
        try:
            attempts, meta = get_attempts(key, mode, n)
            columns.append({"key": key, "guild": g, "attempts": attempts, "meta": meta, "error": None})
        except RaiderIOError as exc:
            columns.append({"key": key, "guild": g, "attempts": [], "meta": {}, "error": str(exc)})

    # Zeilen bilden: Zeile i enthaelt fuer jede Gilde deren i-ten Pull in
    # der jeweiligen Sortierung (last: neuester zuerst, best: bester zuerst).
    # Gilden mit weniger Eintraegen liefern ab da None (Zelle bleibt leer).
    rows = []
    for i in range(n):
        row = [col["attempts"][i] if i < len(col["attempts"]) else None for col in columns]
        if any(cell is not None for cell in row):
            rows.append(row)

    display_meta = next((col["meta"] for col in columns if col["meta"].get("boss_name")), {})

    return render_template(
        "compare.html",
        mode=mode,
        n=n,
        guilds=GUILDS,
        columns=columns,
        rows=rows,
        meta=display_meta,
        raid_slug=RAID_SLUG,
        difficulty=DIFFICULTY,
    )


if DEBUG_ROUTES:

    @app.route("/debug/<guild_key>")
    def debug_raw(guild_key):
        guild_key = _resolve_guild(guild_key)
        try:
            raw = fetch_boss_attempts_raw(guild_key)
        except RaiderIOError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify(raw)


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", message=getattr(e, "description", "Seite nicht gefunden.")), 404


if __name__ == "__main__":
    # Nur fuer lokale Entwicklung mit Auto-Reload.
    # Fuer den produktiven Betrieb: python serve.py (waitress)
    app.run(debug=True, port=5000)
