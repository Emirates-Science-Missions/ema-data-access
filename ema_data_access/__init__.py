"""EMA Data Access.

Lightweight client for the EMA PDC data-access API. Provides a convenient
way to query files in the EMA data archive.
"""

import importlib.metadata
import os
from pathlib import Path

from ema_data_access.io import download, query_ancillary, query_manifest, query_spice, upload

__all__ = [
    "download",
    "query_ancillary",
    "query_manifest",
    "query_spice",
    "upload",
]

__version__ = importlib.metadata.version("ema-data-access")

config = {
    "DATA_ACCESS_URL": os.getenv("EMA_DATA_ACCESS_URL"),
    "API_KEY": os.getenv("EMA_API_KEY"),
    "DATA_DIR": Path(os.getenv("EMA_DATA_DIR") or Path.cwd() / "data"),
}
"""Settings configuration dictionary.

DATA_ACCESS_URL : The URL of the EMA data-access API.
API_KEY : Static API key used to authenticate as a 'team' member. Required
    to see unreleased files; get one from scripts/manage_api_keys.py in the
    ema-pdc repo. Set through the EMA_API_KEY environment variable. Not
    needed to query the 'manifest' table, which is public.
DATA_DIR : Local root directory that ProcessingInputCollection.download_all_files()
    downloads files into, organized under the same relative layout as their
    S3 keys (e.g. DATA_DIR/ancillary/<file>, DATA_DIR/spice/spk/<file>).
    `download()` itself ignores this and takes an explicit destination; this
    only backs ProcessingInputCollection.get_file_paths()/download_all_files().
    Set through the EMA_DATA_DIR environment variable; defaults to "data/" in
    the current working directory.
"""
