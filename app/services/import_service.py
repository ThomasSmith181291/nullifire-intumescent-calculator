"""
Import service — parse CSV/Excel files, detect columns, map to member fields.
"""
import csv
import io
import os

import openpyxl


def parse_upload(file_content, filename):
    """Parse uploaded file content, return headers and rows."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.csv':
        return _parse_csv(file_content)
    elif ext in ('.xlsx', '.xls'):
        return _parse_excel(file_content)
    else:
        raise ValueError(f'Unsupported file type: {ext}')


def _parse_csv(content):
    if isinstance(content, bytes):
        # Try UTF-8 first, fall back to latin-1
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

    # Find header row (first row with >2 non-empty cells)
    header_idx = 0
    for i, row in enumerate(rows[:5]):
        non_empty = sum(1 for c in row if c.strip())
        if non_empty >= 2:
            header_idx = i
            break

    headers = [h.strip() for h in rows[header_idx]]
    data_rows = []
    for row in rows[header_idx + 1:]:
        if any(c.strip() for c in row):  # Skip empty rows
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

    # Find header row
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
        'section': ['section', 'serial', 'size', 'steel', 'member', 'designation'],
        'quantity': ['qty', 'quantity', 'no', 'number', 'count', 'pcs'],
        'length': ['length', 'len', 'span'],
        'zone': ['zone', 'area', 'location', 'loc'],
        'level': ['level', 'floor', 'storey', 'story'],
        'fire_rating': ['fire', 'rating', 'frr', 'resistance'],
    }

    for i, header in enumerate(headers):
        h_lower = header.lower()
        for field, keywords in patterns.items():
            if field not in mapping:
                for kw in keywords:
                    if kw in h_lower:
                        mapping[field] = i
                        break

    return mapping


def validate_import_rows(rows, mapping, section_lookup_fn):
    """Validate parsed rows against the mapping. Returns validated rows with errors."""
    results = []
    section_col = mapping.get('section')
    if section_col is None:
        return [{'row': i, 'data': row, 'error': 'No section column mapped', 'valid': False}
                for i, row in enumerate(rows)]

    for i, row in enumerate(rows):
        result = {'row': i, 'data': row, 'valid': True, 'error': None, 'parsed': {}}

        # Get section name
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

        # Try to find the section
        matches = section_lookup_fn(section_query)
        if not matches:
            result['valid'] = False
            result['error'] = f'Section not found: {section_query}'
        else:
            result['parsed']['section'] = matches[0]

        # Parse other fields
        qty_col = mapping.get('quantity')
        if qty_col is not None and qty_col < len(row):
            try:
                result['parsed']['quantity'] = max(1, int(float(row[qty_col] or '1')))
            except ValueError:
                result['parsed']['quantity'] = 1

        length_col = mapping.get('length')
        if length_col is not None and length_col < len(row):
            try:
                result['parsed']['length_m'] = float(row[length_col] or '0')
            except ValueError:
                result['parsed']['length_m'] = 0

        zone_col = mapping.get('zone')
        if zone_col is not None and zone_col < len(row):
            result['parsed']['zone'] = row[zone_col]

        level_col = mapping.get('level')
        if level_col is not None and level_col < len(row):
            result['parsed']['level'] = row[level_col]

        results.append(result)

    return results
