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


def test_save_messages_ignores_constraint_violations(store: MessageStore) -> None:
    ids = ["123", "456", "789"]
    sql = "SELECT * from messages;"
    conn = sqlite3.connect(store.filename)

    store.save_message_ids(ids)
    results = conn.execute(sql).fetchall()
    results = conn.execute(sql).fetchall()

    assert ids == [r[0] for r in results]


def test_update(store: MessageStore) -> None:
    ids = ["123", "456", "789"]
    sql = "SELECT * from messages WHERE message_id=456;"
    conn = sqlite3.connect(store.filename)
    store.save_message_ids(ids)

    store.update("456", "mockfrom", "mockto", "mocksub", "8675309")
    results = conn.execute(sql).fetchone()

    assert results == ("456", "mockfrom", "mockto", "mocksub", "8675309")


def test_update_does_not_insert_if_id_not_exists(store: MessageStore) -> None:
    sql = "SELECT * from messages WHERE message_id=456;"
    conn = sqlite3.connect(store.filename)

    store.update("456", "mockfrom", "mockto", "mocksub", "8675309")
    results = conn.execute(sql).fetchone()

    assert not results
