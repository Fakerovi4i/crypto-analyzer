from unittest.mock import MagicMock, mock_open, patch

import pytest
from main import OUTPUT_REGISTRY, BaseOutput

def test_outputs_interface(coin_collection_fixture):
    console = MagicMock()
    output_class = OUTPUT_REGISTRY["console"]
    output: BaseOutput = output_class(console)

    output.output(coin_collection_fixture, qty=3)

    console.print.assert_called_once()

@pytest.mark.parametrize("output_key", ["json", "csv"])
def test_file_outputs_write(output_key, coin_collection_fixture):
    console = MagicMock()
    output_class = OUTPUT_REGISTRY[output_key]
    output = output_class(console)

    with patch("builtins.open", mock_open()) as mock_file:
        output.output(coin_collection_fixture, qty=3)

    mock_file.assert_called_once()











