def calculate_member_quantities(dft_mm, heated_perimeter_mm, length_m, quantity, solid_factor, density):
    if not dft_mm or dft_mm <= 0 or not heated_perimeter_mm or not length_m:
        return {'surface_area_m2': 0.0, 'volume_litres': 0.0, 'weight_kg': 0.0}

    surface_area_m2 = (heated_perimeter_mm / 1000) * length_m * quantity
    volume_litres = surface_area_m2 * (dft_mm / 1000) / (solid_factor if solid_factor else 1) * 1000
    weight_kg = volume_litres * (density if density else 1)

    return {
        'surface_area_m2': round(surface_area_m2, 3),
        'volume_litres': round(volume_litres, 2),
        'weight_kg': round(weight_kg, 2),
    }
