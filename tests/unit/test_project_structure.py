"""Smoke test: verify all key modules are importable."""
import importlib


def test_app_main_importable():
    mod = importlib.import_module("app.main")
    assert hasattr(mod, "app")


def test_worker_package_importable():
    importlib.import_module("worker")


def test_app_api_package_importable():
    importlib.import_module("app.api")
