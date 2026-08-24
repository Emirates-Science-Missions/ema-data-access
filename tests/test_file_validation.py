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
    assert parsed.construct_path() == "ancillary/ema_l1_anc_sc_123_20240115.csv"


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


def test_ancillary_file_path_versioned():
    """Test parsing the version suffix the PDC adds once it ingests a file."""
    parsed = AncillaryFilePath.from_filename("ema_l1_anc_sc_123_20240115_v01.csv")

    assert parsed.apid == 123
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)


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
    assert parsed.construct_path() == f"manifest/{payload}/{filename}"


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
    assert parsed.construct_path() == ("housekeeping/emb/ema_l0_hsk_emb_20240115.pkts")


def test_housekeeping_file_path_invalid_payload():
    """Test that "moc" is not a valid housekeeping payload."""
    with pytest.raises(InvalidEmaFileError):
        HousekeepingFilePath.from_filename("ema_l0_hsk_moc_20240115.pkts")


def test_housekeeping_file_path_versioned():
    """Test parsing the version suffix the PDC adds once it ingests a file."""
    parsed = HousekeepingFilePath.from_filename("ema_l0_hsk_emb_20240115_v01.pkts")

    assert parsed.payload == "emb"
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)


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
    assert parsed.construct_path() == "science/emb/l0/ema_l0_sci_emb_20240115.pkts"


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
    assert parsed.construct_path() == f"science/emb/l1a/{filename}"


def test_science_file_path_invalid():
    """Test that a filename matching neither science pattern is rejected."""
    with pytest.raises(InvalidEmaFileError, match="ScienceFilePath"):
        ScienceFilePath.from_filename("not_a_science_file.fits")


def test_science_file_path_l0_versioned():
    """Test parsing the version suffix the PDC adds once it ingests a file."""
    parsed = ScienceFilePath.from_filename("ema_l0_sci_emb_20240115_v01.pkts")

    assert parsed.payload == "emb"
    assert parsed.data_level == "l0"
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)


def test_mission_events_file_path():
    """Test parsing, metadata, and path construction for a mission events file."""
    parsed = MissionEventsFilePath.from_filename(
        "ema_mission_events_20240101_20240131.xml"
    )

    assert parsed.start_date == datetime(2024, 1, 1, tzinfo=UTC)
    assert parsed.end_date == datetime(2024, 1, 31, tzinfo=UTC)
    assert parsed.construct_path() == (
        "mission_events/ema_mission_events_20240101_20240131.xml"
    )


def test_mission_events_file_path_versioned():
    """Test parsing the version suffix the PDC adds once it ingests a file."""
    parsed = MissionEventsFilePath.from_filename(
        "ema_mission_events_20240101_20240131_v01.xml"
    )

    assert parsed.start_date == datetime(2024, 1, 1, tzinfo=UTC)
    assert parsed.end_date == datetime(2024, 1, 31, tzinfo=UTC)


def test_spice_file_path():
    """Tests the ``SPICEFilePath`` class."""
    # Spacecraft ephemeris: predicted/reconstructed/reference
    file_path = SPICEFilePath("ema_recon_20240101_20240115_v001.bsp")
    assert file_path.construct_path() == (
        "spice/ephem_reconstructed/ema_recon_20240101_20240115_v001.bsp"
    )

    # GSINT-224 Asteroid Ephemeris: one file per body
    file_path = SPICEFilePath("ema_sun_v001.bsp")
    assert file_path.construct_path() == "spice/ephem_sun/ema_sun_v001.bsp"

    # Standard NAIF DE-series Planetary Ephemeris -- no "ema_" prefix
    file_path = SPICEFilePath("de440.bsp")
    assert file_path.construct_path() == "spice/ephem_planetary/de440.bsp"

    # Standard NAIF Mars System Ephemeris
    file_path = SPICEFilePath("mar097.bsp")
    assert file_path.construct_path() == "spice/ephem_mars_system/mar097.bsp"

    # Standard NAIF leapseconds / planetary constants conventions
    file_path = SPICEFilePath("naif0012.tls")
    assert file_path.construct_path() == "spice/leapseconds/naif0012.tls"
    file_path = SPICEFilePath("pck00011.tpc")
    assert file_path.construct_path() == "spice/planetary_constants/pck00011.tpc"

    # EMA spacecraft clock / frames -- "vvv" is the version number
    file_path = SPICEFilePath("ema_sclk_001.tsc")
    assert file_path.construct_path() == "spice/spacecraft_clock/ema_sclk_001.tsc"
    file_path = SPICEFilePath("ema_fk_001.tf")
    assert file_path.construct_path() == "spice/frames/ema_fk_001.tf"

    # Observatory attitude reconstructed/predicted
    file_path = SPICEFilePath("ema_rck_20240101_20240115_v001.bc")
    assert file_path.construct_path() == (
        "spice/attitude_reconstructed/ema_rck_20240101_20240115_v001.bc"
    )
    file_path = SPICEFilePath("ema_pck_20240101_20240115_v001.bc")
    assert file_path.construct_path() == (
        "spice/attitude_predicted/ema_pck_20240101_20240115_v001.bc"
    )

    # Test a filename matching no known convention
    with pytest.raises(InvalidEmaFileError):
        SPICEFilePath("test.txt")


@pytest.mark.parametrize(
    ("type_token", "kernel_type"),
    [
        ("pred", "ephem_predicted"),
        ("recon", "ephem_reconstructed"),
        ("ref", "ephem_reference"),
    ],
)
def test_spice_extract_spacecraft_ephemeris_parts(type_token, kernel_type):
    """Test the predicted/reconstructed/reference ephemeris conventions."""
    file_path = SPICEFilePath(f"ema_{type_token}_20240101_20240115_v001.bsp")
    expected_file_root = f"ema_{type_token}_20240101_20240115"
    assert file_path.spice_metadata["version"] == 1
    assert file_path.spice_metadata["kernel_type"] == kernel_type
    assert file_path.spice_metadata["file_root"] == expected_file_root
    assert file_path.spice_metadata["start_date"] == datetime(2024, 1, 1, tzinfo=UTC)
    assert file_path.spice_metadata["end_date"] == datetime(2024, 1, 15, tzinfo=UTC)
    assert len(file_path.spice_metadata) == 5


@pytest.mark.parametrize(
    ("body", "kernel_type"),
    [
        ("sun", "ephem_sun"),
        ("venus", "ephem_venus"),
        ("earth", "ephem_earth"),
        ("mars", "ephem_mars"),
        ("wes", "ephem_wes"),
        ("chi", "ephem_chi"),
        ("roc", "ephem_roc"),
        ("va28", "ephem_va28"),
        ("rc76", "ephem_rc76"),
        ("sg6", "ephem_sg6"),
        ("jus", "ephem_jus"),
    ],
)
def test_spice_extract_body_ephemeris_parts(body, kernel_type):
    """Test the GSINT-224 (Asteroid Ephemeris) per-body convention."""
    file_path = SPICEFilePath(f"ema_{body}_v001.bsp")
    assert file_path.spice_metadata["version"] == 1
    assert file_path.spice_metadata["kernel_type"] == kernel_type
    assert file_path.spice_metadata["file_root"] == f"ema_{body}"
    assert file_path.spice_metadata["start_date"] is None
    assert file_path.spice_metadata["end_date"] is None
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_planetary_ephemeris_parts():
    """Test the standard NAIF DE-series Planetary Ephemeris convention."""
    file_path = SPICEFilePath("de440.bsp")
    assert file_path.spice_metadata["version"] == 440
    assert file_path.spice_metadata["kernel_type"] == "ephem_planetary"
    assert file_path.spice_metadata["file_root"] == "de"
    assert file_path.spice_metadata["start_date"] is None
    assert file_path.spice_metadata["end_date"] is None
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_mars_system_ephemeris_parts():
    """Test the standard NAIF Mars System Ephemeris convention."""
    file_path = SPICEFilePath("mar097.bsp")
    assert file_path.spice_metadata["version"] == 97
    assert file_path.spice_metadata["kernel_type"] == "ephem_mars_system"
    assert file_path.spice_metadata["file_root"] == "mar"
    assert file_path.spice_metadata["start_date"] is None
    assert file_path.spice_metadata["end_date"] is None
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_leapsecond_parts():
    """Test the standard NAIF leapseconds convention."""
    file_path = SPICEFilePath("naif0012.tls")
    assert file_path.spice_metadata["version"] == 12
    assert file_path.spice_metadata["kernel_type"] == "leapseconds"
    assert file_path.spice_metadata["file_root"] == "naif"
    assert file_path.spice_metadata["start_date"] is None
    assert file_path.spice_metadata["end_date"] is None
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_planetary_constants_parts():
    """Test the standard NAIF planetary constants convention."""
    file_path = SPICEFilePath("pck00011.tpc")
    assert file_path.spice_metadata["version"] == 11
    assert file_path.spice_metadata["kernel_type"] == "planetary_constants"
    assert file_path.spice_metadata["file_root"] == "pck"
    assert file_path.spice_metadata["start_date"] is None
    assert file_path.spice_metadata["end_date"] is None
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_binary_planetary_constants_parts():
    """Test the NAIF binary PCK (.bpc) planetary constants convention."""
    file_path = SPICEFilePath("pck00011.bpc")
    assert file_path.spice_metadata["version"] == 11
    assert file_path.spice_metadata["kernel_type"] == "planetary_constants"
    assert file_path.spice_metadata["file_root"] == "pck"
    assert len(file_path.spice_metadata) == 5
    assert file_path.construct_path() == "spice/planetary_constants/pck00011.bpc"


@pytest.mark.parametrize(
    "filename",
    [
        "naif0012.bsp",  # leapseconds prefix with an ephemeris extension
        "de440.tls",  # planetary ephemeris prefix with a leapseconds extension
        "pck00011.bsp",  # planetary constants prefix with an ephemeris extension
        "mar097.tpc",  # mars system ephemeris prefix with a constants extension
    ],
)
def test_spice_rejects_mismatched_type_extension_combos(filename):
    """A kernel prefix must only match its own convention's extension(s)."""
    with pytest.raises(InvalidEmaFileError):
        SPICEFilePath(filename)


def test_spice_file_path_from_filename():
    """SPICEFilePath.from_filename() must delegate to the constructor."""
    file_path = SPICEFilePath.from_filename("naif0012.tls")
    assert isinstance(file_path, SPICEFilePath)
    assert file_path.spice_metadata["kernel_type"] == "leapseconds"


def test_spice_extract_spacecraft_clock_parts():
    """Vvv is the version number."""
    file_path = SPICEFilePath("ema_sclk_001.tsc")
    assert file_path.spice_metadata["version"] == 1
    assert file_path.spice_metadata["kernel_type"] == "spacecraft_clock"
    assert file_path.spice_metadata["file_root"] == "ema_sclk"
    assert file_path.spice_metadata["start_date"] is None
    assert file_path.spice_metadata["end_date"] is None
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_frames_parts():
    """Vvv is the version number."""
    file_path = SPICEFilePath("ema_fk_001.tf")
    assert file_path.spice_metadata["version"] == 1
    assert file_path.spice_metadata["kernel_type"] == "frames"
    assert file_path.spice_metadata["file_root"] == "ema_fk"
    assert file_path.spice_metadata["start_date"] is None
    assert file_path.spice_metadata["end_date"] is None
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_attitude_reconstructed_parts():
    """Test the observatory attitude reconstructed convention."""
    file_path = SPICEFilePath("ema_rck_20240101_20240115_v001.bc")
    assert file_path.spice_metadata["version"] == 1
    assert file_path.spice_metadata["kernel_type"] == "attitude_reconstructed"
    assert file_path.spice_metadata["file_root"] == "ema_rck_20240101_20240115"
    assert file_path.spice_metadata["start_date"] == datetime(2024, 1, 1, tzinfo=UTC)
    assert file_path.spice_metadata["end_date"] == datetime(2024, 1, 15, tzinfo=UTC)
    assert len(file_path.spice_metadata) == 5


def test_spice_extract_attitude_predicted_parts():
    """Test the observatory attitude predicted convention."""
    file_path = SPICEFilePath("ema_pck_20240101_20240115_v001.bc")
    assert file_path.spice_metadata["version"] == 1
    assert file_path.spice_metadata["kernel_type"] == "attitude_predicted"
    assert file_path.spice_metadata["file_root"] == "ema_pck_20240101_20240115"
    assert file_path.spice_metadata["start_date"] == datetime(2024, 1, 1, tzinfo=UTC)
    assert file_path.spice_metadata["end_date"] == datetime(2024, 1, 15, tzinfo=UTC)
    assert len(file_path.spice_metadata) == 5

    planetary_constants = SPICEFilePath("pck00011.tpc")
    assert planetary_constants.spice_metadata["kernel_type"] == "planetary_constants"


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
        ("ema_sclk_001.tsc", SPICEFilePath),
    ],
)
def test_generate_ema_file_path(filename: str, expected_type: type):
    """Test that each convention is dispatched to the right class."""
    assert isinstance(generate_ema_file_path(filename), expected_type)


def test_generate_ema_file_path_invalid():
    """Test that a filename matching nothing raises with a clear message."""
    with pytest.raises(InvalidEmaFileError, match="does not match any known"):
        generate_ema_file_path("not_a_real_file.docx")


def test_generate_ema_file_path_invalid_date_is_not_masked():
    """A pattern match with an invalid calendar date must surface clearly.

    It must not be swallowed into the generic "does not match any known
    convention" message, since that would hide a real validation failure
    behind wording that implies the filename's shape is unrecognized.
    """
    with pytest.raises(InvalidEmaFileError, match="failed to parse"):
        generate_ema_file_path("ema_l1_anc_sc_123_20260230.csv")  # Feb 30


def test_ancillary_file_path_invalid_date():
    """Test that a matching-but-invalid date raises InvalidEmaFileError."""
    with pytest.raises(InvalidEmaFileError, match="failed to parse"):
        AncillaryFilePath.from_filename("ema_l1_anc_sc_123_20260230.csv")


def test_science_file_path_l0_invalid_date():
    """Test that an L0 science filename with an invalid date is rejected."""
    with pytest.raises(InvalidEmaFileError, match="failed to parse"):
        ScienceFilePath.from_filename("ema_l0_sci_emb_20260230.pkts")
