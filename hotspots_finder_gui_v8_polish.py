#!/usr/bin/env python3

"""Final v8 visual-polish test before consolidating the GUI layers."""

import tkinter as tk
from tkinter import ttk

import finder_engine as legacy_engine
from hotspots_finder_gui_v8 import COLORS
from hotspots_finder_gui_v8_layout import FinderV8LayoutApp


FILTERS_PANEL_WIDTH = 265
SYSTEMS_PANEL_WIDTH = 260
LEFT_CLUSTER_WIDTH = 550
RIGHT_SPACER_WIDTH = LEFT_CLUSTER_WIDTH - FILTERS_PANEL_WIDTH - SYSTEMS_PANEL_WIDTH
OPTION_COLUMN_WIDTH = 115
SYSTEM_FILTER_COLUMN_WIDTH = 245
SYSTEM_INPUT_WIDTH = 225


class FinderV8PolishApp(FinderV8LayoutApp):
    @staticmethod
    def _two_column_frame(parent):
        """Slightly tighter filter columns so the Filters panel can move left."""
        frame = tk.Frame(parent, bg=COLORS["panel"])
        frame.pack(fill="x")
        frame.columnconfigure(0, weight=0, minsize=OPTION_COLUMN_WIDTH)
        frame.columnconfigure(1, weight=0, minsize=OPTION_COLUMN_WIDTH)
        return frame

    def _build_ui(self):
        super()._build_ui()

        # Move Systems closer to Filters and leave a visible breathing-space
        # between Systems and Results instead of pinning Systems to the edge.
        self._left_cluster.configure(width=LEFT_CLUSTER_WIDTH)
        self._left_cluster.columnconfigure(0, weight=0, minsize=FILTERS_PANEL_WIDTH)
        self._left_cluster.columnconfigure(1, weight=0, minsize=SYSTEMS_PANEL_WIDTH)
        self._left_cluster.columnconfigure(2, weight=0, minsize=RIGHT_SPACER_WIDTH)

        self._filters_panel.configure(width=FILTERS_PANEL_WIDTH)
        self._systems_panel.configure(width=SYSTEMS_PANEL_WIDTH)

        # Keep the explanatory text completely inside the narrower Systems box.
        for child in self._systems_panel.winfo_children():
            if isinstance(child, tk.Label):
                text = str(child.cget("text") or "")
                if text.startswith("If Faction or Power is set"):
                    child.configure(wraplength=225)

    @staticmethod
    def _fixed_control_frame(parent, *, pady=(1, 4)):
        holder = tk.Frame(
            parent,
            bg=COLORS["panel"],
            width=SYSTEM_INPUT_WIDTH,
            height=25,
        )
        holder.pack(anchor="w", pady=pady)
        holder.pack_propagate(False)
        return holder

    def _build_system_filters(self, parent):
        """Use four visually equal input boxes in two balanced columns."""
        tk.Label(
            parent,
            text="SYSTEM FILTERS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(4, 2))

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
        reference_col = tk.Frame(
            columns,
            bg=COLORS["panel"],
            width=SYSTEM_FILTER_COLUMN_WIDTH,
        )
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        reference_col.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        left_col.grid_propagate(False)
        reference_col.grid_propagate(False)

        self._small_label(left_col, "Faction").pack(anchor="w")
        faction_holder = self._fixed_control_frame(left_col, pady=(1, 4))
        tk.Entry(
            faction_holder,
            textvariable=self.faction_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="both", expand=True)

        self._small_label(left_col, "Power").pack(anchor="w")
        power_holder = self._fixed_control_frame(left_col, pady=(1, 3))
        ttk.Combobox(
            power_holder,
            textvariable=self.power_var,
            values=[""] + list(legacy_engine.POWER_LIST),
            state="readonly",
        ).pack(fill="x")

        self._small_label(left_col, "Power states").pack(anchor="w")
        state_grid = tk.Frame(left_col, bg=COLORS["panel"], width=SYSTEM_INPUT_WIDTH)
        state_grid.pack(anchor="w", fill="x")
        state_grid.columnconfigure(0, weight=1)
        state_grid.columnconfigure(1, weight=1)
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

        self._small_label(reference_col, "Reference system").pack(anchor="w")
        reference_holder = self._fixed_control_frame(reference_col, pady=(1, 8))
        tk.Entry(
            reference_holder,
            textvariable=self.reference_system_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="both", expand=True)

        self._small_label(reference_col, "Max distance (LY)").pack(anchor="w")
        distance_holder = self._fixed_control_frame(reference_col, pady=(1, 0))
        tk.Entry(
            distance_holder,
            textvariable=self.max_distance_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="both", expand=True)


def main():
    app = FinderV8PolishApp()
    app.mainloop()


if __name__ == "__main__":
    main()
