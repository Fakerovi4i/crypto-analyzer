from unittest.mock import patch, MagicMock



import pytest
import requests

from main import Connector


def test_connector_get_without_context_manager():
    console = MagicMock()
    connector = Connector(console)
    with pytest.raises(RuntimeError):
        connector.get(url="", params={})


def test_connector_get_return_json(mock_requests_fixture):
    console = MagicMock()
    mock_requests_fixture.get("http://fake.api/data", json={"ok": True})
    connector = Connector(console)

    with connector:
        result = connector.get(url="http://fake.api/data", params={})
        assert result == {"ok": True}


@patch("main.sleep")
def test_connector_get_raise_for_status(mock_requests_fixture):
    console = MagicMock()
    mock_requests_fixture.get("http://fake.api/data", status_code=404)
    connector = Connector(console)

    with pytest.raises(requests.exceptions.RequestException):
        with connector:
            connector.get(url="http://fake.api/data", params={})

    assert mock_requests_fixture.call_count == 2




