"""
Bestimmt die grobe Boss-Phase (P1/P2/P3/...) eines Pulls anhand von
`encounterId`, `overallPercent` und Kampfdauer, da Raider.io selbst keine
Phaseninformationen liefert.

Die Phasen-Grenzen sind reines Encounter-Wissen (wie die jeweilige Gilde/
das Fight-Team den Kampf einteilt) und muessen daher manuell pro Boss in
PHASE_DEFINITIONS gepflegt werden - siehe Beispiele unten.

Zwei Modi pro Boss moeglich, je nachdem wie der Kampf getaktet ist:

  mode == "percent"
    Phasen werden anhand des Boss-HP% (overallPercent) unterschieden,
    z.B. "P1: 100-70%, P2: 70-40%, P3: 40-0%".
    phases = Liste von (Label, Obergrenze-in-%). Reihenfolge in der Liste
    ist egal, die Funktion sortiert intern.

    Beispiel: [("P1", 100), ("P2", 70), ("P3", 40)]

  mode == "time"
    Phasen werden anhand der bisherigen Kampfdauer unterschieden (z.B. bei
    Fights mit festen Zeitfenstern statt HP-Schwellen),
    z.B. "P1: 0-2min, P2: 2-5min, P3: ab 5min".
    phases = Liste von (Label, Obergrenze-in-Sekunden). Die letzte Phase
    kann als Obergrenze None ("unbegrenzt") bekommen.

    Beispiel: [("P1", 120), ("P2", 300), ("P3", None)]

Die encounterId eines Bosses findest du in der Raider.io-Antwort unter
`boss.encounterId` - am einfachsten ueber /debug/<guild-key> (siehe
README) oder in der App selbst (kleiner grauer Text unter dem Bossnamen).
"""
from typing import Optional


PHASE_DEFINITIONS = {
    # TODO: Fuer jeden zu trackenden Boss die echte encounterId sowie die
    # tatsaechlichen Phasen-Grenzen eintragen, z.B.:
    #
    # 197169: {  # "The Coiled Altar"
    #     "mode": "percent",
    #     "phases": [("P1", 100), ("P2", 70), ("P3", 40)],
    # },
}


def _phase_from_percent(phases, overall_percent) -> Optional[str]:
    if overall_percent is None or not phases:
        return None
    # Aufsteigend nach Obergrenze sortieren, damit die "engste" passende
    # Phase gefunden wird (kleinste Obergrenze, die >= overall_percent ist).
    ordered = sorted(phases, key=lambda p: p[1])
    for label, upper in ordered:
        if overall_percent <= upper:
            return label
    return ordered[-1][0]


def _phase_from_time(phases, duration_seconds) -> Optional[str]:
    if duration_seconds is None or not phases:
        return None
    ordered = sorted(phases, key=lambda p: (p[1] is not None, p[1]))
    for label, upper in ordered:
        if upper is None or duration_seconds <= upper:
            return label
    return ordered[-1][0]


def get_phase(encounter_id, overall_percent, duration_seconds) -> Optional[str]:
    """
    Liefert ein Anzeige-Label wie "P2" fuer einen Pull.

    Gibt None zurueck, wenn fuer die uebergebene encounter_id keine
    Phasen-Definition in PHASE_DEFINITIONS hinterlegt ist - die Tabelle
    zeigt dann einfach keine Phase an, statt einen falschen Wert zu raten.
    """
    if encounter_id is None:
        return None

    definition = PHASE_DEFINITIONS.get(encounter_id)
    if not definition:
        return None

    mode = definition.get("mode")
    phases = definition.get("phases", [])

    if mode == "percent":
        return _phase_from_percent(phases, overall_percent)
    if mode == "time":
        return _phase_from_time(phases, duration_seconds)
    return None
