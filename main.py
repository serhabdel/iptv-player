#!/usr/bin/env python3
"""IPTV Player - A cross-platform IPTV player built with Python Flet."""
import sys
import asyncio

# Use ProactorEventLoop on Windows for better subprocess/IO performance
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import flet as ft
from src.app import main


if __name__ == "__main__":
    ft.run(main)
