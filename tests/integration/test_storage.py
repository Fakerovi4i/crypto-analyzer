import json
from dataclasses import asdict
from unittest.mock import patch, mock_open

from main import STORAGE_REGISTRY, SqliteStorage


def test_json_save_correct_data(report_fixture, storage_fixture, coin_collection_fixture):
    """Тест проверяет корректность сохранения отчета в JSON"""
    storage = STORAGE_REGISTRY["json"](storage_fixture)

    with patch("builtins.open", mock_open()) as mock_file:
        storage.save(report_fixture)

    handle = mock_file()
    written_text = "".join(call.args[0] for call in handle.write.call_args_list)
    data = json.loads(written_text)

    assert data["total_coins_analyzed"] == len(coin_collection_fixture.coins)
    assert len(data["top_gainers"]) == 3
    assert len(data["top_losers"]) == 3
    assert data["highest_volume"] == asdict(coin_collection_fixture.top_volume())


def test_init_sqlite(storage_fixture):
    cursor = storage_fixture._conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert storage_fixture._conn is not None
    assert "snapshots" in tables
    assert "coin_prices" in tables


def test_sqlite_save_snapshots(storage_fixture, report_fixture):
    """Проверяет коректность создания данных в таблице snapshots"""
    cursor = storage_fixture._conn.cursor()
    storage_fixture.save(report_fixture)

    data = cursor.execute(
        "SELECT id, created_at, source FROM snapshots"
    ).fetchall()
    snapshot_id, created_at, source = data[0]

    assert isinstance(snapshot_id, int)
    assert snapshot_id > 0
    assert created_at == "2026-09-03 17:43:00"
    assert source == "coin market"


def test_sqlite_save_coin_prices(report_fixture, storage_fixture):
    """Проверяет коректность создания данных в таблице coin_prices"""
    cursor = storage_fixture._conn.cursor()
    storage_fixture.save(report_fixture)

    cursor.execute("SELECT COUNT(*) FROM coin_prices")
    coin_count = cursor.fetchone()[0]
    assert coin_count == len(report_fixture["all_coins"])

    first_coin = report_fixture["all_coins"][0]
    cursor.execute(
        "SELECT name, symbol, price FROM coin_prices WHERE coin_id = ?",
        (first_coin["id"],)
    )
    row = cursor.fetchone()
    assert row[0] == first_coin["name"]
    assert row[1] == first_coin["symbol"]
    assert row[2] == first_coin["price"]


def test_sqlite_save_accumulates_snapshots(storage_fixture, report_fixture):
    """Повторный save() создаёт новый снимок, а не перезаписывает"""
    cursor = storage_fixture._conn.cursor()

    storage_fixture.save(report_fixture)
    storage_fixture.save(report_fixture)

    cursor.execute("SELECT COUNT(*) FROM snapshots")
    count = cursor.fetchone()[0]
    assert count == 2












