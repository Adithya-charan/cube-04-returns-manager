"""
Test configuration.

The production app uses OllamaQwenVisionProvider. Tests must NOT reach Ollama.
We override the module-level vision_provider in main.py with MockVisionProvider
so the full pipeline is exercised deterministically without network I/O.
"""
import os
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / f"returns_manager_tests_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

import src.main as main_module
from src.vision import MockVisionProvider
from src.database import Base
from src.db_config import engine


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create all tables once per test session; tear down afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)


@pytest.fixture(scope="session", autouse=True)
def inject_mock_vision():
    """
    Replace production OllamaQwenVisionProvider with MockVisionProvider for ALL tests.
    Restores original provider after session ends.
    """
    os.environ["VISION_PROVIDER"] = "mock"
    os.environ["DETECTION_PROVIDER"] = "mock"
    original = getattr(main_module, "vision_provider", None)
    mock_prov = MockVisionProvider(delay_ms=0)
    main_module.vision_provider = mock_prov
    yield
    if original is not None:
        main_module.vision_provider = original



@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app) as c:
        yield c
