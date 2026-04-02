"""
Fuzzy matching for steel sections, fire ratings, failure temps, and free-text fields.
Handles real-world inconsistencies in structural schedules.
"""
import re
from app.db import get_ref_db


def _normalise_section(text):
    """Normalise a section name for matching.
    '254 x 254 x 73 UC' -> '254x254x73'
    'UC 254x254x73' -> '254x254x73'
    'UB457x152x52' -> '457x152x52'
    """
    t = text.strip().upper()
    # Remove common prefixes (UB, UC, CHS, RHS, SHS, PFC, etc.)
    t = re.sub(r'^(UB|UC|CHS|RHS|SHS|PFC|EA|UA|ASB|SFB|T|J|F|O)\s*', '', t)
    # Normalise separators: spaces around 'x' or 'X'
    t = re.sub(r'\s*[xX×]\s*', 'x', t)
    # Remove any remaining spaces
    t = t.replace(' ', '')
    return t.lower()


def match_section(query, origin_id=None):
    """
    Try to match a section query string to a database section.
    Returns (section_dict, confidence) or (None, 0).

    Tries in order:
    1. Exact match on serial_size
    2. Normalised exact match
    3. Starts-with match (handles "254x254x73 UC" where UC is appended)
    4. Contains match (handles "UB 457x152x52")
    5. Numeric-only match (extract dimensions, match pattern)
    """
    db = get_ref_db()
    query = query.strip()
    if not query:
        return None, 0

    # Build origin filter
    origin_clause = ''
    params = []
    if origin_id:
        origin_clause = ' AND s.origin_id = ?'
        params = [origin_id]

    # 1. Exact match
    row = db.execute(
        f'SELECT s.*, st.name AS steel_type_name, st.abbrev AS steel_type_abbrev '
        f'FROM steel_sections s JOIN steel_types st ON s.steel_type_id = st.id '
        f'WHERE s.serial_size = ? {origin_clause} LIMIT 1',
        [query] + params
    ).fetchone()
    if row:
        return dict(row), 1.0

    # 2. Case-insensitive exact match
    row = db.execute(
        f'SELECT s.*, st.name AS steel_type_name, st.abbrev AS steel_type_abbrev '
        f'FROM steel_sections s JOIN steel_types st ON s.steel_type_id = st.id '
        f'WHERE LOWER(s.serial_size) = LOWER(?) {origin_clause} LIMIT 1',
        [query] + params
    ).fetchone()
    if row:
        return dict(row), 0.95

    # Normalise the query
    norm = _normalise_section(query)
    if not norm:
        return None, 0

    # 3. Normalised match — compare normalised forms
    rows = db.execute(
        f'SELECT s.*, st.name AS steel_type_name, st.abbrev AS steel_type_abbrev '
        f'FROM steel_sections s JOIN steel_types st ON s.steel_type_id = st.id '
        f'WHERE 1=1 {origin_clause}',
        params
    ).fetchall()

    best = None
    best_score = 0
    for r in rows:
        r_norm = _normalise_section(r['serial_size'])
        if r_norm == norm:
            return dict(r), 0.9
        # Starts-with: "254x254x73" matches "254x254x73"
        if r_norm.startswith(norm) or norm.startswith(r_norm):
            score = 0.8
            if score > best_score:
                best = dict(r)
                best_score = score
        # Contains the main dimensions
        elif norm in r_norm or r_norm in norm:
            score = 0.7
            if score > best_score:
                best = dict(r)
                best_score = score

    if best:
        return best, best_score

    # 4. Extract just the numbers and try matching dimension pattern
    nums = re.findall(r'[\d.]+', query)
    if len(nums) >= 2:
        # Build a pattern like "254%254%73"
        pattern = '%'.join(nums[:3])
        row = db.execute(
            f'SELECT s.*, st.name AS steel_type_name, st.abbrev AS steel_type_abbrev '
            f'FROM steel_sections s JOIN steel_types st ON s.steel_type_id = st.id '
            f'WHERE s.serial_size LIKE ? {origin_clause} LIMIT 1',
            [f'%{pattern}%'] + params
        ).fetchone()
        if row:
            return dict(row), 0.6

    return None, 0


# ── Fire Rating Matching ──

_FR_PATTERNS = {
    # minutes -> fire_rating_id
    15: 0, 30: 1, 45: 2, 60: 3, 90: 4, 120: 5, 180: 6, 240: 7,
}

_FR_HOUR_MAP = {
    0.25: 15, 0.5: 30, 0.75: 45, 1: 60, 1.5: 90, 2: 120, 3: 180, 4: 240,
}


def match_fire_rating(text):
    """Match a fire rating string to fire_rating_id.
    Handles: '60', '60min', '60 minutes', '1hr', '1 hour', '60 Minutes', etc.
    Returns (fire_rating_id, confidence) or (None, 0).
    """
    if text is None:
        return None, 0
    t = str(text).strip().lower()
    if not t:
        return None, 0

    # Try direct numeric (minutes)
    try:
        mins = int(float(t))
        if mins in _FR_PATTERNS:
            return _FR_PATTERNS[mins], 1.0
    except ValueError:
        pass

    # Strip common suffixes
    t_clean = re.sub(r'\s*(min(ute)?s?|mins?)\s*$', '', t, flags=re.IGNORECASE).strip()
    try:
        mins = int(float(t_clean))
        if mins in _FR_PATTERNS:
            return _FR_PATTERNS[mins], 0.95
    except ValueError:
        pass

    # Try hours
    hr_match = re.match(r'^([\d.]+)\s*(hr|hour|hours|hrs?)$', t, re.IGNORECASE)
    if hr_match:
        hrs = float(hr_match.group(1))
        mins = _FR_HOUR_MAP.get(hrs)
        if mins and mins in _FR_PATTERNS:
            return _FR_PATTERNS[mins], 0.9

    # Try database description match
    db = get_ref_db()
    row = db.execute('SELECT id FROM fire_ratings WHERE LOWER(description) LIKE ?',
                     (f'%{t}%',)).fetchone()
    if row:
        return row['id'], 0.8

    return None, 0


# ── Failure Temperature Matching ──

def match_failure_temp(text):
    """Match a failure temperature string to failure_temp_id.
    Handles: '550', '550C', '550°C', '550 deg', '550 degrees', etc.
    Returns (failure_temp_id, confidence) or (None, 0).
    """
    if text is None:
        return None, 0
    t = str(text).strip()
    if not t:
        return None, 0

    # Extract numeric value
    num_match = re.match(r'([\d.]+)', t)
    if not num_match:
        return None, 0

    temp_val = num_match.group(1)

    # Search database for matching temp description
    db = get_ref_db()

    # Try exact description match first
    row = db.execute('SELECT id FROM failure_temps WHERE description LIKE ? AND is_country_specific = 1',
                     (f'{temp_val}%',)).fetchone()
    if row:
        return row['id'], 0.95

    # Try with degree symbol variations
    for pattern in [f'{temp_val}°C', f'{temp_val}°', f'{temp_val}C']:
        row = db.execute('SELECT id FROM failure_temps WHERE description LIKE ? AND is_country_specific = 1',
                         (f'%{pattern}%',)).fetchone()
        if row:
            return row['id'], 0.9

    return None, 0


# ── Free Text Normalisation ──

def normalise_zone(text, existing_zones):
    """Case-insensitive match against existing zones.
    'ground floor' matches 'Ground Floor' if it exists.
    """
    if not text:
        return text
    t = text.strip()
    lower = t.lower()
    for z in existing_zones:
        if z.lower() == lower:
            return z  # Use the existing casing
    return t


def normalise_level(text, existing_levels):
    """Same as normalise_zone but for levels."""
    if not text:
        return text
    t = text.strip()
    lower = t.lower()
    for l in existing_levels:
        if l.lower() == lower:
            return l
    return t
