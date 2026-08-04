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

## Importing as a package

```python
import ema_data_access

ema_data_access.config["DATA_ACCESS_URL"] = "<url>"
ema_data_access.config["API_KEY"] = "<your-api-key>"

results = ema_data_access.query_ancillary(apid=1234, file_extension="csv")

ema_data_access.upload("path/to/ema_l1_anc_sc_1234_20240101.csv")
```

## Running tests

```
pytest
```