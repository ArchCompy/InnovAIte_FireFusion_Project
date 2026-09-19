"""
Canonical label encodings for the crisis tasks (urgency + humanitarian).

Kept in a dependency-free module (no torch) so the data-build script can import
the same maps the model uses. CrisisTS_Eng.csv stores these labels as strings;
these dicts are the SINGLE source of truth for string -> integer id. The
data-build script encodes with the STR2ID maps and the model's task specs expose
the inverse ID2LABEL. Edit both sides here to keep them in lock-step.
"""

from __future__ import annotations

# urgency: CrisisTS ``label_urgent`` (3 classes). ``not_humanitarian`` == not useful.
URGENCY_STR2ID: dict[str, int] = {
    "not_humanitarian": 0,  # NOT_USEFUL
    "not_urgent": 1,        # NOT_URGENT
    "urgent": 2,            # URGENT
}
URGENCY_ID2LABEL: dict[int, str] = {0: "NOT_USEFUL", 1: "NOT_URGENT", 2: "URGENT"}

# humanitarian: CrisisTS ``label_humanitarian`` (8 classes, incl. ``not_humanitarian``).
HUMANITARIAN_STR2ID: dict[str, int] = {
    "injured_or_dead_people": 0,               # HMN_DMG   (human damage)
    "infrastructure_and_utility_damage": 1,    # MAT_DMG   (material damage)
    "caution_and_advice": 2,                   # WARN      (warning)
    "displaced_people_and_evacuations": 3,     # EVAC      (evacuations)
    "missing_or_found_people": 4,              # HMN_MISS  (missing people)
    "rescue_volunteering_or_donation_effort": 5,  # VOLUNTEER
    "requests_or_urgent_needs": 6,             # REQUEST   (requests / urgent needs)
    "not_humanitarian": 7,                     # NOT_HUM   (no humanitarian category)
}
HUMANITARIAN_ID2LABEL: dict[int, str] = {
    0: "HMN_DMG",
    1: "MAT_DMG",
    2: "WARN",
    3: "EVAC",
    4: "HMN_MISS",
    5: "VOLUNTEER",
    6: "REQUEST",
    7: "NOT_HUM",
}
