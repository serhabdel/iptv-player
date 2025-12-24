#!/bin/bash
set -e

# Build Script for AppImage
# Requires: dist/iptv-player (built via flet pack)
# Downloads appimagetool if not present

APP_NAME="iptv-player"
BUILD_DIR="build_appimage"
APP_DIR="$BUILD_DIR/AppDir"
DIST_BIN="dist/$APP_NAME"

echo "Building AppImage for $APP_NAME..."

# 1. Check for binary
if [ ! -f "$DIST_BIN" ]; then
    echo "Error: $DIST_BIN not found. Please run scripts/build_release.sh or flet pack first."
    exit 1
fi

# 2. Get appimagetool
if ! command -v appimagetool &> /dev/null; then
    if [ ! -f "appimagetool-x86_64.AppImage" ]; then
        echo "Downloading appimagetool..."
        wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x appimagetool-x86_64.AppImage
    fi
    APPIMAGETOOL="./appimagetool-x86_64.AppImage"
else
    APPIMAGETOOL="appimagetool"
fi

# 3. Prepare AppDir
echo "Setting up AppDir..."
rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

# Copy binary
cp "$DIST_BIN" "$APP_DIR/usr/bin/$APP_NAME"

# Copy Icon
cp "assets/logo.png" "$APP_DIR/$APP_NAME.png"
cp "assets/logo.png" "$APP_DIR/.DirIcon"

# Create Desktop File
cat > "$APP_DIR/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Name=IPTV Player
Exec=$APP_NAME
Icon=$APP_NAME
Type=Application
Categories=Video;AudioVideo;
Comment=Modern IPTV Player
Terminal=false
EOF

# Create AppRun
cat > "$APP_DIR/AppRun" <<EOF
#!/bin/bash
HERE="\$(dirname "\$(readlink -f "\${0}")")"
export PATH="\${HERE}/usr/bin:\${PATH}"
exec "$APP_NAME" "\$@"
EOF
chmod +x "$APP_DIR/AppRun"

# 4. Build AppImage
echo "Generating AppImage..."
# ARCH=x86_64 $APPIMAGETOOL "$APP_DIR" "$BUILD_DIR/$APP_NAME.AppImage"
# Using --no-appimage-sanitization if needed in docker/CI, but locally should be fine.
$APPIMAGETOOL "$APP_DIR" "$BUILD_DIR/$APP_NAME.AppImage"

echo "AppImage created: $BUILD_DIR/$APP_NAME.AppImage"
