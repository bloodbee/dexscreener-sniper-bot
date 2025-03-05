import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import os

from .models.token import Token


class Database:
    def __init__(self, db_path: str = "dist/dexscreener_data.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._setup_database()

    def _setup_database(self):
        """Initialize SQLite database and create necessary tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS token (
                    token_address TEXT PRIMARY KEY,
                    symbol TEXT,
                    name TEXT,
                    chain_id TEXT,
                    dev_address TEXT,
                    first_seen TIMESTAMP,
                    last_updated TIMESTAMP,
                    max_price REAL,
                    min_price REAL,
                    current_price REAL,
                    volume_24h REAL,
                    liquidity REAL,
                    fdv REAL,
                    status TEXT,
                    fake_volume_detected BOOLEAN,
                    rugcheck_status TEXT,
                    supply_bundled BOOLEAN
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS token_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT,
                    timestamp TIMESTAMP,
                    price REAL,
                    volume REAL,
                    liquidity REAL,
                    event_type TEXT,
                    FOREIGN KEY (token_address) REFERENCES token (token_address)
                )
            """
            )

            conn.commit()

    def save_token(self, token: Token):
        """Save token data and history to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO token (
                    token_address, symbol, name, chain_id, dev_address, first_seen,
                    last_updated, max_price, min_price, current_price,
                    volume_24h, liquidity, fdv, status, fake_volume_detected,
                    rugcheck_status, supply_bundled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    token.address,
                    token.symbol,
                    token.name,
                    token.chain_id,
                    token.dev_address,
                    token.first_seen.isoformat(),
                    token.last_updated.isoformat(),
                    token.max_price,
                    token.min_price,
                    token.current_price,
                    token.volume_24h,
                    token.liquidity,
                    token.fdv,
                    token.status,
                    token.fake_volume_detected,
                    token.rugcheck_status,
                    token.supply_bundled,
                ),
            )

            cursor.execute(
                """
                INSERT INTO token_history (
                    token_address, timestamp, price, volume, liquidity, event_type
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    token.address,
                    datetime.now().isoformat(),
                    token.current_price,
                    token.volume_24h,
                    token.liquidity,
                    token.status,
                ),
            )

            conn.commit()

    def generate_report(self) -> Dict:
        """Generate analysis report of tracked tokens"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            report = {
                "total_tokens": 0,
                "status_counts": {"normal": 0, "pumped": 0, "rugged": 0, "tier1": 0, "dead": 0},
                "fake_volume_detected": 0,
                "bundled_supply_count": 0,
            }

            cursor.execute(
                "SELECT status, COUNT(*) FROM token WHERE fake_volume_detected = 0 AND supply_bundled = 0 GROUP BY status"  # noqa: E501
            )
            for status, count in cursor.fetchall():
                report["status_counts"][status] = count
                report["total_tokens"] += count

            cursor.execute("SELECT COUNT(*) FROM token WHERE fake_volume_detected = 1")
            report["fake_volume_detected"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM token WHERE supply_bundled = 1")
            report["bundled_supply_count"] = cursor.fetchone()[0]

            return report
