#!/bin/bash
#
# Validate that the generated schema is up-to-date.
#
# This script regenerates the schema and checks if it matches the current state.
# If they don't match, it exits with code 1 (CI failure).
#
# Usage:
#   bash scripts/validate_schema.sh
#

set -e

SCHEMA_FILE="frontend/lib/generated/job_schema.ts"

echo "Regenerating schema..."
python scripts/generate_schema.py

if git diff --exit-code "$SCHEMA_FILE" >/dev/null 2>&1; then
  echo "OK: Schema is up-to-date"
  exit 0
else
  echo "ERROR: Schema is out of sync!"
  echo "Run: python scripts/generate_schema.py"
  echo "Then commit the changes."
  git diff "$SCHEMA_FILE"
  exit 1
fi
