import pytest
from main import CoinCollection, Coin
from tests.conftest import make_coin_fixture


@pytest.mark.parametrize("param", [
    ({}),
    ("not a list"),
    ([1, 2, 3]),
    ([])
])
def test_coin_collection_not_coins_validation(param, make_coin_fixture):
    with pytest.raises(ValueError):
        CoinCollection(param)



