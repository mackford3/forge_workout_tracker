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