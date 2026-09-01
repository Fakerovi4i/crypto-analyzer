import pytest
from unittest.mock import patch

from main import ProviderCMC, Connector, Coin

@patch("main.os.getenv")
def test_provider_cmc_get_coins_valid_data(mock_getenv, cmc_response_fixture, mock_requests_fixture, console_fixture):
    mock_getenv.return_value = "12345"
    connector = Connector(console_fixture, ProviderCMC.build_headers())
    mock_requests_fixture.get("https://api.fake_host.com/api/fake_path", json=cmc_response_fixture)
    provider = ProviderCMC(connector, "https://api.fake_host.com", "/api/fake_path")

    with provider:
        coins = provider.get_coins()

    assert isinstance(coins[0], Coin)
    assert coins[0].id == "bitcoin"
    assert coins[0].name == "Bitcoin"
    assert coins[0].price_change_percentage_24h == 5.2
    assert coins[0].total_volume == 1000000.0
    assert coins[0].market_cap == 500000000.0


@patch("main.os.getenv")
def test_provider_cmc_get_coins_raises_key_error_on_missing_field(mock_getenv, mock_requests_fixture, console_fixture):
    mock_getenv.return_value = "12345"
    connector = Connector(console_fixture, ProviderCMC.build_headers())
    mock_requests_fixture.get(
        "https://api.fake_host.com/api/fake_path",
        json={"data": [{"id": "bitcoin"}]},  # нет quote — как будто CMC изменил формат
    )
    provider = ProviderCMC(connector, "https://api.fake_host.com", "/api/fake_path")

    with pytest.raises(KeyError):
        with provider:
            provider.get_coins()


@patch("main.os.getenv")
def test_provider_cmc_build_headers_includes_api_key(mock_getenv):
    mock_getenv.return_value = "12345"

    headers = ProviderCMC.build_headers()

    assert headers == {
        "Accept": "application/json",
        "X-CMC_PRO_API_KEY": "12345",
    }

