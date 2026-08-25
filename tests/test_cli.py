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
        limit=None,
    )
    assert "test.csv" in capsys.readouterr().out


def test_cli_query_housekeeping(capsys):
    """Test that 'query-housekeeping' calls query_housekeeping()."""
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "query-housekeeping", "--payload", "mst"],
    ):
        with patch.object(
            ema_data_access,
            "query_housekeeping",
            return_value=[{"file_name": "ema_l0_hsk_mst_20240101.pkts"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        payload="mst",
        timetag_start=None,
        timetag_end=None,
        version=None,
        md5checksum=None,
    )
    assert "ema_l0_hsk_mst_20240101.pkts" in capsys.readouterr().out


def test_cli_query_science(capsys):
    """Test that 'query-science' calls ema_data_access.query_science()."""
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "query-science", "--data-level", "l1a"],
    ):
        with patch.object(
            ema_data_access,
            "query_science",
            return_value=[{"file_name": "ema_rpt_l1a_20240101t000000_flux_p_v01.cdf"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        payload=None,
        data_level="l1a",
        timetag_start=None,
        timetag_end=None,
        descriptor=None,
        pred_rec=None,
        file_extension=None,
        major_version=None,
        minor_version=None,
        md5checksum=None,
    )
    assert "ema_rpt_l1a_20240101t000000_flux_p_v01.cdf" in capsys.readouterr().out


def test_cli_query_mission_events(capsys):
    """Test that 'query-mission-events' calls query_mission_events()."""
    with patch.object(
        sys,
        "argv",
        [
            "ema-data-access",
            "query-mission-events",
            "--start-date",
            "20240101",
            "--end-date",
            "20240110",
        ],
    ):
        with patch.object(
            ema_data_access,
            "query_mission_events",
            return_value=[{"file_name": "ema_mission_events_20240101_20240110.xml"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        start_date="20240101",
        end_date="20240110",
        version=None,
        md5checksum=None,
    )
    assert "ema_mission_events_20240101_20240110.xml" in capsys.readouterr().out


def test_cli_query_manifest(capsys):
    """Test that 'query-manifest' calls ema_data_access.query_manifest()."""
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "query-manifest", "--payload", "emb"],
    ):
        with patch.object(
            ema_data_access,
            "query_manifest",
            return_value=[{"file_name": "emb_manifest_202402020000.txt"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        payload="emb",
        timetag_start=None,
        timetag_end=None,
    )
    assert "emb_manifest_202402020000.txt" in capsys.readouterr().out


def test_cli_query_spice(capsys):
    """Test that 'query-spice' calls ema_data_access.query_spice()."""
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "query-spice", "--file-root", "naif"],
    ):
        with patch.object(
            ema_data_access,
            "query_spice",
            return_value=[{"file_name": "naif0012.tls"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        file_root="naif",
        min_date_j2000=None,
        max_date_j2000=None,
        min_date_datetime=None,
        max_date_datetime=None,
        delivery_date=None,
        od_number=None,
        version=None,
        limit=None,
    )
    assert "naif0012.tls" in capsys.readouterr().out


def test_cli_query_manifest_moc(capsys):
    """Test that 'query-manifest --payload moc' is accepted and forwarded."""
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "query-manifest", "--payload", "moc"],
    ):
        with patch.object(
            ema_data_access,
            "query_manifest",
            return_value=[{"file_name": "moc_manifest_202401151230.txt"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        payload="moc",
        timetag_start=None,
        timetag_end=None,
    )
    assert "moc_manifest_202401151230.txt" in capsys.readouterr().out
