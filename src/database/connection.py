"""Database connection management for the LinkedIn Job Agent application."""

import os
from typing import Optional, Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager with connection URL."""
        self.database_url = database_url or self._get_default_database_url()
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None

    def _get_default_database_url(self) -> str:
        """Get default database URL for the application."""
        # Use environment variable if set, otherwise default to local SQLite
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        # Default to SQLite database in the project root
        db_path = os.path.join(os.path.dirname(__file__), "../..", "linkedin_jobs.db")
        return f"sqlite:///{os.path.abspath(db_path)}"

    def initialize(self) -> None:
        """Initialize the database engine and session factory."""
        # Configure engine based on database type
        if self.database_url.startswith("sqlite"):
            # SQLite-specific configuration
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,  # Allow SQLite to be used across threads
                    "timeout": 30,  # 30 second timeout for database locks
                }
            )
        else:
            # PostgreSQL or other database configuration
            self.engine = create_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,  # Recycle connections every hour
            )

        # Create session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

    def create_tables(self) -> None:
        """Create all database tables."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables."""
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.SessionLocal()

    def get_session_context(self):
        """Get a database session with automatic cleanup as context manager."""
        class SessionContext:
            def __init__(self, session_factory):
                self.session_factory = session_factory
                self.session = None

            def __enter__(self):
                self.session = self.session_factory()
                return self.session

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    self.session.rollback()
                else:
                    self.session.commit()
                self.session.close()

        return SessionContext(self.get_session)

    def close(self) -> None:
        """Close database connections and cleanup."""
        if self.engine:
            self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency function to get database session."""
    with db_manager.get_session_context() as session:
        yield session


def initialize_database(database_url: Optional[str] = None) -> DatabaseManager:
    """Initialize the database and return the manager."""
    global db_manager
    if database_url:
        db_manager = DatabaseManager(database_url)

    db_manager.initialize()
    db_manager.create_tables()
    return db_manager