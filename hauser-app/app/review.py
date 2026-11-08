"""Estimator-controlled timber-frame review prototype.
Geometry and cut schedules are illustrative, NOT structural design.
"""
import copy
import io
import json
import math
import sqlite3
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api/review', tags=['Estimator review'])
DATA = Path(__file__).resolve().parent.parent / 'data'
DB = DATA / 'review.sqlite3'


def connection():
    DATA.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return c


def sample():
    return {'id':'demo','name':'Hauser demonstration · Front wall W-014','revision':1,
            'geometry':{'length_mm':6000,'height_mm':2400,'stud_spacing_mm':600,'stud_width_mm':45,'stud_depth_mm':145,
                        'opening':{'id':'OP-003','x_mm':2200,'sill_mm':900,'width_mm':1200,'height_mm':1100}},
            'specification':{'timber_grade':'C24','timber_section':'45 × 145 mm','osb_sheet_mm':[2400,1200],
                             'osb_thickness_mm':11,'timber_stock_lengths_mm':[2400,3000,3600,4200,4800,6000],
                             'kerf_mm':3,'timber_rate_gbp_per_m':3.2,'osb_rate_gbp_per_sheet':19.5},
            'issues':[], 'approvals':{'geometry':None,'specifications':None,'estimate':None},
            'events':[{'type':'created','revision':1,'note':'Illustrative sample geometry; not extracted from drawings'}]}


def get_project(pid):
    with connection() as c:
        row = c.execute('SELECT payload FROM projects WHERE id=?',(pid,)).fetchone()
        if not row:
            if pid != 'demo': raise HTTPException(404,'Review project not found')
            p=sample();c.execute('INSERT INTO projects VALUES (?,?)',(pid,json.dumps(p)))
            return p
    return json.loads(row['payload'])


def save(p):
    with connection() as c:
        c.execute('INSERT OR REPLACE INTO projects VALUES (?,?)',(p['id'],json.dumps(p)))


def invalidate(p,reason):
    p['revision']+=1
    p['approvals']={'geometry':None,'specifications':None,'estimate':None}
    p['events'].append({'type':'revision','revision':p['revision'],'note':reason})


def members(p):
    g=p['geometry']; w=g['length_mm']; h=g['height_mm']; o=g['opening']; x=o['x_mm']; right=x+o['width_mm']; sill=o['sill_mm']; top=sill+o['height_mm']; sw=g['stud_width_mm']; sd=g['stud_depth_mm']
    out=[]
    def add(kind, label, xx, yy, length, orientation='vertical'):
        if length<=0: return
        out.append({'id':f'M-{len(out)+1:03}','kind':kind,'label':label,'x_mm':round(xx,2),'y_mm':round(yy,2),'length_mm':round(length,2),'orientation':orientation,'width_mm':sw,'depth_mm':sd,'grade':p['specification']['timber_grade']})
    add('rail','Bottom rail',0,0,w,'horizontal');add('rail','Top rail',0,h-sw,w,'horizontal')
    # Demonstration layout only. Header/king/jack dimensions require approved framing rules.
    for xx in sorted(set([0,w-sw]+list(range(0,w,g['stud_spacing_mm'])))):
        if xx+sw>x and xx<right: continue
        add('stud','Full-height stud',xx,sw,h-2*sw)
    add('king','Left king stud',x-sw,sw,h-2*sw)
    add('king','Right king stud',right,sw,h-2*sw)
    add('trimmer','Left opening support',x,sw,top-sw)
    add('trimmer','Right opening support',right-sw,sw,top-sw)
    add('header','Lintel placeholder — structural selection required',x,top,o['width_mm'],'horizontal')
    add('sill','Window sill rail',x,sill-sw,o['width_mm'],'horizontal')
    for xx in range(x+g['stud_spacing_mm'],right,g['stud_spacing_mm']):
        add('cripple','Under-sill short stud',xx,sw,sill-2*sw)
        add('cripple','Above-lintel short stud',xx,top+sw,h-top-2*sw)
    return out


def elements(p):
    g=p['geometry'];o=g['opening']
    return [{'id':'W-014','kind':'wall','label':'Front wall','x_mm':0,'y_mm':0,'width_mm':g['length_mm'],'height_mm':g['height_mm']},
            {'id':o['id'],'kind':'opening','label':'Window opening','x_mm':o['x_mm'],'y_mm':o['sill_mm'],'width_mm':o['width_mm'],'height_mm':o['height_mm']}] + members(p)


def validate_geometry(g):
    o=g['opening'];w=g['length_mm'];h=g['height_mm']
    if not (1000<=w<=30000 and 1000<=h<=8000 and 200<=g['stud_spacing_mm']<=1200): raise HTTPException(422,'Wall dimensions or spacing outside prototype limits')
    if not (0<o['width_mm']<w and 0<o['height_mm']<h and 0<=o['x_mm'] and 0<=o['sill_mm'] and o['x_mm']+o['width_mm']<=w and o['sill_mm']+o['height_mm']<=h): raise HTTPException(422,'Opening must fit within wall')


class IssueIn(BaseModel):
    element_id: str
    category: str
    comment: str = Field(min_length=3,max_length=2000)
    proposed_field: str | None = None
    proposed_value_mm: int | None = None


@router.get('/{pid}')
def project(pid:str):
    p=get_project(pid)
    return {**p,'elements':elements(p),'warnings':['Illustrative framing only; no approved lintel/header sizing or structural verification','Drawing extraction and automatic correction from natural language are not implemented']}


@router.post('/{pid}/issues')
def create_issue(pid:str, payload:IssueIn):
    p=get_project(pid)
    if payload.element_id not in {e['id'] for e in elements(p)}: raise HTTPException(422,'Select a valid element')
    if payload.proposed_field is not None and payload.proposed_field not in {'width_mm','height_mm','x_mm','sill_mm'}: raise HTTPException(422,'Only opening dimensions can be directly proposed in this prototype')
    if payload.proposed_field is not None and (payload.element_id!='OP-003' or payload.proposed_value_mm is None): raise HTTPException(422,'Numeric correction requires opening and value')
    proposal=None
    if payload.proposed_field:
        g=copy.deepcopy(p['geometry']);g['opening'][payload.proposed_field]=payload.proposed_value_mm
        validate_geometry(g)
        proposal={'field':payload.proposed_field,'from_mm':p['geometry']['opening'][payload.proposed_field],'to_mm':payload.proposed_value_mm}
    issue={'id':str(uuid.uuid4())[:8],'element_id':payload.element_id,'category':payload.category,'comment':payload.comment,'status':'open','proposal':proposal,'created_revision':p['revision']}
    p['issues'].append(issue)
    p['approvals']={'geometry':None,'specifications':None,'estimate':None}
    p['events'].append({'type':'issue','issue_id':issue['id'],'note':payload.comment})
    save(p)
    return issue


@router.post('/{pid}/issues/{issue_id}/apply')
def apply_issue(pid:str,issue_id:str):
    p=get_project(pid);issue=next((i for i in p['issues'] if i['id']==issue_id),None)
    if not issue: raise HTTPException(404,'Issue not found')
    if issue['status']!='open' or not issue['proposal']: raise HTTPException(409,'Issue has no unapplied numeric proposal')
    prop=issue['proposal']
    if p['geometry']['opening'][prop['field']]!=prop['from_mm']: raise HTTPException(409,'Proposal is stale; create a new issue')
    p['geometry']['opening'][prop['field']]=prop['to_mm'];validate_geometry(p['geometry'])
    issue['status']='resolved';invalidate(p,f"Applied {issue_id}: {prop['field']} {prop['from_mm']} → {prop['to_mm']} mm")
    save(p)
    return project(pid)


@router.post('/{pid}/issues/{issue_id}/close')
def close_issue(pid:str,issue_id:str):
    p=get_project(pid);issue=next((i for i in p['issues'] if i['id']==issue_id),None)
    if not issue: raise HTTPException(404,'Issue not found')
    issue['status']='closed_without_change';p['events'].append({'type':'issue_closed','issue_id':issue_id,'note':'Closed without model change'})
    save(p);return issue


class ApprovalIn(BaseModel):
    reviewer: str = Field(min_length=2,max_length=120)


@router.post('/{pid}/approve/{stage}')
def approve(pid:str,stage:str,payload:ApprovalIn):
    if stage not in ('geometry','specifications','estimate'): raise HTTPException(404,'Unknown gate')
    p=get_project(pid)
    if any(i['status']=='open' for i in p['issues']): raise HTTPException(409,'Resolve or close all issues before approval')
    if stage=='specifications' and not p['approvals']['geometry']: raise HTTPException(409,'Approve geometry first')
    if stage=='estimate' and not p['approvals']['specifications']: raise HTTPException(409,'Approve specifications first')
    if stage=='estimate': raise HTTPException(409,'Estimate approval unavailable: structural lintel schedule and full kit cost validation not implemented')
    p['approvals'][stage]={'revision':p['revision'],'reviewer':payload.reviewer}
    p['events'].append({'type':'approved','stage':stage,'revision':p['revision'],'reviewer':payload.reviewer})
    save(p);return p['approvals']


def cut_plan(p):
    """First-fit decreasing over permitted lengths; preliminary, not globally optimal."""
    stock=sorted(p['specification']['timber_stock_lengths_mm']);kerf=p['specification']['kerf_mm']
    items=sorted(members(p),key=lambda m:m['length_mm'],reverse=True)
    bins=[]
    for m in items:
        length=m['length_mm']
        candidate=None
        for b in bins:
            if b['remaining_mm']>=length+(0 if not b['cuts'] and length==b['stock_length_mm'] else kerf):
                if candidate is None or b['remaining_mm']<candidate['remaining_mm']:candidate=b
        if candidate is None:
            choices=[s for s in stock if s>=length+kerf or s==length]
            if not choices: raise HTTPException(422,f"Member {m['id']} is longer than available stock")
            candidate={'stock_length_mm':min(choices),'remaining_mm':min(choices),'cuts':[]};bins.append(candidate)
        cut_kerf=0 if not candidate['cuts'] and length==candidate['stock_length_mm'] else kerf
        candidate['cuts'].append({'member_id':m['id'],'length_mm':length,'kerf_mm':cut_kerf});candidate['remaining_mm']-=length+cut_kerf
    bought=sum(b['stock_length_mm'] for b in bins);installed=sum(m['length_mm'] for m in items)
    kerf_total=sum(c['kerf_mm'] for b in bins for c in b['cuts']);offcuts=bought-installed-kerf_total
    area=p['geometry']['length_mm']*p['geometry']['height_mm']-p['geometry']['opening']['width_mm']*p['geometry']['opening']['height_mm']
    sheet_w,sheet_h=p['specification']['osb_sheet_mm'];sheet_area=sheet_w*sheet_h
    return {'method':'first-fit decreasing heuristic (not guaranteed optimal)','provisional':True,
            'timber':{'members':len(items),'stock_pieces':len(bins),'stock_mm':bought,'installed_mm':installed,'kerf_mm':kerf_total,'offcut_mm':offcuts,'waste_percent':round((bought-installed)/bought*100,2) if bought else 0,'stock_cost_gbp':round(bought/1000*p['specification']['timber_rate_gbp_per_m'],2),'bins':bins},
            'osb':{'net_area_m2':round(area/1e6,3),'sheet_size_mm':[sheet_w,sheet_h],'theoretical_min_sheets':math.ceil(area/sheet_area),'note':'Area-only lower bound. Sheet nesting, joints, opening cut-outs and offcut reuse are NOT implemented.'},
            'warnings':['Header is a non-structural placeholder; validate against approved engineering details','Insulation nesting, OSB 2D nesting, offcut inventory and full kit costing are not implemented']}


@router.get('/{pid}/cut-plan')
def cuts(pid:str):
    p=get_project(pid)
    if not p['approvals']['geometry'] or not p['approvals']['specifications']:raise HTTPException(409,'Approve geometry and specifications before provisional cutting calculations')
    return cut_plan(p)


@router.get('/{pid}/model.glb')
def model(pid:str):
    p=get_project(pid)
    if not p['approvals']['geometry'] or not p['approvals']['specifications']:raise HTTPException(409,'Approve geometry and specifications before GLB export')
    try:
        import trimesh
        scene=trimesh.Scene()
        for m in members(p):
            # Coordinates in metres; wall lies in XY, depth in Z.
            sw=m['width_mm']/1000;length=m['length_mm']/1000;depth=m['depth_mm']/1000
            if m['orientation']=='horizontal':
                extents=[length,sw,depth];center=[(m['x_mm']+m['length_mm']/2)/1000,(m['y_mm']+m['width_mm']/2)/1000,0]
            else:
                extents=[sw,length,depth];center=[(m['x_mm']+m['width_mm']/2)/1000,(m['y_mm']+m['length_mm']/2)/1000,0]
            mesh=trimesh.creation.box(extents=extents)
            mesh.apply_translation(center)
            mesh.visual.face_colors=[178,130,78,255] if m['kind'] not in ('header','trimmer') else [224,154,78,255]
            scene.add_geometry(mesh,geom_name=m['id'],node_name=m['id'])
        blob=scene.export(file_type='glb')
        return Response(blob,media_type='model/gltf-binary',headers={'Content-Disposition':'attachment; filename="hauser-review-kit.glb"'})
    except ImportError:raise HTTPException(503,'Install trimesh to enable GLB export')
