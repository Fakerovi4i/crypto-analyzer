from unittest.mock import MagicMock, patch
import requests
import pytest

from main import retry


class FakeClass:
    def __init__(self):
        self.console = MagicMock()
        self.call_count = 0

    @retry(max_attempts=3, delay=1)
    def fake_method(self, fail_times):
        self.call_count += 1
        if self.call_count <= fail_times:
            raise requests.exceptions.RequestException("Failed")
        return "success"

@patch("main.sleep")
def test_retries_zero(mock_sleep):
    fake_class = FakeClass()
    result = fake_class.fake_method(fail_times=0)

    assert result == "success"
    assert fake_class.call_count == 1

    mock_sleep.assert_not_called()


@patch("main.sleep")
def test_retries_work_after_fail(mock_sleep):
    fake_class = FakeClass()
    result = fake_class.fake_method(fail_times=2)

    assert result == "success"
    assert fake_class.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(1)



@patch("main.sleep")
def test_retries_limit(mock_sleep):
    fake_class = FakeClass()

    with pytest.raises(requests.exceptions.RequestException):
        fake_class.fake_method(fail_times=4)

    assert fake_class.call_count == 3
    # По логике верно, после 3-ей неудачи ожидание не нужно
    assert mock_sleep.call_count == 2


