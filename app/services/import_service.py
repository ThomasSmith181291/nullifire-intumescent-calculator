"""
Import service — parse CSV/Excel files, detect columns, map to member fields.
Uses fuzzy matching for section names, fire ratings, and failure temps.
"""
import csv
import io
import os

import openpyxl

from app.services import fuzzy_match


def parse_upload(file_content, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.csv':
        return _parse_csv(file_content)
    elif ext in ('.xlsx', '.xls'):
        return _parse_excel(file_content)
    else:
        raise ValueError(f'Unsupported file type: {ext}')


def _parse_csv(content):
    if isinstance(content, bytes):
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
    else:
        text = content

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []

    header_idx = 0
    for i, row in enumerate(rows[:5]):
        non_empty = sum(1 for c in row if c.strip())
        if non_empty >= 2:
            header_idx = i
            break

    headers = [h.strip() for h in rows[header_idx]]
    data_rows = []
    for row in rows[header_idx + 1:]:
        if any(c.strip() for c in row):
            data_rows.append([c.strip() for c in row])

    return headers, data_rows


def _parse_excel(content):
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(c) if c is not None else '' for c in row])
    wb.close()

    if not rows:
        return [], []

    header_idx = 0
    for i, row in enumerate(rows[:5]):
        non_empty = sum(1 for c in row if c.strip())
        if non_empty >= 2:
            header_idx = i
            break

    headers = [h.strip() for h in rows[header_idx]]
    data_rows = []
    for row in rows[header_idx + 1:]:
        if any(c.strip() for c in row):
            data_rows.append([c.strip() for c in row])

    return headers, data_rows


def auto_map_columns(headers):
    """Suggest column mapping based on header names."""
    mapping = {}
    patterns = {
        'section': ['section', 'serial', 'size', 'steel', 'member', 'designation', 'element', 'mark'],
        'quantity': ['qty', 'quantity', 'no', 'number', 'count', 'pcs', 'num'],
        'length': ['length', 'len', 'span', 'height'],
        'zone': ['zone', 'area', 'location', 'loc', 'region'],
        'level': ['level', 'floor', 'storey', 'story'],
        'fire_rating': ['fire', 'rating', 'frr', 'resistance', 'period'],
        'failure_temp': ['temp', 'temperature', 'critical', 'degree', 'failure'],
        'type': ['type', 'member type', 'element type'],
    }

    for i, header in enumerate(headers):
        h_lower = header.lower().strip()
        for field, keywords in patterns.items():
            if field not in mapping:
                for kw in keywords:
                    if kw in h_lower:
                        mapping[field] = i
                        break

    return mapping


def validate_import_rows(rows, mapping, origin_id=None):
    """Validate parsed rows using fuzzy matching. Returns validated rows with match details."""
    results = []
    section_col = mapping.get('section')
    if section_col is None:
        return [{'row': i, 'data': row, 'error': 'No section column mapped', 'valid': False}
                for i, row in enumerate(rows)]

    # Collect existing zones/levels for normalisation
    existing_zones = set()
    existing_levels = set()

    for i, row in enumerate(rows):
        result = {'row': i, 'data': row, 'valid': True, 'error': None, 'warnings': [], 'parsed': {}}

        # Section — fuzzy match
        if section_col >= len(row):
            result['valid'] = False
            result['error'] = 'Row too short'
            results.append(result)
            continue

        section_query = row[section_col]
        if not section_query:
            result['valid'] = False
            result['error'] = 'Empty section'
            results.append(result)
            continue

        section, confidence = fuzzy_match.match_section(section_query, origin_id)
        if not section:
            result['valid'] = False
            result['error'] = f'Section not found: "{section_query}"'
        else:
            result['parsed']['section'] = section
            result['parsed']['section_confidence'] = confidence
            if confidence < 0.9:
                result['warnings'].append(f'Fuzzy match: "{section_query}" -> "{section["serial_size"]}" ({int(confidence*100)}% confidence)')

        # Quantity
        qty_col = mapping.get('quantity')
        if qty_col is not None and qty_col < len(row):
            try:
                result['parsed']['quantity'] = max(1, int(float(row[qty_col] or '1')))
            except ValueError:
                result['parsed']['quantity'] = 1

        # Length
        length_col = mapping.get('length')
        if length_col is not None and length_col < len(row):
            try:
                result['parsed']['length_m'] = abs(float(row[length_col] or '0'))
            except ValueError:
                result['parsed']['length_m'] = 0

        # Fire rating — fuzzy match
        fr_col = mapping.get('fire_rating')
        if fr_col is not None and fr_col < len(row) and row[fr_col].strip():
            fr_id, fr_conf = fuzzy_match.match_fire_rating(row[fr_col])
            if fr_id is not None:
                result['parsed']['fire_rating_id'] = fr_id
                if fr_conf < 0.9:
                    result['warnings'].append(f'Fire rating fuzzy: "{row[fr_col]}" -> id {fr_id} ({int(fr_conf*100)}%)')
            else:
                result['warnings'].append(f'Could not match fire rating: "{row[fr_col]}"')

        # Failure temp — fuzzy match
        ft_col = mapping.get('failure_temp')
        if ft_col is not None and ft_col < len(row) and row[ft_col].strip():
            ft_id, ft_conf = fuzzy_match.match_failure_temp(row[ft_col])
            if ft_id is not None:
                result['parsed']['failure_temp_id'] = ft_id
                if ft_conf < 0.9:
                    result['warnings'].append(f'Temp fuzzy: "{row[ft_col]}" -> id {ft_id} ({int(ft_conf*100)}%)')
            else:
                result['warnings'].append(f'Could not match failure temp: "{row[ft_col]}"')

        # Zone — normalise
        zone_col = mapping.get('zone')
        if zone_col is not None and zone_col < len(row):
            zone = fuzzy_match.normalise_zone(row[zone_col], existing_zones)
            result['parsed']['zone'] = zone
            if zone:
                existing_zones.add(zone)

        # Level — normalise
        level_col = mapping.get('level')
        if level_col is not None and level_col < len(row):
            level = fuzzy_match.normalise_level(row[level_col], existing_levels)
            result['parsed']['level'] = level
            if level:
                existing_levels.add(level)

        # Member type
        type_col = mapping.get('type')
        if type_col is not None and type_col < len(row):
            t = row[type_col].strip().lower()
            if t in ('beam', 'column', 'bracing', 'brace', 'rafter'):
                result['parsed']['member_type'] = 'bracing' if t in ('brace', 'bracing', 'rafter') else t

        results.append(result)

    valid_count = sum(1 for r in results if r['valid'])
    warning_count = sum(1 for r in results if r['warnings'])

    return results
