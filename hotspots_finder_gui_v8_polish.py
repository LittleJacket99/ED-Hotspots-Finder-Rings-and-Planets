#!/usr/bin/env python3

"""Final v8 visual-polish test before consolidating the GUI layers."""

import tkinter as tk
from tkinter import ttk

import finder_engine as legacy_engine
from hotspots_finder_gui_v8 import COLORS
from hotspots_finder_gui_v8_layout import FinderV8LayoutApp


# Geometry taken from the annotated layout target.
FILTERS_PANEL_WIDTH = 250
SYSTEMS_PANEL_WIDTH = 240
LEFT_CLUSTER_WIDTH = 550
CONTENT_WIDTH = FILTERS_PANEL_WIDTH + SYSTEMS_PANEL_WIDTH
RIGHT_SPACER_WIDTH = LEFT_CLUSTER_WIDTH - CONTENT_WIDTH

OPTION_COLUMN_WIDTH = 108
SYSTEM_FILTERS_HEIGHT = 195
SYSTEM_FILTER_BOTTOM_GAP = 35
SYSTEM_FILTER_COLUMN_WIDTH = 230
SYSTEM_INPUT_WIDTH = 205
SYSTEM_INPUT_HEIGHT = 25


class FinderV8PolishApp(FinderV8LayoutApp):
    @staticmethod
    def _two_column_frame(parent):
        frame = tk.Frame(parent, bg=COLORS["panel"])
        frame.pack(fill="x")
        frame.columnconfigure(0, weight=0, minsize=OPTION_COLUMN_WIDTH)
        frame.columnconfigure(1, weight=0, minsize=OPTION_COLUMN_WIDTH)
        return frame

    def _build_ui(self):
        super()._build_ui()

        # The previous polish only changed requested widths inside the old grid,
        # so visually almost nothing moved. Here the three left-side zones are
        # positioned explicitly to match the sketch.
        self._left_cluster.configure(width=LEFT_CLUSTER_WIDTH)

        for panel in (
            self._filters_panel,
            self._systems_panel,
            self._system_filters_panel,
        ):
            try:
                panel.grid_forget()
            except tk.TclError:
                pass
            panel.place_forget()

        # Filters on the far left. Systems begins immediately after it, rather
        # than being pushed toward Results. A visible spacer remains on the
        # right side before the Results panel.
        upper_height_offset = -(SYSTEM_FILTERS_HEIGHT + SYSTEM_FILTER_BOTTOM_GAP)

        self._filters_panel.place(
            x=0,
            y=0,
            width=FILTERS_PANEL_WIDTH,
            relheight=1.0,
            height=upper_height_offset,
        )
        self._systems_panel.place(
            x=FILTERS_PANEL_WIDTH,
            y=0,
            width=SYSTEMS_PANEL_WIDTH,
            relheight=1.0,
            height=upper_height_offset,
        )

        # Pull SYSTEM FILTERS upward and keep it aligned only with the useful
        # left-side content. The remaining RIGHT_SPACER_WIDTH stays empty.
        self._system_filters_panel.place(
            x=0,
            rely=1.0,
            y=-(SYSTEM_FILTERS_HEIGHT + SYSTEM_FILTER_BOTTOM_GAP),
            width=CONTENT_WIDTH,
            height=SYSTEM_FILTERS_HEIGHT,
        )

        # Keep every widget inside Systems comfortably away from the right edge.
        for child in self._systems_panel.winfo_children():
            try:
                info = child.pack_info()
            except tk.TclError:
                continue

            if isinstance(child, tk.Label):
                text = str(child.cget("text") or "")
                if text.startswith("If Faction or Power is set"):
                    child.configure(wraplength=205)

            if info:
                try:
                    child.pack_configure(padx=(4, 18))
                except tk.TclError:
                    pass

    @staticmethod
    def _fixed_control_frame(parent, *, pady=(1, 4)):
        holder = tk.Frame(
            parent,
            bg=COLORS["panel"],
            width=SYSTEM_INPUT_WIDTH,
            height=SYSTEM_INPUT_HEIGHT,
        )
        holder.pack(anchor="w", pady=pady)
        holder.pack_propagate(False)
        return holder

    @staticmethod
    def _fill_holder(widget):
        # Exact pixel size for Faction, Power, Reference system and Max distance.
        widget.place(
            x=0,
            y=0,
            width=SYSTEM_INPUT_WIDTH,
            height=SYSTEM_INPUT_HEIGHT,
        )
        return widget

    def _build_system_filters(self, parent):
        tk.Label(
            parent,
            text="SYSTEM FILTERS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(2, 2))

        columns = tk.Frame(parent, bg=COLORS["panel"])
        columns.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        columns.columnconfigure(0, weight=0, minsize=SYSTEM_FILTER_COLUMN_WIDTH)
        columns.columnconfigure(1, weight=0, minsize=SYSTEM_FILTER_COLUMN_WIDTH)
        columns.rowconfigure(0, weight=1)

        left_col = tk.Frame(
            columns,
            bg=COLORS["panel"],
            width=SYSTEM_FILTER_COLUMN_WIDTH,
        )
        right_col = tk.Frame(
            columns,
            bg=COLORS["panel"],
            width=SYSTEM_FILTER_COLUMN_WIDTH,
        )
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        right_col.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        left_col.grid_propagate(False)
        right_col.grid_propagate(False)

        self._small_label(left_col, "Faction").pack(anchor="w")
        faction_holder = self._fixed_control_frame(left_col, pady=(1, 4))
        self._fill_holder(
            tk.Entry(
                faction_holder,
                textvariable=self.faction_var,
                bg="#3b3b3b",
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
            )
        )

        self._small_label(left_col, "Power").pack(anchor="w")
        power_holder = self._fixed_control_frame(left_col, pady=(1, 3))
        self._fill_holder(
            ttk.Combobox(
                power_holder,
                textvariable=self.power_var,
                values=[""] + list(legacy_engine.POWER_LIST),
                state="readonly",
            )
        )

        self._small_label(left_col, "Power states").pack(anchor="w")
        state_grid = tk.Frame(
            left_col,
            bg=COLORS["panel"],
            width=SYSTEM_INPUT_WIDTH,
        )
        state_grid.pack(anchor="w")
        state_grid.grid_propagate(False)
        state_grid.columnconfigure(0, weight=0, minsize=102)
        state_grid.columnconfigure(1, weight=0, minsize=103)
        self._grid_check(
            state_grid, "Unoccupied", self.power_state_vars["Unoccupied"], 0, 0
        )
        self._grid_check(
            state_grid, "Fortified", self.power_state_vars["Fortified"], 0, 1
        )
        self._grid_check(
            state_grid, "Exploited", self.power_state_vars["Exploited"], 1, 0
        )
        self._grid_check(
            state_grid, "Stronghold", self.power_state_vars["Stronghold"], 1, 1
        )

        self._small_label(right_col, "Reference system").pack(anchor="w")
        reference_holder = self._fixed_control_frame(right_col, pady=(1, 8))
        self._fill_holder(
            tk.Entry(
                reference_holder,
                textvariable=self.reference_system_var,
                bg="#3b3b3b",
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
            )
        )

        self._small_label(right_col, "Max distance (LY)").pack(anchor="w")
        distance_holder = self._fixed_control_frame(right_col, pady=(1, 0))
        self._fill_holder(
            tk.Entry(
                distance_holder,
                textvariable=self.max_distance_var,
                bg="#3b3b3b",
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
            )
        )


def main():
    app = FinderV8PolishApp()
    app.mainloop()


if __name__ == "__main__":
    main()
