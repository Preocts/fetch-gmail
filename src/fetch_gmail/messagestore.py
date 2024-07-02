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

    def update(
        self,
        message_id: str,
        from_: str,
        delivered_to: str,
        subject: str,
        timestamp: str,
    ) -> None:
        """
        Update table row details by message_id.

        Args:
            message_id: Must exist in the table already
            from_: Address message was delivered from (Header: From)
            delivered_to: Address message was delivered to (Header: Delivered-To)
            subject: Subject of the message (Header: Subject)
            timestamp: Local timestamp of message (internalDate)
        """
        sql = """\
            UPDATE messages
            SET
                [from]=?,
                delivered_to=?,
                subject=?,
                timestamp=?
            WHERE message_id=?;
        """

        with self._get_cursor() as cursor:
            cursor.execute(sql, (from_, delivered_to, subject, timestamp, message_id))

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
