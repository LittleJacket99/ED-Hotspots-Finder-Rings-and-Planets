from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any, Callable

from theme import theme


COLUMN_NAMES = (
    "Body",
    "Material",
    "Rigs",
    "Amount",
    "Density",
    "Latitude",
    "Longitude",
    "Reports",
    "Updated",
)

CENTERED_COLUMNS = {"Rigs", "Reports"}

MIN_COLUMN_WIDTH = 52
MAX_COLUMN_WIDTH = 420
CELL_PADDING = 24
WINDOW_HORIZONTAL_CHROME = 58


def _first(record: dict[str, Any], *keys: str):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return ""


def _theme_colours() -> dict[str, str]:
    current = getattr(theme, "current", {}) or {}
    return {
        "background": current.get("background") or "#101410",
        "foreground": current.get("foreground") or "#f2f5f2",
        "selection_bg": current.get("activebackground") or "#5acd57",
        "selection_fg": current.get("activeforeground") or "#101410",
        "disabled": current.get("disabledforeground") or "#707770",
        "highlight": current.get("highlight") or "#5acd57",
    }


class DepositsWindow:
    def __init__(
        self,
        master: tk.Misc,
        *,
        system: str,
        records: list[dict[str, Any]],
        on_track: Callable[[dict[str, Any]], None],
    ):
        self.records = records
        self.on_track = on_track

        colours = _theme_colours()

        self.window = tk.Toplevel(master)
        self.window.title(f"Community Deposits — {system}")
        self.window.attributes("-topmost", True)
        self.window.configure(background=colours["background"])

        style = ttk.Style(self.window)

        # Plugin-specific ttk styles: do not alter EDMC or other plugins.
        style.configure(
            "EDHFCommunity.Treeview",
            background=colours["background"],
            fieldbackground=colours["background"],
            foreground=colours["foreground"],
            borderwidth=0,
            relief="flat",
            rowheight=24,
        )
        style.map(
            "EDHFCommunity.Treeview",
            background=[("selected", colours["selection_bg"])],
            foreground=[("selected", colours["selection_fg"])],
        )

        style.configure(
            "EDHFCommunity.Treeview.Heading",
            background=colours["background"],
            foreground=colours["foreground"],
            relief="flat",
            borderwidth=1,
        )
        style.map(
            "EDHFCommunity.Treeview.Heading",
            background=[
                ("active", colours["selection_bg"]),
                ("pressed", colours["selection_bg"]),
            ],
            foreground=[
                ("active", colours["selection_fg"]),
                ("pressed", colours["selection_fg"]),
            ],
        )

        style.configure(
            "EDHFCommunity.TFrame",
            background=colours["background"],
        )
        style.configure(
            "EDHFCommunity.TLabel",
            background=colours["background"],
            foreground=colours["foreground"],
        )

        outer = ttk.Frame(
            self.window,
            padding=10,
            style="EDHFCommunity.TFrame",
        )
        outer.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            outer,
            text=f"Community Deposits — {system} ({len(records)})",
            style="EDHFCommunity.TLabel",
        )
        title.pack(anchor=tk.W, pady=(0, 8))

        table_frame = ttk.Frame(
            outer,
            style="EDHFCommunity.TFrame",
        )
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=COLUMN_NAMES,
            show="headings",
            selectmode="browse",
            style="EDHFCommunity.Treeview",
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = ttk.Scrollbar(
            outer,
            orient=tk.HORIZONTAL,
            command=self.tree.xview,
        )
        scroll_x.pack(fill=tk.X, pady=(3, 0))

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        values_by_column: dict[str, list[str]] = {
            name: [] for name in COLUMN_NAMES
        }

        for index, record in enumerate(records):
            values = (
                _first(record, "body", "body_name", "planet_name"),
                _first(record, "commodity", "material"),
                _first(record, "rigs"),
                _first(record, "amount"),
                _first(record, "density"),
                _first(record, "latitude", "lat"),
                _first(record, "longitude", "lon", "lng"),
                _first(record, "report_count", "reports_count", "reports"),
                _first(record, "updated_at", "last_reported_at", "last_seen_at"),
            )

            display_values = tuple(
                "" if value is None else str(value)
                for value in values
            )

            self.tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=display_values,
            )

            for name, value in zip(COLUMN_NAMES, display_values):
                values_by_column[name].append(value)

        self._autosize_columns(values_by_column)

        buttons = ttk.Frame(
            outer,
            style="EDHFCommunity.TFrame",
        )
        buttons.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            buttons,
            text="Track Selected",
            command=self._track_selected,
        ).pack(side=tk.LEFT)

        ttk.Button(
            buttons,
            text="Close",
            command=self.window.destroy,
        ).pack(side=tk.RIGHT)

        self.tree.bind("<Double-1>", lambda _event: self._track_selected())

        if records:
            self.tree.selection_set("0")
            self.tree.focus("0")

        self._size_window_to_columns()

    def _autosize_columns(
        self,
        values_by_column: dict[str, list[str]],
    ) -> None:
        font = tkfont.nametofont("TkDefaultFont")

        for name in COLUMN_NAMES:
            self.tree.heading(name, text=name)

            width = font.measure(name) + CELL_PADDING
            for value in values_by_column[name]:
                width = max(
                    width,
                    font.measure(value) + CELL_PADDING,
                )

            width = max(MIN_COLUMN_WIDTH, min(width, MAX_COLUMN_WIDTH))
            anchor = tk.CENTER if name in CENTERED_COLUMNS else tk.W

            self.tree.column(
                name,
                width=width,
                minwidth=MIN_COLUMN_WIDTH,
                anchor=anchor,
                stretch=False,
            )

    def _size_window_to_columns(self) -> None:
        self.window.update_idletasks()

        table_width = sum(
            int(self.tree.column(name, "width"))
            for name in COLUMN_NAMES
        )

        desired_width = table_width + WINDOW_HORIZONTAL_CHROME
        screen_width = self.window.winfo_screenwidth()
        max_width = max(760, int(screen_width * 0.92))
        window_width = min(desired_width, max_width)

        # Enough room for a useful table without making the popup huge.
        row_count = min(max(len(self.records), 4), 14)
        window_height = 180 + row_count * 24

        self.window.geometry(f"{window_width}x{window_height}")
        self.window.minsize(min(window_width, 700), 300)

    def _track_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return

        index = int(selected[0])
        if 0 <= index < len(self.records):
            self.on_track(self.records[index])
