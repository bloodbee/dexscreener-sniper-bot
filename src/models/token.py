from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Token:
    """Data class to store all token-related information"""

    address: str
    symbol: str
    name: str
    chain_id: str = "solana"
    dex_id: str = "auto"
    dev_address: Optional[str] = None  # Placeholder until blockchain data is integrated
    first_seen: datetime = datetime.now()
    last_updated: datetime = datetime.now()
    max_price: float = 0.0
    min_price: float = 0.0
    current_price: float = 0.0
    volume_24h: float = 0.0
    liquidity: float = 0.0
    fdv: float = 0.0
    status: str = "normal"
    fake_volume_detected: bool = False
    rugcheck_status: str = "unknown"
    supply_bundled: bool = False
    websites: List[str] = field(default_factory=list)
    socials: List[str] = field(default_factory=list)

    @classmethod
    def parse(cls, token_data: dict) -> "Token":
        """Create a Token instance from Dexscreener API data"""
        liquidity = float(token_data.get("liquidity", {}).get("usd", 0.0))

        price_usd = cls.__safe_float(token_data["priceUsd"])

        fdv = token_data.get("fdv", None)
        if not fdv:
            fdv = token_data.get("marketCap", None)

        return cls(
            address=token_data["baseToken"]["address"],
            symbol=token_data["baseToken"]["symbol"],
            name=token_data["baseToken"]["name"],
            chain_id=token_data["chainId"],
            dex_id=cls.__get_pool(token_data.get("dexId")),
            current_price=cls.__safe_float(token_data["priceUsd"]),
            volume_24h=cls.__safe_float(token_data["volume"]["h24"]),
            liquidity=cls.__safe_float(liquidity),
            fdv=cls.__safe_float(fdv),
            max_price=price_usd,  # Initial value
            min_price=price_usd,  # Initial value
            websites=cls.__get_socials(token_data.get("info", {}).get("websites", [])),
            socials=cls.__get_socials(token_data.get("info", {}).get("socials", [])),
        )

    def update_price(self, new_price: float):
        """Update price-related fields"""
        self.current_price = new_price
        self.max_price = max(self.max_price, new_price)
        self.min_price = min(self.min_price, new_price)
        self.last_updated = datetime.now()

    @classmethod
    def __safe_float(cls, val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def __get_socials(cls, socials: list = []):
        return [social["url"] for social in socials]

    @classmethod
    def __get_pool(cls, dex: str = "auto"):
        if dex == "pumpfun":
            return "pump"
        elif dex == "raydium":
            return "raydium"
        else:
            return "auto"
