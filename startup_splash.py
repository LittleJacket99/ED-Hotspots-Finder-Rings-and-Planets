#!/usr/bin/env python3

"""Small transparent startup splash used while the v8 interface is built."""

import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk


SPLASH_IMAGE = "ED_Hotspots_Finder.png"
TRANSPARENT_KEY = "#ff00ff"
MAX_SPLASH_SIZE = 460
ALPHA_CUTOFF = 176


def resource_path(filename):
    """Resolve bundled resources both from source and from PyInstaller."""

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / filename


def _prepare_chromakey_image(source):
    """Remove semi-transparent edge pixels that would blend with the key colour.

    Tk's ``-transparentcolor`` only removes pixels that exactly match the key.
    Normal PNG antialiasing contains partially transparent edge pixels; Tk blends
    those pixels with the magenta label background first, leaving a visible
    fuchsia fringe. Converting the resized alpha channel to binary transparency
    keeps the splash background fully keyed without contaminating the logo edge.
    """

    alpha = source.getchannel("A")
    alpha = alpha.point(lambda value: 255 if value >= ALPHA_CUTOFF else 0)
    source.putalpha(alpha)
    return source


def show_startup_splash():
    """Show only the transparent logo while the main Tk interface is built."""

    image_path = resource_path(SPLASH_IMAGE)
    if not image_path.is_file():
        return None

    splash = tk.Tk()
    splash.withdraw()
    splash.overrideredirect(True)
    splash.configure(bg=TRANSPARENT_KEY)

    try:
        splash.attributes("-topmost", True)
        splash.attributes("-transparentcolor", TRANSPARENT_KEY)
    except tk.TclError:
        # The app targets Windows, where transparentcolor is available. Keep a
        # harmless fallback for development on other platforms.
        splash.configure(bg="#101214")

    try:
        source = Image.open(image_path).convert("RGBA")
        bounds = source.getbbox()
        if bounds:
            source = source.crop(bounds)

        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        target = min(
            MAX_SPLASH_SIZE,
            max(280, int(min(screen_width, screen_height) * 0.43)),
        )
        source.thumbnail((target, target), Image.Resampling.LANCZOS)
        source = _prepare_chromakey_image(source)
        photo = ImageTk.PhotoImage(source, master=splash)
    except Exception:
        splash.destroy()
        return None

    label = tk.Label(
        splash,
        image=photo,
        bg=TRANSPARENT_KEY,
        bd=0,
        highlightthickness=0,
    )
    label.image = photo
    label.pack()

    splash.update_idletasks()
    width = max(1, splash.winfo_reqwidth())
    height = max(1, splash.winfo_reqheight())
    x = max(0, (splash.winfo_screenwidth() - width) // 2)
    y = max(0, (splash.winfo_screenheight() - height) // 2)
    geometry = f"{width}x{height}+{x}+{y}"
    splash.geometry(geometry)
    splash.deiconify()
    splash.lift()

    # Force the first paint before main-window construction starts blocking.
    splash.update_idletasks()
    splash.update()
    splash.geometry(geometry)
    return splash


def close_startup_splash(splash):
    """Remove the splash from the compositor before the main window is revealed."""

    if splash is None:
        return
    try:
        if not splash.winfo_exists():
            return
        splash.withdraw()
        splash.update_idletasks()
        splash.update()
        splash.destroy()
    except tk.TclError:
        pass
