import re


def clean_exercise_name(name):
    """Strip trailing set/rep/duration info from a planned workout exercise name."""
    n = name.strip()
    n = re.sub(r'\s+\d+x\d+[/\w]*$', '', n)                      # "3x10/side"
    n = re.sub(r'\s+[\d\-]+min$', '', n)                           # "10min", "30-45min"
    n = re.sub(r'\s+Zone\s+\d+$', '', n, flags=re.IGNORECASE)     # "Zone 2"
    n = re.sub(r'\s+\([^)]*\)\s*$', '', n)                        # trailing "(hips/shoulders)"
    return n.lower().strip()


def fuzzy_match(cleaned_name, ex_map):
    """Match a cleaned name against exercise map. Handles 'X or Y' alternatives."""
    if ' or ' in cleaned_name:
        for part in cleaned_name.split(' or '):
            result = fuzzy_match(part.strip(), ex_map)
            if result:
                return result
    clean = re.sub(r'[^\w\s]', '', cleaned_name).lower()
    words = clean.split()
    for length in range(len(words), 0, -1):
        candidate = words[:length]
        for k, ex in ex_map.items():
            if all(w in k for w in candidate):
                return ex
    return None


def seconds_to_display(seconds):
    """Convert seconds to HH:MM:SS or MM:SS string."""
    if not seconds:
        return '--'
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def kg_to_lbs(kg):
    if kg is None:
        return None
    return round(float(kg) * 2.20462, 2)


def lbs_to_kg(lbs):
    if lbs is None:
        return None
    return round(float(lbs) / 2.20462, 2)


def format_weight(kg, unit='kg'):
    if kg is None:
        return '--'
    if unit == 'lbs':
        return f"{kg_to_lbs(kg)} lbs"
    return f"{float(kg):.1f} kg"


def format_distance(km):
    if km is None:
        return '--'
    km = float(km)
    if km >= 1:
        return f"{km:.2f} km"
    return f"{km * 1000:.0f} m"