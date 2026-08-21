"""Tests for the ``processing_input`` module."""

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

import ema_data_access
from ema_data_access.file_validation import SPICEFilePath
from ema_data_access.processing_input import (
    ProcessingInput,
    ProcessingInputCollection,
    ProcessingInputType,
    SPICEInput,
)


def test_create_spice_input():
    """Test constructing a SPICEInput from one or more SPICE kernel files."""
    one_file = SPICEInput("naif0012.tls")
    two_files = SPICEInput("naif0012.tls", "de440.bsp")

    assert one_file.filename_list == ["naif0012.tls"]
    assert len(one_file.ema_file_paths) == 1
    assert isinstance(one_file.ema_file_paths[0], SPICEFilePath)
    assert one_file.input_type == ProcessingInputType.SPICE_FILE
    assert one_file.data_type == "spice"
    assert one_file.descriptor == "historical"
    assert one_file.source == ["leapseconds"]

    assert two_files.filename_list == ["naif0012.tls", "de440.bsp"]
    assert len(two_files.ema_file_paths) == 2
    assert two_files.source == ["leapseconds", "ephem_planetary"]


def test_create_spice_input_no_files():
    """Test that constructing a SPICEInput with no files raises."""
    with pytest.raises(ProcessingInput.ProcessingInputError, match="At least one"):
        SPICEInput()


def test_create_spice_input_invalid_filename():
    """Test that an unrecognized filename raises when building a SPICEInput."""
    with pytest.raises(Exception, match=r"not_a_spice_file\.exe"):
        SPICEInput("not_a_spice_file.exe")


def test_get_time_range():
    """Test that only date-ranged kernels contribute to the time range."""
    spice_input = SPICEInput(
        "naif0012.tls",  # no date range - should be ignored
        "ema_recon_20240101_20240115_v001.bsp",
        "ema_pred_20240116_20240131_v001.bsp",
    )

    assert spice_input.get_time_range() == (
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 31, tzinfo=UTC),
    )


def test_get_time_range_no_dated_kernels():
    """Test that a collection with no date-ranged kernels returns (None, None)."""
    spice_input = SPICEInput("naif0012.tls")

    assert spice_input.get_time_range() == (None, None)


def test_construct_json_output():
    """Test that a SPICEInput serializes its type and filenames."""
    spice_input = SPICEInput("naif0012.tls", "de440.bsp")

    assert spice_input.construct_json_output() == {
        "type": "spice",
        "files": ["naif0012.tls", "de440.bsp"],
    }


def test_processing_input_collection_serialize():
    """Test that a collection serializes to the documented JSON shape."""
    collection = ProcessingInputCollection(
        SPICEInput("naif0012.tls"), SPICEInput("de440.bsp")
    )

    assert json.loads(collection.serialize()) == [
        {"type": "spice", "files": ["naif0012.tls"]},
        {"type": "spice", "files": ["de440.bsp"]},
    ]


def test_processing_input_collection_deserialize():
    """Test that a collection round-trips through serialize/deserialize."""
    json_input = json.dumps([{"type": "spice", "files": ["naif0012.tls", "de440.bsp"]}])

    collection = ProcessingInputCollection()
    collection.deserialize(json_input)

    assert len(collection.processing_input) == 1
    spice_input = collection.processing_input[0]
    assert isinstance(spice_input, SPICEInput)
    assert spice_input.filename_list == ["naif0012.tls", "de440.bsp"]


def test_processing_input_collection_deserialize_unknown_type():
    """Test that an unrecognized type in the JSON input raises."""
    json_input = json.dumps([{"type": "ancillary", "files": ["some_file.csv"]}])

    with pytest.raises(ValueError, match="ancillary"):
        ProcessingInputCollection().deserialize(json_input)


def test_get_processing_inputs():
    """Test filtering the collection by input type and data type."""
    spice_input = SPICEInput("naif0012.tls")
    collection = ProcessingInputCollection(spice_input)

    assert collection.get_processing_inputs() == [spice_input]
    assert collection.get_processing_inputs(
        input_type=ProcessingInputType.SPICE_FILE
    ) == [spice_input]
    assert collection.get_processing_inputs(data_type="spice") == [spice_input]
    assert collection.get_processing_inputs(data_type="ancillary") == []


def test_get_file_paths():
    """Test getting local file paths, rooted at DATA_DIR, for all files."""
    data_dir = ema_data_access.config["DATA_DIR"]
    collection = ProcessingInputCollection(SPICEInput("naif0012.tls", "de440.bsp"))

    paths = collection.get_file_paths()

    assert set(paths) == {
        data_dir / "spice/lsk/naif0012.tls",
        data_dir / "spice/spk/de440.bsp",
    }
    assert collection.get_file_paths(data_type="ancillary") == []


def test_download_all_files():
    """Test that download_all_files downloads each file to its DATA_DIR path."""
    data_dir = ema_data_access.config["DATA_DIR"]
    collection = ProcessingInputCollection(SPICEInput("naif0012.tls", "de440.bsp"))

    with patch("ema_data_access.processing_input.download") as mock_download:
        collection.download_all_files()

    assert mock_download.call_count == 2
    called = {
        (call.args[0], call.kwargs["destination"])
        for call in mock_download.call_args_list
    }
    assert called == {
        ("naif0012.tls", data_dir / "spice/lsk/naif0012.tls"),
        ("de440.bsp", data_dir / "spice/spk/de440.bsp"),
    }
