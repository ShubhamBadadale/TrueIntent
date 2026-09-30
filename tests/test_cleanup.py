"""Boundary regressions: no network, bounded images, honest missing results."""
import io
from types import SimpleNamespace

import joblib
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.app import main
from ml import model_loading, predict_module_b as b, predict_module_c as c
from ml.ocr_module_c import _load_image

client = TestClient(main.app)


@pytest.mark.parametrize('url', ['http://[broken', 'https://example.com:bad', 'ftp://example.com', 'https://example.com\\@evil.com', 'https://exa\x00mple.com'])
def test_malformed_urls_are_client_errors(url):
    assert client.post('/check-url', json={'url': url}).status_code == 422
    assert client.post('/check-combined', json={'url': url}).status_code == 422


def test_live_fetch_is_disabled(monkeypatch):
    import socket
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: pytest.fail('Network access'))
    assert b.inspect_live_page('http://127.0.0.1/admin')[0] is False
    assert 'disabled' in b.inspect_live_page('http://169.254.169.254/')[2][0]


def test_brand_subdomains_are_not_typosquats():
    assert b.check_typosquatting('accounts.google.com')[0] is False
    assert b.check_typosquatting('google.com.evil.example')[0] is True


def test_embedded_urls_are_case_insensitive_and_deduplicated():
    assert c.extract_urls('HTTPS://example.com HTTPS://example.com') == ['HTTPS://example.com']


def test_model_cache_notices_replacement_deletion_and_corruption(tmp_path):
    from sklearn.dummy import DummyClassifier
    path = tmp_path / 'model.pkl'
    pipeline = DummyClassifier().fit([[0], [1]], [0, 1])
    joblib.dump(dict(pipeline=pipeline, marker=1), path)
    cached = model_loading.load_artifact(path)
    assert cached['marker'] == 1
    joblib.dump(dict(pipeline=pipeline, marker='replacement'), path)
    cached = model_loading.load_artifact(path, cached)
    assert cached['marker'] == 'replacement'
    path.write_bytes(b'broken')
    assert model_loading.load_artifact(path, cached) is None
    path.unlink()
    assert model_loading.load_artifact(path, cached) is None


def test_image_dimensions_and_disguised_format_rejected():
    with pytest.raises(OSError, match='million pixels'):
        _load_image(Image.new('1', (4000, 3000)))
    stream = io.BytesIO()
    Image.new('RGB', (2, 2)).save(stream, format='GIF')
    assert client.post('/check-message', files={'image': ('fake.png', stream.getvalue(), 'image/png')}).status_code == 400


def test_ocr_timeout_is_bounded(monkeypatch):
    import pytesseract
    from ml.ocr_module_c import extract_text_from_image
    def fake_ocr(image, **kwargs):
        assert kwargs['timeout'] == 15
        return 'hello'
    monkeypatch.setattr(pytesseract, 'image_to_string', fake_ocr)
    assert extract_text_from_image(Image.new('RGB', (2, 2))) == 'hello'


def test_empty_ocr_is_explicitly_unassessed(monkeypatch):
    from ml import ocr_module_c
    monkeypatch.setattr(ocr_module_c, 'extract_text_from_image', lambda _: '')
    response = client.post('/check-message', files={'image': ('blank.png', b'fixture', 'image/png')})
    assert response.status_code == 200
    assert response.json()['text_assessed'] is False
    assert response.json()['ocr_status'] == 'insufficient_text'


def test_text_resource_limits():
    assert client.post('/check-message', data={'text': 'x' * 20001}).status_code == 422
    assert client.post('/check-combined', json={'text': 'x' * 20001}).status_code == 422


def test_nonfinite_url_model_output_falls_back(monkeypatch):
    import numpy as np
    pipeline = SimpleNamespace(classes_=[0, 1], predict_proba=lambda _: np.array([[0., np.nan]]))
    monkeypatch.setattr(b, '_load_ml_model', lambda: {'pipeline': pipeline})
    result = b.check_url('https://example.com')
    assert result['score'] == 0
    assert 'inference failed' in result['ml_status']
