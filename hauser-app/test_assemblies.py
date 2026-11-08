from app.assemblies import PRESETS,takeoff,validate_assembly

def test_wall_insulation_and_sheets():
    result=takeoff(PRESETS[0],{'area_m2':24,'length_m':10,'height_m':2.4})
    assert result['lines'][1]['net_quantity']==21.6
    assert result['lines'][2]['net_quantity']==9
    assert result['subtotal']>0

def test_floor_roof():
    for a in PRESETS[2:]:
        assert takeoff(a,{'area_m2':40})['subtotal']>0

def test_invalid_spacing():
    import pytest
    a=__import__('copy').deepcopy(PRESETS[0]);a['layers'][0]['parameters']['spacing_mm']=0
    with pytest.raises(ValueError):takeoff(a,{'area_m2':20,'length_m':8})
