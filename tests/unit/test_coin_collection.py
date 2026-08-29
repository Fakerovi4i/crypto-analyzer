import pytest
from main import CoinCollection, Coin


@pytest.mark.parametrize("param", [
    ({}),
    ("not a list"),
    ([1, 2, 3]),
    ([])
])
def test_coin_collection_not_coins_validation(param, make_coin_fixture):
    with pytest.raises(ValueError):
        CoinCollection(param)


def test_coin_collection_top_gainers(coin_collection_fixture):
    top_gainers_2 = coin_collection_fixture.top_gainers(qty=2)
    top_gainers_0 = coin_collection_fixture.top_gainers(qty=0)
    top_gainers_4 = coin_collection_fixture.top_gainers(qty=4)

    assert len(top_gainers_2) == 2
    assert len(top_gainers_0) == 0

    assert top_gainers_2[0].id == "dogecoin"
    assert top_gainers_2[1].id == "bitcoin"
    assert len(top_gainers_4) == 4

    assert top_gainers_4[0] > top_gainers_4[1] > top_gainers_4[2] > top_gainers_4[3]

    assert top_gainers_0 == []


def test_coin_collection_top_losers(coin_collection_fixture):
    top_losers_2 = coin_collection_fixture.top_losers(qty=2)
    top_losers_0 = coin_collection_fixture.top_losers(qty=0)
    top_losers_4 = coin_collection_fixture.top_losers(qty=4)

    assert len(top_losers_4) == 4
    assert len(top_losers_2) == 2
    assert len(top_losers_0) == 0
    assert top_losers_0 == []

    assert top_losers_2[0].id == "cardano"
    assert top_losers_2[1].id == "ethereum"

    assert top_losers_4[0] < top_losers_4[1] < top_losers_4[2] < top_losers_4[3]


def test_top_volume(coin_collection_fixture):
    top_volume = coin_collection_fixture.top_volume()

    assert isinstance(top_volume, Coin)
    assert top_volume.id == "bitcoin"



