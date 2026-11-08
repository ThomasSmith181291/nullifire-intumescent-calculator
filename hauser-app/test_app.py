import io
import os
import tempfile
from pathlib import Path

os.environ['HAUSER_DATA_DIR'] = tempfile.mkdtemp(prefix='hauser-test-')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def sample_pdf():
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((70, 80), 'Wall area: 120 m2')
    page.insert_text((70, 110), 'Floor area: 80 m2')
    page.insert_text((70, 140), 'Wall length: 50 m')
    data = doc.tobytes()
    doc.close()
    return data


def test_workflow():
    assert client.get('/api/health').json()['ok']
    response = client.post('/api/jobs', files={'file': ('plan.pdf', sample_pdf(), 'application/pdf')})
    assert response.status_code == 201, response.text
    job = response.json()
    assert job['extraction']['candidates']['wall_area_m2'] == 120
    job_id = job['id']
    assert client.get(f'/api/jobs/{job_id}/export.pdf').status_code == 409
    result = client.put(f'/api/jobs/{job_id}', json={'quantities': {'wall_area_m2': 120, 'floor_area_m2': 80, 'wall_length_m': 50}, 'approved': True, 'notes': 'Verified against drawing'})
    assert result.status_code == 200, result.text
    assert result.json()['estimate']['total'] == 10332.0
    assert client.get(f'/api/jobs/{job_id}/export.pdf').content.startswith(b'%PDF-')
    assert b'Wall area' in client.get(f'/api/jobs/{job_id}/export.csv').content


def test_invalid_upload():
    assert client.post('/api/jobs', files={'file': ('bad.pdf', b'hello', 'application/pdf')}).status_code == 400
