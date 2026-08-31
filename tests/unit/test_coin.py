import pytest
from main import Coin

def test_coin_create_successful():
    """Тут для наглядности не использую фикстуру"""
    coin = Coin(
        id="bitcoin",
        name="Bitcoin",
        symbol="btc",
        price_change_percentage_24h=5.2,
        total_volume=1000000.0,
        market_cap=50000000.0,
    )

    assert coin.id == "bitcoin"
    assert coin.name == "Bitcoin"
    assert coin.symbol == "btc"
    assert coin.price_change_percentage_24h == 5.2
    assert coin.total_volume == 1000000.0
    assert coin.market_cap == 50000000.0


@pytest.mark.parametrize(
    "params", [
        ({"name": 123}),
        ({"symbol": ['']}),
        ({"price_change_percentage_24h": []}),
        ({"total_volume": -1}),
        ({"market_cap": -1}),
        ({"market_cap": ""}),
    ],
    ids=[
        "name_not_str",
        "symbol_not_str",
        "price_change_not_number",
        "total_volume_negative",
        "market_cap_negative",
        "market_cap_not_number",
    ],
)
def test_coin_validate_failed(make_coin_fixture, params):
    with pytest.raises(ValueError):
        make_coin_fixture(**params)


def test_coin_zero_volume_and_market_cap_valid(make_coin_fixture):
    """Проверка, что объем и капитализация могут быть нулевыми"""
    coin = make_coin_fixture(total_volume=0, market_cap=0)

    assert coin.total_volume == 0
    assert coin.market_cap == 0


def test_coin_negative_price_change_is_valid(make_coin_fixture):
    """Проверка, что процент изменения цены может быть отрицательным"""
    coin = make_coin_fixture(price_change_percentage_24h=-10.5)

    assert coin.price_change_percentage_24h == -10.5


def test_coin_dunder_lt(make_coin_fixture):
    coin1 = make_coin_fixture(price_change_percentage_24h=10.5)
    coin2 = make_coin_fixture(price_change_percentage_24h=5.2)

    assert coin1 > coin2
    assert coin2 < coin1


def test_coin_dunder_str(make_coin_fixture):
    coin: Coin = make_coin_fixture(id="fake_id", name="fake_name")

    str_coin = str(coin)

    assert "fake_id" in str_coin
    assert "fake_name" in str_coin
    assert coin.__class__.__name__ in str_coin


