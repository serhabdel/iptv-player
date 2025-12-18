#!/bin/bash
set -e

# Build Script for IPTV Player Release
# Generates .deb package (Linux)
# Notes regarding other formats:
# - .exe (Windows): Must be built on Windows or via Wine (complex setup). 
#   Run `flet build windows` on a Windows machine.
# - .AppImage (Linux): Requires appimagetool or flet build linux (bundle).
#   This script focuses on the requested .deb rebuild.

APP_NAME="iptv-player"
VERSION="1.0.0"
BUILD_DIR="build_deb"
DIST_DIR="dist"
ASSETS_DIR="assets"

echo "Building $APP_NAME v$VERSION..."

# 1. Clean previous dist
echo "Cleaning dist..."
rm -rf "$DIST_DIR"
rm -f "$BUILD_DIR/$APP_NAME.deb"

# 2. Build binary using flet pack (PyInstaller wrapper)
echo "Compiling binary with flet pack..."
# Ensure flet is installed
if ! command -v flet &> /dev/null; then
    echo "Error: flet command not found. Activate your venv?"
    exit 1
fi

# Pack the application
# We use --icon to set the icon
flet pack main.py --name "$APP_NAME" --icon "assets/logo.png" --add-data "assets:assets" --add-data "src:src"

# 3. Prepare Debian Package Structure
echo "Preparing Debian package..."
TARGET_BIN="$BUILD_DIR/$APP_NAME/usr/bin"
TARGET_SHARE="$BUILD_DIR/$APP_NAME/usr/share/$APP_NAME"
mkdir -p "$TARGET_BIN"
mkdir -p "$TARGET_SHARE"

# Copy binary
cp "$DIST_DIR/$APP_NAME" "$TARGET_BIN/$APP_NAME"
# Make executable
chmod +x "$TARGET_BIN/$APP_NAME"

# Copy assets if needed (though --add-data usually bundles them, 
# sometimes external access is preferred, but for single-file binary they are internal.
# We'll copy icon for desktop entry usage)
mkdir -p "$TARGET_SHARE/assets"
cp -r "$ASSETS_DIR"/* "$TARGET_SHARE/assets/"

# 4. Build .deb
echo "Building .deb package..."
dpkg-deb --build "$BUILD_DIR/$APP_NAME" "$BUILD_DIR/$APP_NAME.deb"

echo "Build Complete!"
echo "DEB: $BUILD_DIR/$APP_NAME.deb"
echo ""
echo "For Windows .exe: Please copy the project to Windows and run 'flet pack main.py --icon assets/logo.png'"
echo "For AppImage: Use appimagetool on the binary or 'flet build linux'"
