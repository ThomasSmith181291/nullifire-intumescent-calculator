"""
Verification service — determines RAG status for steel members.

Green (ok): Hp/A within product's tested range, DFT data found
Amber (warning): Hp/A near the maximum tested range (within 90-100%)
Red (exceeds): Hp/A exceeds the product's maximum tested range
Grey (pending): Missing data, cannot verify
"""
from app.db import get_ref_db


def get_max_hpa_for_product(product_id, fire_rating_id, failure_temp_id):
    """Get the maximum Hp/A value that has DFT data for this product/rating/temp combination."""
    db = get_ref_db()
    row = db.execute('''
        SELECT MAX(cr.max_hpa) as max_hpa
        FROM dft_data d
        JOIN coverage_ranges cr ON d.coverage_id = cr.coverage_id
        WHERE d.product_id = ? AND d.fire_rating_id = ? AND d.failure_temp_id = ?
          AND cr.min_hpa = cr.max_hpa
    ''', (product_id, fire_rating_id, failure_temp_id)).fetchone()
    return row['max_hpa'] if row and row['max_hpa'] else None


def get_min_hpa_for_product(product_id, fire_rating_id, failure_temp_id):
    """Get the minimum Hp/A value that has DFT data."""
    db = get_ref_db()
    row = db.execute('''
        SELECT MIN(cr.min_hpa) as min_hpa
        FROM dft_data d
        JOIN coverage_ranges cr ON d.coverage_id = cr.coverage_id
        WHERE d.product_id = ? AND d.fire_rating_id = ? AND d.failure_temp_id = ?
          AND cr.min_hpa = cr.max_hpa
    ''', (product_id, fire_rating_id, failure_temp_id)).fetchone()
    return row['min_hpa'] if row and row['min_hpa'] else None


def classify_member_status(hp_over_a, dft_status, product_id, fire_rating_id, failure_temp_id):
    """
    Returns RAG classification:
    - 'ok' (green): DFT found, within range
    - 'warning' (amber): DFT found but Hp/A is >=90% of max tested range
    - 'exceeds' (red): Hp/A exceeds max tested range
    - 'pending' (grey): cannot determine (missing data)
    """
    if dft_status != 'ok':
        if dft_status in ('no_coverage', 'no_dft_data'):
            return 'exceeds'
        return 'pending'

    if hp_over_a is None:
        return 'pending'

    max_hpa = get_max_hpa_for_product(product_id, fire_rating_id, failure_temp_id)
    if max_hpa is None:
        return 'pending'

    if hp_over_a > max_hpa:
        return 'exceeds'
    elif hp_over_a >= max_hpa * 0.9:
        return 'warning'
    else:
        return 'ok'


def get_verification_summary(members):
    """Count members by RAG status."""
    counts = {'ok': 0, 'warning': 0, 'exceeds': 0, 'pending': 0}
    for m in members:
        status = m.get('status', 'pending')
        if status in counts:
            counts[status] += 1
        else:
            counts['pending'] += 1
    return counts
