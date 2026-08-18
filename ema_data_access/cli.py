#!/usr/bin/env python3

"""Command line interface to the EMA PDC Data Access API.

This module serves as a command line utility to invoke the EMA Data Access
API. It provides the ability to query files from the EMA Payload Data
Center.

Use
---
    ema-data-access <command> [<args>]
    ema-data-access --help
    ema-data-access query-ancillary --apid 123 --file-extension csv
    ema-data-access query-manifest --payload emb
    ema-data-access query-spice --file-root naif
    ema-data-access upload path/to/ema_l1_anc_sc_1234_20240101.csv
"""

import argparse
import json
from argparse import ArgumentParser
from pathlib import Path

import ema_data_access


def _query_ancillary_parser(args: argparse.Namespace) -> None:
    """Query the EMA PDC ancillary table for files matching the given filters.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    results = ema_data_access.query_ancillary(
        file_name=args.file_name,
        apid=args.apid,
        timetag_start=args.timetag_start,
        timetag_end=args.timetag_end,
        file_extension=args.file_extension,
        version=args.version,
        md5checksum=args.md5checksum,
        limit=args.limit,
    )
    print(json.dumps(results, indent=2))


def add_query_ancillary_args(subparser: ArgumentParser) -> None:
    """Add query-ancillary arguments to a subparser.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the query-ancillary arguments to.
    """
    subparser.add_argument("--file-name", type=str, help="Exact file name to match.")
    subparser.add_argument("--apid", type=int, help="APID to match.")
    subparser.add_argument(
        "--timetag-start",
        type=str,
        help="Only include files with timetag on or after this, in YYYYMMDD format.",
    )
    subparser.add_argument(
        "--timetag-end",
        type=str,
        help="Only include files with timetag on or before this, in YYYYMMDD format.",
    )
    subparser.add_argument(
        "--file-extension",
        type=str,
        choices=["csv", "fits", "pkts"],
        help="File extension to match.",
    )
    subparser.add_argument("--version", type=int, help="File version to match.")
    subparser.add_argument("--md5checksum", type=str, help="MD5 checksum to match.")
    subparser.add_argument(
        "--limit",
        type=int,
        help="Max number of rows to return. Defaults to 100 server-side.",
    )
    subparser.set_defaults(func=_query_ancillary_parser)


def _query_manifest_parser(args: argparse.Namespace) -> None:
    """Query the EMA PDC manifest table for files matching the given filters.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    results = ema_data_access.query_manifest(
        file_name=args.file_name,
        payload=args.payload,
        timetag_start=args.timetag_start,
        timetag_end=args.timetag_end,
    )
    print(json.dumps(results, indent=2))


def add_query_manifest_args(subparser: ArgumentParser) -> None:
    """Add query-manifest arguments to a subparser.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the query-manifest arguments to.
    """
    subparser.add_argument("--file-name", type=str, help="Exact file name to match.")
    subparser.add_argument(
        "--payload",
        type=str,
        choices=["mst", "emb", "emc", "rpt", "ldr", "moc"],
        help="Payload to match. 'moc' matches payload-less MOC manifests.",
    )
    subparser.add_argument(
        "--timetag-start",
        type=str,
        help="Only include files with timetag on or after this, in "
        "YYYYMMDDHHMM format.",
    )
    subparser.add_argument(
        "--timetag-end",
        type=str,
        help="Only include files with timetag on or before this, in "
        "YYYYMMDDHHMM format.",
    )
    subparser.set_defaults(func=_query_manifest_parser)


def _query_spice_parser(args: argparse.Namespace) -> None:
    """Query the EMA PDC spice table for files matching the given filters.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    results = ema_data_access.query_spice(
        file_name=args.file_name,
        file_root=args.file_root,
        min_date_j2000=args.min_date_j2000,
        max_date_j2000=args.max_date_j2000,
        min_date_datetime=args.min_date_datetime,
        max_date_datetime=args.max_date_datetime,
        delivery_date=args.delivery_date,
        od_number=args.od_number,
        version=args.version,
        limit=args.limit,
    )
    print(json.dumps(results, indent=2))


def add_query_spice_args(subparser: ArgumentParser) -> None:
    """Add query-spice arguments to a subparser.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the query-spice arguments to.
    """
    subparser.add_argument("--file-name", type=str, help="Exact file name to match.")
    subparser.add_argument(
        "--file-root", type=str, help="Root of the file tree to match."
    )
    subparser.add_argument(
        "--min-date-j2000",
        type=float,
        help="Minimum date to match, in J2000 format.",
    )
    subparser.add_argument(
        "--max-date-j2000",
        type=float,
        help="Maximum date to match, in J2000 format.",
    )
    subparser.add_argument(
        "--min-date-datetime",
        type=str,
        help="Minimum date to match, as an ISO 8601 datetime string.",
    )
    subparser.add_argument(
        "--max-date-datetime",
        type=str,
        help="Maximum date to match, as an ISO 8601 datetime string.",
    )
    subparser.add_argument(
        "--delivery-date",
        type=str,
        help="Exact delivery date to match, as an ISO 8601 datetime string.",
    )
    subparser.add_argument("--od-number", type=int, help="OD number to match.")
    subparser.add_argument("--version", type=int, help="File version to match.")
    subparser.add_argument(
        "--limit",
        type=int,
        help="Max number of rows to return. Defaults to 100 server-side.",
    )
    subparser.set_defaults(func=_query_spice_parser)


def _upload_parser(args: argparse.Namespace) -> None:
    """Upload a file to the EMA PDC data archive.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    ema_data_access.upload(args.file_path)
    print(f"Uploaded {args.file_path.name}")


def add_upload_args(subparser: ArgumentParser) -> None:
    """Add upload arguments to a subparser.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the upload arguments to.
    """
    subparser.add_argument(
        "file_path", type=Path, help="Path to the local file to upload."
    )
    subparser.set_defaults(func=_upload_parser)


def main():
    """Parse the command line arguments.

    Run the command line interface to the EMA Data Access API.
    """
    parser = argparse.ArgumentParser(prog="ema-data-access")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {ema_data_access.__version__}",
        help="Show program's version number and exit.",
    )
    parser.add_argument("--url", type=str, required=False)
    parser.add_argument("--api-key", type=str, required=False)

    subparsers = parser.add_subparsers(required=True)

    query_ancillary_parser = subparsers.add_parser("query-ancillary")
    add_query_ancillary_args(query_ancillary_parser)

    query_manifest_parser = subparsers.add_parser("query-manifest")
    add_query_manifest_args(query_manifest_parser)

    query_spice_parser = subparsers.add_parser("query-spice")
    add_query_spice_args(query_spice_parser)

    upload_parser = subparsers.add_parser("upload")
    add_upload_args(upload_parser)

    args = parser.parse_args()

    if args.url:
        ema_data_access.config["DATA_ACCESS_URL"] = args.url

    if args.api_key:
        ema_data_access.config["API_KEY"] = args.api_key

    try:
        args.func(args)
    except Exception as e:
        parser.exit(status=1, message=f"{e!r}\n")


if __name__ == "__main__":
    main()
