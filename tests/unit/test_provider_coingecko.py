import pytest

from main import ProviderCoingecko, Connector, Coin


def test_provider_coingecko_get_coins_valid_data(coingecko_response_fixture, mock_requests_fixture, console_fixture):
    connector = Connector(console_fixture)
    mock_requests_fixture.get("https://api.fake_host.com/api/fake_path", json=coingecko_response_fixture)
    provider = ProviderCoingecko(connector, "https://api.fake_host.com", "/api/fake_path")

    with provider:
        coins = provider.get_coins()

    assert isinstance(coins[0], Coin)

    assert coins[0].id == "bitcoin"
    assert coins[0].name == "Bitcoin"
    assert coins[0].price_change_percentage_24h == 5.2
    assert coins[0].total_volume == 1000000.0
    assert coins[0].market_cap == 500000000.0



def test_provider_coingecko_get_coins_raise_key_error(mock_requests_fixture, console_fixture):
    connector = Connector(console_fixture)
    mock_requests_fixture.get(
        "https://api.fake_host.com/api/fake_path",
        json=[{"id": "bitcoin", "name": "Bitcoin"}] # нет quote — как будто Coingecko изменил формат
    )

    provider = ProviderCoingecko(connector, "https://api.fake_host.com", "/api/fake_path")

    with pytest.raises(KeyError):
        with provider:
            provider.get_coins()












