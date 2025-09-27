import pytest
import os
from pathlib import Path


@pytest.fixture(scope="session")
def asset_folder() -> str:
    return Path(os.path.join(os.path.dirname(__file__), "examples", "seed"))
