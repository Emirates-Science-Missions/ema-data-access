# ema-data-access

Lightweight Python tools to query and access EMA data from S3 and RDS.

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

## Running tests

```
pytest
```