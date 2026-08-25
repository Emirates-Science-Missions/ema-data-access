"""Input/output capabilities for the EMA data-access API."""

import contextlib
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

import ema_data_access

logger = logging.getLogger(__name__)


class EmaDataAccessError(Exception):
    """Base class for exceptions in this module."""

    pass


_RETRY_ADAPTER = requests.adapters.HTTPAdapter(max_retries=3)


@contextlib.contextmanager
def _make_request(request: requests.PreparedRequest):
    """Get the response from a URL request using the requests library.

    This is a helper function to handle different types of errors that can
    occur when making HTTP requests and yield the response body.
    """
    logger.debug("Making request: %s", request)

    if ema_data_access.config["API_KEY"]:
        request.headers["x-api-key"] = ema_data_access.config["API_KEY"]
    try:
        with requests.Session() as session:
            session.mount("https://", _RETRY_ADAPTER)
            response = session.send(request)
            response.raise_for_status()
            yield response
    except requests.exceptions.HTTPError as e:
        error_msg = f"{e.response.status_code} {e.response.reason}: {e.response.text}"
        raise EmaDataAccessError(error_msg) from e
    except requests.exceptions.RequestException as e:
        raise EmaDataAccessError(str(e)) from e


def _get_base_url() -> str:
    """Get the base URL of the EMA data-access API."""
    return ema_data_access.config["DATA_ACCESS_URL"]


def _normalize_date_param(value: str | None) -> str | None:
    """Convert compact date strings to dashed form for the API.

    The API parses datetime query params with pydantic, which reads a bare
    digit string as Unix epoch seconds. Compact YYYYMMDD and YYYYMMDDHHMM
    inputs are converted to YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS here so they
    filter as the dates the caller meant. Non-digit values pass through
    unchanged.

    Parameters
    ----------
    value : str or None
        The date filter value as given by the caller.

    Returns
    -------
    str or None
        The value to send to the API.
    """
    if value is None or not value.isdigit():
        return value
    if len(value) == 8:
        in_format, out_format = "%Y%m%d", "%Y-%m-%d"
    elif len(value) == 12:
        in_format, out_format = "%Y%m%d%H%M", "%Y-%m-%dT%H:%M:%S"
    else:
        raise EmaDataAccessError(
            f"Ambiguous numeric date {value!r}: use YYYYMMDD, YYYYMMDDHHMM, "
            "or YYYY-MM-DDTHH:MM:SS."
        )
    try:
        parsed = datetime.strptime(value, in_format)
    except ValueError as e:
        raise EmaDataAccessError(f"Invalid date {value!r}: {e}") from e
    return parsed.strftime(out_format)


def query_ancillary(  # noqa: PLR0913
    *,
    file_name: str | None = None,
    apid: int | None = None,
    timetag_start: str | None = None,
    timetag_end: str | None = None,
    file_extension: str | None = None,
    version: int | None = None,
    md5checksum: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Query the ancillary table for files matching the given filters.

    Parameters
    ----------
    file_name : str, optional
        Exact file name to match.
    apid : int, optional
        APID to match.
    timetag_start : str, optional
        Only include files with timetag on or after this, in YYYYMMDD or
        YYYY-MM-DD format.
    timetag_end : str, optional
        Only include files with timetag on or before this, in YYYYMMDD or
        YYYY-MM-DD format.
    file_extension : str, optional
        File extension to match, one of "csv", "fits", "cdf", "pkts".
    version : int, optional
        File version to match.
    md5checksum : str, optional
        MD5 checksum to match.
    limit : int, optional
        Max number of rows to return. Defaults to 100 server-side, and is
        a hard cap, not just a suggestion. Narrow `timetag_start`/
        `timetag_end` to page through results larger than `limit`.

    Returns
    -------
    list
        List of rows matching the query, as dicts.
    """
    params = {
        "file_name": file_name,
        "apid": apid,
        "timetag_start": _normalize_date_param(timetag_start),
        "timetag_end": _normalize_date_param(timetag_end),
        "file_extension": file_extension,
        "version": version,
        "md5checksum": md5checksum,
        "limit": limit,
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_ancillary"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying ancillary table with url %s", request.url)
    with _make_request(request) as response:
        items = response.json()
        logger.debug("Received JSON: %s", items)

    return items


def query_housekeeping(  # noqa: PLR0913
    *,
    file_name: str | None = None,
    payload: str | None = None,
    timetag_start: str | None = None,
    timetag_end: str | None = None,
    version: int | None = None,
    md5checksum: str | None = None,
) -> list[dict]:
    """Query the housekeeping table for files matching the given filters.

    Parameters
    ----------
    file_name : str, optional
        Exact file name to match.
    payload : str, optional
        Payload to match, one of "mst", "emb", "emc", "rpt", "ldr".
    timetag_start : str, optional
        Only include files with timetag on or after this, in YYYYMMDD or
        YYYY-MM-DD format.
    timetag_end : str, optional
        Only include files with timetag on or before this, in YYYYMMDD or
        YYYY-MM-DD format.
    version : int, optional
        File version to match.
    md5checksum : str, optional
        MD5 checksum to match.

    Returns
    -------
    list
        List of rows matching the query, as dicts.
    """
    params = {
        "file_name": file_name,
        "payload": payload,
        "timetag_start": _normalize_date_param(timetag_start),
        "timetag_end": _normalize_date_param(timetag_end),
        "version": version,
        "md5checksum": md5checksum,
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_housekeeping"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying housekeeping table with url %s", request.url)
    with _make_request(request) as response:
        items = response.json()
        logger.debug("Received JSON: %s", items)

    return items


def query_science(  # noqa: PLR0913
    *,
    file_name: str | None = None,
    payload: str | None = None,
    data_level: str | None = None,
    timetag_start: str | None = None,
    timetag_end: str | None = None,
    descriptor: str | None = None,
    pred_rec: str | None = None,
    file_extension: str | None = None,
    major_version: int | None = None,
    minor_version: int | None = None,
    md5checksum: str | None = None,
) -> list[dict]:
    """Query the science table for files matching the given filters.

    Parameters
    ----------
    file_name : str, optional
        Exact file name to match.
    payload : str, optional
        Payload to match, one of "mst", "emb", "emc", "rpt", "ldr".
    data_level : str, optional
        Data level to match, one of "l0", "l1", "l1a", "l1b", "l2", "l2a",
        "l2b", "l3", "ql".
    timetag_start : str, optional
        Only include files with timetag on or after this, in YYYYMMDD or
        YYYY-MM-DD format.
    timetag_end : str, optional
        Only include files with timetag on or before this, in YYYYMMDD or
        YYYY-MM-DD format.
    descriptor : str, optional
        Descriptor to match.
    pred_rec : str, optional
        Predicted/reconstructed flag to match, "p" or "r".
    file_extension : str, optional
        File extension to match, one of "csv", "fits", "cdf", "pkts".
    major_version : int, optional
        Major version to match.
    minor_version : int, optional
        Minor version to match.
    md5checksum : str, optional
        MD5 checksum to match.

    Returns
    -------
    list
        List of rows matching the query, as dicts.
    """
    params = {
        "file_name": file_name,
        "payload": payload,
        "data_level": data_level,
        "timetag_start": _normalize_date_param(timetag_start),
        "timetag_end": _normalize_date_param(timetag_end),
        "descriptor": descriptor,
        "pred_rec": pred_rec,
        "file_extension": file_extension,
        "major_version": major_version,
        "minor_version": minor_version,
        "md5checksum": md5checksum,
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_science"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying science table with url %s", request.url)
    with _make_request(request) as response:
        items = response.json()
        logger.debug("Received JSON: %s", items)

    return items


def query_mission_events(
    *,
    file_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    version: int | None = None,
    md5checksum: str | None = None,
) -> list[dict]:
    """Query the mission_events table for files matching the given filters.

    Events span a date range, so start_date and end_date define a query
    window and any event whose own range overlaps that window is returned.

    Parameters
    ----------
    file_name : str, optional
        Exact file name to match.
    start_date : str, optional
        Start of the query window, in YYYYMMDD or YYYY-MM-DD format. Only
        include events that end on or after this.
    end_date : str, optional
        End of the query window, in YYYYMMDD or YYYY-MM-DD format. Only
        include events that start on or before this.
    version : int, optional
        File version to match.
    md5checksum : str, optional
        MD5 checksum to match.

    Returns
    -------
    list
        List of rows matching the query, as dicts.
    """
    params = {
        "file_name": file_name,
        "start_date": _normalize_date_param(start_date),
        "end_date": _normalize_date_param(end_date),
        "version": version,
        "md5checksum": md5checksum,
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_mission_events"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying mission_events table with url %s", request.url)
    with _make_request(request) as response:
        items = response.json()
        logger.debug("Received JSON: %s", items)

    return items


def query_manifest(
    *,
    file_name: str | None = None,
    payload: str | None = None,
    timetag_start: str | None = None,
    timetag_end: str | None = None,
) -> list[dict]:
    """Query the manifest table for files matching the given filters.

    Parameters
    ----------
    file_name : str, optional
        Exact file name to match.
    payload : str, optional
        Payload to match, one of "mst", "emb", "emc", "rpt", "ldr", "moc".
    timetag_start : str, optional
        Only include files with timetag on or after this, in YYYYMMDDHHMM
        or YYYY-MM-DDTHH:MM:SS format.
    timetag_end : str, optional
        Only include files with timetag on or before this, in YYYYMMDDHHMM
        or YYYY-MM-DDTHH:MM:SS format.

    Returns
    -------
    list
        List of rows matching the query, as dicts.
    """
    params = {
        "file_name": file_name,
        "payload": payload,
        "timetag_start": _normalize_date_param(timetag_start),
        "timetag_end": _normalize_date_param(timetag_end),
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_manifest"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying manifest table with url %s", request.url)
    with _make_request(request) as response:
        items = response.json()
        logger.debug("Received JSON: %s", items)

    return items


def query_spice(  # noqa: PLR0913
    *,
    file_name: str | None = None,
    file_root: str | None = None,
    min_date_j2000: float | None = None,
    max_date_j2000: float | None = None,
    min_date_datetime: str | None = None,
    max_date_datetime: str | None = None,
    delivery_date: str | None = None,
    od_number: int | None = None,
    version: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Query the spice table for files matching the given filters.

    Parameters
    ----------
    file_name : str, optional
        Exact file name to match.
    file_root : str, optional
        Root of the file tree to match.
    min_date_j2000 : float, optional
        Minimum date to match, in J2000 format.
    max_date_j2000 : float, optional
        Maximum date to match, in J2000 format.
    min_date_datetime : str, optional
        Minimum date to match, as an ISO 8601 datetime string.
    max_date_datetime : str, optional
        Maximum date to match, as an ISO 8601 datetime string.
    delivery_date : str, optional
        Exact delivery date to match, as an ISO 8601 datetime string.
    od_number : int, optional
        OD number to match.
    version : int, optional
        File version to match.
    limit : int, optional
        Max number of rows to return. Defaults to 100 server-side, and is
        a hard cap, not just a suggestion. Narrow `min_date_datetime`/
        `max_date_datetime` to page through results larger than `limit`.

    Returns
    -------
    list
        List of rows matching the query, as dicts.
    """
    params = {
        "file_name": file_name,
        "file_root": file_root,
        "min_date_j2000": min_date_j2000,
        "max_date_j2000": max_date_j2000,
        "min_date_datetime": min_date_datetime,
        "max_date_datetime": max_date_datetime,
        "delivery_date": delivery_date,
        "od_number": od_number,
        "version": version,
        "limit": limit,
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_spice"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying spice table with url %s", request.url)
    with _make_request(request) as response:
        items = response.json()
        logger.debug("Received JSON: %s", items)

    return items


def download(file_name: str, destination: Path | str | None = None) -> Path:
    """Download a file from the EMA data archive.

    Parameters
    ----------
    file_name : str
        Exact name of the file to download.
    destination : pathlib.Path or str, optional
        Where to save the downloaded file. May be a directory, in which case
        the file is saved inside it as `file_name`, or a full file path.
        Defaults to `file_name` in the current working directory.

    Returns
    -------
    pathlib.Path
        Path to the downloaded file.

    Raises
    ------
    ValueError
        If `file_name` is not a bare file name (e.g. contains path
        separators or `..`).
    """
    if file_name in ("", ".", "..") or Path(file_name).name != file_name:
        raise ValueError(f"file_name must be a bare file name, got {file_name!r}")

    destination = Path(destination) if destination is not None else Path(file_name)
    if destination.is_dir():
        destination = destination / file_name

    if destination.exists():
        logger.info(
            "%s already exists at %s, skipping download", file_name, destination
        )
        return destination

    url = f"{_get_base_url()}/download/{quote(file_name)}"
    request = requests.Request(method="GET", url=url).prepare()

    logger.info("Downloading %s", file_name)
    with _make_request(request) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)

    return destination


def upload(file_path: Path | str) -> None:
    """Upload a file to the EMA data archive.

    Parameters
    ----------
    file_path : pathlib.Path or str
        Path to the file to upload.
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    url = f"{_get_base_url()}/upload/{file_path.name}"
    request = requests.Request(method="POST", url=url).prepare()

    logger.info("Requesting upload URL for %s", file_path.name)
    with _make_request(request) as response:
        upload_url = response.json()["upload_url"]
        logger.debug("Received s3 presigned URL")

    put_request = requests.Request(
        method="PUT",
        url=upload_url,
        data=file_path.read_bytes(),
        headers={"Content-Type": ""},
    ).prepare()

    logger.info("Uploading %s", file_path.name)
    with _make_request(put_request):
        pass
