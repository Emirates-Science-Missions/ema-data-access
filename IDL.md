# Using EMA data from IDL

The `ema-data-access` package is Python, but everything it does goes through
the EMA PDC web API, which IDL can call directly. [`idl/ema_api.pro`](idl/ema_api.pro)
contains a few small helpers for this. Requires IDL 8.2 or later.

## Setup

1. Download [`idl/ema_api.pro`](idl/ema_api.pro) into a directory on your IDL
   path.

2. Set the API URL, and your API key if you have one. Without a key, only
   released files are visible.

   ```idl
   setenv, 'EMA_DATA_ACCESS_URL=<url>'
   setenv, 'EMA_API_KEY=<your-api-key>'
   ```

3. Compile the helpers once per IDL session:

   ```idl
   .compile ema_api
   ```

## Dates

**Write dates as `YYYY-MM-DD`** (or `YYYY-MM-DDTHH:MM:SS`). A bare
`20240101` is read by the API as seconds since 1970, so the query returns
the wrong files without an error.

## Query for files

`ema_query` takes an endpoint name and a `HASH` of filters. It returns a
`LIST` with one `ORDEREDHASH` per file.

```idl
rows = ema_query('query_science', hash('payload', 'embirs', $
                                       'data_level', 'l1a', $
                                       'timetag_start', '2024-01-01', $
                                       'timetag_end', '2024-01-31'))
foreach row, rows do print, row['file_name']
```

The available endpoints and filters are the same as the Python client's (see
the [README](README.md)):

| Endpoint | Example filters |
| --- | --- |
| `query_science` | `payload`, `data_level`, `timetag_start`, `timetag_end`, `descriptor`, `pred_rec`, `file_extension`, `major_version`, `minor_version` |
| `query_housekeeping` | `payload`, `timetag_start`, `timetag_end`, `version` |
| `query_ancillary` | `apid`, `timetag_start`, `timetag_end`, `file_extension`, `version` |
| `query_mission_events` | `start_date`, `end_date`, `version` |
| `query_manifest` | `payload`, `timetag_start`, `timetag_end` |
| `query_spice` | `file_root`, `version`, `od_number` |

Every endpoint also accepts `file_name`. Results are capped (100 rows by
default), so narrow the time range to page through larger result sets.

## Download files

```idl
ema_download, ['naif0012.tls', 'de440.bsp'], 'path/to/dir'
```

Or download everything a query returned:

```idl
names = list()
foreach row, rows do names.add, row['file_name']
ema_download, names.toArray(), 'data'
```

## SPICE: build and furnish a metakernel

This uses NAIF's [Icy](https://naif.jpl.nasa.gov/naif/toolkit_IDL.html)
toolkit, the IDL equivalent of SpiceyPy. Times are seconds past J2000. Pass
them as doubles (e.g. from `cspice_str2et`) or integers, not floats. A float
only holds about 7 digits, so a time near 9e8 can be off by a minute.

```idl
window = hash('start_time', 0, 'end_time', 100000)
kernel_dir = 'kernels'

; Download every kernel the metakernel lists.
files = ema_query('metakernel', window + hash('list_files', 'true'))
ema_download, files.toArray(), kernel_dir

; Save the metakernel next to the kernels.
openw, lun, filepath('mission.tm', ROOT_DIR=kernel_dir), /GET_LUN
printf, lun, ema_query('metakernel', window, /TEXT)
free_lun, lun

; The metakernel lists bare file names, which SPICE looks for in the
; current directory, so furnish it from inside kernel_dir.
cd, kernel_dir, CURRENT=old_dir
cspice_furnsh, 'mission.tm'
cd, old_dir
```

Other options you can add to `window`:

| Option | Effect |
| --- | --- |
| `'kernel_types', 'ephem_reconstructed,ephem_predicted'` | Only include these kernel types. |
| `'require_coverage', 'true'` | Fail instead of returning a partial metakernel if the window isn't fully covered. The error message lists the gaps. Always pass `kernel_types` with it (see below). |

`require_coverage` checks every kernel type EMA knows about, including
types the archive has no files for yet, so on its own it can fail even
when the kernels you need fully cover the window. Use `kernel_types` to
list the types you need:

```idl
window = hash('start_time', 821275200d, 'end_time', 823953600d, $
              'require_coverage', 'true', $
              'kernel_types', 'leapseconds,ephem_planetary,ephem_reconstructed,ephem_predicted')
files = ema_query('metakernel', window + hash('list_files', 'true'))
```

## Upload files

Upload a single file, or every file in a directory. File names must match
one of the EMA naming conventions in the [README](README.md#file-naming-conventions),
and `EMA_API_KEY` must be a developer-level key. Request one from the EMA
PDC team.

```idl
ema_upload, 'path/to/ema_l1_anc_sc_1234_20240101.csv'
ema_upload, 'path/to/dir'
```

For a directory, subdirectories and hidden files are skipped. Files the API
rejects (for example, a name that doesn't match a convention) are listed,
and the rest still upload.
