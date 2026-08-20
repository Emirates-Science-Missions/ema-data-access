"""EMA Data Access.

Lightweight client for the EMA PDC data-access API. Provides a convenient
way to query files in the EMA data archive.
"""

import importlib.metadata
import os

from ema_data_access.io import (
    query_ancillary,
    query_housekeeping,
    query_manifest,
    query_mission_events,
    query_science,
    upload,
)

__all__ = [
    "query_ancillary",
    "query_housekeeping",
    "query_manifest",
    "query_mission_events",
    "query_science",
    "upload",
]

__version__ = importlib.metadata.version("ema-data-access")

config = {
    "DATA_ACCESS_URL": os.getenv("EMA_DATA_ACCESS_URL"),
    "API_KEY": os.getenv("EMA_API_KEY"),
}
"""Settings configuration dictionary.

DATA_ACCESS_URL : The URL of the EMA data-access API.
API_KEY : Static API key used to authenticate as a 'team' member. Required
    to see unreleased files; get one from scripts/manage_api_keys.py in the
    ema-pdc repo. Set through the EMA_API_KEY environment variable. Not
    needed to query the 'manifest' table, which is public.
"""
