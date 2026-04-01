"""
Multi-product DFT comparison — for a given member, show which Nullifire
products can provide coverage and at what DFT.
"""
from app.services import product_service, dft_service


def check_all_products(section_id, hp_profile_name, fire_rating_id, failure_temp_id):
    """
    For a given section + exposure + fire rating + temp, check ALL active
    Nullifire products and return which ones can provide coverage.

    Returns list of dicts sorted by DFT (thinnest first):
    [
        {
            "product_id": 284,
            "product_name": "Nullifire SC901",
            "dft_mm": 0.88,
            "final_dft_mm": 0.88,
            "status": "ok",
            "hp_over_a": 155.0,
            ...
        },
        ...
    ]
    """
    products = product_service.get_products()
    results = []

    for product in products:
        result = dft_service.lookup_dft(
            section_id, hp_profile_name,
            product['id'], fire_rating_id, failure_temp_id
        )
        results.append({
            'product_id': product['id'],
            'product_name': product['name'],
            'is_solvent_based': product['is_solvent_based'],
            'density': product['density'],
            'dft_mm': result.get('dft_mm'),
            'final_dft_mm': result.get('final_dft_mm'),
            'status': result.get('status'),
            'hp_over_a': result.get('hp_over_a'),
            'heated_perimeter': result.get('heated_perimeter'),
            'error': result.get('error'),
        })

    # Sort: ok results first (by DFT ascending), then non-ok
    ok_results = sorted([r for r in results if r['status'] == 'ok'],
                        key=lambda r: r['dft_mm'] or 999)
    other_results = [r for r in results if r['status'] != 'ok']

    return ok_results + other_results


def check_member_coverage(section_id, hp_profile_name, fire_rating_id, failure_temp_id):
    """
    Summary: can this member be covered by ANY Nullifire product?
    Returns dict with coverage summary.
    """
    results = check_all_products(section_id, hp_profile_name, fire_rating_id, failure_temp_id)
    covered = [r for r in results if r['status'] == 'ok']

    return {
        'total_products': len(results),
        'products_with_coverage': len(covered),
        'best_product': covered[0] if covered else None,
        'all_results': results,
        'is_coverable': len(covered) > 0,
        'min_dft_mm': covered[0]['dft_mm'] if covered else None,
        'max_dft_mm': covered[-1]['dft_mm'] if covered else None,
    }
