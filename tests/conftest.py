"""Shared test configuration."""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def temp_work_dir():
    """Provide temporary work directory for tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="pytest_cprobe_test_"))
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)