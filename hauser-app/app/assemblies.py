"""Configurable, non-structural timber-frame assembly takeoff calculations."""
from copy import deepcopy
from math import ceil, isfinite

PRESETS = [
    {"id":"external-wall-140","name":"External wall — 140 mm mineral wool","category":"wall","description":"Illustrative external wall build-up; not an approved design.","layers":[
        {"id":"studs","name":"C24 studs 45 × 140","kind":"linear","unit":"m","rate":3.2,"waste_percent":10,"parameters":{"spacing_mm":600,"height_m":2.4,"extra_members":2}},
        {"id":"wool","name":"Mineral wool 140 mm between studs","kind":"area","unit":"m²","rate":12,"waste_percent":5,"parameters":{"coverage_factor":0.9,"thickness_mm":140}},
        {"id":"osb","name":"OSB3 11 mm sheathing","kind":"sheet","unit":"sheet","rate":18,"waste_percent":10,"parameters":{"sheet_width_m":1.22,"sheet_height_m":2.44}},
        {"id":"membrane","name":"Breather membrane","kind":"area","unit":"m²","rate":2.5,"waste_percent":10,"parameters":{}}]},
    {"id":"partition-89","name":"Internal partition — 89 mm acoustic wool","category":"wall","description":"Illustrative non-loadbearing partition.","layers":[
        {"id":"studs","name":"C24 studs 45 × 89","kind":"linear","unit":"m","rate":2.3,"waste_percent":10,"parameters":{"spacing_mm":400,"height_m":2.4,"extra_members":2}},
        {"id":"wool","name":"Acoustic mineral wool 89 mm","kind":"area","unit":"m²","rate":8,"waste_percent":5,"parameters":{"coverage_factor":0.9,"thickness_mm":89}},
        {"id":"board","name":"Plasterboard both faces","kind":"area","unit":"m²","rate":7,"waste_percent":10,"parameters":{"faces":2}}]},
    {"id":"floor-joists","name":"Intermediate floor — timber joists","category":"floor","description":"Illustrative floor; spans and structural sizing must be verified.","layers":[
        {"id":"joists","name":"Timber joists","kind":"linear","unit":"m","rate":4.8,"waste_percent":10,"parameters":{"spacing_mm":400,"span_m":4.0}},
        {"id":"deck","name":"Floor decking","kind":"sheet","unit":"sheet","rate":22,"waste_percent":10,"parameters":{"sheet_width_m":1.22,"sheet_height_m":2.44}},
        {"id":"acoustic","name":"Acoustic insulation between joists","kind":"area","unit":"m²","rate":9,"waste_percent":5,"parameters":{"coverage_factor":0.9}}]},
    {"id":"pitched-roof","name":"Pitched roof — insulated rafters","category":"roof","description":"Illustrative roof; use true sloping surface area, not plan area.","layers":[
        {"id":"rafters","name":"Timber rafters","kind":"linear","unit":"m","rate":5,"waste_percent":10,"parameters":{"spacing_mm":600,"slope_length_m":4.0}},
        {"id":"insulation","name":"Between-rafter mineral wool","kind":"area","unit":"m²","rate":13,"waste_percent":5,"parameters":{"coverage_factor":0.9}},
        {"id":"deck","name":"Roof deck","kind":"sheet","unit":"sheet","rate":20,"waste_percent":10,"parameters":{"sheet_width_m":1.22,"sheet_height_m":2.44}}]},
]

def validate_assembly(a):
    if not isinstance(a,dict) or a.get('category') not in ('wall','floor','roof') or not isinstance(a.get('name'),str) or not a['name'].strip():
        raise ValueError('Assembly needs a name and wall, floor or roof category')
    layers=a.get('layers')
    if not isinstance(layers,list) or not layers or len(layers)>50: raise ValueError('Provide 1–50 layers')
    ids=[]
    for l in layers:
        if not isinstance(l,dict) or l.get('kind') not in ('area','linear','sheet','fixed') or not isinstance(l.get('name'),str) or not l['name'].strip():
            raise ValueError('Each layer needs a name and valid kind')
        if not isinstance(l.get('id'),str) or not l['id'].strip(): raise ValueError('Each layer needs an ID')
        ids.append(l['id'])
        for k in ('rate','waste_percent'):
            v=l.get(k,0)
            if not isinstance(v,(int,float)) or not isfinite(v) or v<0 or (k=='waste_percent' and v>100): raise ValueError('Invalid '+k)
        p=l.get('parameters',{})
        if not isinstance(p,dict): raise ValueError('Layer parameters must be an object')
        for v in p.values():
            if not isinstance(v,(int,float)) or not isfinite(v) or v<0: raise ValueError('Invalid layer parameter')
    if len(set(ids))!=len(ids): raise ValueError('Layer IDs must be unique')
    return deepcopy(a)

def takeoff(a, geometry):
    """Area input is NET surface area after openings; linear framing uses gross run/height.
    This is a provisional material model, not engineering, and assumes rectangular geometry.
    """
    validate_assembly(a)
    area=float(geometry.get('area_m2',0)); length=float(geometry.get('length_m',0)); height=float(geometry.get('height_m',2.4))
    if any(not isfinite(x) or x<0 for x in (area,length,height)): raise ValueError('Geometry must be non-negative finite numbers')
    if a['category']=='wall' and area==0 and length>0: area=length*height
    lines=[]
    for layer in a['layers']:
        p=layer.get('parameters',{}); kind=layer['kind']; qty=0
        if kind=='area': qty=area*float(p.get('coverage_factor',1))*float(p.get('faces',1))
        elif kind=='sheet':
            sheet_area=float(p.get('sheet_width_m',1.22))*float(p.get('sheet_height_m',2.44))
            if sheet_area<=0: raise ValueError('Sheet dimensions must be positive')
            qty=ceil(area*float(p.get('faces',1))/sheet_area)
        elif kind=='fixed': qty=float(p.get('quantity',1))
        elif kind=='linear':
            spacing=float(p.get('spacing_mm',600))
            if spacing<=0: raise ValueError('Spacing must be positive')
            if a['category']=='wall':
                run=length if length>0 else (area/height if height>0 else 0)
                qty=(ceil(run*1000/spacing)+1+int(p.get('extra_members',0)))*height if run>0 else 0
            else:
                span=float(p.get('span_m',p.get('slope_length_m',0)))
                if span<=0: raise ValueError('Joist/rafter span must be positive')
                width=area/span
                qty=(ceil(width*1000/spacing)+1)*span if area>0 else 0
        waste=float(layer.get('waste_percent',0))/100
        order_qty=ceil(qty*(1+waste)) if kind=='sheet' else round(qty*(1+waste),3)
        lines.append({'layer_id':layer['id'],'name':layer['name'],'kind':kind,'unit':layer.get('unit','m²'),'net_quantity':round(qty,3),'order_quantity':order_qty,'rate':layer['rate'],'amount':round(order_qty*float(layer['rate']),2)})
    return {'assembly_id':a['id'],'assembly_name':a['name'],'category':a['category'],'geometry':{'area_m2':area,'length_m':length,'height_m':height},'lines':lines,'subtotal':round(sum(l['amount'] for l in lines),2),'provisional':True,'warnings':['Illustrative formulas: confirm member counts, openings, spans, layer coverage, waste and specifications before quoting.']}
