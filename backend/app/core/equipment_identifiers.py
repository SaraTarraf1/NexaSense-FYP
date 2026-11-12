import re


def identifier_prefix(equipment_type: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", equipment_type.lower()).strip()
    known = {
        "ac": "AC", "air conditioner": "AC", "air conditioning": "AC", "hvac": "AC",
        "electrical panel": "EP", "water pump": "WP", "ventilation": "VU",
        "ventilation unit": "VU", "water heater": "WH", "heat pump": "HP",
        "generator": "GEN",
    }
    if normalized in known:
        return known[normalized]
    words = normalized.split()
    return ("".join(word[0] for word in words) if len(words) > 1 else normalized[:4]).upper() or "EQ"


def next_identifier(equipment_type: str, used: set[str]) -> str:
    prefix = identifier_prefix(equipment_type)
    number = 1
    while f"{prefix}{number}" in used:
        number += 1
    return f"{prefix}{number}"
