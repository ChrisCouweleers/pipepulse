"""The repository ships with generated synthetic data.

This script is intentionally a placeholder entry point for future regeneration logic.
The checked-in demo datasets are synthetic and safe to publish in a portfolio repository.
"""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    print(f"Synthetic demo data is already present under {BASE / 'data'}")
