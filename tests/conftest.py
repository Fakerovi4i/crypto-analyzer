import pytest
from main import Coin


@pytest.fixture
def make_coin_fixture():
    # Фикстура возвращает функцию-фабрику _make_coin
    def _make_coin(**kwargs):
        defaults = dict(
            id="bitcoin",
            name="Bitcoin",
            symbol="btc",
            price_change_percentage_24h=1.0,
            total_volume=1000.0,
            market_cap=500000.0,
        )
        defaults.update(kwargs)
        return Coin(**defaults)

    return _make_coin