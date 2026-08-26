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
    ema-data-access query-housekeeping --payload mst
    ema-data-access query-science --payload emb --data-level l1a
    ema-data-access query-mission-events --start-date 20240101 --end-date 20240110
    ema-data-access query-manifest --payload emb
    ema-data-access query-spice --file-root naif
    ema-data-access upload path/to/ema_l1_anc_sc_1234_20240101.csv
    ema-data-access download ema_l1_anc_sc_1234_20240101.csv
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
        help="Only include files with timetag on or after this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
    )
    subparser.add_argument(
        "--timetag-end",
        type=str,
        help="Only include files with timetag on or before this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
    )
    subparser.add_argument(
        "--file-extension",
        type=str,
        choices=["csv", "fits", "cdf", "pkts"],
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


def _query_housekeeping_parser(args: argparse.Namespace) -> None:
    """Query the EMA PDC housekeeping table for files matching the filters.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    results = ema_data_access.query_housekeeping(
        file_name=args.file_name,
        payload=args.payload,
        timetag_start=args.timetag_start,
        timetag_end=args.timetag_end,
        version=args.version,
        md5checksum=args.md5checksum,
    )
    print(json.dumps(results, indent=2))


def add_query_housekeeping_args(subparser: ArgumentParser) -> None:
    """Add query-housekeeping arguments to a subparser.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the query-housekeeping arguments to.
    """
    subparser.add_argument("--file-name", type=str, help="Exact file name to match.")
    subparser.add_argument(
        "--payload",
        type=str,
        choices=["mst", "emb", "emc", "rpt", "ldr"],
        help="Payload to match.",
    )
    subparser.add_argument(
        "--timetag-start",
        type=str,
        help="Only include files with timetag on or after this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
    )
    subparser.add_argument(
        "--timetag-end",
        type=str,
        help="Only include files with timetag on or before this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
    )
    subparser.add_argument("--version", type=int, help="File version to match.")
    subparser.add_argument("--md5checksum", type=str, help="MD5 checksum to match.")
    subparser.set_defaults(func=_query_housekeeping_parser)


def _query_science_parser(args: argparse.Namespace) -> None:
    """Query the EMA PDC science table for files matching the given filters.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    results = ema_data_access.query_science(
        file_name=args.file_name,
        payload=args.payload,
        data_level=args.data_level,
        timetag_start=args.timetag_start,
        timetag_end=args.timetag_end,
        descriptor=args.descriptor,
        pred_rec=args.pred_rec,
        file_extension=args.file_extension,
        major_version=args.major_version,
        minor_version=args.minor_version,
        md5checksum=args.md5checksum,
    )
    print(json.dumps(results, indent=2))


def add_query_science_args(subparser: ArgumentParser) -> None:
    """Add query-science arguments to a subparser.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the query-science arguments to.
    """
    subparser.add_argument("--file-name", type=str, help="Exact file name to match.")
    subparser.add_argument(
        "--payload",
        type=str,
        choices=["mst", "emb", "emc", "rpt", "ldr"],
        help="Payload to match.",
    )
    subparser.add_argument(
        "--data-level",
        type=str,
        choices=["l0", "l1", "l1a", "l1b", "l2", "l2a", "l2b", "l3", "ql"],
        help="Data level to match.",
    )
    subparser.add_argument(
        "--timetag-start",
        type=str,
        help="Only include files with timetag on or after this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
    )
    subparser.add_argument(
        "--timetag-end",
        type=str,
        help="Only include files with timetag on or before this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
    )
    subparser.add_argument("--descriptor", type=str, help="Descriptor to match.")
    subparser.add_argument(
        "--pred-rec",
        type=str,
        choices=["p", "r"],
        help="Predicted/reconstructed flag to match.",
    )
    subparser.add_argument(
        "--file-extension",
        type=str,
        choices=["csv", "fits", "cdf", "pkts"],
        help="File extension to match.",
    )
    subparser.add_argument("--major-version", type=int, help="Major version to match.")
    subparser.add_argument("--minor-version", type=int, help="Minor version to match.")
    subparser.add_argument("--md5checksum", type=str, help="MD5 checksum to match.")
    subparser.set_defaults(func=_query_science_parser)


def _query_mission_events_parser(args: argparse.Namespace) -> None:
    """Query the EMA PDC mission_events table for events matching the filters.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    results = ema_data_access.query_mission_events(
        file_name=args.file_name,
        start_date=args.start_date,
        end_date=args.end_date,
        version=args.version,
        md5checksum=args.md5checksum,
    )
    print(json.dumps(results, indent=2))


def add_query_mission_events_args(subparser: ArgumentParser) -> None:
    """Add query-mission-events arguments to a subparser.

    Events span a date range, so --start-date and --end-date define a query
    window and any event whose own range overlaps that window is returned.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the query-mission-events arguments to.
    """
    subparser.add_argument("--file-name", type=str, help="Exact file name to match.")
    subparser.add_argument(
        "--start-date",
        type=str,
        help="Start of the query window, in YYYYMMDD or YYYY-MM-DD format. "
        "Only include events that end on or after this.",
    )
    subparser.add_argument(
        "--end-date",
        type=str,
        help="End of the query window, in YYYYMMDD or YYYY-MM-DD format. "
        "Only include events that start on or before this.",
    )
    subparser.add_argument("--version", type=int, help="File version to match.")
    subparser.add_argument("--md5checksum", type=str, help="MD5 checksum to match.")
    subparser.set_defaults(func=_query_mission_events_parser)


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
        "YYYYMMDDHHMM or YYYY-MM-DDTHH:MM:SS format.",
    )
    subparser.add_argument(
        "--timetag-end",
        type=str,
        help="Only include files with timetag on or before this, in "
        "YYYYMMDDHHMM or YYYY-MM-DDTHH:MM:SS format.",
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
        delivery_date_start=args.delivery_date_start,
        delivery_date_end=args.delivery_date_end,
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
        help="Minimum date to match, in YYYYMMDD or YYYY-MM-DD format.",
    )
    subparser.add_argument(
        "--max-date-datetime",
        type=str,
        help="Maximum date to match, in YYYYMMDD or YYYY-MM-DD format.",
    )
    subparser.add_argument(
        "--delivery-date-start",
        type=str,
        help="Only include files delivered on or after this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
    )
    subparser.add_argument(
        "--delivery-date-end",
        type=str,
        help="Only include files delivered on or before this, in YYYYMMDD "
        "or YYYY-MM-DD format.",
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


def _download_parser(args: argparse.Namespace) -> None:
    """Download a file from the EMA PDC data archive.

    Parameters
    ----------
    args : argparse.Namespace
        An object containing the parsed arguments and their values.
    """
    output_path = ema_data_access.download(args.file_name, destination=args.destination)
    print(f"Downloaded {args.file_name} to {output_path}")


def add_download_args(subparser: ArgumentParser) -> None:
    """Add download arguments to a subparser.

    Parameters
    ----------
    subparser : argparse.ArgumentParser
        A subparser to add the download arguments to.
    """
    subparser.add_argument(
        "file_name", type=str, help="Exact name of the file to download."
    )
    subparser.add_argument(
        "--destination",
        type=Path,
        help="Directory or file path to save the downloaded file to. "
        "Defaults to the current directory.",
    )
    subparser.set_defaults(func=_download_parser)


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

    query_housekeeping_parser = subparsers.add_parser("query-housekeeping")
    add_query_housekeeping_args(query_housekeeping_parser)

    query_science_parser = subparsers.add_parser("query-science")
    add_query_science_args(query_science_parser)

    query_mission_events_parser = subparsers.add_parser("query-mission-events")
    add_query_mission_events_args(query_mission_events_parser)

    query_manifest_parser = subparsers.add_parser("query-manifest")
    add_query_manifest_args(query_manifest_parser)

    query_spice_parser = subparsers.add_parser("query-spice")
    add_query_spice_args(query_spice_parser)

    upload_parser = subparsers.add_parser("upload")
    add_upload_args(upload_parser)

    download_parser = subparsers.add_parser("download")
    add_download_args(download_parser)

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
