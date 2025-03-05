import pytest
import sqlite3
from datetime import datetime
import os
from src.database import Database
from src.models.token import Token


class TestDatabase:
    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Create a temporary database file for testing"""
        db_file = tmp_path / "test.db"
        return str(db_file)

    @pytest.fixture
    def db(self, test_db_path):
        """Initialize database instance with test database"""
        return Database(test_db_path)

    @pytest.fixture
    def sample_token(self):
        """Create a sample token for testing"""
        return Token(
            address="0x123",
            symbol="TEST",
            name="Test Token",
            chain_id="1",
            dev_address="0xdev",
            first_seen=datetime.now(),
            last_updated=datetime.now(),
            max_price=100.0,
            min_price=10.0,
            current_price=50.0,
            volume_24h=1000.0,
            liquidity=10000.0,
            fdv=1000000.0,
            status="normal",
            fake_volume_detected=False,
            rugcheck_status="safe",
            supply_bundled=False,
        )

    def test_database_initialization(self, test_db_path):
        """Test if database is properly initialized with required tables"""
        db = Database(test_db_path)

        # Check if database file exists
        assert os.path.exists(test_db_path)

        # Check if tables are created
        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()

            # Check token table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='token'"
            )
            assert cursor.fetchone() is not None

            # Check token_history table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='token_history'"
            )
            assert cursor.fetchone() is not None

    def test_save_token(self, db, sample_token):
        """Test if token data is properly saved to database"""
        db.save_token(sample_token)

        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()

            # Check token table
            cursor.execute(
                "SELECT * FROM token WHERE token_address = ?", (sample_token.address,)
            )
            token_data = cursor.fetchone()
            assert token_data is not None
            assert token_data[0] == sample_token.address
            assert token_data[1] == sample_token.symbol

            # Check token_history table
            cursor.execute(
                "SELECT * FROM token_history WHERE token_address = ?",
                (sample_token.address,),
            )
            history_data = cursor.fetchone()
            assert history_data is not None
            assert history_data[1] == sample_token.address

    def test_generate_report(self, db, sample_token):
        """Test report generation with sample data"""
        # Save a normal token
        db.save_token(sample_token)

        # Save a token with fake volume
        fake_volume_token = sample_token
        fake_volume_token.address = "0x456"
        fake_volume_token.fake_volume_detected = True
        db.save_token(fake_volume_token)

        # Save a token with bundled supply
        bundled_token = sample_token
        bundled_token.address = "0x789"
        bundled_token.supply_bundled = True
        db.save_token(bundled_token)

        report = db.generate_report()

        assert report["total_tokens"] == 1  # Only normal token counted
        assert report["status_counts"]["normal"] == 1
        assert report["fake_volume_detected"] == 2
        assert report["bundled_supply_count"] == 1

    def test_token_update(self, db, sample_token):
        """Test updating existing token data"""
        # Initial save
        db.save_token(sample_token)

        # Update token
        sample_token.current_price = 75.0
        sample_token.status = "pumped"
        db.save_token(sample_token)

        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT current_price, status FROM token WHERE token_address = ?",
                (sample_token.address,),
            )
            token_data = cursor.fetchone()

            assert token_data[0] == 75.0
            assert token_data[1] == "pumped"

            # Check history entries
            cursor.execute(
                "SELECT COUNT(*) FROM token_history WHERE token_address = ?",
                (sample_token.address,),
            )
            history_count = cursor.fetchone()[0]
            assert history_count == 2  # Should have two entries
