"""
Test configuration.

The production app uses OllamaQwenVisionProvider. Tests must NOT reach Ollama.
We override the module-level vision_provider in main.py with MockVisionProvider
so the full pipeline is exercised deterministically without network I/O.
"""
import pytest
from fastapi.testclient import TestClient
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


@pytest.fixture(scope="session", autouse=True)
def inject_mock_vision():
    """
    Replace production OllamaQwenVisionProvider with MockVisionProvider for ALL tests.
    Restores original provider after session ends.
    """
    original = main_module.vision_provider
    main_module.vision_provider = MockVisionProvider(delay_ms=0)
    yield
    main_module.vision_provider = original


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app) as c:
        yield c
