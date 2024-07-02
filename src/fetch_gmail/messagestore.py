from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Generator


class MessageStore:
    """Data store for messages powered by sqlite3."""

    def __init__(self, filename: str = "messages.sqlite3") -> None:
        """Create a message store. Use filename ":memory:" for a memory-only store."""
        self.filename = filename

    def init_file(self) -> None:
        """Initialize the file if required table does not exist."""
        sql = """\
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT UNIQUE,
                [from] TEXT,
                delivered_to TEXT,
                subject TEXT,
                timestamp TEXT
            );
        """

        with self._get_cursor() as cursor:
            cursor.executescript(sql)

    @contextlib.contextmanager
    def _get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for returning a cursor after opening a connection."""
        try:
            connection = sqlite3.Connection(self.filename)
            connection.row_factory = sqlite3.Row

        except sqlite3.OperationalError as err:
            raise ConnectionError() from err

        try:
            with contextlib.closing(connection.cursor()) as cursor:
                yield cursor

        finally:
            connection.commit()
            connection.close()
