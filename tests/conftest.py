import pytest
import json
from src.models.token import Token


@pytest.fixture
def load_json():
    """Fixture to load JSON data from a given file path."""

    def _load_json(filepath):
        with open(filepath, "r") as f:
            return json.load(f)

    return _load_json


@pytest.fixture
def load_file():
    """Fixture to load JSON data from a given file path."""

    def _load_file(filepath):
        with open(filepath, "r") as f:
            return f.read()

    return _load_file


@pytest.fixture
def sample_token_data():
    return {
        "baseToken": {"address": "0x123abc", "symbol": "TEST", "name": "Test Token"},
        "chainId": "solana",
        "priceUsd": "1.23",
        "volume": {"h24": "100000.50"},
        "liquidity": {"usd": "500000.75"},
        "fdv": "1000000.00",
        "priceChange": {"h24": 1},
    }


@pytest.fixture
def mock_token():
    return Token(
        address="0x123abc", symbol="TEST", name="Test Token", chain_id="solana", current_price=1.0
    )
