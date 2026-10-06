"""Tests for the ``cli`` module."""

import sys
from pathlib import Path
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
        ["ema-data-access", "query-housekeeping", "--payload", "mista"],
    ):
        with patch.object(
            ema_data_access,
            "query_housekeeping",
            return_value=[{"file_name": "ema_l0_hsk_mista_flight_20240101.pkts"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        payload="mista",
        timetag_start=None,
        timetag_end=None,
        version=None,
        md5checksum=None,
    )
    assert "ema_l0_hsk_mista_flight_20240101.pkts" in capsys.readouterr().out


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
        ["ema-data-access", "query-manifest", "--payload", "embirs"],
    ):
        with patch.object(
            ema_data_access,
            "query_manifest",
            return_value=[{"file_name": "embirs_manifest_202402020000.txt"}],
        ) as mock_query:
            main()

    mock_query.assert_called_once_with(
        file_name=None,
        payload="embirs",
        timetag_start=None,
        timetag_end=None,
    )
    assert "embirs_manifest_202402020000.txt" in capsys.readouterr().out


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
        delivery_date_start=None,
        delivery_date_end=None,
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


def test_cli_metakernel(capsys):
    """Test that 'metakernel' calls ema_data_access.metakernel()."""
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "metakernel", "--start-time", "0", "--end-time", "100000"],
    ):
        with patch.object(
            ema_data_access,
            "metakernel",
            return_value="\\begindata\nKERNELS_TO_LOAD = ( )\n\\begintext\n",
        ) as mock_metakernel:
            main()

    mock_metakernel.assert_called_once_with(
        start_time=0.0,
        end_time=100000.0,
        kernel_types=None,
        list_files=False,
        require_coverage=False,
    )
    assert "KERNELS_TO_LOAD" in capsys.readouterr().out


def test_cli_metakernel_list_files(capsys):
    """Test that 'metakernel --list-files' prints JSON instead of plain text."""
    with patch.object(
        sys,
        "argv",
        [
            "ema-data-access",
            "metakernel",
            "--start-time",
            "0",
            "--end-time",
            "100000",
            "--kernel-types",
            "ephem_reconstructed,ephem_predicted",
            "--list-files",
        ],
    ):
        with patch.object(
            ema_data_access,
            "metakernel",
            return_value=["ema_pred_v001.bsp", "ema_recon_v001.bsp"],
        ) as mock_metakernel:
            main()

    mock_metakernel.assert_called_once_with(
        start_time=0.0,
        end_time=100000.0,
        kernel_types="ephem_reconstructed,ephem_predicted",
        list_files=True,
        require_coverage=False,
    )
    assert "ema_pred_v001.bsp" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["ema_l1_anc_sc_1234_20240101.csv", "dir"])
def test_cli_upload(capsys, tmp_path, name):
    """Test that 'upload' passes its path to ema_data_access.upload()."""
    path = tmp_path / name
    with patch.object(sys, "argv", ["ema-data-access", "upload", str(path)]):
        with patch.object(ema_data_access, "upload") as mock_upload:
            main()

    mock_upload.assert_called_once_with(path)
    assert f"Uploaded {path}" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("extra_args", "expected_destination"),
    [([], Path(".")), (["--destination", "out"], Path("out"))],
    ids=["default", "explicit"],
)
def test_cli_download(capsys, extra_args: list, expected_destination: Path):
    """Test that 'download' calls ema_data_access.download().

    Without --destination, the current directory is passed rather than None.

    Parameters
    ----------
    capsys : pytest.fixture
        Fixture capturing stdout/stderr.
    extra_args : list
        Additional CLI arguments after the file names.
    expected_destination : pathlib.Path
        The destination `download()` should receive.
    """
    with patch.object(
        sys,
        "argv",
        ["ema-data-access", "download", "naif0012.tls", *extra_args],
    ):
        with patch.object(
            ema_data_access,
            "download",
            return_value=[expected_destination / "naif0012.tls"],
        ) as mock_download:
            main()

    mock_download.assert_called_once_with(
        ["naif0012.tls"], destination=expected_destination
    )
    assert "Downloaded" in capsys.readouterr().out
