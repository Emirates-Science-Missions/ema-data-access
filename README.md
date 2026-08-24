# ema-data-access

Lightweight Python tools to query and access EMA data.

## Setup

### Python environment (Poetry)

1. [Install Poetry](https://python-poetry.org/docs/#installation) if you don't have it:
   ```
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Create a virtual environment in the project directory:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   poetry install --extras "dev test"
   ```

4. Install pre-commit hooks:
   ```
   poetry run pre-commit install
   ```

## File naming conventions

Every file in the EMA archive must match one of the naming conventions
below.

`<payload>` is one of `mst`, `emb`, `emc`, `rpt`, `ldr`. `<data_level>` is one
of `l0`, `l1`, `l1a`, `l1b`, `l2`, `l2a`, `l2b`, `l3`, `ql`.

| Table | Convention |
| --- | --- |
| `ancillary` | `ema_l1_anc_sc_<apid>_<YYYYMMDD>.csv` |
| `manifest` | `<payload>_manifest_<YYYYMMDDHHMM>.txt`, or `moc_manifest_<YYYYMMDDHHMM>.txt` for a payload-less MOC manifest |
| `housekeeping` | `ema_l0_hsk_<payload>_<YYYYMMDD>.pkts` |
| `science` (L0) | `ema_l0_sci_<payload>_<YYYYMMDD>.pkts` |
| `science` (L1a+) | `ema_<payload>_<data_level>_<YYYYMMDDtHHMMSS>_<descriptor>_<pred_rec>_v<version>[-<subversion>].fits`, where `<pred_rec>` is `p` (predicted) or `r` (reconstructed) |
| `mission_events` | `ema_mission_events_<start_date:YYYYMMDD>_<end_date:YYYYMMDD>.xml` |

## Command Line Utility

### Query the ancillary table

Query the ancillary table for files matching a set of filters. An API key is
optional — without one, only `released` files are returned.

```bash
$ EMA_API_KEY=<your-api-key> ema-data-access --url <url> query-ancillary --apid 1234 --file-extension csv
```

or with CLI flags

```bash
$ ema-data-access --url <url> --api-key <your-api-key> query-ancillary --apid 1234 --file-extension csv
```

Other available filters: `--file-name`, `--timetag-start`, `--timetag-end`,
`--version`, `--md5checksum`. Results are returned as JSON.

Under the hood, this is equivalent to:

```bash
$ curl -H "x-api-key: $EMA_API_KEY" "<url>/query_ancillary?apid=1234&file_extension=csv"
```

### Query the housekeeping table

Query the housekeeping table for files matching a set of filters. An API key
is optional. Without one, only `released` files are returned.

```bash
$ EMA_API_KEY=<your-api-key> ema-data-access --url <url> query-housekeeping --payload mst
```

Other available filters: `--file-name`, `--timetag-start`, `--timetag-end`,
`--version`, `--md5checksum`. Results are returned as JSON.

Under the hood, this is equivalent to:

```bash
$ curl -H "x-api-key: $EMA_API_KEY" "<url>/query_housekeeping?payload=mst"
```

### Query the science table

Query the science table for files matching a set of filters. An API key is
optional. Without one, only `released` files are returned.

```bash
$ EMA_API_KEY=<your-api-key> ema-data-access --url <url> query-science --payload emb --data-level l1a
```

Other available filters: `--file-name`, `--timetag-start`, `--timetag-end`,
`--descriptor`, `--pred-rec`, `--file-extension`, `--major-version`,
`--minor-version`, `--md5checksum`. Results are returned as JSON.

Under the hood, this is equivalent to:

```bash
$ curl -H "x-api-key: $EMA_API_KEY" "<url>/query_science?payload=emb&data_level=l1a"
```

### Query the mission events table

Query the mission_events table for event files matching a set of filters. An
API key is optional. Without one, only `released` files are returned.

Events span a date range, so `--start-date` and `--end-date` define a query
window and any event whose own range overlaps that window is returned.

```bash
$ EMA_API_KEY=<your-api-key> ema-data-access --url <url> query-mission-events --start-date 20240101 --end-date 20240110
```

Other available filters: `--file-name`, `--version`, `--md5checksum`.
Results are returned as JSON.

Under the hood, this is equivalent to:

```bash
$ curl -H "x-api-key: $EMA_API_KEY" "<url>/query_mission_events?start_date=20240101&end_date=20240110"
```

### Query the manifest table

Query the manifest table for files matching a set of filters. Manifest rows
are public, so no API key is required.

```bash
$ ema-data-access --url <url> query-manifest --payload emb
```

Other available filters: `--file-name`, `--timetag-start`, `--timetag-end`.
Results are returned as JSON.

`--payload moc` matches MOC manifests, which have no payload of their own
(`moc_manifest_<YYYYMMDDHHMM>.txt`).

Under the hood, this is equivalent to:

```bash
$ curl "<url>/query_manifest?payload=emb"
```

### Upload a file

Upload a local file to the EMA data archive. The file name must match a
known EMA naming convention, and requires an API key with developer-level
access — request one from the EMA PDC team.

```bash
$ EMA_API_KEY=<your-api-key> ema-data-access --url <url> upload path/to/ema_l1_anc_sc_1234_20240101.csv
```

or with CLI flags

```bash
$ ema-data-access --url <url> --api-key <your-api-key> upload path/to/ema_l1_anc_sc_1234_20240101.csv
```

Under the hood, this requests a presigned upload URL and then PUTs the file
to it, equivalent to:

```bash
$ curl -X POST -H "x-api-key: $EMA_API_KEY" <url>/upload/ema_l1_anc_sc_1234_20240101.csv
# => {"upload_url": "<presigned-url>"}
$ curl -X PUT -T path/to/ema_l1_anc_sc_1234_20240101.csv "<presigned-url>"
```

### Download a file

Download a file from the EMA data archive by name. Unreleased files require
an API key with at least team-level access.

```bash
$ EMA_API_KEY=<your-api-key> ema-data-access --url <url> download ema_l1_anc_sc_1234_20240101.csv
```

or with CLI flags

```bash
$ ema-data-access --url <url> --api-key <your-api-key> download ema_l1_anc_sc_1234_20240101.csv
```

By default, the file is saved in the current directory under its own name.
Pass `--destination` to save it elsewhere, either as a directory or a full
file path:

```bash
$ ema-data-access --url <url> download ema_l1_anc_sc_1234_20240101.csv --destination path/to/dir
```

If the destination file already exists, the download is skipped. Under the
hood, this is equivalent to:

```bash
$ curl -H "x-api-key: $EMA_API_KEY" -o ema_l1_anc_sc_1234_20240101.csv "<url>/download/ema_l1_anc_sc_1234_20240101.csv"
```

## Importing as a package

```python
import ema_data_access

ema_data_access.config["DATA_ACCESS_URL"] = "<url>"
ema_data_access.config["API_KEY"] = "<your-api-key>"

results = ema_data_access.query_ancillary(apid=1234, file_extension="csv")

results = ema_data_access.query_housekeeping(payload="mst")

results = ema_data_access.query_science(payload="emb", data_level="l1a")

results = ema_data_access.query_mission_events(
    start_date="20240101", end_date="20240110"
)

results = ema_data_access.query_manifest(payload="emb")

ema_data_access.upload("path/to/ema_l1_anc_sc_1234_20240101.csv")

ema_data_access.download("ema_l1_anc_sc_1234_20240101.csv", destination="path/to/dir")
```

## Running tests

```
pytest
```