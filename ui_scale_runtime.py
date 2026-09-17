#!/usr/bin/env python3

"""Runtime geometry scaling for the fixed-pixel v8 Tk interface.

The v8 layout was designed at a 96-DPI logical baseline.  Windows DPI awareness
keeps text crisp; this module scales Tk geometry-manager pixel arguments so the
whole interface grows together instead of enlarging fonts independently.
"""

import tkinter as tk


_SCALE = 1.0
_INSTALLED = False

_ORIGINAL_PLACE_CONFIGURE = tk.Place.place_configure
_ORIGINAL_PLACE = tk.Place.place
_ORIGINAL_PACK_CONFIGURE = tk.Pack.pack_configure
_ORIGINAL_PACK = tk.Pack.pack
_ORIGINAL_GRID_CONFIGURE = tk.Grid.grid_configure
_ORIGINAL_GRID = tk.Grid.grid

_PLACE_KEYS = {"x", "y", "width", "height"}
_PADDING_KEYS = {"padx", "pady", "ipadx", "ipady"}


def normalise_scale(value, default=1.15):
    """Return one of the supported application scale factors."""

    allowed = (1.00, 1.10, 1.15, 1.25)
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = float(default)

    return min(allowed, key=lambda item: abs(item - number))


def current_scale():
    return _SCALE


def px(value):
    """Convert a logical baseline pixel value to a physical pixel value."""

    try:
        return int(round(float(value) * _SCALE))
    except (TypeError, ValueError):
        return value


def logical_px(value):
    """Convert a physical pixel value back to baseline logical pixels."""

    try:
        return int(round(float(value) / _SCALE))
    except (TypeError, ValueError, ZeroDivisionError):
        return value


def _scale_scalar(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return px(value)
    return value


def _scale_padding(value):
    if isinstance(value, (tuple, list)):
        scaled = [_scale_scalar(item) for item in value]
        return tuple(scaled) if isinstance(value, tuple) else scaled
    return _scale_scalar(value)


def _scaled_config(cnf, kw, keys):
    options = {}
    if isinstance(cnf, dict):
        options.update(cnf)
    options.update(kw)

    for key in tuple(options):
        if key not in keys:
            continue
        if key in _PADDING_KEYS:
            options[key] = _scale_padding(options[key])
        else:
            options[key] = _scale_scalar(options[key])
    return options


def install(scale):
    """Install process-wide scaling for place plus manager padding.

    Tk's place coordinates are pixel geometry, so scaling them is what preserves
    the approved proportions. Pack/grid are left structurally unchanged; only
    their explicit padding values are scaled.
    """

    global _SCALE, _INSTALLED
    _SCALE = normalise_scale(scale)
    if _INSTALLED:
        return _SCALE

    def scaled_place_configure(widget, cnf=None, **kw):
        options = _scaled_config(cnf or {}, kw, _PLACE_KEYS)
        return _ORIGINAL_PLACE_CONFIGURE(widget, options)

    def scaled_pack_configure(widget, cnf=None, **kw):
        options = _scaled_config(cnf or {}, kw, _PADDING_KEYS)
        return _ORIGINAL_PACK_CONFIGURE(widget, options)

    def scaled_grid_configure(widget, cnf=None, **kw):
        options = _scaled_config(cnf or {}, kw, _PADDING_KEYS)
        return _ORIGINAL_GRID_CONFIGURE(widget, options)

    tk.Place.place_configure = scaled_place_configure
    tk.Place.place = scaled_place_configure
    tk.Pack.pack_configure = scaled_pack_configure
    tk.Pack.pack = scaled_pack_configure
    tk.Grid.grid_configure = scaled_grid_configure
    tk.Grid.grid = scaled_grid_configure

    _INSTALLED = True
    return _SCALE


def place_physical(widget, **options):
    """Place a widget using already-physical coordinates without rescaling.

    Used only for overlays whose coordinates come from winfo_* measurements,
    such as one-pixel button borders and the Results outline.
    """

    return _ORIGINAL_PLACE_CONFIGURE(widget, options)
