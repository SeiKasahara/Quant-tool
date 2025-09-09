import json
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_invalid_pattern_rejected():
    payload = {"foo": ["(unclosed"]}
    resp = client.put('/event-patterns', json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert 'validation_errors' in body.get('detail', {})
