"""Tests for the ``file_validation`` module."""

from datetime import UTC, datetime

import pytest

from ema_data_access.file_validation import (
    AncillaryFilePath,
    HousekeepingFilePath,
    InvalidEmaFileError,
    ManifestFilePath,
    MissionEventsFilePath,
    ScienceFilePath,
    SPICEFilePath,
    generate_ema_file_path,
)


def test_ancillary_file_path():
    """Test parsing, metadata, and path construction for an ancillary file."""
    parsed = AncillaryFilePath.from_filename("ema_l1_anc_sc_123_20240115.csv")

    assert parsed.apid == 123
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)
    assert parsed.file_extension == "csv"
    assert parsed.to_metadata() == {
        "file_name": "ema_l1_anc_sc_123_20240115.csv",
        "apid": 123,
        "timetag": datetime(2024, 1, 15, tzinfo=UTC),
        "file_extension": "csv",
    }
    assert parsed.construct_path() == "ema/ancillary/ema_l1_anc_sc_123_20240115.csv"


@pytest.mark.parametrize(
    "filename",
    [
        "ema_l1_anc_sc_123_20240115.fits",  # only csv is a known extension
        "ema_l1_anc_sc_abc_20240115.csv",  # apid isn't numeric
        "ema_l1_anc_sc_123_20240115.csv.bak",  # trailing junk must not match
        "not_ancillary_at_all.csv",
    ],
)
def test_ancillary_file_path_invalid(filename: str):
    """Test that malformed or wrong-convention filenames are rejected."""
    with pytest.raises(InvalidEmaFileError, match=filename):
        AncillaryFilePath.from_filename(filename)


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("moc_manifest_202401151230.txt", "moc"),
        ("mst_manifest_202401151230.txt", "mst"),
    ],
)
def test_manifest_file_path(filename: str, payload: str):
    """Test both the "moc" and payload-scoped manifest conventions."""
    parsed = ManifestFilePath.from_filename(filename)

    assert parsed.payload == payload
    assert parsed.timetag == datetime(2024, 1, 15, 12, 30, tzinfo=UTC)
    assert parsed.construct_path() == f"ema/manifest/{payload}/{filename}"


def test_manifest_file_path_invalid_payload():
    """Test that a payload outside the known set is rejected."""
    with pytest.raises(InvalidEmaFileError):
        ManifestFilePath.from_filename("xyz_manifest_202401151230.txt")


def test_housekeeping_file_path():
    """Test parsing, metadata, and path construction for a housekeeping file."""
    parsed = HousekeepingFilePath.from_filename("ema_l0_hsk_emb_20240115.pkts")

    assert parsed.payload == "emb"
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)
    assert parsed.to_metadata() == {
        "file_name": "ema_l0_hsk_emb_20240115.pkts",
        "payload": "emb",
        "timetag": datetime(2024, 1, 15, tzinfo=UTC),
    }
    assert parsed.construct_path() == (
        "ema/housekeeping/emb/ema_l0_hsk_emb_20240115.pkts"
    )


def test_housekeeping_file_path_invalid_payload():
    """Test that "moc" is not a valid housekeeping payload."""
    with pytest.raises(InvalidEmaFileError):
        HousekeepingFilePath.from_filename("ema_l0_hsk_moc_20240115.pkts")


def test_science_file_path_l0():
    """Test parsing an L0 science file, which has no version/descriptor."""
    parsed = ScienceFilePath.from_filename("ema_l0_sci_emb_20240115.pkts")

    assert parsed.payload == "emb"
    assert parsed.data_level == "l0"
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)
    assert parsed.descriptor is None
    assert parsed.pred_rec is None
    assert parsed.version is None
    assert parsed.subversion is None
    assert parsed.file_extension == "pkts"
    assert parsed.construct_path() == "ema/science/emb/l0/ema_l0_sci_emb_20240115.pkts"


def test_science_file_path_l1a():
    """Test parsing an L1a+ science file using the example from models.py."""
    filename = "ema_emb_l1a_20321207t122030_observing-mode-info_p_v02-01.fits"
    parsed = ScienceFilePath.from_filename(filename)

    assert parsed.payload == "emb"
    assert parsed.data_level == "l1a"
    assert parsed.timetag == datetime(2032, 12, 7, 12, 20, 30, tzinfo=UTC)
    assert parsed.descriptor == "observing-mode-info"
    assert parsed.pred_rec == "p"
    assert parsed.version == 2
    assert parsed.subversion == 1
    assert parsed.file_extension == "fits"
    assert parsed.to_metadata() == {
        "file_name": filename,
        "payload": "emb",
        "data_level": "l1a",
        "timetag": datetime(2032, 12, 7, 12, 20, 30, tzinfo=UTC),
        "descriptor": "observing-mode-info",
        "pred_rec": "p",
        "version": 2,
        "subversion": 1,
        "file_extension": "fits",
    }
    assert parsed.construct_path() == f"ema/science/emb/l1a/{filename}"


def test_science_file_path_invalid():
    """Test that a filename matching neither science pattern is rejected."""
    with pytest.raises(InvalidEmaFileError, match="ScienceFilePath"):
        ScienceFilePath.from_filename("not_a_science_file.fits")


def test_mission_events_file_path():
    """Test parsing, metadata, and path construction for a mission events file."""
    parsed = MissionEventsFilePath.from_filename(
        "ema_mission_events_20240101_20240131.xml"
    )

    assert parsed.start_date == datetime(2024, 1, 1, tzinfo=UTC)
    assert parsed.end_date == datetime(2024, 1, 31, tzinfo=UTC)
    assert parsed.construct_path() == (
        "ema/mission_events/ema_mission_events_20240101_20240131.xml"
    )


@pytest.mark.parametrize(
    ("filename", "file_root", "kernel_type"),
    [
        ("ema_sclk_00001.tsc", "ema_sclk_00001", "sclk"),
        ("ema_2024_001_2024_002_01.bc", "ema_2024_001_2024_002_01", "ck"),
        ("ema_de440.bsp", "ema_de440", "spk"),
        ("ema_pck00011.tpc", "ema_pck00011", "pck"),
        ("ema_naif0012.tls", "ema_naif0012", "lsk"),
        ("ema_frames.tf", "ema_frames", "fk"),
        ("ema_meta.tm", "ema_meta", "mk"),
    ],
)
def test_spice_file_path(filename: str, file_root: str, kernel_type: str):
    """Test the placeholder SPICE convention (see its TODO for context)."""
    parsed = SPICEFilePath.from_filename(filename)

    assert parsed.file_root == file_root
    assert parsed.kernel_type == kernel_type
    assert parsed.construct_path() == f"ema/spice/{kernel_type}/{filename}"


def test_spice_file_path_unknown_extension():
    """Test that an unrecognized kernel extension is rejected."""
    with pytest.raises(InvalidEmaFileError):
        SPICEFilePath.from_filename("ema_sclk_00001.exe")


@pytest.mark.parametrize(
    ("filename", "expected_type"),
    [
        ("ema_l1_anc_sc_123_20240115.csv", AncillaryFilePath),
        ("ema_l0_hsk_emb_20240115.pkts", HousekeepingFilePath),
        ("ema_l0_sci_emb_20240115.pkts", ScienceFilePath),
        (
            "ema_emb_l1a_20321207t122030_observing-mode-info_p_v02-01.fits",
            ScienceFilePath,
        ),
        ("ema_mission_events_20240101_20240131.xml", MissionEventsFilePath),
        ("moc_manifest_202401151230.txt", ManifestFilePath),
        ("ema_sclk_00001.tsc", SPICEFilePath),
    ],
)
def test_generate_ema_file_path(filename: str, expected_type: type):
    """Test that each convention is dispatched to the right class."""
    assert isinstance(generate_ema_file_path(filename), expected_type)


def test_generate_ema_file_path_invalid():
    """Test that a filename matching nothing raises with a clear message."""
    with pytest.raises(InvalidEmaFileError, match="does not match any known"):
        generate_ema_file_path("not_a_real_file.docx")
