import pytest

from main import Coin




def test_coin_create():
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






