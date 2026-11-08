from app.importers import pixels_to_metres, candidates_from_text

def test_scale():
    assert pixels_to_metres(300, 150, 3) == 6

def test_labels():
    values, warnings = candidates_from_text('Wall area: 125 m2\nFloor area: 90 m2')
    assert values['wall_area_m2'] == 125
    assert values['floor_area_m2'] == 90
    assert warnings
