# Well Operations Agent Platform

Approval-gated agents that do engineering work on offshore field data: post-well reviews,
lost-time investigations and records reconciliation. Every claim an agent makes is checked against
the source data, and every run is recorded in an append-only audit log that can be replayed.

**Status: Phase 1, data audit**

## Data sources

- **Volve field data**: Equinor ASA and the Volve licence partners, released under the
  Equinor Open Data Licence. The data may not be sold.
- **Sodir FactPages**: Norwegian Offshore Directorate, released under the Norwegian Licence for
  Open Government Data (NLOD) 2.0.
- **CIRA Centrifugal Pump Dataset** ([doi:10.5281/zenodo.18479728](https://doi.org/10.5281/zenodo.18479728)):
  released under CC BY 4.0.

The data is not stored in this repository. See [NOTICE](NOTICE) for full attribution.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```sh
make setup   # install dependencies
make lint    # ruff and mypy
make test    # pytest
```

## Licence

Code licensed under Apache-2.0; data licences in [NOTICE](NOTICE).
