# Volve data: access and download

The Volve files used by this project come from the Equinor "Volve Data Village" listing in
Databricks. They are copied, read-only, from a Unity Catalog volume to `data/raw/volve/`, which is
never committed.

## Prerequisites

1. A Databricks workspace in which the Equinor "Volve Data Village" listing has been added. Its
   files are exposed as the volume:

   ```
   dbfs:/Volumes/equinor_asa_volve_data_village/public/volve
   ```

2. The [Databricks CLI](https://docs.databricks.com/dev-tools/cli/) installed and signed in with
   OAuth. No access token is stored in this repository or in `.env`.

   ```sh
   databricks auth login --host <your-workspace-url>
   databricks fs ls dbfs:/Volumes/equinor_asa_volve_data_village/public/volve
   ```

   The second command should list the volume's top-level folders.

## What is copied

| Path in the volume | Files |
|---|---:|
| `HRS and Terms and conditions for license to data - Volve.pdf` (licence terms) | 1 |
| `Well_technical_data/Daily Drilling Report - XML Version/` | 1,759 |
| `WITSML Realtime drilling data/` | 11,894 |
| `Production_data/Volve production data.xlsx` | 1 |
| `Geophysical_Interpretations/Wells/Well_picks_Volve_v1.dat` | 1 |
| `Geophysical_Interpretations/Wells/Well_perforations_Volve.dat` | 1 |
| `Well_technical_data/EDM.XML/Volve F.edm.xml` | 1 |

The list is defined in `TARGETS` in `src/well_ops/ingestion/volve_files.py`. The file counts are
those listed when this document was written; about 3.1 GB in total.

## Steps

1. Measure without copying. This lists every target recursively and prints file counts and sizes:

   ```sh
   uv run python scripts/download_volve.py --list-only
   ```

2. Copy:

   ```sh
   make download-volve
   ```

   Files are copied one by one, eight at a time, into `data/raw/volve/`, keeping the folder
   structure of the volume. Each file is copied to a `.part` file and renamed only when its size
   matches the listing. Failed copies are retried up to three times with backoff.

   The copy is resumable: a file already present with the listed size is skipped, so the command
   can be run again after an interruption.

3. Check the summary line: `expected N, copied N, already present N, failed 0`. Any failed file is
   printed with its error, and the command exits non-zero.

## Manifest

Every Volve file present locally is recorded in `data/manifest.json` with its path, size, SHA-256,
retrieval time (UTC), source `Equinor Volve Data Village` and licence `Equinor Open Data Licence`.
Entries for other sources are kept unchanged.

## Licence

Volve data: Equinor ASA and the Volve licence partners, Equinor Open Data Licence. The data must not
be sold. The full licence terms are in the copied file
`data/raw/volve/HRS and Terms and conditions for license to data - Volve.pdf`. See `NOTICE`.
