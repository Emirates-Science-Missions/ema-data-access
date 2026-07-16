"""Tests for the ``cli`` module."""

import sys
from unittest.mock import patch

import pytest

import ema_data_access
from ema_data_access.cli import main


def test_cli_works(monkeypatch):
    """Smoke test for the CLI module making sure it is callable."""
    monkeypatch.setattr("sys.argv", ["ema-data-access", "-h"])
    with pytest.raises(SystemExit, match="0"):
        main()


def test_cli_query_ancillary(capsys):
    """Test that 'query-ancillary' calls ema_data_access.query_ancillary()."""
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "query-ancillary", "--apid", "123"],
    ):
        with patch.object(
            ema_data_access,
            "query_ancillary",
            return_value=[{"file_name": "test.csv"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        apid=123,
        timetag_start=None,
        timetag_end=None,
        file_extension=None,
        version=None,
        md5checksum=None,
    )
    assert "test.csv" in capsys.readouterr().out
