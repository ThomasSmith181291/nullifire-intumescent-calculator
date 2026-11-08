import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app
from app import review


def test_review_workflow(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'DATA',tmp_path)
    monkeypatch.setattr(review,'DB',tmp_path/'review.sqlite3')
    c=TestClient(app)
    p=c.get('/api/review/demo').json()
    assert p['geometry']['opening']['width_mm']==1200
    assert c.get('/api/review/demo/cut-plan').status_code==409
    issue=c.post('/api/review/demo/issues',json={'element_id':'OP-003','category':'Incorrect dimension','comment':'Correct width from drawing','proposed_field':'width_mm','proposed_value_mm':1500}).json()
    assert issue['proposal']['to_mm']==1500
    assert c.post('/api/review/demo/approve/geometry',json={'reviewer':'Estimator'}).status_code==409
    assert c.post(f"/api/review/demo/issues/{issue['id']}/apply").status_code==200
    p=c.get('/api/review/demo').json()
    assert p['geometry']['opening']['width_mm']==1500 and p['revision']==2
    assert c.post('/api/review/demo/approve/geometry',json={'reviewer':'Estimator'}).status_code==200
    assert c.post('/api/review/demo/approve/specifications',json={'reviewer':'Estimator'}).status_code==200
    assert c.get('/api/review/demo/cut-plan').status_code==200
    assert c.get('/api/review/demo/model.glb').content[:4]==b'glTF'
    assert c.post('/api/review/demo/approve/estimate',json={'reviewer':'Estimator'}).status_code==409


def test_invalid_opening(tmp_path,monkeypatch):
    monkeypatch.setattr(review,'DATA',tmp_path);monkeypatch.setattr(review,'DB',tmp_path/'review.sqlite3')
    c=TestClient(app)
    r=c.post('/api/review/demo/issues',json={'element_id':'OP-003','category':'Width','comment':'Too wide','proposed_field':'width_mm','proposed_value_mm':99999})
    assert r.status_code==422
