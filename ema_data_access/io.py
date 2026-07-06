"""Input/output capabilities for the EMA data-access API."""

import contextlib
import logging

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
