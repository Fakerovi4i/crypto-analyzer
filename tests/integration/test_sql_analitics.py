from main import SqliteAnalytics


def test_coin_price_history_len_correct(storage_with_data_fixture):
    """Проверяет, что записано 2 значения"""
    analytics = SqliteAnalytics(conn=storage_with_data_fixture._conn)

    history = analytics.coin_price_history("bitcoin")

    assert len(history) == 2


def test_list_snapshot_len_correct(storage_with_data_fixture):
    """"""
    analytics = SqliteAnalytics(conn=storage_with_data_fixture._conn)

    snaps = analytics.list_snapshots()

    assert len(snaps) == 2


def test_compare_correct(storage_with_data_fixture):
    """Проверяет, что сравнение снимков работает корректно"""
    analytics = SqliteAnalytics(conn=storage_with_data_fixture._conn)
    snapshots = storage_with_data_fixture._conn.execute(
    "SELECT id FROM snapshots ORDER BY id"
    ).fetchall()

    assert len(snapshots) == 2

    analytic_rows, = analytics.compare_snapshots(snapshots[0][0], snapshots[1][0])
    coin_id, name, price_before, price_after, price_difference = analytic_rows
    assert coin_id == "bitcoin"
    assert price_before == 1000
    assert price_after == 1200
    assert price_difference == -200


def test_top_5_gainers_losers_not_have_snapshots(storage_fixture):
    """Проверяет, что если нет снимков, то возвращается пустой словарь"""
    analytics = SqliteAnalytics(conn=storage_fixture._conn)

    analytic_dict = analytics.top_5_gainers_losers()

    assert analytic_dict == {"top_gainers": [], "top_losers": []}








