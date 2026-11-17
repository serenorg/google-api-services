# ABOUTME: Exercises gateway access on the real nano-banana FastAPI routes.
# ABOUTME: Covers refusals, configured access and the public health endpoint without Gemini spend.

import importlib.util
import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient

from shared.config import get_settings


def test_nano_banana_gateway_access():
    service_dir = Path(__file__).resolve().parents[1] / "nano-banana"
    previous = {name: os.environ.get(name) for name in ("GATEWAY_SECRET", "GOOGLE_AI_STUDIO_API_KEY")}
    os.environ["GATEWAY_SECRET"] = "test-only-gateway-secret"
    os.environ["GOOGLE_AI_STUDIO_API_KEY"] = ""
    get_settings.cache_clear()
    sys.path.insert(0, str(service_dir))
    try:
        spec = importlib.util.spec_from_file_location("nano_banana_main", service_dir / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TestClient(module.app) as client:
            for route in ("/generate", "/generate/4k", "/edit", "/blend"):
                # Even invalid bodies must be refused before entering a paid route.
                assert client.post(route, json={}).status_code == 401
                assert client.post(route, json={}, headers={"X-Seren-Gateway-Secret": "wrong"}).status_code == 401
                assert client.post(route, json={}, headers={"X-Seren-Gateway-Secret": "test-only-gateway-secret"}).status_code == 422
            assert client.get("/health").status_code == 200
            for unconfigured in (None, ""):
                if unconfigured is None:
                    os.environ.pop("GATEWAY_SECRET", None)
                else:
                    os.environ["GATEWAY_SECRET"] = unconfigured
                get_settings.cache_clear()
                for route in ("/generate", "/generate/4k", "/edit", "/blend"):
                    assert client.post(route, json={}).status_code == 503
                    assert client.post(route, json={}, headers={"X-Seren-Gateway-Secret": "test-only-gateway-secret"}).status_code == 503
                assert client.get("/health").status_code == 200
    finally:
        sys.path.remove(str(service_dir))
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        get_settings.cache_clear()
