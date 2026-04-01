"""
Summary service — project totals, container optimization, zone/level subtotals.
"""
import math


def calculate_project_summary(members, product):
    """Calculate project-wide totals from member list."""
    total_litres = sum(m.get('volume_litres', 0) or 0 for m in members)
    total_kg = sum(m.get('weight_kg', 0) or 0 for m in members)
    total_area = sum(m.get('surface_area_m2', 0) or 0 for m in members)
    member_count = len(members)

    containers = optimize_containers(total_litres, product) if product else {}

    return {
        'member_count': member_count,
        'total_litres': round(total_litres, 2),
        'total_kg': round(total_kg, 2),
        'total_area_m2': round(total_area, 2),
        'containers': containers,
    }


def optimize_containers(total_litres, product):
    """
    Given total litres needed and product container sizes,
    find optimal container mix (fewest containers, least waste).
    Products have up to 4 container sizes (litres).
    """
    sizes = []
    for i in range(1, 5):
        key = f'container_{i}_litres'
        val = product.get(key)
        if val and val > 0:
            sizes.append(val)

    if not sizes:
        return {'containers': [], 'total_container_litres': 0, 'waste_litres': 0}

    sizes.sort(reverse=True)  # Largest first

    remaining = total_litres
    result = []
    for size in sizes:
        count = int(remaining // size)
        if count > 0:
            result.append({'size_litres': size, 'count': count})
            remaining -= count * size

    # If there's remaining, add one of the smallest container
    if remaining > 0.01:
        smallest = sizes[-1]
        # Find the smallest container that covers the remainder
        for size in reversed(sizes):
            if size >= remaining:
                smallest = size
        result.append({'size_litres': smallest, 'count': 1})
        remaining = 0

    total_container_litres = sum(c['size_litres'] * c['count'] for c in result)
    waste = total_container_litres - total_litres

    return {
        'containers': result,
        'total_container_litres': round(total_container_litres, 2),
        'waste_litres': round(max(0, waste), 2),
    }


def calculate_subtotals(members, group_field):
    """Calculate subtotals grouped by a field (zone or level)."""
    groups = {}
    for m in members:
        key = m.get(group_field, '') or '(unassigned)'
        if key not in groups:
            groups[key] = {'litres': 0, 'kg': 0, 'area_m2': 0, 'count': 0}
        groups[key]['litres'] += m.get('volume_litres', 0) or 0
        groups[key]['kg'] += m.get('weight_kg', 0) or 0
        groups[key]['area_m2'] += m.get('surface_area_m2', 0) or 0
        groups[key]['count'] += 1

    return {k: {field: round(v, 2) for field, v in vals.items()}
            for k, vals in sorted(groups.items())}
