from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Generator
from collections.abc import Iterable


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
                [from] TEXT DEFAULT '',
                delivered_to TEXT DEFAULT '',
                subject TEXT DEFAULT '',
                timestamp TEXT DEFAULT '0'
            );
        """

        with self._get_cursor() as cursor:
            cursor.executescript(sql)

    def save_message_ids(self, ids: Iterable[str]) -> None:
        """
        Save message ids to the database table.

        This is an insert or ignore operation. Existing ids will be ignored.

        Args:
            ids: Iterable of message ids
        """
        sql = "INSERT INTO messages (message_id) VALUES (?)"

        with self._get_cursor() as cursor:
            cursor.executemany(sql, ((id_,) for id_ in ids))

    @contextlib.contextmanager
    def _get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for returning a cursor after opening a connection.

        NOTE: auto commits on exit.
        """
        try:
            connection = sqlite3.Connection(self.filename)
            connection.row_factory = sqlite3.Row

        except sqlite3.OperationalError as err:
            raise ConnectionError() from err

        try:
            with contextlib.closing(connection.cursor()) as cursor:
                yield cursor
                connection.commit()

        finally:
            connection.commit()
            connection.close()
