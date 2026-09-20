from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable


COLUMNS = (
    ("Body", 150),
    ("Material", 120),
    ("Rigs", 55),
    ("Amount", 70),
    ("Density", 70),
    ("Latitude", 95),
    ("Longitude", 95),
    ("Reports", 65),
    ("Updated", 145),
)


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

        self.window = tk.Toplevel(master)
        self.window.title(f"Community Deposits — {system}")
        self.window.geometry("940x420")
        self.window.minsize(760, 320)
        self.window.attributes("-topmost", True)

        outer = ttk.Frame(self.window, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            outer,
            text=f"Community Deposits — {system} ({len(records)})",
        )
        title.pack(anchor=tk.W, pady=(0, 8))

        table_frame = ttk.Frame(outer)
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            table_frame,
            columns=[name for name, _width in COLUMNS],
            show="headings",
            selectmode="browse",
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll_y.set)

        for name, width in COLUMNS:
            self.tree.heading(name, text=name)
            anchor = tk.CENTER if name in {"Rigs", "Reports"} else tk.W
            self.tree.column(name, width=width, minwidth=45, anchor=anchor)

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
            self.tree.insert("", tk.END, iid=str(index), values=values)

        buttons = ttk.Frame(outer)
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

    def _track_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        index = int(selected[0])
        if 0 <= index < len(self.records):
            self.on_track(self.records[index])
