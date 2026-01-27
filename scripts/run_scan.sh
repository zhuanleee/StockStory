#!/bin/bash
# Run full stock scan

cd "$(dirname "$0")/.."
python main.py scan "$@"
