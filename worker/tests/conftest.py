from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def orca_fixture():
    return lambda name: FIXTURES / "orca" / name
