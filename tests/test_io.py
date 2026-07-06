"""Tests for the ``io`` module."""

from unittest.mock import MagicMock

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
