import csv
import io
import json
from unittest.mock import mock_open, patch

import pytest
from main import OUTPUT_REGISTRY, BaseOutput

def test_outputs_interface(coin_collection_fixture, console_fixture):
    output_class = OUTPUT_REGISTRY["console"]
    output: BaseOutput = output_class(console_fixture)

    output.output(coin_collection_fixture, qty=3)

    console_fixture.print.assert_called_once()

def test_csv_output_writes_correct_data(coin_collection_fixture, console_fixture):
    output = OUTPUT_REGISTRY["csv"](console_fixture)

    with patch("builtins.open", mock_open()) as mock_file:
        output.output(coin_collection_fixture, qty=3)

    handle = mock_file()
    written_text = "".join(call.args[0] for call in handle.write.call_args_list)
    rows = list(csv.reader(io.StringIO(written_text)))

    assert rows[0] == ["id", "name", "symbol", "price_change_percentage_24h", "total_volume", "market_cap", "price"]
    assert len(rows) == 7  # header + 3 gainers + 3 losers












