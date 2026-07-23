"""Filename validation and parsing for EMA PDC files."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

_PAYLOADS = "mst|emb|emc|rpt|ldr"
_MANIFEST_PAYLOADS = f"moc|{_PAYLOADS}"
_DATA_LEVELS = "l1|l1a|l1b|l2|l2a|l2b|l3|ql"
_ROOT = "ema"


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
    def construct_path(self) -> str:
        """Build the S3 key this file should be stored at.

        Returns
        -------
        str
            Destination key, relative to the bucket root.
        """


@dataclass
class AncillaryFilePath(EmaFilePath):
    """ema_l1_anc_sc_<apid>_YYYYMMDD.csv."""

    apid: int
    timetag: datetime
    file_extension: str

    _PATTERN: ClassVar[re.Pattern] = re.compile(
        r"ema_l1_anc_sc_(?P<apid>\d+)_(?P<timetag>\d{8})\.(?P<file_extension>csv)"
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

    def construct_path(self) -> str:
        """See base class."""
        return f"{_ROOT}/ancillary/{self.filename}"


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

    def construct_path(self) -> str:
        """See base class."""
        return f"{_ROOT}/manifest/{self.payload}/{self.filename}"


@dataclass
class HousekeepingFilePath(EmaFilePath):
    """ema_l0_hsk_<payload>_YYYYMMDD.pkts."""

    payload: str
    timetag: datetime

    _PATTERN: ClassVar[re.Pattern] = re.compile(
        rf"ema_l0_hsk_(?P<payload>{_PAYLOADS})_(?P<timetag>\d{{8}})\.pkts"
    )

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        return {
            "payload": match["payload"],
            "timetag": _parse_ymd(match["timetag"]),
        }

    def _extra_metadata(self) -> dict:
        return {"payload": self.payload, "timetag": self.timetag}

    def construct_path(self) -> str:
        """See base class."""
        return f"{_ROOT}/housekeeping/{self.payload}/{self.filename}"


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
        rf"ema_l0_sci_(?P<payload>{_PAYLOADS})_(?P<timetag>\d{{8}})\.(?P<file_extension>pkts)"
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

    def construct_path(self) -> str:
        """See base class."""
        return f"{_ROOT}/science/{self.payload}/{self.data_level}/{self.filename}"


@dataclass
class MissionEventsFilePath(EmaFilePath):
    """ema_mission_events_YYYYMMDD_YYYYMMDD.xml."""

    start_date: datetime
    end_date: datetime

    _PATTERN: ClassVar[re.Pattern] = re.compile(
        r"ema_mission_events_(?P<start_date>\d{8})_(?P<end_date>\d{8})\.xml"
    )

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        return {
            "start_date": _parse_ymd(match["start_date"]),
            "end_date": _parse_ymd(match["end_date"]),
        }

    def _extra_metadata(self) -> dict:
        return {"start_date": self.start_date, "end_date": self.end_date}

    def construct_path(self) -> str:
        """See base class."""
        return f"{_ROOT}/mission_events/{self.filename}"


@dataclass
class SPICEFilePath(EmaFilePath):
    """SPICE kernel naming."""

    file_root: str
    kernel_type: str

    # Standard SPICE kernel extension .
    _KERNEL_TYPE_BY_EXTENSION: ClassVar[dict[str, str]] = {
        "bc": "ck",
        "tf": "fk",
        "tls": "lsk",
        "tm": "mk",
        "tpc": "pck",
        "bpc": "pck",
        "tsc": "sclk",
        "bsp": "spk",
    }

    # TODO: update pattern when determined.
    _PATTERN: ClassVar[re.Pattern] = re.compile(
        r"(?P<file_root>[a-zA-Z0-9\-_]+)\."
        rf"(?P<extension>{'|'.join(_KERNEL_TYPE_BY_EXTENSION)})"
    )

    @classmethod
    def _extract_fields(cls, match: re.Match) -> dict:
        return {
            "file_root": match["file_root"],
            "kernel_type": cls._KERNEL_TYPE_BY_EXTENSION[match["extension"]],
        }

    def _extra_metadata(self) -> dict:
        return {"file_root": self.file_root, "kernel_type": self.kernel_type}

    def construct_path(self) -> str:
        """See base class."""
        return f"{_ROOT}/spice/{self.kernel_type}/{self.filename}"


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
    for cls in (
        AncillaryFilePath,
        HousekeepingFilePath,
        ScienceFilePath,
        MissionEventsFilePath,
        ManifestFilePath,
        SPICEFilePath,
    ):
        try:
            return cls.from_filename(filename)
        except _FilenamePatternMismatchError:
            continue
    raise InvalidEmaFileError(f"{filename} does not match any known EMA convention")
