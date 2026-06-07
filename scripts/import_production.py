#!/usr/bin/env python
"""Production import entrypoint (uv). Logic lives in its.data.production.

Requires DATA_MODE=prod. Usage (from apps/api):
  uv run python ../../scripts/import_production.py --roster roster.csv
  uv run python ../../scripts/import_production.py --content /path/to/vault
"""

from its.data.production import main

if __name__ == "__main__":
    main()
