import pytest
import requests_mock
from main import Coin, CoinCollection



@pytest.fixture
def make_coin_fixture():
    """Фикстура возвращает функцию-фабрику"""
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

@pytest.fixture
def coin_collection_fixture(make_coin_fixture):
    sample = [
        make_coin_fixture(id="bitcoin", price_change_percentage_24h=5.2, total_volume=1000000.0, market_cap=500000000.0),
        make_coin_fixture(id="ethereum", price_change_percentage_24h=-3.1, total_volume=800000.0, market_cap=300000000.0),
        make_coin_fixture(id="dogecoin", price_change_percentage_24h=12.7, total_volume=50000.0, market_cap=10000000.0),
        make_coin_fixture(id="cardano", price_change_percentage_24h=-8.4, total_volume=30000.0, market_cap=8000000.0),
    ]
    return CoinCollection(sample)


@pytest.fixture
def mock_requests_fixture():
    """Фикстура для мокирования HTTP"""
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def coingecko_response_fixture():
    return [
        {
            "id": "bitcoin",
            "name": "Bitcoin",
            "symbol": "btc",
            "price_change_percentage_24h": 5.2,
            "total_volume": 1000000.0,
            "market_cap": 500000000.0,
        },
    ]


@pytest.fixture
def cmc_response_fixture():
    return {
        "data": [
            {
                "id": "bitcoin",
                "name": "Bitcoin",
                "symbol": "btc",
                "quote": [
                    {
                    "percent_change_24h": 5.2,
                    "volume_24h": 1000000.0,
                    "market_cap": 500000000.0,
                    }
                ],
            },
        ]
    }