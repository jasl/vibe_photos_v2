"""
Database utility functions for session management and common queries.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from models import get_session


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Automatically commits on success and rolls back on error.
    
    Usage:
        with get_db_session() as session:
            # Do database operations
            session.add(obj)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def execute_with_session(func):
    """
    Decorator that provides a database session to a function.
    
    Usage:
        @execute_with_session
        def my_function(session, arg1, arg2):
            # Use session here
            pass
    """
    def wrapper(*args, **kwargs):
        with get_db_session() as session:
            return func(session, *args, **kwargs)
    return wrapper

