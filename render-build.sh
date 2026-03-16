#!/bin/bash
set -e

echo "Forcing Python 3.11.9 installation..."
pyenv install 3.11.9 --skip-existing
pyenv global 3.11.9

echo "Installing dependencies with Python 3.11.9..."
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r requirements.txt

echo "Build completed with Python 3.11.9"
