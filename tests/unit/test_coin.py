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
        ({"id": 123}),
        ({"name": ""}),
        ({"symbol": 12}),
        ({"price_change_percentage_24h": []}),
        ({"total_volume": -1}),
        ({"market_cap": -1}),
        ({"market_cap": ""}),
    ]
)
def test_coin_validate_failed(make_coin_fixture, params):
    with pytest.raises(ValueError):
        make_coin_fixture(**params)
