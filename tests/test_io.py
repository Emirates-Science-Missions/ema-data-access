"""Tests for the ``io`` module."""

from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
import requests

import ema_data_access
from ema_data_access.io import EmaDataAccessError, _get_base_url


def test_base_url(monkeypatch):
    """Test that the base URL is read straight from the config.

    Parameters
    ----------
    monkeypatch : pytest.fixture
        Fixture for monkeypatching module/global state.
    """
    monkeypatch.setitem(
        ema_data_access.config, "DATA_ACCESS_URL", "https://api.test.com"
    )
    assert _get_base_url() == "https://api.test.com"


def test_redirect(mock_send_request):
    """Verify that we follow a 307 redirect from newly created s3 buckets.

    Since we are mocking here, we just need to make sure that we are getting
    back the correct response and it doesn't raise for status.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for requests.Session
    """
    mock_redirect_response = MagicMock()
    mock_redirect_response.status_code = 307
    mock_redirect_response.headers = {"Location": "http://followed-redirect.com"}
    mock_send_request.return_value = mock_redirect_response

    with ema_data_access.io._make_request(
        requests.Request(method="GET", url="http://test-example.com").prepare()
    ) as response:
        assert mock_send_request.call_count == 1
        assert response.status_code == 307


def test_request_errors(mock_send_request):
    """Test that invalid requests raise an appropriate error.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for requests.Session
    """
    # Set up the mock to raise an HTTPError with a response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.reason = "Not Found"
    mock_response.text = "The requested resource was not found."
    mock_send_request.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )
    with pytest.raises(EmaDataAccessError, match="404 Not Found"):
        ema_data_access.query_ancillary()

    # Set up the mock to raise a RequestException with a response
    mock_send_request.side_effect = requests.exceptions.RequestException(
        "connection error"
    )
    with pytest.raises(EmaDataAccessError, match="connection error"):
        ema_data_access.query_ancillary()


@pytest.mark.parametrize(
    "query_params",
    [
        # All parameters should send full query
        {
            "file_name": "test.csv",
            "apid": 123,
            "timetag_start": "2024-01-01",
            "timetag_end": "2024-01-02",
            "file_extension": "csv",
            "version": 1,
            "md5checksum": "abc123",
        },
        # Make sure not all query params are sent if they are missing
        {"apid": 123},
        # No parameters at all
        {},
    ],
)
def test_query_ancillary(mock_send_request, query_params: dict):
    """Test a basic call to the ancillary Query API.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for requests.Session
    query_params : dict
        Dictionary of key/value pairs that set the query parameters
    """
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_send_request.return_value = mock_response

    response = ema_data_access.query_ancillary(**query_params)
    # No data found, and JSON decoding works as expected
    assert response == list()

    # Should have only been one call to send
    mock_send_request.assert_called_once()
    # Assert that the correct URL was used for the query
    sent_request = mock_send_request.call_args[0][0]
    called_url = sent_request.url
    str_params = "&".join(f"{k}={v}" for k, v in query_params.items())
    expected_url_encoded = "https://api.test.com/query_ancillary"
    if str_params:
        expected_url_encoded += f"?{str_params}"
    assert called_url == expected_url_encoded


def test_query_ancillary_bad_params(mock_send_request):
    """Test a call to query_ancillary with an invalid parameter.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.session``
    """
    with pytest.raises(TypeError, match="got an unexpected"):
        ema_data_access.query_ancillary(bad_param="test")
    # Should not have made any calls to send
    assert mock_send_request.call_count == 0


@pytest.mark.parametrize(
    "query_params",
    [
        # All parameters should send full query
        {
            "file_name": "emb_manifest_202402020000.txt",
            "payload": "emb",
            "timetag_start": "202401010000",
            "timetag_end": "202401020000",
        },
        # Make sure not all query params are sent if they are missing
        {"payload": "emb"},
        # No parameters at all
        {},
    ],
)
def test_query_manifest(mock_send_request, query_params: dict):
    """Test a basic call to the manifest Query API.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for requests.Session
    query_params : dict
        Dictionary of key/value pairs that set the query parameters
    """
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_send_request.return_value = mock_response

    response = ema_data_access.query_manifest(**query_params)
    # No data found, and JSON decoding works as expected
    assert response == list()

    # Should have only been one call to send
    mock_send_request.assert_called_once()
    # Assert that the correct URL was used for the query
    sent_request = mock_send_request.call_args[0][0]
    called_url = urlparse(sent_request.url)
    assert f"{called_url.scheme}://{called_url.netloc}{called_url.path}" == (
        "https://api.test.com/query_manifest"
    )
    called_params = parse_qs(called_url.query)
    expected_params = {k: [str(v)] for k, v in query_params.items()}
    assert called_params == expected_params


def test_query_manifest_bad_params(mock_send_request):
    """Test a call to query_manifest with an invalid parameter.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.session``
    """
    with pytest.raises(TypeError, match="got an unexpected"):
        ema_data_access.query_manifest(bad_param="test")
    # Should not have made any calls to send
    assert mock_send_request.call_count == 0


@pytest.mark.parametrize("as_str", [False, True], ids=["path", "str"])
@pytest.mark.parametrize(
    ("api_key", "expected_header"),
    [
        (None, {}),
        ("test-api-key", {"x-api-key": "test-api-key"}),
    ],
)
def test_upload(  # noqa: PLR0913
    mock_send_request,
    tmp_path,
    monkeypatch,
    as_str: bool,
    api_key: str | None,
    expected_header: dict,
):
    """Test the two-step upload flow: POST for a URL, then PUT the file.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    monkeypatch : pytest.fixture
        Fixture for monkeypatching module/global state.
    as_str : bool
        Whether to pass the file path as a ``str`` instead of a ``Path``.
    api_key : str or None
        The API key to use for the upload.
    expected_header : dict
        The expected auth header on the presign request.
    """
    monkeypatch.setitem(ema_data_access.config, "API_KEY", api_key)

    file_path = tmp_path / "ema_l1_anc_sc_1234_20240101.csv"
    file_path.write_bytes(b"test data")

    mock_presign_response = MagicMock()
    mock_presign_response.json.return_value = {
        "upload_url": "https://s3.example.com/presigned"
    }
    mock_put_response = MagicMock()
    mock_send_request.side_effect = [mock_presign_response, mock_put_response]

    ema_data_access.upload(str(file_path) if as_str else file_path)

    assert mock_send_request.call_count == 2

    presign_request = mock_send_request.call_args_list[0][0][0]
    assert presign_request.method == "POST"
    assert presign_request.url == (
        "https://api.test.com/upload/ema_l1_anc_sc_1234_20240101.csv"
    )
    assert presign_request.headers == {"Content-Length": "0", **expected_header}

    put_request = mock_send_request.call_args_list[1][0][0]
    assert put_request.method == "PUT"
    assert put_request.url == "https://s3.example.com/presigned"
    assert put_request.body == b"test data"
    assert put_request.headers["Content-Type"] == ""


@pytest.mark.parametrize("as_str", [False, True], ids=["path", "str"])
def test_download(mock_send_request, tmp_path, as_str: bool):
    """Test downloading a file writes the response content to disk.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    as_str : bool
        Whether to pass the destination as a ``str`` instead of a ``Path``.
    """
    file_name = "ema_l1_anc_sc_1234_20240101.csv"
    destination = tmp_path / file_name

    result = ema_data_access.download(
        file_name, destination=str(destination) if as_str else destination
    )

    assert result == destination
    assert destination.read_bytes() == b"Mock file content"

    mock_send_request.assert_called_once()
    sent_request = mock_send_request.call_args[0][0]
    assert sent_request.method == "GET"
    assert sent_request.url == f"https://api.test.com/download/{file_name}"


def test_download_default_destination(mock_send_request, tmp_path, monkeypatch):
    """Test that download defaults to saving `file_name` in the cwd.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    monkeypatch : pytest.fixture
        Fixture for monkeypatching module/global state.
    """
    monkeypatch.chdir(tmp_path)
    file_name = "ema_l1_anc_sc_1234_20240101.csv"

    result = ema_data_access.download(file_name)

    assert result.resolve() == tmp_path / file_name
    assert result.read_bytes() == b"Mock file content"


def test_download_to_directory(mock_send_request, tmp_path):
    """Test that passing a directory as the destination saves inside it.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    """
    file_name = "ema_l1_anc_sc_1234_20240101.csv"

    result = ema_data_access.download(file_name, destination=tmp_path)

    assert result == tmp_path / file_name
    assert result.read_bytes() == b"Mock file content"


def test_download_already_exists(mock_send_request, tmp_path):
    """Test that download skips the request if the file already exists.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    """
    file_name = "ema_l1_anc_sc_1234_20240101.csv"
    destination = tmp_path / file_name
    destination.write_bytes(b"already here")

    result = ema_data_access.download(file_name, destination=destination)

    assert result == destination
    assert destination.read_bytes() == b"already here"
    mock_send_request.assert_not_called()


def test_download_request_error(mock_send_request, tmp_path):
    """Test that a rejected download request raises EmaDataAccessError.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    """
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.reason = "Not Found"
    mock_response.text = "The requested resource was not found."
    mock_send_request.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    with pytest.raises(EmaDataAccessError, match="404 Not Found"):
        ema_data_access.download(
            "ema_l1_anc_sc_1234_20240101.csv", destination=tmp_path
        )


@pytest.mark.parametrize(
    "file_name",
    ["../../etc/passwd", "foo/bar.csv", "..", ".", "", "/etc/passwd"],
)
def test_download_rejects_non_bare_file_name(mock_send_request, tmp_path, file_name):
    """Test that download rejects file names containing path components.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    file_name : str
        Non-bare file name that should be rejected.
    """
    with pytest.raises(ValueError, match="bare file name"):
        ema_data_access.download(file_name, destination=tmp_path)

    mock_send_request.assert_not_called()


def test_download_url_encodes_file_name(mock_send_request, tmp_path):
    """Test that special characters in the file name are URL-encoded.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    """
    file_name = "ema_l1_anc_sc_1234_20240101 (copy)#1.csv"

    ema_data_access.download(file_name, destination=tmp_path)

    sent_request = mock_send_request.call_args[0][0]
    assert (
        sent_request.url == "https://api.test.com/download/"
        "ema_l1_anc_sc_1234_20240101%20%28copy%29%231.csv"
    )


def test_upload_missing_file(tmp_path):
    """Test that uploading a nonexistent file raises FileNotFoundError.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    """
    with pytest.raises(FileNotFoundError):
        ema_data_access.upload(tmp_path / "does_not_exist.csv")


def test_upload_request_error(mock_send_request, tmp_path):
    """Test that a rejected presign request raises EmaDataAccessError.

    Parameters
    ----------
    mock_send_request : unittest.mock.MagicMock
        Mock object for ``requests.Session``
    tmp_path : pathlib.Path
        Pytest fixture giving a per-test temporary directory.
    """
    file_path = tmp_path / "ema_l1_anc_sc_1234_20240101.csv"
    file_path.write_bytes(b"test data")

    mock_response = MagicMock()
    mock_response.status_code = 409
    mock_response.reason = "Conflict"
    mock_response.text = "The file already exists."
    mock_send_request.side_effect = requests.exceptions.HTTPError(
        response=mock_response
    )

    with pytest.raises(EmaDataAccessError, match="409 Conflict"):
        ema_data_access.upload(file_path)
