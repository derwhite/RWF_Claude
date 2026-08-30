"""
Bestimmt die grobe Boss-Phase (P1/P2/P3/...) eines Pulls anhand von
`encounterId`, `overallPercent` und Kampfdauer, da Raider.io selbst keine
Phaseninformationen liefert.

Die Phasen-Logik ist reines Encounter-Wissen und muss daher manuell pro
Boss in PHASE_DEFINITIONS gepflegt werden.

-------------------------------------------------------------------------
1) Welcher Phase gehoert ein Pull an? ("when")
-------------------------------------------------------------------------
Jede Phase hat eine "when"-Bedingung. Die Phasen werden GENAU IN DER
REIHENFOLGE der Liste geprueft, die erste zutreffende Bedingung gewinnt.
Das erlaubt gemischte Kriterien pro Boss, z.B. "P1 ist immer die ersten
2 Minuten (egal wie viel % das sind), P3 beginnt immer ab 40% (egal wie
lange der Pull schon laeuft), P2 ist alles dazwischen":

    phases = [
        {"label": "P1", "when": {"type": "time_max", "seconds": 120}},
        {"label": "P3", "when": {"type": "percent_max", "percent": 40}},
        {"label": "P2", "when": {"type": "always"}},  # Fallback, muss zuletzt stehen
    ]

Wichtig: Weil P1 (Zeit) vor P3 (Prozent) in der Liste steht, gewinnt
innerhalb der ersten 2 Minuten IMMER P1 - selbst wenn der Pull dort schon
unter 40% waere. Erst nach den 2 Minuten kommt die Prozent-Regel fuer P3
zum Tragen. Reihenfolge der Liste = Prioritaet der Pruefung, nicht
zwingend die chronologische Reihenfolge im Kampf.

Verfuegbare "when"-Typen:
  {"type": "time_max", "seconds": N}      Kampfdauer <= N Sekunden
  {"type": "time_min", "seconds": N}      Kampfdauer >= N Sekunden
  {"type": "percent_max", "percent": P}   Boss-HP <= P %
  {"type": "percent_min", "percent": P}   Boss-HP >= P %
  {"type": "always"}                      Trifft immer zu (Fallback/Rest)

-------------------------------------------------------------------------
2) Phasen-bezogene Prozentanzeige ("percent_range")
-------------------------------------------------------------------------
Unabhaengig von der "when"-Erkennung kann jede Phase einen eigenen
Prozentbereich (Obergrenze, Untergrenze) bekommen. Damit wird die
Overall-Percent in eine "Rest-HP innerhalb dieser Phase"-Prozentanzeige
umgerechnet - genauso wie overallPercent die Rest-HP des gesamten Bosses
zeigt.

Beispiel: P1 deckt gedanklich 100% bis 70% ab (percent_range: (100, 70)).
Ein Pull endet bei 77% Overall. Dann ist innerhalb von P1 noch
    (77 - 70) / (100 - 70) * 100 = 23.33 %
uebrig -> Anzeige "P1 · 23.33%".

percent_range ist rein fuer die Anzeige und unabhaengig vom "when" - auch
eine zeitbasierte Phase wie P1 oben kann (muss aber nicht) einen
percent_range fuer die Anzeige bekommen. Ohne percent_range wird nur das
Phasen-Label angezeigt, keine Phasen-Prozentzahl.
"""

from typing import Optional

PHASE_DEFINITIONS = {
    # TODO: Fuer jeden zu trackenden Boss die echte encounterId sowie die
    # tatsaechliche Phasenlogik eintragen. Beispiel fuer einen Boss mit
    # 2 Minuten fixer Startphase, Ausfuehrungsphase ab 40% und einer
    # Zwischenphase dazwischen:
    #
    197169: {
        "phases": [
            {
                "label": "P1",
                "when": {"type": "percent_min", "percent": 70},
                "percent_range": (100, 70),
            },
            {
                "label": "P2",
                "when": {"type": "percent_min", "percent": 40},
                "percent_range": (70, 40),
            },
            {
                "label": "P3",
                "when": {"type": "percent_max", "percent": 30},
                "percent_range": (0, 30),
            },
            {
                "label": "I1",
                "when": {"type": "always"},
                "percent_range": (30, 40),
            },
        ],
    },
}


def _condition_matches(when: dict, overall_percent, duration_seconds) -> bool:
    cond_type = when.get("type")

    if cond_type == "always":
        return True
    if cond_type == "time_max":
        return duration_seconds is not None and duration_seconds <= when["seconds"]
    if cond_type == "time_min":
        return duration_seconds is not None and duration_seconds >= when["seconds"]
    if cond_type == "percent_max":
        return overall_percent is not None and overall_percent <= when["percent"]
    if cond_type == "percent_min":
        return overall_percent is not None and overall_percent >= when["percent"]

    return False


def _phase_percent(percent_range, overall_percent) -> Optional[float]:
    if percent_range is None or overall_percent is None:
        return None
    upper, lower = percent_range
    span = upper - lower
    if span <= 0:
        return None
    raw = overall_percent - lower
    clamped = max(0.0, min(span, raw))
    return round((clamped / span) * 100, 2)


def get_phase(encounter_id, overall_percent, duration_seconds) -> dict:
    """
    Liefert {"label": "P2", "percent": 41.67} fuer einen Pull.

    - "label" ist None, wenn keine "when"-Bedingung fuer die encounter_id
      zutrifft (oder keine Definition hinterlegt ist).
    - "percent" ist None, wenn die gefundene Phase keinen percent_range
      hat oder overall_percent fehlt.
    """
    result = {"label": None, "percent": None}

    if encounter_id is None:
        return result

    definition = PHASE_DEFINITIONS.get(encounter_id)
    if not definition:
        return result

    for phase in definition.get("phases", []):
        when = phase.get("when", {})
        if _condition_matches(when, overall_percent, duration_seconds):
            result["label"] = phase.get("label")
            result["percent"] = _phase_percent(phase.get("percent_range"), overall_percent)
            return result

    return result
