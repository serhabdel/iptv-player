#!/bin/bash
# Build Script for Android APK
# Requires: Android SDK, NDK, Flutter, Flet

echo "Building Android APK..."

# Check requirements
if ! command -v flutter &> /dev/null; then
    echo "Error: Flutter SDK not found. Please install Flutter and configure Android SDK."
    echo "Visit: https://flutter.dev/docs/get-started/install"
    exit 1
fi

if [ -z "$ANDROID_HOME" ]; then
    echo "Warning: ANDROID_HOME is not set. Build might fail if SDK is not found."
fi

# Build
echo "Running flet build apk..."
flet build apk --project "iptv_player" --org "com.serhabdel.iptvplayer" --product "IPTV Player"

echo "Build complete (if successful)."
echo "Check build/app/outputs/flutter-apk/"
