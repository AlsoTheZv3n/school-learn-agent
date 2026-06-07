#!/usr/bin/env python
"""Mock-data seeder entrypoint (uv). Logic lives in its.data.seed (testable).

Usage (from apps/api so the `its` package resolves):
  uv run python ../../scripts/seed.py --profile demo
  uv run python ../../scripts/seed.py --profile load --classes 5 --students-per-class 24
  uv run python ../../scripts/seed.py --reset        # dev only (DATA_MODE=mock)
"""

from its.data.seed import main

if __name__ == "__main__":
    main()
