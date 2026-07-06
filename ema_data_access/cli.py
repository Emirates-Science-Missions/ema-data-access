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
"""

import argparse
import json
from argparse import ArgumentParser

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
    subparser.set_defaults(func=_query_ancillary_parser)


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

    try:
        args = parser.parse_args()
    except TypeError:
        parser.exit(
            status=1,
            message="Please provide input parameters, "
            "or use '-h' for more information.",
        )

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
