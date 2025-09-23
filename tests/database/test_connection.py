"""Tests for database connection management."""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

from src.database.connection import DatabaseManager, initialize_database, get_db_session


class TestDatabaseManager:
    """Test cases for the DatabaseManager class."""

    def test_database_manager_init_default(self):
        """Test DatabaseManager initialization with default settings."""
        manager = DatabaseManager()
        assert manager.database_url is not None
        assert "sqlite:///" in manager.database_url
        assert manager.engine is None
        assert manager.SessionLocal is None

    def test_database_manager_init_custom_url(self):
        """Test DatabaseManager initialization with custom URL."""
        custom_url = "sqlite:///custom_test.db"
        manager = DatabaseManager(custom_url)
        assert manager.database_url == custom_url

    @patch.dict(os.environ, {"DATABASE_URL": "sqlite:///env_test.db"})
    def test_database_manager_env_url(self):
        """Test DatabaseManager uses environment variable for database URL."""
        manager = DatabaseManager()
        assert manager.database_url == "sqlite:///env_test.db"

    def test_database_manager_sqlite_initialization(self):
        """Test SQLite database initialization."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_url = f"sqlite:///{tmp.name}"

        try:
            manager = DatabaseManager(db_url)
            manager.initialize()

            assert manager.engine is not None
            assert manager.SessionLocal is not None

            # Test table creation
            manager.create_tables()

            # Test session creation
            session = manager.get_session()
            assert session is not None
            session.close()

        finally:
            if manager.engine:
                manager.close()
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

    def test_database_manager_postgresql_initialization(self):
        """Test PostgreSQL database configuration (mocked)."""
        pg_url = "postgresql://user:pass@localhost/testdb"
        manager = DatabaseManager(pg_url)

        # Mock create_engine to avoid actual connection
        with patch('src.database.connection.create_engine') as mock_engine, \
             patch('src.database.connection.sessionmaker') as mock_sessionmaker:

            mock_engine.return_value = MagicMock()
            mock_sessionmaker.return_value = MagicMock()

            manager.initialize()

            # Verify create_engine was called with correct parameters
            mock_engine.assert_called_once()
            args, kwargs = mock_engine.call_args
            assert args[0] == pg_url
            assert kwargs['echo'] is False
            assert kwargs['pool_pre_ping'] is True
            assert kwargs['pool_size'] == 5
            assert kwargs['max_overflow'] == 10
            assert kwargs['pool_recycle'] == 3600

    def test_database_manager_error_handling(self):
        """Test error handling for uninitialized database manager."""
        manager = DatabaseManager()

        # Should raise error when not initialized
        with pytest.raises(RuntimeError, match="Database not initialized"):
            manager.create_tables()

        with pytest.raises(RuntimeError, match="Database not initialized"):
            manager.drop_tables()

        with pytest.raises(RuntimeError, match="Database not initialized"):
            manager.get_session()

    def test_database_manager_session_context(self):
        """Test session context manager functionality."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_url = f"sqlite:///{tmp.name}"

        try:
            manager = DatabaseManager(db_url)
            manager.initialize()
            manager.create_tables()

            # Test successful transaction
            with manager.get_session_context() as session:
                # Session should be active
                assert session is not None
                # No exceptions should be raised

        finally:
            if manager.engine:
                manager.close()
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

    def test_database_manager_drop_tables(self):
        """Test table dropping functionality."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_url = f"sqlite:///{tmp.name}"

        try:
            manager = DatabaseManager(db_url)
            manager.initialize()
            manager.create_tables()

            # Tables should exist, drop them
            manager.drop_tables()

        finally:
            if manager.engine:
                manager.close()
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)


class TestUtilityFunctions:
    """Test utility functions in connection module."""

    def test_initialize_database_default(self):
        """Test initialize_database function with default settings."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            pass

        try:
            manager = initialize_database(f"sqlite:///{tmp.name}")
            assert manager is not None
            assert manager.engine is not None
            assert manager.SessionLocal is not None

        finally:
            if manager.engine:
                manager.close()
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

    def test_get_db_session_function(self):
        """Test get_db_session dependency function."""
        # This function returns a generator, so we need to test it differently
        session_gen = get_db_session()
        assert hasattr(session_gen, '__next__')  # It's a generator