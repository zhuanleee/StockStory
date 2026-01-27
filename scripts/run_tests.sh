#!/bin/bash
# Run test suite

cd "$(dirname "$0")/.."
python -m pytest -v tests/ "$@"
