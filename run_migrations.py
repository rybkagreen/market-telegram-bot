#!/usr/bin/env python3
"""Stamp database with latest migrations."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

# Create Alembic config from file (reads script_location correctly)
alembic_cfg = Config("alembic.ini")

# DATABASE_URL is read from env.py via os.environ["DATABASE_URL"]
# No hardcoded credentials here!

# Get all heads
script = ScriptDirectory.from_config(alembic_cfg)
heads = list(script.get_heads())
print(f"Available heads: {heads}")

# Stamp database with all heads (don't run migrations, just update version table)
print("\nStamping database with all heads...")
try:
    command.stamp(alembic_cfg, "heads")
    print("Database stamped successfully!")

    # Verify
    print("\nVerifying current version...")
    command.current(alembic_cfg)
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
