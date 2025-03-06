from telethon import TelegramClient
from telethon.sessions import StringSession
from typing import Optional, Any
import asyncio


class ToxiBotClient:
    bot_username = "@toxi_solana_bot"
    _bot_chat_id: Optional[int] = None

    def __init__(self, api_id: int, api_hash: str, phone_number: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self._client = None

    async def setup(self):
        client = TelegramClient(StringSession(), self.api_id, self.api_hash, connection_retries=5)
        await client.start(
            phone=self.phone_number,
            code_callback=lambda: input(f"Enter Telegram code for {self.phone_number}: "),
        )
        session_id = client.session.save()

        self._client = TelegramClient(
            StringSession(session_id), self.api_id, self.api_hash, connection_retries=5
        )

    async def connect(self) -> None:
        if not self._client.is_connected():
            await self._client.connect()

    async def stop(self) -> None:
        if self._client.is_connected():
            await self._client.disconnect()

    async def send_message_to_bot(self, message: str) -> Any:
        chat_id = self._bot_chat_id or self.bot_username
        msg = await self._client.send_message(chat_id, message)
        if not self._bot_chat_id and msg.chat_id:
            self._bot_chat_id = msg.chat_id
        return msg

    async def send_buy_command(self, token_mint: str, buy_amount: float) -> Any:
        return await self.send_message_to_bot(f"/buy {token_mint} {buy_amount}")

    async def send_sell_command(self, token_mint: str, sell_percentage: int) -> Any:
        return await self.send_message_to_bot(f"/sell {token_mint} {sell_percentage}%")
