#!/usr/bin/env bash
# exit on error
set -o errexit

# Build dashboard
echo "Building Dashboard..."
cd dashboard
npm install
npm run build
cd ..

# Install python dependencies
echo "Installing Python Dependencies..."
pip install -r requirements.txt
pip install -r obu/requirements.txt
# Add any other sub-module requirements if needed
