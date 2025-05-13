#!/bin/bash
echo "🔍 Checking for unused packages..."

# Ignore .venv, __pycache__, and optionally tests
pip-missing-reqs . \
  --ignore-file=.venv \
  --ignore-file=__pycache__ \
  --ignore-file=tests
