"""Tests for the ``file_validation`` module."""

from datetime import UTC, datetime

import pytest

import ema_data_access
from ema_data_access.file_validation import (
    AncillaryFilePath,
    CalibrationFilePath,
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
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "ancillary/ema_l1_anc_sc_123_20240115.csv"
    )


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
        ("mista_manifest_202401151230.txt", "mista"),
    ],
)
def test_manifest_file_path(filename: str, payload: str):
    """Test both the "moc" and payload-scoped manifest conventions."""
    parsed = ManifestFilePath.from_filename(filename)

    assert parsed.payload == payload
    assert parsed.timetag == datetime(2024, 1, 15, 12, 30, tzinfo=UTC)
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
        f"manifest/{payload}/{filename}"
    )


def test_manifest_file_path_invalid_payload():
    """Test that a payload outside the known set is rejected."""
    with pytest.raises(InvalidEmaFileError):
        ManifestFilePath.from_filename("xyz_manifest_202401151230.txt")


@pytest.mark.parametrize("source", ["flight", "softsim", "flatsat"])
def test_housekeeping_file_path(source: str):
    """Test parsing, metadata, and path construction for a housekeeping file."""
    filename = f"ema_l0_hsk_embirs_{source}_20240115.pkts"
    parsed = HousekeepingFilePath.from_filename(filename)

    assert parsed.payload == "embirs"
    assert parsed.source == source
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)
    assert parsed.to_metadata() == {
        "file_name": filename,
        "payload": "embirs",
        "source": source,
        "timetag": datetime(2024, 1, 15, tzinfo=UTC),
    }
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
        f"{source}/housekeeping/embirs/2024/01/{filename}"
    )


@pytest.mark.parametrize(
    "filename",
    [
        "ema_l0_hsk_moc_flight_20240115.pkts",  # moc isn't a housekeeping payload
        "ema_l0_hsk_emb_flight_20240115.pkts",  # old three-letter payload code
        "ema_l0_hsk_embirs_20240115.pkts",  # missing source
        "ema_l0_hsk_embirs_ground_20240115.pkts",  # unknown source
    ],
)
def test_housekeeping_file_path_invalid(filename: str):
    """Test that bad payloads and missing or unknown sources are rejected."""
    with pytest.raises(InvalidEmaFileError):
        HousekeepingFilePath.from_filename(filename)


def test_housekeeping_file_path_versioned():
    """Test parsing the version suffix the PDC adds once it ingests a file."""
    parsed = HousekeepingFilePath.from_filename(
        "ema_l0_hsk_embirs_flight_20240115_v01.pkts"
    )

    assert parsed.payload == "embirs"
    assert parsed.source == "flight"
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)


@pytest.mark.parametrize("source", ["flight", "softsim", "flatsat"])
def test_science_file_path_l0(source: str):
    """Test parsing an L0 science file, which has no version/descriptor."""
    filename = f"ema_l0_sci_embirs_{source}_20240115.pkts"
    parsed = ScienceFilePath.from_filename(filename)

    assert parsed.payload == "embirs"
    assert parsed.source == source
    assert parsed.data_level == "l0"
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)
    assert parsed.descriptor is None
    assert parsed.orbit_number is None
    assert parsed.pred_rec is None
    assert parsed.version is None
    assert parsed.subversion is None
    assert parsed.file_extension == "pkts"
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
        f"{source}/science/embirs/l0/2024/01/{filename}"
    )


@pytest.mark.parametrize(
    "filename",
    [
        "ema_l0_sci_emb_flight_20240115.pkts",  # old three-letter payload code
        "ema_l0_sci_embirs_20240115.pkts",  # missing source
        "ema_l0_sci_embirs_ground_20240115.pkts",  # unknown source
    ],
)
def test_science_file_path_l0_invalid(filename: str):
    """Test that bad payloads and missing or unknown sources are rejected."""
    with pytest.raises(InvalidEmaFileError):
        ScienceFilePath.from_filename(filename)


@pytest.mark.parametrize("payload", ["mac", "gnc"])
def test_mac_gnc_payloads(payload: str):
    """Test that the mac and gnc payload codes are accepted in L0 names.

    Manifests use upper-level codes, so only mac is a valid manifest payload;
    gnc manifests are covered by test_l1_and_manifest_reject_non_l1_payloads.
    """
    hsk = HousekeepingFilePath.from_filename(
        f"ema_l0_hsk_{payload}_flight_20240115.pkts"
    )
    assert hsk.payload == payload

    sci = ScienceFilePath.from_filename(f"ema_l0_sci_{payload}_flight_20240115.pkts")
    assert sci.payload == payload

    if payload == "mac":
        manifest = ManifestFilePath.from_filename(
            f"{payload}_manifest_202401151230.txt"
        )
        assert manifest.payload == payload


def test_science_file_path_l1a():
    """Test parsing an L1a+ science file, which has no source."""
    filename = (
        "ema_embirs_l1a_20321207t122030_observing-mode-info_orbit000_p_v02-01.fits"
    )
    parsed = ScienceFilePath.from_filename(filename)

    assert parsed.payload == "embirs"
    assert parsed.source is None
    assert parsed.data_level == "l1a"
    assert parsed.timetag == datetime(2032, 12, 7, 12, 20, 30, tzinfo=UTC)
    assert parsed.target is None
    assert parsed.mode is None
    assert parsed.descriptor == "observing-mode-info"
    assert parsed.orbit_number == 0
    assert parsed.pred_rec == "p"
    assert parsed.version == 2
    assert parsed.subversion == 1
    assert parsed.file_extension == "fits"
    assert parsed.to_metadata() == {
        "file_name": filename,
        "payload": "embirs",
        "source": None,
        "data_level": "l1a",
        "timetag": datetime(2032, 12, 7, 12, 20, 30, tzinfo=UTC),
        "target": None,
        "mode": None,
        "descriptor": "observing-mode-info",
        "orbit_number": 0,
        "pred_rec": "p",
        "version": 2,
        "subversion": 1,
        "file_extension": "fits",
    }
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
        f"science/embirs/l1a/2032/12/{filename}"
    )


def test_calibration_file_path():
    """Test parsing, metadata, and path construction for a calibration file."""
    filename = "ema_cal_mista_dark-frame_20240101_v01-00.fits"
    parsed = CalibrationFilePath.from_filename(filename)

    assert parsed.to_metadata() == {
        "file_name": filename,
        "payload": "mista",
        "descriptor": "dark-frame",
        "timetag": datetime(2024, 1, 1, tzinfo=UTC),
        "version": 1,
        "subversion": 0,
        "file_extension": "fits",
    }
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
        f"calibration/mista/{filename}"
    )


def test_calibration_file_path_datetime_start():
    """Test that a YYYYMMDDtHHMMSS start is parsed to the second."""
    parsed = CalibrationFilePath.from_filename(
        "ema_cal_reptile-3_gain-table_20321207t122030_v02-11.json"
    )
    assert parsed.payload == "reptile-3"
    assert parsed.timetag == datetime(2032, 12, 7, 12, 20, 30, tzinfo=UTC)
    assert (parsed.version, parsed.subversion) == (2, 11)


@pytest.mark.parametrize("ext", ["csv", "fits", "cdf", "txt", "ascii", "json"])
def test_calibration_file_path_extensions(ext: str):
    """Test every accepted calibration file extension."""
    parsed = CalibrationFilePath.from_filename(
        f"ema_cal_embirs_flat-field_20240101_v01-00.{ext}"
    )
    assert parsed.file_extension == ext


@pytest.mark.parametrize(
    "filename",
    [
        # L0-only payload code.
        "ema_cal_gnc_dark-frame_20240101_v01-00.fits",
        # Missing descriptor.
        "ema_cal_mista_20240101_v01-00.fits",
        # Missing subversion.
        "ema_cal_mista_dark-frame_20240101_v01.fits",
        # Single-digit version.
        "ema_cal_mista_dark-frame_20240101_v1-00.fits",
        # Unsupported extension.
        "ema_cal_mista_dark-frame_20240101_v01-00.pkts",
        # Underscore in descriptor.
        "ema_cal_mista_dark_frame_20240101_v01-00.fits",
    ],
)
def test_calibration_file_path_invalid(filename: str):
    """Test that malformed calibration names are rejected."""
    with pytest.raises(InvalidEmaFileError):
        CalibrationFilePath.from_filename(filename)


def test_calibration_file_path_invalid_date():
    """Test that a pattern match with an impossible date fails to parse."""
    with pytest.raises(InvalidEmaFileError, match="failed to parse"):
        CalibrationFilePath.from_filename(
            "ema_cal_mista_dark-frame_20240230_v01-00.fits"
        )


L0_PAYLOADS = ["mista", "embirs", "emacs", "rept", "gnc", "prb", "mac"]
L1_PAYLOADS = [
    "mista",
    "embirs",
    "emacs",
    "pnac",
    "cnac",
    "irc",
    "reptile-3",
    "mac",
    "prb",
]


@pytest.mark.parametrize("payload", L0_PAYLOADS)
def test_l0_payloads(payload: str):
    """Test that every L0 payload code parses in L0 science and housekeeping.

    Parameters
    ----------
    payload : str
        L0 payload code under test.
    """
    sci = ScienceFilePath.from_filename(f"ema_l0_sci_{payload}_flight_20240115.pkts")
    hsk = HousekeepingFilePath.from_filename(
        f"ema_l0_hsk_{payload}_flight_20240115.pkts"
    )

    assert sci.payload == payload
    assert hsk.payload == payload


@pytest.mark.parametrize("payload", ["pnac", "cnac", "irc", "reptile-3", "pnc"])
def test_l0_rejects_non_l0_payloads(payload: str):
    """Test that upper-level-only and retired codes are rejected in L0 names.

    Parameters
    ----------
    payload : str
        Payload code that isn't valid for L0.
    """
    with pytest.raises(InvalidEmaFileError):
        ScienceFilePath.from_filename(f"ema_l0_sci_{payload}_flight_20240115.pkts")
    with pytest.raises(InvalidEmaFileError):
        HousekeepingFilePath.from_filename(f"ema_l0_hsk_{payload}_flight_20240115.pkts")


@pytest.mark.parametrize("payload", L1_PAYLOADS)
def test_l1_and_manifest_payloads(payload: str):
    """Test that every upper-level payload code parses in L1a+ and manifests.

    Parameters
    ----------
    payload : str
        Upper-level payload code under test.
    """
    sci = ScienceFilePath.from_filename(
        f"ema_{payload}_l1a_20321207t122030_flux_orbit000_p_v01-00.fits"
    )
    manifest = ManifestFilePath.from_filename(f"{payload}_manifest_202401151230.txt")

    assert sci.payload == payload
    assert manifest.payload == payload


@pytest.mark.parametrize("payload", ["rept", "gnc", "cnc", "pnc"])
def test_l1_and_manifest_reject_non_l1_payloads(payload: str):
    """Test that L0-only and retired codes are rejected in L1a+ and manifests.

    Parameters
    ----------
    payload : str
        Payload code that isn't valid for upper-level names.
    """
    with pytest.raises(InvalidEmaFileError):
        ScienceFilePath.from_filename(
            f"ema_{payload}_l1a_20321207t122030_flux_orbit000_p_v01-00.fits"
        )
    with pytest.raises(InvalidEmaFileError):
        ManifestFilePath.from_filename(f"{payload}_manifest_202401151230.txt")


def test_science_file_path_l1a_optional_fields():
    """Test an L1a+ name with a date-only start, no target/mode, and "na"."""
    parsed = ScienceFilePath.from_filename(
        "ema_reptile-3_l2_20321207_flux_orbit012_na_v01-00.cdf"
    )

    assert parsed.timetag == datetime(2032, 12, 7, tzinfo=UTC)
    assert parsed.target is None
    assert parsed.mode is None
    assert parsed.descriptor == "flux"
    assert parsed.orbit_number == 12
    assert parsed.pred_rec == "na"
    assert parsed.file_extension == "cdf"


@pytest.mark.parametrize("ext", ["fits", "png", "cdf", "ascii", "csv"])
def test_science_file_path_l1a_extensions(ext: str):
    """Test that every allowed L1a+ file extension parses.

    Parameters
    ----------
    ext : str
        File extension under test.
    """
    parsed = ScienceFilePath.from_filename(
        f"ema_embirs_l1a_20321207t122030_flux_orbit000_p_v01-00.{ext}"
    )

    assert parsed.file_extension == ext


@pytest.mark.parametrize(
    ("token", "target", "mode", "descriptor"),
    [
        ("a1-sci-spectra", "a1", "sci", "spectra"),
        ("a6-icu-cal-lamp", "a6", "icu", "cal-lamp"),
        ("a7iso-sky-img", "a7iso", "sky", "img"),
        ("a7pso-flt-img", "a7pso", "flt", "img"),
        ("c0-drk-img", "c0", "drk", "img"),
        ("c12-cal-frame", "c12", "cal", "frame"),
    ],
)
def test_science_file_path_l1a_target_mode(
    token: str, target: str, mode: str, descriptor: str
):
    """Test that a target-mode prefix is split off the descriptor.

    Parameters
    ----------
    token : str
        The full `<target>-<mode>-<descriptor>` filename field.
    target : str
        Expected parsed target.
    mode : str
        Expected parsed mode.
    descriptor : str
        Expected parsed descriptor.
    """
    filename = f"ema_mista_l1a_20321207t122030_{token}_orbit003_r_v01-00.fits"
    parsed = ScienceFilePath.from_filename(filename)

    assert parsed.target == target
    assert parsed.mode == mode
    assert parsed.descriptor == descriptor
    assert parsed.to_metadata()["target"] == target
    assert parsed.to_metadata()["mode"] == mode
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
        f"science/mista/l1a/2032/12/{filename}"
    )


@pytest.mark.parametrize(
    "token",
    [
        # unknown target code is not split off, so it all stays descriptor
        "a8-sci-spectra",
        # unknown mode is not split off either
        "a1-obs-spectra",
    ],
)
def test_science_file_path_l1a_unrecognized_target_mode(token: str):
    """Test that a prefix that isn't a known target-mode stays in the descriptor.

    Parameters
    ----------
    token : str
        Descriptor field whose prefix isn't a known target and mode.
    """
    parsed = ScienceFilePath.from_filename(
        f"ema_mista_l1a_20321207t122030_{token}_orbit003_r_v01-00.fits"
    )

    assert parsed.target is None
    assert parsed.mode is None
    assert parsed.descriptor == token


@pytest.mark.parametrize(
    "filename",
    [
        # missing descriptor
        "ema_embirs_l1a_20321207t122030_orbit000_p_v01-00.fits",
        # target-mode with no descriptor
        "ema_mista_l1a_20321207t122030_a1-sci_orbit000_p_v01-00.fits",
        # uppercase target
        "ema_mista_l1a_20321207t122030_A1-sci-spectra_orbit000_p_v01-00.fits",
        # missing orbit field
        "ema_embirs_l1a_20321207t122030_mode-descriptor_p_v01-00.fits",
        # orbit must be exactly three digits
        "ema_embirs_l1a_20321207t122030_flux_orbit01_p_v01-00.fits",
        "ema_embirs_l1a_20321207t122030_flux_orbit0001_p_v01-00.fits",
        # start time truncated to the hour or minute
        "ema_embirs_l1a_20321207t12_flux_orbit000_p_v01-00.fits",
        "ema_embirs_l1a_20321207t1220_flux_orbit000_p_v01-00.fits",
        # unknown predict/reconstruct flag
        "ema_embirs_l1a_20321207t122030_flux_orbit000_x_v01-00.fits",
        # pkts is L0 only
        "ema_embirs_l1a_20321207t122030_flux_orbit000_p_v01-00.pkts",
    ],
)
def test_science_file_path_l1a_invalid(filename: str):
    """Test that L1a+ names breaking the convention are rejected.

    Parameters
    ----------
    filename : str
        Invalid L1a+ file name.
    """
    with pytest.raises(InvalidEmaFileError):
        ScienceFilePath.from_filename(filename)


def test_science_file_path_l1a_requires_subversion():
    """Test that an L1a+ name without a subversion is rejected.

    The ICD format is vNN-NN, so the subversion is mandatory.
    """
    with pytest.raises(InvalidEmaFileError):
        ScienceFilePath.from_filename(
            "ema_embirs_l1a_20321207t122030_observing-mode-info_orbit000_p_v01.fits"
        )


def test_science_file_path_l1a_major_version_zero():
    """Test that a v00-NN pre-deployment version parses, with major 0."""
    parsed = ScienceFilePath.from_filename(
        "ema_embirs_l1a_20321207t122030_observing-mode-info_orbit000_p_v00-03.fits"
    )

    assert parsed.version == 0
    assert parsed.subversion == 3


def test_science_file_path_invalid():
    """Test that a filename matching neither science pattern is rejected."""
    with pytest.raises(InvalidEmaFileError, match="ScienceFilePath"):
        ScienceFilePath.from_filename("not_a_science_file.fits")


def test_science_file_path_l0_versioned():
    """Test parsing the version suffix the PDC adds once it ingests a file."""
    parsed = ScienceFilePath.from_filename("ema_l0_sci_embirs_flight_20240115_v01.pkts")

    assert parsed.payload == "embirs"
    assert parsed.source == "flight"
    assert parsed.data_level == "l0"
    assert parsed.timetag == datetime(2024, 1, 15, tzinfo=UTC)


def test_mission_events_file_path():
    """Test parsing, metadata, and path construction for a mission events file."""
    parsed = MissionEventsFilePath.from_filename(
        "ema_mission_events_20240101_20240131.xml"
    )

    assert parsed.start_date == datetime(2024, 1, 1, tzinfo=UTC)
    assert parsed.end_date == datetime(2024, 1, 31, tzinfo=UTC)
    assert parsed.construct_path() == ema_data_access.config["DATA_DIR"] / (
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
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/ephem_reconstructed/ema_recon_20240101_20240115_v001.bsp"
    )

    # GSINT-224 Asteroid Ephemeris: one file per body
    file_path = SPICEFilePath("ema_sun_v001.bsp")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/ephem_sun/ema_sun_v001.bsp"
    )

    # Standard NAIF DE-series Planetary Ephemeris -- no "ema_" prefix
    file_path = SPICEFilePath("de440.bsp")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/ephem_planetary/de440.bsp"
    )

    # Standard NAIF Mars System Ephemeris
    file_path = SPICEFilePath("mar097.bsp")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/ephem_mars_system/mar097.bsp"
    )

    # Standard NAIF leapseconds / planetary constants conventions
    file_path = SPICEFilePath("naif0012.tls")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/leapseconds/naif0012.tls"
    )
    file_path = SPICEFilePath("pck00011.tpc")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/planetary_constants/pck00011.tpc"
    )

    # EMA spacecraft clock / frames -- "vvv" is the version number
    file_path = SPICEFilePath("ema_sclk_001.tsc")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/spacecraft_clock/ema_sclk_001.tsc"
    )
    file_path = SPICEFilePath("ema_fk_001.tf")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/frames/ema_fk_001.tf"
    )

    # Observatory attitude reconstructed/predicted
    file_path = SPICEFilePath("ema_rck_20240101_20240115_v001.bc")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/attitude_reconstructed/ema_rck_20240101_20240115_v001.bc"
    )
    file_path = SPICEFilePath("ema_pck_20240101_20240115_v001.bc")
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
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
    assert file_path.construct_path() == ema_data_access.config["DATA_DIR"] / (
        "spice/planetary_constants/pck00011.bpc"
    )


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
        ("ema_l0_hsk_embirs_flight_20240115.pkts", HousekeepingFilePath),
        ("ema_l0_sci_embirs_softsim_20240115.pkts", ScienceFilePath),
        (
            "ema_embirs_l1a_20321207t122030_observing-mode-info_orbit000_p_v02-01.fits",
            ScienceFilePath,
        ),
        ("ema_cal_mista_dark-frame_20240101_v01-00.fits", CalibrationFilePath),
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
        ScienceFilePath.from_filename("ema_l0_sci_embirs_flight_20260230.pkts")
