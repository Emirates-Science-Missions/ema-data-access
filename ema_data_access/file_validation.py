"""Filename validation and parsing for EMA PDC files."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import ema_data_access

_PAYLOADS = "mst|emb|emc|rpt|ldr"
_MANIFEST_PAYLOADS = f"moc|{_PAYLOADS}"
_DATA_LEVELS = "l1|l1a|l1b|l2|l2a|l2b|l3|ql"


class InvalidEmaFileError(Exception):
    """Indicates a bad file type."""


class _FilenamePatternMismatchError(InvalidEmaFileError):
    """A filename didn't match a convention's pattern at all."""


def _parse_ymd(value: str) -> datetime:
    """Parse a YYYYMMDD string into a UTC datetime."""
    return datetime.strptime(value, "%Y%m%d").replace(tzinfo=UTC)


def _parse_ymd_hm(value: str) -> datetime:
    """Parse a YYYYMMDDHHMM string into a UTC datetime."""
    return datetime.strptime(value, "%Y%m%d%H%M").replace(tzinfo=UTC)


def _parse_ymdthms(value: str) -> datetime:
    """Parse a YYYYMMDDtHHMMSS string into a UTC datetime."""
    return datetime.strptime(value, "%Y%m%dt%H%M%S").replace(tzinfo=UTC)


_VERSION_PREFIX_RE = re.compile(r"^[^\d]*")


def _parse_spice_version(value: str) -> int:
    """Parse a SPICE version token (e.g. "v001", "440") into an int."""
    return int(_VERSION_PREFIX_RE.sub("", value))


@dataclass
class EmaFilePath(ABC):
    """Base class for a parsed, validated EMA file name."""

    filename: str

    _PATTERN: ClassVar[re.Pattern]

    @classmethod
    def from_filename(cls, filename: str) -> "EmaFilePath":
        """Parse `filename`, raising InvalidEmaFileError if it doesn't match.

        Parameters
        ----------
        filename : str
            The file name to validate and parse.

        Returns
        -------
        EmaFilePath
            The parsed representation of `filename`.
        """
        match = cls._PATTERN.fullmatch(filename)
        if not match:
            raise _FilenamePatternMismatchError(
                f"{filename} does not match {cls.__name__}"
            )
        try:
            fields = cls._extract_fields(match)
        except ValueError as err:
            raise InvalidEmaFileError(
                f"{filename} matched {cls.__name__} but failed to parse: {err}"
            ) from err
        return cls(filename=filename, **fields)

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        """Turn a regex match into the subclass's extra constructor args."""
        return match.groupdict()

    @abstractmethod
    def _extra_metadata(self) -> dict:
        """Table-specific fields."""

    def to_metadata(self) -> dict:
        """Fields to insert into this file's DB table.

        Returns
        -------
        dict
            Column name/value pairs for this file's metadata table.
        """
        return {"file_name": self.filename, **self._extra_metadata()}

    @abstractmethod
    def construct_path(self) -> Path:
        """Build the local path this file should be stored at.

        Returns
        -------
        Path
            `ema_data_access.config["DATA_DIR"]` joined with this file's
            relative key (e.g. `DATA_DIR/ancillary/<filename>`).
        """
        raise NotImplementedError


@dataclass
class AncillaryFilePath(EmaFilePath):
    """ema_l1_anc_sc_<apid>_YYYYMMDD.csv."""

    apid: int
    timetag: datetime
    file_extension: str

    _PATTERN: ClassVar[re.Pattern] = re.compile(
        r"ema_l1_anc_sc_(?P<apid>\d+)_(?P<timetag>\d{8})(?:_v\d+)?"
        r"\.(?P<file_extension>csv)"
    )

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        return {
            "apid": int(match["apid"]),
            "timetag": _parse_ymd(match["timetag"]),
            "file_extension": match["file_extension"],
        }

    def _extra_metadata(self) -> dict:
        return {
            "apid": self.apid,
            "timetag": self.timetag,
            "file_extension": self.file_extension,
        }

    def construct_path(self) -> Path:
        """See base class."""
        return ema_data_access.config["DATA_DIR"] / f"ancillary/{self.filename}"


@dataclass
class ManifestFilePath(EmaFilePath):
    """moc_manifest_YYYYMMDDHHMM.txt | <payload>_manifest_YYYYMMDDHHMM.txt."""

    payload: str
    timetag: datetime

    _PATTERN: ClassVar[re.Pattern] = re.compile(
        rf"(?P<payload>{_MANIFEST_PAYLOADS})_manifest_(?P<timetag>\d{{12}})\.txt"
    )

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        return {
            "payload": match["payload"],
            "timetag": _parse_ymd_hm(match["timetag"]),
        }

    def _extra_metadata(self) -> dict:
        return {"payload": self.payload, "timetag": self.timetag}

    def construct_path(self) -> Path:
        """See base class."""
        return (
            ema_data_access.config["DATA_DIR"]
            / f"manifest/{self.payload}/{self.filename}"
        )


@dataclass
class HousekeepingFilePath(EmaFilePath):
    """ema_l0_hsk_<payload>_YYYYMMDD.pkts."""

    payload: str
    timetag: datetime

    _PATTERN: ClassVar[re.Pattern] = re.compile(
        rf"ema_l0_hsk_(?P<payload>{_PAYLOADS})_(?P<timetag>\d{{8}})(?:_v\d+)?\.pkts"
    )

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        return {
            "payload": match["payload"],
            "timetag": _parse_ymd(match["timetag"]),
        }

    def _extra_metadata(self) -> dict:
        return {"payload": self.payload, "timetag": self.timetag}

    def construct_path(self) -> Path:
        """See base class."""
        return (
            ema_data_access.config["DATA_DIR"]
            / f"housekeeping/{self.payload}/{self.filename}"
        )


@dataclass
class ScienceFilePath(EmaFilePath):
    """Covers two conventions that both land in the `science` table.

    L0:   ema_l0_sci_<payload>_YYYYMMDD.pkts
    L1a+: ema_<payload>_<data_level>_YYYYMMDDtHHMMSS_<descriptor>_<pred_rec>_
          v<version>(-<subversion>).fits
    """

    payload: str
    data_level: str
    timetag: datetime
    descriptor: str | None
    pred_rec: str | None
    version: int | None
    subversion: int | None
    file_extension: str

    _L0_PATTERN: ClassVar[re.Pattern] = re.compile(
        rf"ema_l0_sci_(?P<payload>{_PAYLOADS})_(?P<timetag>\d{{8}})(?:_v\d+)?"
        rf"\.(?P<file_extension>pkts)"
    )
    _L1_PATTERN: ClassVar[re.Pattern] = re.compile(
        rf"ema_(?P<payload>{_PAYLOADS})_(?P<data_level>{_DATA_LEVELS})_"
        r"(?P<timetag>\d{8}t\d{6})_(?P<descriptor>[a-z0-9\-]+)_"
        r"(?P<pred_rec>p|r)_v(?P<version>\d+)(?:-(?P<subversion>\d+))?"
        r"\.(?P<file_extension>fits)"
    )

    @classmethod
    def from_filename(cls, filename: str) -> "ScienceFilePath":
        """Parse `filename` against the L0 pattern, then the L1a+ pattern.

        Parameters
        ----------
        filename : str
            The file name to validate and parse.

        Returns
        -------
        ScienceFilePath
            The parsed representation of `filename`.
        """
        try:
            if match := cls._L0_PATTERN.fullmatch(filename):
                return cls(
                    filename=filename,
                    payload=match["payload"],
                    data_level="l0",
                    timetag=_parse_ymd(match["timetag"]),
                    descriptor=None,
                    pred_rec=None,
                    version=None,
                    subversion=None,
                    file_extension=match["file_extension"],
                )
            if match := cls._L1_PATTERN.fullmatch(filename):
                return cls(
                    filename=filename,
                    payload=match["payload"],
                    data_level=match["data_level"],
                    timetag=_parse_ymdthms(match["timetag"]),
                    descriptor=match["descriptor"],
                    pred_rec=match["pred_rec"],
                    version=int(match["version"]),
                    subversion=(
                        int(match["subversion"]) if match["subversion"] else None
                    ),
                    file_extension=match["file_extension"],
                )
        except ValueError as err:
            raise InvalidEmaFileError(
                f"{filename} matched {cls.__name__} but failed to parse: {err}"
            ) from err
        raise _FilenamePatternMismatchError(
            f"{filename} does not match ScienceFilePath"
        )

    def _extra_metadata(self) -> dict:
        return {
            "payload": self.payload,
            "data_level": self.data_level,
            "timetag": self.timetag,
            "descriptor": self.descriptor,
            "pred_rec": self.pred_rec,
            "version": self.version,
            "subversion": self.subversion,
            "file_extension": self.file_extension,
        }

    def construct_path(self) -> Path:
        """See base class."""
        return (
            ema_data_access.config["DATA_DIR"]
            / f"science/{self.payload}/{self.data_level}/{self.filename}"
        )


@dataclass
class MissionEventsFilePath(EmaFilePath):
    """ema_mission_events_YYYYMMDD_YYYYMMDD.xml."""

    start_date: datetime
    end_date: datetime

    _PATTERN: ClassVar[re.Pattern] = re.compile(
        r"ema_mission_events_(?P<start_date>\d{8})_(?P<end_date>\d{8})"
        r"(?:_v\d+)?\.xml"
    )

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        return {
            "start_date": _parse_ymd(match["start_date"]),
            "end_date": _parse_ymd(match["end_date"]),
        }

    def _extra_metadata(self) -> dict:
        return {"start_date": self.start_date, "end_date": self.end_date}

    def construct_path(self) -> Path:
        """See base class."""
        return ema_data_access.config["DATA_DIR"] / f"mission_events/{self.filename}"


class SPICEFilePath(EmaFilePath):
    """Class for building and validating filepaths for SPICE files."""

    _dir_prefix = "spice"

    _SPICE_TYPE_MAPPING: ClassVar[dict[str, str]] = {
        # ema_pred_YYYYMMDD_YYYYMMDD_vvv.bsp
        # ema_recon_..._vvv.bsp
        # ema_ref_..._vvv.bsp
        "pred": "ephem_predicted",
        "recon": "ephem_reconstructed",
        "ref": "ephem_reference",
        # ema_YYY_vvv.bsp
        "sun": "ephem_sun",
        "venus": "ephem_venus",
        "earth": "ephem_earth",
        "mars": "ephem_mars",
        "wes": "ephem_wes",
        "chi": "ephem_chi",
        "roc": "ephem_roc",
        "va28": "ephem_va28",
        "rc76": "ephem_rc76",
        "sg6": "ephem_sg6",
        "jus": "ephem_jus",
        # deXXX.bsp
        # marXXX.bsp
        "de": "ephem_planetary",
        "mar": "ephem_mars_system",
        # naifXXXX.tls
        # pckXXXXX.tpc
        "naif": "leapseconds",
        "pck": "planetary_constants",
        # ema_sclk_vvv.tsc
        # ema_fk_vvv.tf
        "sclk": "spacecraft_clock",
        "fk": "frames",
    }

    # ema_rck_YYYYMMDD_YYYYMMDD_vvv.bc
    # ema_pck_YYYYMMDD_YYYYMMDD_vvv.bc
    _ATTITUDE_TYPE_MAPPING: ClassVar[dict[str, str]] = {
        "rck": "attitude_reconstructed",
        "pck": "attitude_predicted",
    }

    # Standard NAIF single-current-file conventions.
    _BARE_FILE_ROOT_TYPES: ClassVar[frozenset[str]] = frozenset(
        {"de", "mar", "naif", "pck"}
    )

    spacecraft_ephemeris_pattern = (
        r"ema_(?P<type>pred|recon|ref)_"
        r"(?P<start_date>\d{8})_"
        r"(?P<end_date>\d{8})_"
        r"(?P<version>[a-zA-Z0-9\-]+)\.bsp"
    )
    attitude_pattern = (
        r"ema_(?P<attitude_type>rck|pck)_"
        r"(?P<start_date>\d{8})_"
        r"(?P<end_date>\d{8})_"
        r"(?P<version>[a-zA-Z0-9\-]+)\.bc"
    )
    body_ephemeris_pattern = (
        r"ema_(?P<type>sun|venus|earth|mars|wes|chi|roc|va28|rc76|sg6|jus)_"
        r"(?P<version>[a-zA-Z0-9\-]+)\.bsp"
    )
    planetary_ephemeris_pattern = r"(?P<type>de|mar)(?P<version>\d+)\.bsp"
    leapseconds_pattern = r"(?P<type>naif)(?P<version>\d+)\.tls"
    planetary_constants_pattern = r"(?P<type>pck)(?P<version>\d+)\.(?:tpc|bpc)"
    single_kernel_pattern = r"ema_(?P<type>sclk|fk)_(?P<version>\d+)\.(?:tsc|tf)"

    valid_spice_regexes: ClassVar[tuple[re.Pattern, ...]] = (
        re.compile(spacecraft_ephemeris_pattern),
        re.compile(attitude_pattern),
        re.compile(body_ephemeris_pattern),
        re.compile(planetary_ephemeris_pattern),
        re.compile(leapseconds_pattern),
        re.compile(planetary_constants_pattern),
        re.compile(single_kernel_pattern),
    )

    def __init__(self, filename: str):
        """Parse and validate a SPICE file name.

        Parameters
        ----------
        filename : str
            The file name to validate and parse.
        """
        self.filename = filename
        self.spice_metadata = SPICEFilePath.extract_filename_components(self.filename)

    @classmethod
    def from_filename(cls, filename: str) -> "SPICEFilePath":
        """Parse `filename`, raising InvalidEmaFileError if it doesn't match.

        Parameters
        ----------
        filename : str
            The file name to validate and parse.

        Returns
        -------
        SPICEFilePath
            The parsed representation of `filename`.
        """
        return cls(filename)

    @staticmethod
    def extract_filename_components(filename: str) -> dict:
        """Extract SPICE metadata from `filename` via its matching convention.

        Parameters
        ----------
        filename : str
            The file name to validate and parse.

        Returns
        -------
        dict
            `kernel_type`, `file_root`, `start_date`, `end_date`, `version`.
        """
        try:
            for regex in SPICEFilePath.valid_spice_regexes:
                if match := regex.fullmatch(filename):
                    return SPICEFilePath._spice_parts_handler(match.groupdict())
        except ValueError as err:
            raise InvalidEmaFileError(
                f"{filename} matched a SPICE convention but failed to parse: {err}"
            ) from err
        raise _FilenamePatternMismatchError(f"{filename} does not match SPICEFilePath")

    @staticmethod
    def _dated_file_root(prefix: str, components: dict) -> str:
        """Build a date-ranged file_root: ema_<prefix>_<start_date>_<end_date>.

        Parameters
        ----------
        prefix : str
            The convention's type token (e.g. "pred", "rck").
        components : dict
            Regex-captured components, with `start_date`/`end_date` still
            in their raw (unparsed) string form.

        Returns
        -------
        str
            The constructed file_root.
        """
        return f"ema_{prefix}_{components['start_date']}_{components['end_date']}"

    @staticmethod
    def _spice_parts_handler(components: dict) -> dict:
        """Validate and transform SPICE file components.

        Parameters
        ----------
        components : dict
            Regex-captured components of the filename.

        Returns
        -------
        dict
            `kernel_type`, `file_root`, `start_date`, `end_date`, `version`,
            with dates converted and missing fields defaulted to `None`.
        """
        if "attitude_type" in components:
            attitude_token = components.pop("attitude_type").lower()
            components["kernel_type"] = SPICEFilePath._ATTITUDE_TYPE_MAPPING[
                attitude_token
            ]
            components["file_root"] = SPICEFilePath._dated_file_root(
                attitude_token, components
            )
        else:
            type_token = components.pop("type").lower()
            components["kernel_type"] = SPICEFilePath._SPICE_TYPE_MAPPING[type_token]
            if type_token in SPICEFilePath._BARE_FILE_ROOT_TYPES:
                components["file_root"] = type_token
            elif "start_date" in components:
                components["file_root"] = SPICEFilePath._dated_file_root(
                    type_token, components
                )
            else:
                components["file_root"] = f"ema_{type_token}"

        if "start_date" in components:
            components["start_date"] = _parse_ymd(components["start_date"])
        if "end_date" in components:
            components["end_date"] = _parse_ymd(components["end_date"])
        if "version" in components:
            components["version"] = _parse_spice_version(components["version"])

        components.setdefault("start_date", None)
        components.setdefault("end_date", None)
        components.setdefault("version", None)
        return components

    def _extra_metadata(self) -> dict:
        return dict(self.spice_metadata)

    def construct_path(self) -> Path:
        """See base class."""
        return (
            ema_data_access.config["DATA_DIR"]
            / f"spice/{self.kernel_type}/{self.filename}"
        )


def generate_ema_file_path(filename: str) -> EmaFilePath:
    """Try each known file convention in turn.

    Parameters
    ----------
    filename : str
        The file name to validate and parse (no path components).

    Returns
    -------
    EmaFilePath
        The parsed representation of `filename`, using whichever of the
        known conventions matched.

    Raises
    ------
    InvalidEmaFileError
        If `filename` doesn't match any known EMA file convention.
    """
    for construct in (
        AncillaryFilePath.from_filename,
        HousekeepingFilePath.from_filename,
        ScienceFilePath.from_filename,
        MissionEventsFilePath.from_filename,
        ManifestFilePath.from_filename,
        SPICEFilePath.from_filename,
    ):
        try:
            return construct(filename)
        except _FilenamePatternMismatchError:
            continue
    raise InvalidEmaFileError(f"{filename} does not match any known EMA convention")
