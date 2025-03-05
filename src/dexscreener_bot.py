import requests
import json
import time
import sqlite3
from datetime import datetime
import logging
from typing import Dict, List, Optional
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import aiohttp
import signal
import os
import subprocess
import traceback
from solana.rpc.api import Client
from solders.pubkey import Pubkey

from .database import Database
from .models.token import Token

# Set up logging
logging.basicConfig(
    filename="dexscreener_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class DexScreenerBot:
    def __init__(self, config_path: str = "config.json"):
        # Add signal handler
        signal.signal(signal.SIGINT, self.__signal_handler)

        self.config = self.__load_config(config_path)
        self.database = Database()
        self.headers = {
            "User-Agent": "DexScreenerBot/1.0",
            "Accept": "application/json",
        }
        # api settings
        self.dexscreener_url = self.config["api_settings"]["dexscreener_api_url"]
        self.rugcheck_url = self.config["api_settings"]["rugcheck_url"]
        self.request_delay = self.config["api_settings"]["request_delay"]
        self.pumpportal_api_key = self.config["api_settings"]["pump_portal_api_key"]
        self.solana_client = Client(self.config["api_settings"]["solana_rpc_url"])
        self.wallet_pubkey = Pubkey.from_string(
            self.config["api_settings"]["solana_wallet_public_key"]
        ) if "solana_wallet_public_key" in self.config["api_settings"] else None
        # telegram settings
        self.telegram_bot = Bot(self.config["telegram_settings"]["telegram_bot_token"])
        self.chat_id = self.config["telegram_settings"]["telegram_chat_id"]
        # transaction settings
        self.slippage = self.config["transaction_settings"].get("slippage", 5)
        self.amount_sol = self.config["transaction_settings"].get("amountInSol", 0.05)
        self.amount_token = self.config["transaction_settings"].get("amountInToken", 100)
        self.min_sol_balance = self.config["transaction_settings"].get("minSolBalance", 0.1)
        self.session = None  # Will be initialized in run()

    async def run(self):
        """Main bot execution loop with dynamic token fetching"""
        self.running = True
        async with aiohttp.ClientSession() as session:
            self.session = session
            await self.send_telegram_notification(
                "DexScreenerBot started and will run every minute."
            )
            logging.info("DexScreenerBot started and will run every minute.")

            while self.running:
                await self.__process_tokens()

    async def stop(self):
        """Stop the bot gracefully"""
        self.running = False
        await self.send_telegram_notification("DexScreenerBot stopped.")
        logging.info("DexScreenerBot stopped.")
        self.__exit()

    async def send_telegram_notification(self, message: str):
        """Send notification via Telegram"""
        try:
            await self.telegram_bot.send_message(chat_id=self.chat_id, text=message)
        except TelegramError as e:
            logging.error(f"Telegram notification error: {e}")

    async def __fetch_api_data(self, endpoint: str) -> List[Dict]:
        """Fetch data from a Dexscreener API endpoint asynchronously"""
        try:
            url = f"{self.dexscreener_url}/{endpoint}"
            async with self.session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching {endpoint}: {e}")
            return []

    async def __get_dynamic_token_list(self) -> List[str]:
        """Fetch token addresses concurrently from multiple Dexscreener endpoints"""
        endpoints = [
            "token-profiles/latest/v1",
            "token-boosts/latest/v1",
            "token-boosts/top/v1",
        ]

        token_addresses = set()

        # Create tasks for all API calls
        tasks = [self.__fetch_api_data(endpoint) for endpoint in endpoints]
        # Execute all requests concurrently and wait for results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, list):  # Successful response
                for item in result:
                    if item["chainId"] == "solana":
                        token_addresses.add(item["tokenAddress"])
            else:
                logging.warning(f"Error in one of the API calls: {result}")

        logging.info(f"Fetched {len(token_addresses)} unique token addresses")
        return list(token_addresses)

    async def __fetch_token_data(self, token_address: str) -> Optional[Dict]:
        """Fetch detailed data for a specific token"""
        try:
            url = f"{self.dexscreener_url}/tokens/v1/solana/{token_address}"
            async with self.session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data[0] if len(data) > 0 else None
        except Exception as e:
            logging.error(f"Error fetching token data for {token_address}: {e}")
            return None

    async def __verify_rugcheck(self, token: Token) -> bool:
        """Verify token contract status on Rugcheck.xyz with specific risk checks"""
        try:
            url = f"{self.rugcheck_url}/{token.address}/report/summary"
            async with self.session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                result = await response.json()

                risks = result.get("risks", [])
                score = result.get("score", 0)

                # Define dealbreaker risks
                dealbreaker_risks = {
                    "Copycat",
                    "High holder correlation",
                    "Mutable metadata",
                    "Symbol Mismatch",
                    "Name Mismatch"
                }

                # Check for dealbreaker risks
                detected_risks = [risk["name"] for risk in risks]
                dealbreakers = [
                    risk for risk in detected_risks if risk in dealbreaker_risks
                ]

                if not risks or score < 300:
                    token.rugcheck_status = "good"
                    return True
                elif not dealbreakers:
                    # Risks exist but none are dealbreakers
                    token.rugcheck_status = "good"
                    return True
                else:
                    # Dealbreaker risks found
                    token.rugcheck_status = "rug"
                    return False

        except Exception as e:
            logging.error(f"Rugcheck API error for {token.address}: {e}")
            token.rugcheck_status = "Error"
            return False

    def __check_token_socials(self, token: Token) -> bool:
        """Check if token has at least one website and one social media"""
        return len(token.websites) > 0 and len(token.socials) > 0

    def __check_bundled_supply(self, token: Token) -> bool:
        """Check if token supply is bundled"""
        top_holder_ratio = 1 - (token.liquidity / token.fdv) if token.fdv > 0 else 0.0
        is_bundled = top_holder_ratio > self.config["supply_check"]["bundled_threshold"]
        token.supply_bundled = is_bundled
        return is_bundled

    def __detect_fake_volume(self, token: Token, price_change_24h: float) -> bool:
        """Detect fake volume patterns"""
        if (
            token.volume_24h > self.config["filters"]["min_volume_24h"] * 10
            and abs(price_change_24h) < 5  # noqa: W503
        ):
            token.fake_volume_detected = True
            return True
        return False

    def __apply_filters(self, token: Token, price_change_24h: float) -> bool:
        """Apply configured filters to token data"""
        filters = self.config["filters"]
        return (
            token.liquidity >= filters["min_liquidity"]
            and token.volume_24h >= filters["min_volume_24h"]  # noqa: W503
            and token.fdv >= filters["min_fdv"]  # noqa: W503
            and abs(price_change_24h) <= filters["max_price_change_24h"]  # noqa: W503
        )

    def __check_blacklists(self, token: Token) -> bool:
        """Check if token or developer is blacklisted"""
        return (
            token.dev_address and token.dev_address in self.config["blacklisted_devs"]
        ) or token.address in self.config["blacklisted_coins"]

    def __update_blacklists(self, token: Token):
        """Update blacklists for token and developer"""
        if token.address not in self.config["blacklisted_coins"]:
            self.config["blacklisted_coins"].append(token.address)
            logging.info(f"Blacklisted token: {token.address}")
        if (
            token.dev_address
            and token.dev_address not in self.config["blacklisted_devs"]  # noqa: W503
        ):
            self.config["blacklisted_devs"].append(token.dev_address)
            logging.info(f"Blacklisted developer: {token.dev_address}")
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)

    def __get_solana_balance(self) -> float:
        """Check the SOL balance of the configured wallet"""
        try:
            if not self.wallet_pubkey:
                return 0.0
            balance_lamports = self.solana_client.get_balance(self.wallet_pubkey).value
            balance_sol = balance_lamports / 1_000_000_000  # Convert lamports to SOL
            logging.info(f"Current SOL balance: {balance_sol} SOL")
            return balance_sol
        except Exception as e:
            logging.error(f"Error fetching Solana balance: {e}")
            return 0.0

    async def __trade_with_pumpportal(
        self, token: Token, action: str, amount: float
    ) -> bool:
        try:
            logging.info(
                f"{action.upper()} token {token.address} with status {token.status} ..."
            )

            transaction_amount = amount if action == "buy" else f"{amount}%"
            denominated_in_sol = "true" if action == "buy" else "false"
            url = f"https://pumpportal.fun/api/trade?api-key={self.pumpportal_api_key}"

            balance = self.__get_solana_balance()
            if (action == "buy" and balance < amount) or (
                action == "sell" and balance < self.min_sol_balance
            ):
                logging.warning(
                    f"Insufficient SOL balance ({balance} SOL) for {action} of {amount} SOL on {token.address}"  # noqa: E501
                )
                await self.send_telegram_notification(
                    f"Trade failed: Insufficient SOL balance ({balance} SOL) for {action} of {amount} SOL on {token.address}"  # noqa: E501
                )
                return False

            async with self.session.post(
                url=url,
                data={
                    "action": action,
                    "mint": token.address,
                    "amount": transaction_amount,
                    "denominatedInSol": denominated_in_sol,
                    "slippage": self.slippage,
                    "priorityFee": 0.0001,
                    "pool": token.dex_id,
                },
            ) as response:
                data = await response.json()
                if "errors" in data and data["errors"]:
                    logging.error(
                        f"{action.capitalize()} transaction failed for token {token.address}: {data['errors']}"  # noqa: E501
                    )
                    return False

                logging.info(
                    f"Transaction {action.upper()} successful for token {token.address}"
                )
                await self.send_telegram_notification(
                    f"{action.capitalize()} command sent for {token.symbol}"
                )
                return True
        except Exception as e:
            logging.error(
                f"{action.capitalize()} transaction failed for token {token.address}: {e}"
            )
            return False

    async def __analyze_and_trade(self, token_data: dict) -> Optional[Token]:
        """Analyze token and execute trade if conditions met"""
        token = Token.parse(token_data)
        price_change_24h = float(token_data["priceChange"]["h24"])

        if not self.__check_token_socials(token):
            return None
        if not await self.__verify_rugcheck(token):
            self.__update_blacklists(token)
            return None
        if self.__check_bundled_supply(token):
            return None
        if (
            self.__check_blacklists(token)
            or not self.__apply_filters(token, price_change_24h)  # noqa: W503
            or self.__detect_fake_volume(token, price_change_24h)  # noqa: W503
        ):
            return None

        if price_change_24h > 100:
            token.status = "pumped"
            await self.__trade_with_pumpportal(token, "buy", self.amount_sol)
        elif price_change_24h < -90 and token.liquidity < 1000:
            token.status = "rugged"
        elif token.volume_24h > 1000000 and token.liquidity > 250000:
            token.status = "tier1"
            await self.__trade_with_pumpportal(token, "buy", self.amount_sol)
        else:
            token.status = "dead"

        return token

    async def __process_tokens(self):
        """Process tokens once (core logic of run)"""
        token_list = await self.__get_dynamic_token_list()

        for token_address in token_list:
            try:
                token_data = await self.__fetch_token_data(token_address)
                if token_data:
                    token = await self.__analyze_and_trade(token_data)
                    if token:
                        self.database.save_token(token)
                        logging.info(
                            f"Processed token: {token.address} - Status: {token.status}"
                        )
                    else:
                        logging.info(f"Token rejected: {token_address}")
                await asyncio.sleep(self.request_delay)
            except Exception as e:
                logging.error(f"Error processing token {token_address}: {e}")

        report = self.database.generate_report()
        report["blacklisted"] = len(self.config["blacklisted_coins"])
        await self.send_telegram_notification(
            f"Analysis Report: {json.dumps(report, indent=2)}"
        )

    def __load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            raise

    def __signal_handler(self, signum, frame):
        """Handle CTRL+C signal"""
        logging.info("Received shutdown signal (CTRL+C)")
        asyncio.create_task(self.stop())

    def __exit(self):
        """Kill all subprocess and exit app"""
        pid = os.getpid()

        process = subprocess.Popen(
            ["ps", "o", "pid=", "--pid", str(pid)],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )

        for output_pid in process.stdout:
            os.kill(int(output_pid), signal.SIGKILL)

        exit()
