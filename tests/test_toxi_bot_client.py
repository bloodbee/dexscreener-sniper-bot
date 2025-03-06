import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from telethon.sessions import MemorySession, StringSession
from telethon import TelegramClient
from src.toxi_bot_client import (
    ToxiBotClient,
)  # Adjust import based on your project structure


@pytest.mark.asyncio
class TestToxiBotClient:
    API_ID = 123456  # Replace with a test API ID
    API_HASH = "test_api_hash"
    PHONE_NUMBER = "+123456789"
    SESSION = MemorySession()

    @pytest.fixture
    def bot_client(self):
        """Fixture to create a ToxiBotClient instance with mocked TelegramClient."""
        client = ToxiBotClient(self.API_ID, self.API_HASH, self.PHONE_NUMBER)
        client._client = AsyncMock(spec=TelegramClient)
        client._client.is_connected = MagicMock(return_value=False)
        client._client.connect = AsyncMock()
        client._client.disconnect = AsyncMock()
        client._client.send_message = AsyncMock()
        yield client

    async def test_setup(self):
        """Test the setup method initializes the session properly."""
        valid_session_string = StringSession().save()  # Generate a valid session string

        with patch(
            "telethon.TelegramClient.start", new_callable=AsyncMock
        ) as mock_start, patch(
            "telethon.TelegramClient", autospec=True
        ) as mock_telegram_client:

            # Create a real StringSession instance
            session_instance = StringSession(valid_session_string)

            # Mock the TelegramClient instance
            mock_telegram_instance = AsyncMock()
            type(mock_telegram_instance).session = PropertyMock(
                return_value=session_instance
            )

            mock_telegram_client.return_value = mock_telegram_instance

            bot_client = ToxiBotClient(self.API_ID, self.API_HASH, self.PHONE_NUMBER)
            await bot_client.setup()

            mock_start.assert_called_once()
            assert bot_client._client is not None  # Ensure client is initialized

    async def test_connect(self, bot_client):
        """Test that the bot connects properly."""
        await bot_client.connect()
        bot_client._client.connect.assert_called_once()

    async def test_stop(self, bot_client):
        """Test that the bot stops properly."""
        bot_client._client.is_connected.return_value = True
        await bot_client.stop()
        bot_client._client.disconnect.assert_called_once()

    async def test_send_message_to_bot(self, bot_client):
        """Test sending a message to the bot."""
        bot_client._client.send_message.return_value = AsyncMock(chat_id=123456)

        message = "Hello Bot"
        msg = await bot_client.send_message_to_bot(message)

        bot_client._client.send_message.assert_called_once_with(
            bot_client.bot_username, message
        )
        assert msg.chat_id == 123456
        assert bot_client._bot_chat_id == 123456  # Ensure bot chat ID is updated

    async def test_send_buy_command(self, bot_client):
        """Test sending a buy command."""
        bot_client._client.send_message.return_value = AsyncMock()

        token_mint = "TOKEN123"
        buy_amount = 1.5
        await bot_client.send_buy_command(token_mint, buy_amount)

        bot_client._client.send_message.assert_called_once_with(
            bot_client.bot_username, f"/buy {token_mint} {buy_amount}"
        )

    async def test_send_sell_command(self, bot_client):
        """Test sending a sell command."""
        bot_client._client.send_message.return_value = AsyncMock()

        token_mint = "TOKEN123"
        sell_percentage = 50
        await bot_client.send_sell_command(token_mint, sell_percentage)

        bot_client._client.send_message.assert_called_once_with(
            bot_client.bot_username, f"/sell {token_mint} {sell_percentage}%"
        )
