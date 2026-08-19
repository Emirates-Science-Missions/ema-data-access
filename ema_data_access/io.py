"""Input/output capabilities for the EMA data-access API."""

import contextlib
import logging
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


def query_ancillary(  # noqa: PLR0913
    *,
    file_name: str | None = None,
    apid: int | None = None,
    timetag_start: str | None = None,
    timetag_end: str | None = None,
    file_extension: str | None = None,
    version: int | None = None,
    md5checksum: str | None = None,
) -> list[dict]:
    """Query the ancillary table for files matching the given filters.

    Parameters
    ----------
    file_name : str, optional
        Exact file name to match.
    apid : int, optional
        APID to match.
    timetag_start : str, optional
        Only include files with timetag on or after this, in YYYYMMDD format.
    timetag_end : str, optional
        Only include files with timetag on or before this, in YYYYMMDD format.
    file_extension : str, optional
        File extension to match, one of "csv", "fits", "pkts".
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
        "apid": apid,
        "timetag_start": timetag_start,
        "timetag_end": timetag_end,
        "file_extension": file_extension,
        "version": version,
        "md5checksum": md5checksum,
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_ancillary"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying ancillary table with url %s", request.url)
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
        Only include files with timetag on or after this, in
        YYYYMMDDHHMM format.
    timetag_end : str, optional
        Only include files with timetag on or before this, in
        YYYYMMDDHHMM format.

    Returns
    -------
    list
        List of rows matching the query, as dicts.
    """
    params = {
        "file_name": file_name,
        "payload": payload,
        "timetag_start": timetag_start,
        "timetag_end": timetag_end,
    }
    params = {k: v for k, v in params.items() if v is not None}

    url = f"{_get_base_url()}/query_manifest"
    request = requests.Request(method="GET", url=url, params=params).prepare()

    logger.info("Querying manifest table with url %s", request.url)
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
