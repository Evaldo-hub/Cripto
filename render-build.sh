#!/bin/bash
set -e

echo "Forcing Python 3.11.9 installation..."
pyenv install 3.11.9 --skip-existing
pyenv global 3.11.9

echo "Upgrading pip..."
python3.11 -m pip install --upgrade pip setuptools wheel

echo "Installing dependencies with Python 3.11.9..."
python3.11 -m pip install --no-cache-dir -r requirements.txt

echo "Installing additional dependencies for network operations..."
python3.11 -m pip install --no-cache-dir aiohttp httpx

echo "Verifying critical packages..."
python3.11 -c "import ccxt, pandas, streamlit; print('✅ All packages imported successfully')"

echo "Setting up environment..."
export PYTHONPATH="/opt/render/project/src:/opt/render/project:$PYTHONPATH"

echo "Build completed successfully with Python 3.11.9"
