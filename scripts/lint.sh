#!/bin/bash

# Exit on error
set -e

echo "Running isort..."
isort .

echo "Running black..."
black .

echo "Running flake8..."
flake8 .

echo "Running pylint..."
pylint app/ main.py

echo "Running mypy..."
mypy app/ main.py

echo "All checks passed! ✨" 