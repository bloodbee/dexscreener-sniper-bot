import pytest
import asyncio
import json
import pytest_asyncio
import aiohttp
from aioresponses import aioresponses
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from src.dexscreener_bot import DexScreenerBot
from src.models.token import Token


@pytest.fixture
def mock_config():
    return {
        "api_settings": {
            "dexscreener_api_url": "https://api.dexscreener.com",
            "rugcheck_url": "https://api.rugcheck.xyz",
            "request_delay": 1,
        },
        "telegram_settings": {
            "telegram_bot_token": "test_bot_token",
            "telegram_chat_id": "test_chat_id",
        },
        "toxi_bot_settings": {
            "telegram_api_id": "11111111",
            "telegram_api_hash": "xxxxxxxxx",
            "telegram_phone_number": "+011212121212"
        },
        "transaction_settings": {
            "amountInSol": 0.1,
            "amountInToken": 100
        },
        "filters": {
            "min_liquidity": 5000,
            "min_volume_24h": 10000,
            "min_fdv": 100000,
            "max_price_change_24h": 50,
        },
        "supply_check": {"bundled_threshold": 0.8},
        "blacklisted_coins": [],
        "blacklisted_devs": [],
    }


@pytest.fixture
def bot(mock_config):
    with patch(
        "src.dexscreener_bot.DexScreenerBot._DexScreenerBot__load_config",
        return_value=mock_config,
    ), patch("telegram.Bot", return_value=MagicMock()) as mock_bot:
        bot = DexScreenerBot()
        mock_bot.send_message = AsyncMock()
        bot.telegram_bot = mock_bot
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot.session = aiohttp.ClientSession(loop=loop)
        yield bot

        loop.run_until_complete(bot.session.close())


class TestDexScreenerBot:

    @pytest.mark.asyncio
    async def test_fetch_api_data(self, bot, mock_token, load_json):
        endpoint = f"tokens/v1/solana/{mock_token.address}"
        url = f"{bot.dexscreener_url}/{endpoint}"
        mock_responses = load_json("tests/etc/fetch_api_data.json")
        with aioresponses() as m:
            m.get(url, payload=mock_responses, status=200)
            data = await bot._DexScreenerBot__fetch_api_data(endpoint)
            assert isinstance(data, list)
            assert data[0]["baseToken"]["address"] == "0x123456"

    @pytest.mark.asyncio
    async def test_get_dynamic_token_list(self, bot):
        with patch.object(
            bot,
            "_DexScreenerBot__fetch_api_data",
            AsyncMock(
                return_value=[{"tokenAddress": "test_token", "chainId": "solana"}]
            ),
        ):
            tokens = await bot._DexScreenerBot__get_dynamic_token_list()
            assert isinstance(tokens, list)
            assert "test_token" in tokens

    @pytest.mark.asyncio
    async def test_verify_rugcheck(self, bot, mock_token, load_json):
        url = f"{bot.rugcheck_url}/{mock_token.address}/report/summary"

        # good
        mock_response = load_json("tests/etc/rugcheck/good.json")
        with aioresponses() as m:

            m.get(url, payload=mock_response)

            result = await bot._DexScreenerBot__verify_rugcheck(mock_token)
            assert result is True
            assert mock_token.rugcheck_status == "good"

        # unknown
        mock_response = load_json("tests/etc/rugcheck/unknown.json")
        with aioresponses() as m:
            m.get(url, payload=mock_response)

            result = await bot._DexScreenerBot__verify_rugcheck(mock_token)
            assert result is True
            assert mock_token.rugcheck_status == "good"

        # bad
        mock_response = load_json("tests/etc/rugcheck/bad.json")
        with aioresponses() as m:
            m.get(url, payload=mock_response)

            result = await bot._DexScreenerBot__verify_rugcheck(mock_token)
            assert result is False
            assert mock_token.rugcheck_status == "rug"

    @pytest.mark.asyncio
    async def test_process_tokens(self, bot):
        with patch.object(
            bot,
            "_DexScreenerBot__get_dynamic_token_list",
            AsyncMock(return_value=["test_token"]),
        ), patch.object(
            bot,
            "_DexScreenerBot__fetch_token_data",
            AsyncMock(
                return_value={
                    "priceChange": {"h24": 1.5},
                    "tokenAddress": "test_token",
                }
            ),
        ), patch.object(
            bot, "_DexScreenerBot__analyze_and_trade", AsyncMock(return_value=None)
        ), patch(
            "src.dexscreener_bot.Database.save_token", MagicMock()
        ):

            await bot._DexScreenerBot__process_tokens()
            bot._DexScreenerBot__get_dynamic_token_list.assert_called_once()
            bot._DexScreenerBot__fetch_token_data.assert_called_once()
            bot._DexScreenerBot__analyze_and_trade.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_telegram_notification(self, bot, mocker):
        await bot.send_telegram_notification("Test message")
        bot.telegram_bot.send_message.assert_called_once()
        assert bot.telegram_bot.send_message.call_args[1]["text"] == "Test message"

    def test_load_config_valid_file(self, mock_config):
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
            with patch("json.load", return_value=mock_config):
                bot = DexScreenerBot("config.json")
                assert bot.config == mock_config

    def test_load_config_invalid_file(self):
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(Exception):
                DexScreenerBot("invalid_config.json")
