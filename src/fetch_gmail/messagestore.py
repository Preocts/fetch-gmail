from __future__ import annotations

import contextlib
import csv
import os
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
                timestamp TEXT DEFAULT '0',
                label_ids TEXT DEFAULT ''
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
        sql = "INSERT OR IGNORE INTO messages (message_id) VALUES (?)"

        with self._get_cursor() as cursor:
            cursor.executemany(sql, ((id_,) for id_ in ids))

    def update(
        self,
        message_id: str,
        from_: str,
        delivered_to: str,
        subject: str,
        timestamp: str,
        label_ids: Iterable[str],
    ) -> None:
        """
        Update table row details by message_id.

        Args:
            message_id: Must exist in the table already
            from_: Address message was delivered from (Header: From)
            delivered_to: Address message was delivered to (Header: Delivered-To)
            subject: Subject of the message (Header: Subject)
            timestamp: Local timestamp of message (internalDate)
            label_ids: An iterable of labels on the message
        """
        sql = """\
            UPDATE messages
            SET
                [from]=?,
                delivered_to=?,
                subject=?,
                timestamp=?,
                label_ids=?
            WHERE message_id=?;
        """
        labels = self._lables_to_csv(label_ids)

        with self._get_cursor() as cursor:
            cursor.execute(
                sql,
                (from_, delivered_to, subject, timestamp, labels, message_id),
            )

    @staticmethod
    def _lables_to_csv(label_ids: Iterable[str]) -> str:
        """
        Sanitize an interable of labels to comma seperated values.

        Follows RFC 4180 - excludes new line handling

        Args:
            label_ids: An iterable of labels on the message
        """
        clean_labels = []
        for label in label_ids:
            label = label.replace('"', '""')
            if "," in label or '"' in label:
                label = f'"{label}"'
            clean_labels.append(label)

        return ",".join(clean_labels)

    @staticmethod
    def _csv_to_labels(csv_string: str) -> list[str]:
        """
        Convert a stored csv of label ids back to a tuple of label ids

        Follows RFC 4180 - excludes new line handling

        Args:
            csv_string: A stored string of label ids from table
        """
        segments = []
        in_quote = False
        head = 0
        for idx, char in enumerate(csv_string):
            if char == '"':
                in_quote = not in_quote

            if not in_quote and char == ",":
                segments.append(csv_string[head:idx])
                head = idx + 1

        segments.append(csv_string[head:])

        for idx, segment in enumerate(segments):
            if segment.startswith('"') and segment.endswith('"'):
                segment = segment[1 : len(segment) - 1]
            segment = segment.replace('""', '"')
            segments[idx] = segment

        return segments

    def has_unique_ids(self, ids: Iterable[str]) -> bool:
        """Returns true if any of the provided ids are unique to the table."""
        ids_ = tuple(ids)
        # sqlite3 does not support spreading values from one placeholder so
        # this will create as many as provided.
        ph = "?" + ",?" * (len(ids_) - 1)
        sql = f"SELECT COUNT(message_id) FROM messages WHERE message_id IN ({ph})"

        with self._get_cursor() as cursor:
            results = cursor.execute(sql, ids_).fetchone()

        return len(ids_) != results["COUNT(message_id)"]

    def row_count(self, *, only_empty: bool = False) -> int:
        """
        Returns the total number of rows in the table.

        Args:
            only_empty: When True only rows needing hydration will be counted
        """
        if only_empty:
            sql = "SELECT COUNT(*) FROM messages WHERE timestamp=0"
        else:
            sql = "SELECT COUNT(*) FROM messages"

        with self._get_cursor() as cursor:
            result = cursor.execute(sql).fetchone()

        return result["COUNT(*)"]

    def get_emtpy_message_ids(self) -> Generator[str, None, None]:
        """Generate list of message ids that need to be hydrated."""
        sql = "SELECT message_id FROM messages WHERE timestamp=0;"

        with self._get_cursor() as cursor:
            results = cursor.execute(sql)
            while "The road goes ever on and on":
                row = results.fetchone()
                if not row:
                    break
                yield row["message_id"]

    def csv_export(self, filename: str, *, allow_overwrite: bool = False) -> None:
        """
        Export MessageStore as a csv with headers.

        Args:
            filename: Full filename and path to save export to
            allow_overwrite: When true an existing file will be overwritten

        Raises:
            FileExistsError: When filename already exists
        """
        if not allow_overwrite and os.path.exists(filename):
            raise FileExistsError(f"'{filename}' already exists!")

        sql = "SELECT * FROM messages"
        csvwriter = None
        with self._get_cursor() as cursor:
            results = cursor.execute(sql)
            with open(filename, "w", encoding="utf-8") as outfile:

                while "Mary had a little lamb":
                    row = results.fetchone()
                    if not row:
                        break
                    if not csvwriter:
                        fieldnames = list(row.keys())
                        csvwriter = csv.DictWriter(
                            outfile,
                            fieldnames=fieldnames,
                            lineterminator="\n",
                        )
                        csvwriter.writeheader()

                    csvwriter.writerow({k: row[k] for k in row.keys()})

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
