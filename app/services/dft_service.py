from app.db import get_ref_db

DIRECT_CUB = {'C1', 'R1', 'R2', 'R3', 'S1', 'S2', 'S3', 'U1', 'U2', 'U4'}


def _resolve_composite_use_band(db, hp_profile_name):
    if hp_profile_name in DIRECT_CUB:
        return hp_profile_name

    profile = db.execute(
        'SELECT hp_over_a_band, steel_type_id FROM hp_profiles WHERE name = ?',
        (hp_profile_name,)
    ).fetchone()
    if not profile:
        return None

    target_band = profile['hp_over_a_band']
    target_type = profile['steel_type_id']

    cub_profiles = db.execute('''
        SELECT name, hp_over_a_band, steel_type_id
        FROM hp_profiles
        WHERE name IN ('C1','R1','R2','R3','S1','S2','S3','U1','U2','U4')
    ''').fetchall()

    # First: match on both hp_over_a_band AND steel_type_id
    for p in cub_profiles:
        if p['hp_over_a_band'] == target_band and p['steel_type_id'] == target_type:
            return p['name']

    # Fallback: match on hp_over_a_band only
    for p in cub_profiles:
        if p['hp_over_a_band'] == target_band:
            return p['name']

    return None


def _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id, **kwargs):
    base = {
        'section_id': section_id,
        'hp_profile_name': hp_profile_name,
        'product_id': product_id,
        'fire_rating_id': fire_rating_id,
        'failure_temp_id': failure_temp_id,
        'hp_over_a': None,
        'heated_perimeter': None,
        'hp_over_a_band': None,
        'composite_use_band': None,
        'use_band': None,
        'coverage_id': None,
        'dft_mm': None,
        'offset_dft': 0.0,
        'final_dft_mm': None,
        'status': 'error',
        'error': None,
    }
    base.update(kwargs)
    return base


def lookup_dft(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id):
    try:
        db = get_ref_db()

        # Step 1: Get hp_over_a_band from hp_profiles
        profile = db.execute(
            'SELECT hp_over_a_band FROM hp_profiles WHERE name = ?',
            (hp_profile_name,)
        ).fetchone()
        if not profile:
            return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                                status='error', error=f'Unknown HP profile: {hp_profile_name}')

        hp_over_a_band = profile['hp_over_a_band']

        # Step 2: Get section factor
        sf = db.execute('''
            SELECT hp_over_a, heated_perimeter
            FROM section_factors
            WHERE steel_section_id = ? AND hp_over_a_band = ?
        ''', (section_id, hp_over_a_band)).fetchone()
        if not sf:
            return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                                hp_over_a_band=hp_over_a_band,
                                status='no_section_factor')

        hp_over_a = sf['hp_over_a']
        heated_perimeter = sf['heated_perimeter']

        # Step 3: Resolve composite_use_band
        composite_use_band = _resolve_composite_use_band(db, hp_profile_name)
        if not composite_use_band:
            return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                                hp_over_a_band=hp_over_a_band, hp_over_a=hp_over_a,
                                heated_perimeter=heated_perimeter,
                                status='no_band_mapping', error=f'No composite_use_band mapping for {hp_profile_name}')

        # Step 4: Get use_band from hp_data_info
        info = db.execute('''
            SELECT use_band FROM hp_data_info
            WHERE product_id = ? AND hour_id = ? AND composite_use_band = ?
        ''', (product_id, fire_rating_id, composite_use_band)).fetchone()
        if not info:
            return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                                hp_over_a_band=hp_over_a_band, hp_over_a=hp_over_a,
                                heated_perimeter=heated_perimeter,
                                composite_use_band=composite_use_band,
                                status='no_band_mapping',
                                error=f'No use_band in hp_data_info for product={product_id}, hour={fire_rating_id}, cub={composite_use_band}')

        use_band = info['use_band']

        # Step 5: Get coverage_id (exact match)
        hpa_int = int(hp_over_a)
        cov = db.execute('''
            SELECT coverage_id FROM coverage_ranges
            WHERE band = ? AND min_hpa = ? AND max_hpa = ?
        ''', (use_band, hpa_int, hpa_int)).fetchone()
        if not cov:
            return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                                hp_over_a_band=hp_over_a_band, hp_over_a=hp_over_a,
                                heated_perimeter=heated_perimeter,
                                composite_use_band=composite_use_band, use_band=use_band,
                                status='no_coverage',
                                error=f'No coverage for band={use_band}, hpa={hpa_int}')

        coverage_id = cov['coverage_id']

        # Step 6: Get DFT
        dft_row = db.execute('''
            SELECT dft_mm FROM dft_data
            WHERE product_id = ? AND coverage_id = ? AND fire_rating_id = ? AND failure_temp_id = ?
        ''', (product_id, coverage_id, fire_rating_id, failure_temp_id)).fetchone()
        if not dft_row:
            return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                                hp_over_a_band=hp_over_a_band, hp_over_a=hp_over_a,
                                heated_perimeter=heated_perimeter,
                                composite_use_band=composite_use_band, use_band=use_band,
                                coverage_id=coverage_id,
                                status='no_dft_data',
                                error=f'No DFT data for product={product_id}, coverage={coverage_id}, rating={fire_rating_id}, temp={failure_temp_id}')

        dft_mm = dft_row['dft_mm']

        # Apply offset
        product = db.execute('SELECT offset_dft FROM products WHERE id = ?', (product_id,)).fetchone()
        offset_dft = product['offset_dft'] if product and product['offset_dft'] else 0.0
        final_dft_mm = dft_mm + offset_dft

        return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                            hp_over_a_band=hp_over_a_band, hp_over_a=hp_over_a,
                            heated_perimeter=heated_perimeter,
                            composite_use_band=composite_use_band, use_band=use_band,
                            coverage_id=coverage_id, dft_mm=dft_mm,
                            offset_dft=offset_dft, final_dft_mm=final_dft_mm,
                            status='ok')

    except Exception as e:
        return _make_result(section_id, hp_profile_name, product_id, fire_rating_id, failure_temp_id,
                            status='error', error=str(e))
