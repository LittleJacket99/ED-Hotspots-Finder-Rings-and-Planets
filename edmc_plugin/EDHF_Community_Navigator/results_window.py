from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any, Callable


BACKGROUND = "#101410"
ROW_BACKGROUND = "#101410"
HEADER_BACKGROUND = "#171d17"
ACCENT = "#5acd57"
TEXT = "#f2f5f2"
MUTED = "#a6b0a6"
SELECT_BACKGROUND = "#244024"
BORDER = "#355035"

COLUMNS = (
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

MIN_COLUMN_WIDTH = 55
MAX_COLUMN_WIDTH = 420
CELL_PADDING = 20
ROW_HEIGHT = 25
HEADER_HEIGHT = 27


def _first(record: dict[str, Any], *keys: str):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return ""


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
        self.selected_index: int | None = 0 if records else None
        self.row_widgets: dict[int, list[tk.Label]] = {}

        self.window = tk.Toplevel(master)
        self.window.title(f"Community Deposits — {system}")
        self.window.attributes("-topmost", True)
        self.window.configure(background=BACKGROUND)

        outer = tk.Frame(
            self.window,
            background=BACKGROUND,
            padx=10,
            pady=10,
        )
        outer.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(
            outer,
            text=f"Community Deposits — {system} ({len(records)})",
            background=BACKGROUND,
            foreground=ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        title.pack(fill=tk.X, pady=(0, 8))

        self._display_rows = [
            (
                str(_first(record, "body", "body_name", "planet_name")),
                str(_first(record, "commodity", "material")),
                str(_first(record, "rigs")),
                str(_first(record, "amount")),
                str(_first(record, "density")),
                str(_first(record, "latitude", "lat")),
                str(_first(record, "longitude", "lon", "lng")),
                str(_first(record, "report_count", "reports_count", "reports")),
                str(_first(record, "updated_at", "last_reported_at", "last_seen_at")),
            )
            for record in records
        ]

        self.column_widths = self._measure_columns()

        table_shell = tk.Frame(
            outer,
            background=BORDER,
            bd=0,
        )
        table_shell.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            table_shell,
            background=BACKGROUND,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(
            table_shell,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = ttk.Scrollbar(
            outer,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview,
        )
        scroll_x.pack(fill=tk.X, pady=(4, 0))

        self.canvas.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        self.table = tk.Frame(
            self.canvas,
            background=BACKGROUND,
        )
        self.table_window = self.canvas.create_window(
            (0, 0),
            window=self.table,
            anchor="nw",
        )

        self._build_header()
        self._build_rows()

        self.table.bind("<Configure>", self._sync_scrollregion)
        self.canvas.bind("<Configure>", self._sync_canvas_height)

        buttons = tk.Frame(
            outer,
            background=BACKGROUND,
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

        self._apply_selection()
        self._size_window()

    def _measure_columns(self) -> dict[str, int]:
        font = tkfont.Font(family="Segoe UI", size=9)
        widths: dict[str, int] = {}

        for column_index, name in enumerate(COLUMNS):
            width = font.measure(name) + CELL_PADDING

            for row in self._display_rows:
                width = max(
                    width,
                    font.measure(row[column_index]) + CELL_PADDING,
                )

            widths[name] = max(
                MIN_COLUMN_WIDTH,
                min(width, MAX_COLUMN_WIDTH),
            )

        return widths

    def _build_header(self) -> None:
        for column_index, name in enumerate(COLUMNS):
            width = self.column_widths[name]
            anchor = "center" if name in CENTERED_COLUMNS else "w"

            label = tk.Label(
                self.table,
                text=name,
                background=HEADER_BACKGROUND,
                foreground=ACCENT,
                font=("Segoe UI", 9, "bold"),
                anchor=anchor,
                padx=7,
                pady=4,
                bd=0,
            )
            label.grid(
                row=0,
                column=column_index,
                sticky="nsew",
                padx=(0, 1),
                pady=(0, 1),
            )
            self.table.grid_columnconfigure(
                column_index,
                minsize=width,
            )

    def _build_rows(self) -> None:
        for row_index, row in enumerate(self._display_rows):
            widgets: list[tk.Label] = []

            for column_index, value in enumerate(row):
                column = COLUMNS[column_index]
                anchor = "center" if column in CENTERED_COLUMNS else "w"

                label = tk.Label(
                    self.table,
                    text=value,
                    background=ROW_BACKGROUND,
                    foreground=TEXT,
                    font=("Segoe UI", 9),
                    anchor=anchor,
                    padx=7,
                    pady=3,
                    bd=0,
                )
                label.grid(
                    row=row_index + 1,
                    column=column_index,
                    sticky="nsew",
                    padx=(0, 1),
                    pady=(0, 1),
                )

                label.bind(
                    "<Button-1>",
                    lambda _event, index=row_index: self._select(index),
                )
                label.bind(
                    "<Double-1>",
                    lambda _event, index=row_index: self._track_index(index),
                )
                widgets.append(label)

            self.row_widgets[row_index] = widgets

    def _select(self, index: int) -> None:
        self.selected_index = index
        self._apply_selection()

    def _apply_selection(self) -> None:
        for row_index, widgets in self.row_widgets.items():
            selected = row_index == self.selected_index
            background = SELECT_BACKGROUND if selected else ROW_BACKGROUND
            foreground = TEXT

            for widget in widgets:
                widget.configure(
                    background=background,
                    foreground=foreground,
                )

    def _track_index(self, index: int) -> None:
        self._select(index)
        self._track_selected()

    def _track_selected(self) -> None:
        if self.selected_index is None:
            return

        if 0 <= self.selected_index < len(self.records):
            self.on_track(self.records[self.selected_index])

    def _sync_scrollregion(self, _event=None) -> None:
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all"),
        )

    def _sync_canvas_height(self, _event=None) -> None:
        # Keep the table at its natural width. The horizontal scrollbar handles
        # systems with exceptionally long values instead of stretching columns.
        self.canvas.itemconfigure(
            self.table_window,
            height=max(
                self.canvas.winfo_height(),
                self.table.winfo_reqheight(),
            ),
        )

    def _size_window(self) -> None:
        self.window.update_idletasks()

        table_width = sum(self.column_widths.values()) + len(COLUMNS)
        screen_width = self.window.winfo_screenwidth()
        max_width = int(screen_width * 0.92)
        window_width = min(table_width + 55, max_width)

        visible_rows = min(max(len(self.records), 1), 12)
        table_height = HEADER_HEIGHT + visible_rows * ROW_HEIGHT
        window_height = table_height + 125

        self.window.geometry(
            f"{max(window_width, 650)}x{max(window_height, 220)}"
        )
        self.window.minsize(650, 220)
