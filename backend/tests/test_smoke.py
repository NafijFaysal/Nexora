"""Smoke test: the test setup can import this project's own packages.

A failure here means a problem with the environment (running from the wrong folder,
a missing pythonpath setting, or another package named `app` being found first),
not a problem with decision logic.
"""

import importlib
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_app_package_imports_from_backend_folder() -> None:
    app = importlib.import_module("app")

    # Checking the location guards against importing an unrelated installed package
    # that happens to be called "app".
    assert Path(app.__file__).resolve().parent == BACKEND_DIR / "app"


def test_engine_package_imports_from_backend_folder() -> None:
    engine = importlib.import_module("app.engine")

    assert Path(engine.__file__).resolve().parent == BACKEND_DIR / "app" / "engine"
