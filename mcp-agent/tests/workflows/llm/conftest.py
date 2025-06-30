import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_context():
    """Common mock context fixture usable by all provider tests"""
    mock_context = MagicMock()
    mock_context.executor = MagicMock()
    mock_context.model_selector = MagicMock()
    return mock_context
