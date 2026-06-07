"""Data tooling: the mock seeder (seed.py) and the production import (production.py).

Strictly separated by DATA_MODE: the seeder refuses to run unless DATA_MODE=mock;
the production import requires DATA_MODE=prod. Mock and real data never share a DB.
"""
