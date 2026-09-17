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
OFFSCREEN_POSITION = "-32000-32000"
OFFSCREEN_PAINT_PASSES = 4


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


def _release_splash_as_default_root(splash):
    """Keep the splash alive without letting it own Tkinter's implicit variables.

    The splash is the first ``Tk()`` instance, so Tkinter normally registers it
    as the process default root. Several older v8 layers still create
    ``BooleanVar``/``StringVar`` objects without an explicit master. If the
    splash remains the default root, those variables live in the splash Tcl
    interpreter while the visible controls live in the main-window interpreter.
    The UI can then appear to toggle while scan/settings code reads a different
    value. Clearing only the implicit-root reference here lets the real app
    ``Tk()`` become the default root when it is constructed a moment later.
    """

    try:
        if (
            getattr(tk, "_support_default_root", True)
            and getattr(tk, "_default_root", None) is splash
        ):
            tk._default_root = None
    except (AttributeError, tk.TclError):
        pass


def _install_staged_main_deiconify():
    """Paint the next Tk root offscreen before revealing it.

    Windows can briefly show a newly mapped window's non-client border or paint
    individual controls over several compositor frames. The splash has already
    been mapped by the time this hook is installed, so the *next* ``Tk`` root to
    be deiconified is the real application window. Map that window far offscreen,
    let Tk and DWM complete a few paint passes, restore its requested geometry,
    then immediately restore the original ``Tk.deiconify`` implementation.

    The hook is deliberately one-shot and cannot affect Settings or any later
    window operations.
    """

    if getattr(tk.Tk, "_edhf_staged_deiconify", False):
        return

    original_deiconify = tk.Tk.deiconify

    def staged_deiconify(window, *args, **kwargs):
        # Restore normal Tk behaviour before doing anything else. Even if the
        # staging path fails, every later deiconify call behaves normally.
        tk.Tk.deiconify = original_deiconify
        try:
            delattr(tk.Tk, "_edhf_staged_deiconify")
        except AttributeError:
            pass

        target_geometry = None
        mapped = False
        try:
            window.update_idletasks()
            target_geometry = window.geometry()

            # Position-only geometry preserves the fully calculated window size
            # while moving the first native paint far outside any real monitor.
            window.geometry(OFFSCREEN_POSITION)
            original_deiconify(window, *args, **kwargs)
            mapped = True

            for _ in range(OFFSCREEN_PAINT_PASSES):
                window.update_idletasks()
                window.update()

            if target_geometry:
                window.geometry(target_geometry)
                window.update_idletasks()
        except tk.TclError:
            # If mapping itself failed, fall back to the ordinary behaviour so
            # startup can still continue instead of leaving the app withdrawn.
            if not mapped:
                try:
                    original_deiconify(window, *args, **kwargs)
                except tk.TclError:
                    pass
            elif target_geometry:
                try:
                    window.geometry(target_geometry)
                except tk.TclError:
                    pass

    tk.Tk.deiconify = staged_deiconify
    tk.Tk._edhf_staged_deiconify = True


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

    # The splash must not remain Tkinter's implicit root while the actual app is
    # built. It stays fully alive and visible; only implicit variable ownership
    # is released so the main Tk root can own all app state.
    _release_splash_as_default_root(splash)

    # The splash has already consumed its own deiconify, so this one-shot hook
    # applies only to the real application root that will be revealed later.
    _install_staged_main_deiconify()
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
