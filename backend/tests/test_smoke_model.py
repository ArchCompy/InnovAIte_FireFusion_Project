"""Smoke tests for model-api (ML inference service)."""
import os

import pytest

# model-api serves output to other services, so /model/geojson requires the key.
API_KEY = os.getenv("API_KEY", "local-development-key")

pytestmark = pytest.mark.integration


def test_model_hello(model, http):
    r = http.get(f"{model}/model/hello")
    assert r.status_code == 200
    assert r.json() == {"message": "Hello from model-api"}


def test_model_geojson_is_feature_collection(model, http):
    r = http.get(f"{model}/model/geojson", headers={"X-API-Key": API_KEY})
    assert r.status_code == 200
    body = r.json()
    # served risk layer should be GeoJSON (FeatureCollection) or a list of them
    if isinstance(body, dict):
        assert body.get("type") == "FeatureCollection"
    else:
        assert isinstance(body, list)
