import json
import os
import pytest
from app.services import dft_service

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'dft_reference_data.json')


def load_reference_data():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def case_id(case):
    return f"{case['product_name']}-{case['section_name']}-{case['hp_profile_name']}-{case['fire_rating']}-{case['failure_temp']}"


reference_data = load_reference_data()


@pytest.mark.parametrize('case', reference_data, ids=[case_id(c) for c in reference_data])
def test_dft_reference_data(app, case):
    with app.app_context():
        result = dft_service.lookup_dft(
            case['section_id'], case['hp_profile_name'],
            case['product_id'], case['fire_rating_id'], case['failure_temp_id']
        )
        assert result['status'] == case['expected_status'], \
            f"Expected status={case['expected_status']}, got {result['status']}: {result.get('error')}"
        if case['expected_status'] == 'ok':
            assert result['dft_mm'] == case['expected_dft_mm'], \
                f"DFT mismatch: expected {case['expected_dft_mm']}, got {result['dft_mm']}"
            if case['expected_hp_over_a'] is not None:
                assert result['hp_over_a'] == case['expected_hp_over_a'], \
                    f"Hp/A mismatch: expected {case['expected_hp_over_a']}, got {result['hp_over_a']}"


def test_dft_specific_known_value(app):
    """Hard-coded verification: SC802, 254x254x73 UC, U4 4-sided, 60min, 550C -> 0.367mm"""
    with app.app_context():
        r = dft_service.lookup_dft(750, 'U4', 266, 3, 7)
        assert r['status'] == 'ok'
        assert r['dft_mm'] == 0.367
        assert r['hp_over_a'] == 155.0
        assert r['coverage_id'] == 720


def test_dft_invalid_section(app):
    with app.app_context():
        r = dft_service.lookup_dft(999999, 'U4', 266, 3, 7)
        assert r['status'] == 'no_section_factor'
        assert r['dft_mm'] is None


def test_dft_invalid_profile(app):
    with app.app_context():
        r = dft_service.lookup_dft(750, 'NONEXISTENT', 266, 3, 7)
        assert r['status'] == 'error'
        assert 'Unknown HP profile' in r['error']


def test_dft_all_products_have_data(app):
    """Every active product must have at least one valid DFT lookup."""
    product_ids = [266, 278, 283, 284, 324]
    with app.app_context():
        for pid in product_ids:
            r = dft_service.lookup_dft(750, 'U4', pid, 3, 7)
            assert r['status'] == 'ok', f"Product {pid} has no DFT data for UC 254x254x73 60min 550C"


def test_dft_api_endpoint(client, app):
    with app.app_context():
        r = client.post('/api/dft/lookup', json={
            'section_id': 750, 'hp_profile_name': 'U4',
            'product_id': 266, 'fire_rating_id': 3, 'failure_temp_id': 7
        })
        assert r.status_code == 200
        assert r.json['status'] == 'ok'
        assert r.json['dft_mm'] == 0.367


def test_dft_api_missing_fields(client, app):
    with app.app_context():
        r = client.post('/api/dft/lookup', json={'section_id': 750})
        assert r.status_code == 400
        assert 'Missing required fields' in r.json['error']
