from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator

import pytest

from fetch_gmail.messagestore import MessageStore


@pytest.fixture
def store(tmpdir) -> Generator[MessageStore, None, None]:
    tempfile = tmpdir.join("messagestore_test_database")
    store = MessageStore(tempfile)

    try:
        store.init_file()
        yield store

    finally:
        os.remove(tempfile)


def test_init_file(store: MessageStore) -> None:
    expected = ["message_id", "from", "delivered_to", "subject", "timestamp"]
    sql = "SELECT * from messages;"
    conn = sqlite3.connect(store.filename)
    store.init_file()

    desc = conn.execute(sql).description
    columns = [d[0] for d in desc]

    assert columns == expected
