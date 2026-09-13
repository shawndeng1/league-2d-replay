import json
import pytest
from fastapi.testclient import TestClient
from server import app as api

def test_health_and_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(api,'STORE',tmp_path)
    with TestClient(api.app) as client:
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/replays/not-an-id').status_code == 404
        assert client.post('/api/replays',files={'file':('bad.txt',b'123')}).status_code == 415
        response = client.post('/api/replays',files={'file':('bad.rofl',b'123')})
        assert response.status_code == 422
        assert response.json()['detail']['code'] == 'INVALID_REPLAY'
    assert not list(tmp_path.glob('*.rofl'))
    assert not api.parse_lock.locked()

def test_real_upload_read_workflow(tmp_path,monkeypatch,replay_file,replay_parser):
    if not replay_parser.client_exe.is_file(): pytest.skip('Exact client required for semantic integration')
    monkeypatch.setattr(api,'STORE',tmp_path)
    monkeypatch.setattr(api,'CLIENT',str(replay_parser.client_exe))
    with TestClient(api.app) as client, replay_file.open('rb') as handle:
        response = client.post('/api/replays',files={'file':(replay_file.name,handle,'application/octet-stream')})
        assert response.status_code == 201, response.text
        replay_id = response.json()['id']
        data = client.get(f'/api/replays/{replay_id}/data').json()
        assert len(data['players']) == 10
        assert data['diagnostics']['sampleCount'] == 56432
        assert client.get(f'/api/replays/{replay_id}/metadata').json()['metadata']['patch'] == '16.18.817.5716'
        assert json.loads((tmp_path/f'{replay_id}.json').read_text()) == data
    assert not list(tmp_path.glob('*.rofl'))
