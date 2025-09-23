"""Test configuration and fixtures for the LinkedIn Job Agent project."""

import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from src.database.models import Base


@pytest.fixture(scope="function")
def test_db_engine():
    """Create a temporary SQLite database for testing."""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Create engine with SQLite
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function")
def test_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def clean_db(test_session):
    """Provide a clean database for each test."""
    # Clear all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        test_session.execute(table.delete())
    test_session.commit()
    return test_session