#!/bin/bash
set -e

# Build Script for IPTV Player Linux .deb release.
# Mirrors the core steps used by GitHub Actions build-linux-deb job.

APP_NAME="iptv-player"
RAW_VERSION="$(tr -d '[:space:]' < VERSION)"
VERSION="${RAW_VERSION#v}"
BUILD_DIR="build_deb"
DIST_DIR="dist"
DEB_ROOT="${BUILD_DIR}/deb_package"

echo "Building $APP_NAME v$VERSION..."

# 1. Clean previous outputs
echo "Cleaning previous outputs..."
rm -rf "$DIST_DIR" "$BUILD_DIR" build
mkdir -p "$DEB_ROOT/DEBIAN"
mkdir -p "$DEB_ROOT/usr/bin"
mkdir -p "$DEB_ROOT/usr/share/applications"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$DEB_ROOT/usr/share/doc/iptv-player"

# 2. Build binary using PyInstaller (same style as CI linux jobs)
echo "Building binary with PyInstaller..."
if ! command -v pyinstaller &> /dev/null; then
    echo "Error: pyinstaller not found. Activate your venv and install dependencies first."
    exit 1
fi

pyinstaller --onefile --noconsole --name "$APP_NAME" --add-data "assets:assets" --add-data "src:src" --add-data "LICENSE:." main.py

# 3. Prepare Debian package structure
echo "Preparing Debian package..."
cp "$DIST_DIR/$APP_NAME" "$DEB_ROOT/usr/bin/"
chmod +x "$DEB_ROOT/usr/bin/$APP_NAME"
cp assets/logo.png "$DEB_ROOT/usr/share/icons/hicolor/256x256/apps/iptv-player.png"
cp LICENSE "$DEB_ROOT/usr/share/doc/iptv-player/LICENSE"

cat > "$DEB_ROOT/DEBIAN/control" << EOF
Package: iptv-player
Version: ${VERSION}
Section: video
Priority: optional
Architecture: amd64
Maintainer: IPTV Player <iptv-player@example.com>
Description: Cross-platform IPTV Player
 A modern IPTV player built with Python and Flet.
 Supports M3U playlists and Xtream Codes API.
EOF

cat > "$DEB_ROOT/usr/share/applications/iptv-player.desktop" << EOF
[Desktop Entry]
Name=IPTV Player
Comment=Cross-platform IPTV Player
Exec=/usr/bin/iptv-player
Icon=iptv-player
Terminal=false
Type=Application
Categories=AudioVideo;Video;Player;
EOF

echo "Building .deb package..."
dpkg-deb --build "$DEB_ROOT" "$BUILD_DIR/$APP_NAME.deb"

echo "Build Complete!"
echo "DEB: $BUILD_DIR/$APP_NAME.deb"
