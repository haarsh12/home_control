#!/usr/bin/env bash
# Render build script - No ffmpeg needed

set -o errexit  # Exit on error

echo "=========================================="
echo "Starting build process..."
echo "=========================================="

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "=========================================="
echo "Build completed successfully!"
echo "Text-only mode - no ffmpeg required"
echo "=========================================="
