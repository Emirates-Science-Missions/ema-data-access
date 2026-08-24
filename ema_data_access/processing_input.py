"""Classes for abstracting and organizing collections of input files.

Mirrors the design of `imap_data_access.processing_input`: a `ProcessingInput`
describes a group of same-kind files, and a `ProcessingInputCollection`
bundles several `ProcessingInput`s together and can serialize/deserialize
that bundle to/from JSON so it can be passed between processes (e.g. handed
to a downstream processing job as its list of dependencies).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ema_data_access.file_validation import EmaFilePath, SPICEFilePath
from ema_data_access.io import download


class ProcessingInputType(Enum):
    """Enum matching types of ProcessingInputs to output strings describing them."""

    SPICE_FILE = "spice"


@dataclass
class ProcessingInput(ABC):
    """Interface for input file management and serialization.

    ProcessingInput is an abstract class used to manage input files for
    processing. Any kind of input file can define an Input class that
    inherits from this abstract class, which can then be used in a
    ProcessingInputCollection describing a set of files for processing.

    Each instance of an Input class can contain multiple files that share
    the same source, data type, and descriptor, but which may cover a wide
    time range.

    Attributes
    ----------
    filename_list : list[str]
        A list of filename(s).
    ema_file_paths : list[EmaFilePath]
        A list of file objects, one for each filename.
    input_type : ProcessingInputType
        The type of input file.
    source : str | list[str]
        The source of the file, e.g. an instrument/payload name, or, for
        SPICE files, the list of kernel types present.
    data_type : str
        The type of data, e.g. instrument data level, "ancillary", or
        "spice". Used to serialize() output and to query by data type.
    descriptor : str
        A descriptor for the file. SPICE files use "historical".
    """

    filename_list: list[str] = None
    ema_file_paths: list[EmaFilePath] = None
    input_type: ProcessingInputType = None
    # The following three are derived from the filenames themselves.
    source: str | list[str] = field(init=False)
    data_type: str = field(init=False)
    descriptor: str = field(init=False)

    class ProcessingInputError(Exception):
        """Indicate that the ProcessingInput is invalid."""

        pass

    def __init__(self, *args: str) -> None:
        """Initialize using a list of filenames and set the class's attributes.

        Parameters
        ----------
        args : str
            Filenames (not paths), as strings.
        """
        if len(args) < 1:
            raise ProcessingInput.ProcessingInputError(
                "At least one file must be provided."
            )
        self.filename_list = []
        for filename in args:
            if not isinstance(filename, str):
                raise ProcessingInput.ProcessingInputError(
                    "All arguments must be strings"
                )
            self.filename_list.append(filename)
        self._set_attributes_from_filenames()

    @abstractmethod
    def _set_attributes_from_filenames(self) -> None:
        """Set source, data_type, descriptor, and ema_file_paths.

        Called once by the constructor, using `self.filename_list`. Must be
        overridden by each subclass, since EMA's file-naming conventions
        differ too much between file types (e.g. `SPICEFilePath` has no
        `descriptor` field) to share one generic implementation.
        """

    def construct_json_output(self) -> dict:
        """Construct a JSON output.

        This contains the minimum information needed to construct an
        identical ProcessingInput instance (input_type and filenames).

        Returns
        -------
        dict
            A dict with the input type and list of filenames.
        """
        return {"type": self.input_type.value, "files": self.filename_list}


class SPICEInput(ProcessingInput):
    """SPICE kernel file subclass for ProcessingInput."""

    input_type = ProcessingInputType.SPICE_FILE
    descriptor = "historical"

    def _set_attributes_from_filenames(self) -> None:
        """Set the source and file object attributes."""
        source = []
        file_obj_list = []

        for file in self.filename_list:
            path_validator = SPICEFilePath.from_filename(file)
            kernel_type = path_validator.spice_metadata["kernel_type"]
            if kernel_type not in source:
                source.append(kernel_type)
            file_obj_list.append(path_validator)

        self.source = source
        self.data_type = ProcessingInputType.SPICE_FILE.value
        self.ema_file_paths = file_obj_list


@dataclass
class ProcessingInputCollection:
    """Describe a collection of ProcessingInput objects.

    This can be used to organize a set of ProcessingInput objects, which
    together fully describe all the required inputs to a processing step.

    This also serializes and deserializes the ProcessingInput classes to
    and from JSON so they can be passed between processes.

    Attributes
    ----------
    processing_input : list[ProcessingInput]
        A list of ProcessingInput objects.
    """

    processing_input: list[ProcessingInput]

    def __init__(self, *args: ProcessingInput) -> None:
        """Initialize the collection with the inputs.

        Parameters
        ----------
        args : ProcessingInput
            ProcessingInput objects to add to the collection. May be empty.
        """
        self.processing_input = []
        for processing_input in args:
            self.add(processing_input)

    def add(self, processing_inputs: list | ProcessingInput) -> None:
        """Add a ProcessingInput or list of ProcessingInputs to the collection.

        Parameters
        ----------
        processing_inputs : list | ProcessingInput
            Either a list of ProcessingInputs or a single ProcessingInput
            instance.
        """
        if isinstance(processing_inputs, list):
            self.processing_input.extend(processing_inputs)
        else:
            self.processing_input.append(processing_inputs)

    def serialize(self) -> str:
        """Convert the collection to a JSON string.

        Returns
        -------
        str
            A string of JSON-formatted serialized output.
        """
        json_out = [file.construct_json_output() for file in self.processing_input]
        return json.dumps(json_out)

    def deserialize(self, json_input: str) -> None:
        """Deserialize JSON into the collection of ProcessingInput instances.

        Parameters
        ----------
        json_input : str
            JSON input matching the output of ProcessingInputCollection.serialize().
            Input is organized by type. Eg.
            [
                {"type": "spice", "files": [<list of SPICE files>]}
            ]
        """
        full_input = json.loads(json_input)

        for file_creator in full_input:
            if file_creator["type"] == ProcessingInputType.SPICE_FILE.value:
                self.add(SPICEInput(*file_creator["files"]))
            else:
                raise ValueError(
                    f"Unrecognized processing input type: {file_creator['type']!r}"
                )

    def get_processing_inputs(
        self,
        input_type: ProcessingInputType | None = None,
        source: str | None = None,
        descriptor: str | None = None,
        data_type: str | None = None,
    ) -> list[ProcessingInput]:
        """Get the processing inputs from the collection that match the parameters.

        If called with no parameters, the entire ProcessingInput list is returned.

        Parameters
        ----------
        input_type : ProcessingInputType | None
            The type of input to filter by. If None, all types are included.
        source : str | None
            The source to filter by. If None, all sources are included.
        descriptor : str | None
            The descriptor to filter by. If None, all descriptors are included.
        data_type : str | None
            The data type to filter by. If None, all data types are included.

        Returns
        -------
        list[ProcessingInput]
            List of ProcessingInput objects that match the parameters.
        """
        output = []
        for processing_input in self.processing_input:
            match_type = input_type is None or processing_input.input_type == input_type
            match_source = source is None or processing_input.source == source
            match_descriptor = (
                descriptor is None or descriptor in processing_input.descriptor
            )
            match_data_type = (
                data_type is None or processing_input.data_type == data_type
            )
            if match_type and match_source and match_descriptor and match_data_type:
                output.append(processing_input)

        return output

    def get_file_paths(
        self,
        source: str | None = None,
        descriptor: str | None = None,
        data_type: str | None = None,
    ) -> list[Path]:
        """Get the local file paths for the dependencies in the collection.

        Returns all file paths if no filters are provided. Otherwise, it
        returns only the files that match the given source, descriptor,
        and/or data type. Each path is under `ema_data_access.config
        ["DATA_DIR"]` (see `EmaFilePath.construct_path`) - the same layout
        `download_all_files` downloads into, so these paths are valid to
        open once that's done.

        Parameters
        ----------
        source : str, optional
            Source to filter by, e.g. a SPICE kernel type.
        descriptor : str, optional
            Descriptor to filter by.
        data_type : str, optional
            Data type to filter by, e.g. "spice".

        Returns
        -------
        list[Path]
            List of local file paths for files contained in the collection.
        """
        out = []
        for processing_input in self.get_processing_inputs(
            source=source, descriptor=descriptor, data_type=data_type
        ):
            out.extend(
                file.construct_path() for file in processing_input.ema_file_paths
            )

        return out

    def download_all_files(self) -> None:
        """Download all the dependency files in the collection.

        Each file is saved under `ema_data_access.config["DATA_DIR"]`, at
        the same relative path `get_file_paths()` returns for it.
        """
        for path in self.get_file_paths():
            download(path.name, destination=path)
