import sys
from pathlib import Path

import pytest

# Add scripts/ to path so briefbot_engine is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.fixture
def FIXTURES_DIR():
    """Return the absolute path to the fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"
