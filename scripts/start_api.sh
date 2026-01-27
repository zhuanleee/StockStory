#!/bin/bash
# Start Flask API server

cd "$(dirname "$0")/.."
python main.py api
