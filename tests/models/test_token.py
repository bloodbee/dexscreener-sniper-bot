from datetime import datetime
import pytest
from src.models.token import Token


class TestToken:

    def test_token_initialization(self, mock_token):
        """Test basic token initialization with required fields"""
        assert mock_token.address == "0x123abc"
        assert mock_token.symbol == "TEST"
        assert mock_token.name == "Test Token"
        assert mock_token.chain_id == "solana"
        assert mock_token.status == "normal"
        assert mock_token.fake_volume_detected is False
        assert mock_token.rugcheck_status == "unknown"
        assert mock_token.supply_bundled is False

    def test_parse_from_dexscreener_data(self, sample_token_data):
        """Test parsing token data from Dexscreener API response"""
        token = Token.parse(sample_token_data)

        assert token.address == "0x123abc"
        assert token.symbol == "TEST"
        assert token.name == "Test Token"
        assert token.chain_id == "solana"
        assert token.current_price == 1.23
        assert token.volume_24h == 100000.50
        assert token.liquidity == 500000.75
        assert token.fdv == 1000000.00
        assert token.max_price == 1.23
        assert token.min_price == 1.23

    def test_update_price(self, mock_token):
        """Test price update functionality"""
        initial_time = mock_token.last_updated

        # Wait a small amount to ensure timestamp difference
        import time

        time.sleep(0.001)

        mock_token.update_price(2.0)

        assert mock_token.current_price == 2.0
        assert mock_token.max_price == 2.0
        assert mock_token.min_price == 0.0
        assert mock_token.last_updated > initial_time

    def test_update_price_multiple_times(self, mock_token):
        """Test price updates with multiple values to verify max/min tracking"""
        prices = [1.0, 2.5, 0.5, 1.75]

        for price in prices:
            mock_token.update_price(price)

        assert mock_token.current_price == 1.75
        assert mock_token.max_price == 2.5
        assert mock_token.min_price == 0.0

    def test_parse_invalid_data(self):
        """Test parsing with invalid data structure"""
        invalid_data = {"baseToken": {}, "chainId": "solana"}

        with pytest.raises(KeyError):
            Token.parse(invalid_data)
