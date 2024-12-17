from unittest.mock import patch
import pytest

@pytest.fixture(scope="module")
def mock_conda():
    with patch("src.ersilia_pack.parsers.install_parser.eval_conda_prefix", return_value=""):
        yield