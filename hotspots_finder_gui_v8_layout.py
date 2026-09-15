#!/usr/bin/env python3

"""v8 layout test: fixed Filters / Systems / Results zones and compact controls."""

import tkinter as tk
from tkinter import ttk

import finder_engine as legacy_engine
from hotspots_finder_gui_v8 import COLORS, FinderV8App
from hotspots_finder_gui_v8_columnfilters import FILTER_COLUMNS
from hotspots_finder_gui_v8_community import COMMUNITY_FALLBACK_HEADERS
from hotspots_finder_gui_v8_expandresults import (
    BODY_COLUMN,
    DISTANCE_COLUMN,
    SORT_TABLES,
)
from hotspots_finder_gui_v8_loglayout import FinderV8LogLayoutApp


FILTERS_WIDTH = 300
SYSTEMS_WIDTH = 250
LEFT_WIDTH = FILTERS_WIDTH + SYSTEMS_WIDTH + 6
SYSTEM_FILTERS_HEIGHT = 190


class FinderV8LayoutApp(FinderV8LogLayoutApp):
    def _build_ui(self):
        # State normally prepared by the intermediate feature-test layers.
        self.reference_system_var = tk.StringVar(master=self, value="")
        self.max_distance_var = tk.StringVar(master=self, value="50")
        self._distance_sort_state = {table: None for table in SORT_TABLES}
        self._body_sort_state = {table: None for table in SORT_TABLES}
        self._active_sort_column = {table: None for table in SORT_TABLES}

        self._column_filter_rows = {}
        self._column_filter_headers = {}
        self._column_filter_state = {
            table: {column: None for column in columns}
            for table, columns in FILTER_COLUMNS.items()
        }
        self._autosize_next_populate = set()

        self.community_deposits_enabled = tk.BooleanVar(master=self, value=False)
        self.community_commodity_filter = tk.StringVar(master=self, value="All")
        self.community_body_filter = tk.StringVar(master=self, value="All")
        self.community_all_headers = list(COMMUNITY_FALLBACK_HEADERS)
        self.community_all_rows = []
        self.rhino_upload_running = False

        header = tk.Frame(self, bg="#242424", height=76)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Hotspots & Landables Finder",
            bg="#242424",
            fg=COLORS["orange"],
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", padx=18, pady=(12, 0))

        tk.Label(
            header,
            text="v8 local interface · Spansh · no Google Sheets",
            bg="#242424",
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=19, pady=(0, 8))

        self._main_grid = tk.Frame(self, bg=COLORS["bg"])
        self._main_grid.pack(fill="both", expand=True, padx=10, pady=10)
        self._main_grid.rowconfigure(0, weight=1)
        self._main_grid.columnconfigure(0, weight=0, minsize=LEFT_WIDTH)
        self._main_grid.columnconfigure(1, weight=1, minsize=520)

        self._left_cluster = tk.Frame(
            self._main_grid,
            bg=COLORS["bg"],
            width=LEFT_WIDTH,
        )
        self._left_cluster.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._left_cluster.grid_propagate(False)
        self._left_cluster.columnconfigure(0, weight=0, minsize=FILTERS_WIDTH)
        self._left_cluster.columnconfigure(1, weight=0, minsize=SYSTEMS_WIDTH)
        self._left_cluster.rowconfigure(0, weight=1)
        self._left_cluster.rowconfigure(1, weight=0, minsize=SYSTEM_FILTERS_HEIGHT)

        self._filters_panel = tk.Frame(
            self._left_cluster,
            bg=COLORS["panel"],
            width=FILTERS_WIDTH,
        )
        self._filters_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        self._filters_panel.grid_propagate(False)

        self._systems_panel = tk.Frame(
            self._left_cluster,
            bg=COLORS["panel"],
            width=SYSTEMS_WIDTH,
        )
        self._systems_panel.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        self._systems_panel.grid_propagate(False)

        self._system_filters_panel = tk.Frame(
            self._left_cluster,
            bg=COLORS["panel"],
            height=SYSTEM_FILTERS_HEIGHT,
        )
        self._system_filters_panel.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(6, 0),
        )
        self._system_filters_panel.grid_propagate(False)

        self._results_panel = tk.Frame(self._main_grid, bg=COLORS["panel"])
        self._results_panel.grid(row=0, column=1, sticky="nsew")

        self._build_filters(self._filters_panel)
        self._build_systems(self._systems_panel)
        self._build_system_filters(self._system_filters_panel)
        self._build_results(self._results_panel)
        self._build_bottom_bar()

        # Keep the convenient paste behaviour from the column-filter layer.
        self.systems_text.bind("<<Paste>>", self._paste_systems_with_newline)

    @staticmethod
    def _grid_check(parent, text, variable, row, column, *, sticky="w"):
        widget = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["text"],
            selectcolor="#404040",
            highlightthickness=0,
            bd=0,
            anchor="w",
        )
        widget.grid(row=row, column=column, sticky=sticky, padx=2, pady=1)
        return widget

    @staticmethod
    def _small_label(parent, text):
        return tk.Label(
            parent,
            text=text,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
        )

    def _build_filters(self, parent):
        content = tk.Frame(parent, bg=COLORS["panel"])
        content.pack(fill="both", expand=True, padx=12, pady=(7, 8))

        tk.Label(
            content,
            text="HOTSPOTS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(2, 3))

        hotspot_switches = tk.Frame(content, bg=COLORS["panel"])
        hotspot_switches.pack(fill="x")
        hotspot_switches.columnconfigure(0, weight=1)
        hotspot_switches.columnconfigure(1, weight=1)
        self._grid_check(hotspot_switches, "Enable hotspots", self.hotspots_enabled, 0, 0)
        self._grid_check(hotspot_switches, "Only pristine", self.only_pristine, 0, 1)

        hotspot_options = tk.Frame(content, bg=COLORS["panel"])
        hotspot_options.pack(fill="x", pady=(4, 3))
        hotspot_options.columnconfigure(0, weight=1)
        hotspot_options.columnconfigure(1, weight=1)

        ring_col = tk.Frame(hotspot_options, bg=COLORS["panel"])
        commodity_col = tk.Frame(hotspot_options, bg=COLORS["panel"])
        ring_col.grid(row=0, column=0, sticky="nw")
        commodity_col.grid(row=0, column=1, sticky="nw")

        self._small_label(ring_col, "Ring types").pack(anchor="w", pady=(0, 1))
        for key, label in (
            ("icy", "Icy"),
            ("metallic", "Metallic"),
            ("metal rich", "Metal Rich"),
            ("rocky", "Rocky"),
        ):
            tk.Checkbutton(
                ring_col,
                text=label,
                variable=self.ring_vars[key],
                bg=COLORS["panel"],
                fg=COLORS["text"],
                activebackground=COLORS["panel"],
                activeforeground=COLORS["text"],
                selectcolor="#404040",
                highlightthickness=0,
                bd=0,
                anchor="w",
            ).pack(anchor="w")

        self._small_label(commodity_col, "Commodities").pack(anchor="w", pady=(0, 1))
        for key, label in (
            ("platinum", "Platinum"),
            ("bromellite", "Bromellite"),
            ("monazite", "Monazite"),
        ):
            tk.Checkbutton(
                commodity_col,
                text=label,
                variable=self.material_vars[key],
                bg=COLORS["panel"],
                fg=COLORS["text"],
                activebackground=COLORS["panel"],
                activeforeground=COLORS["text"],
                selectcolor="#404040",
                highlightthickness=0,
                bd=0,
                anchor="w",
            ).pack(anchor="w")

        tk.Label(
            content,
            text="PLANETS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(7, 3))

        planet_switches = tk.Frame(content, bg=COLORS["panel"])
        planet_switches.pack(fill="x")
        planet_switches.columnconfigure(0, weight=1)
        planet_switches.columnconfigure(1, weight=1)
        self._grid_check(planet_switches, "Enable planets", self.planets_enabled, 0, 0)
        self._grid_check(planet_switches, "Only landables", self.only_landables, 0, 1)

        self._small_label(content, "Planet types").pack(anchor="w", pady=(4, 1))
        planet_types = tk.Frame(content, bg=COLORS["panel"])
        planet_types.pack(fill="x")
        planet_types.columnconfigure(0, weight=1)
        planet_types.columnconfigure(1, weight=1)

        for row, (key, label) in enumerate((
            ("metal rich", "Metal Rich"),
            ("high metal content", "High Metal Content"),
            ("rocky", "Rocky"),
        )):
            self._grid_check(planet_types, label, self.planet_type_vars[key], row, 0)

        for row, (key, label) in enumerate((
            ("rocky ice", "Rocky Ice"),
            ("icy", "Icy"),
        )):
            self._grid_check(planet_types, label, self.planet_type_vars[key], row, 1)

        tk.Label(
            content,
            text="RESULTS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(7, 2))

        tk.Checkbutton(
            content,
            text="Only positive results",
            variable=self.only_positive,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["text"],
            selectcolor="#404040",
            highlightthickness=0,
            bd=0,
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            content,
            text="COMMUNITY DEPOSITS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(7, 2))

        tk.Checkbutton(
            content,
            text="Show Community Deposits",
            variable=self.community_deposits_enabled,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["text"],
            selectcolor="#404040",
            highlightthickness=0,
            bd=0,
            anchor="w",
        ).pack(anchor="w")

        self.rhino_upload_button = tk.Button(
            content,
            text="Upload RhinoSpotter Deposits",
            command=self.start_rhino_upload,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            disabledforeground="#777777",
            relief="flat",
            padx=9,
            pady=4,
        )
        self.rhino_upload_button.pack(fill="x", pady=(4, 0))

    def _build_systems(self, parent):
        # Use the clean v8 Systems panel directly, skipping the old Community
        # block which has moved into Filters.
        FinderV8App._build_systems(self, parent)

    def _build_system_filters(self, parent):
        tk.Label(
            parent,
            text="SYSTEM FILTERS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(8, 3))

        columns = tk.Frame(parent, bg=COLORS["panel"])
        columns.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        for index in range(3):
            columns.columnconfigure(index, weight=1, uniform="systemfilters")
        columns.rowconfigure(0, weight=1)

        faction_col = tk.Frame(columns, bg=COLORS["panel"])
        power_col = tk.Frame(columns, bg=COLORS["panel"])
        reference_col = tk.Frame(columns, bg=COLORS["panel"])
        faction_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        power_col.grid(row=0, column=1, sticky="nsew", padx=8)
        reference_col.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        self._small_label(faction_col, "Faction").pack(anchor="w")
        tk.Entry(
            faction_col,
            textvariable=self.faction_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="x", pady=(2, 8), ipady=4)

        tk.Button(
            faction_col,
            text="Clear Filters",
            command=self._clear_scan_filters,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            relief="flat",
            padx=10,
            pady=3,
        ).pack(anchor="w")

        self._small_label(power_col, "Power").pack(anchor="w")
        ttk.Combobox(
            power_col,
            textvariable=self.power_var,
            values=[""] + list(legacy_engine.POWER_LIST),
            state="readonly",
        ).pack(fill="x", pady=(2, 4))

        self._small_label(power_col, "Power states").pack(anchor="w", pady=(1, 0))
        state_grid = tk.Frame(power_col, bg=COLORS["panel"])
        state_grid.pack(fill="x")
        state_grid.columnconfigure(0, weight=1)
        state_grid.columnconfigure(1, weight=1)
        for row, state in enumerate(("Unoccupied", "Exploited")):
            self._grid_check(state_grid, state, self.power_state_vars[state], row, 0)
        for row, state in enumerate(("Fortified", "Stronghold")):
            self._grid_check(state_grid, state, self.power_state_vars[state], row, 1)

        self._small_label(reference_col, "Reference system").pack(anchor="w")
        tk.Entry(
            reference_col,
            textvariable=self.reference_system_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="x", pady=(2, 7), ipady=4)

        self._small_label(reference_col, "Max distance (LY)").pack(anchor="w")
        tk.Entry(
            reference_col,
            textvariable=self.max_distance_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="x", pady=(2, 0), ipady=4)

    def _toggle_results_expansion(self):
        # Same user-facing behaviour as before, adapted to the fixed grid
        # instead of draggable PanedWindow sashes.
        if not self._results_expanded:
            self._log_was_visible_before_results_expand = self._log_visible
            if self._log_visible:
                self._log_panel.place_forget()

            self._left_cluster.grid_remove()
            self._main_grid.columnconfigure(0, minsize=0, weight=0)
            self._results_panel.grid_configure(column=0, columnspan=2)

            if getattr(self, "_bottom_bar", None) is not None:
                self._bottom_bar.pack_forget()

            self._results_expanded = True
            self.expand_results_button.configure(text="Restore Panels")
            return

        self._results_panel.grid_configure(column=1, columnspan=1)
        self._main_grid.columnconfigure(0, minsize=LEFT_WIDTH, weight=0)
        self._left_cluster.grid()

        if getattr(self, "_bottom_bar", None) is not None:
            self._bottom_bar.pack(fill="x", side="bottom")

        self._results_expanded = False
        self.expand_results_button.configure(text="Expand Results")

        if self._log_was_visible_before_results_expand:
            self._log_visible = False
            self.after_idle(self._show_log_panel)


def main():
    app = FinderV8LayoutApp()
    app.mainloop()


if __name__ == "__main__":
    main()
