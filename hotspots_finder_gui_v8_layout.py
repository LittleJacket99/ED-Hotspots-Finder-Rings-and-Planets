#!/usr/bin/env python3

"""v8 layout test: fixed Filters / Systems / Results zones and compact controls."""

import tkinter as tk
from tkinter import ttk

import finder_engine as legacy_engine
from hotspots_finder_gui_v8 import COLORS, FinderV8App
from hotspots_finder_gui_v8_columnfilters import FILTER_COLUMNS
from hotspots_finder_gui_v8_community import COMMUNITY_FALLBACK_HEADERS
from hotspots_finder_gui_v8_expandresults import SORT_TABLES
from hotspots_finder_gui_v8_loglayout import FinderV8LogLayoutApp


FILTERS_WIDTH = 300
SYSTEMS_WIDTH = 250
LEFT_WIDTH = FILTERS_WIDTH + SYSTEMS_WIDTH
SYSTEM_FILTERS_HEIGHT = 195
OPTION_COLUMN_WIDTH = 135
SYSTEM_FILTER_LEFT_WIDTH = 305
SYSTEM_FILTER_REFERENCE_WIDTH = 211


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

        # One visually continuous left area. Filters and Systems keep their
        # fixed widths, but there are no gutters forming the old inverted T.
        self._left_cluster = tk.Frame(
            self._main_grid,
            bg=COLORS["panel"],
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
        self._filters_panel.grid(row=0, column=0, sticky="nsew")
        self._filters_panel.grid_propagate(False)

        self._systems_panel = tk.Frame(
            self._left_cluster,
            bg=COLORS["panel"],
            width=SYSTEMS_WIDTH,
        )
        self._systems_panel.grid(row=0, column=1, sticky="nsew")
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
            padx=0,
            pady=0,
            anchor="w",
        )
        widget.grid(row=row, column=column, sticky=sticky, padx=0, pady=1)
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

    @staticmethod
    def _two_column_frame(parent):
        frame = tk.Frame(parent, bg=COLORS["panel"])
        frame.pack(fill="x")
        frame.columnconfigure(0, weight=0, minsize=OPTION_COLUMN_WIDTH)
        frame.columnconfigure(1, weight=0, minsize=OPTION_COLUMN_WIDTH)
        return frame

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

        hotspot_switches = self._two_column_frame(content)
        self._grid_check(
            hotspot_switches, "Enable hotspots", self.hotspots_enabled, 0, 0
        )
        self._grid_check(
            hotspot_switches, "Only pristine", self.only_pristine, 0, 1
        )

        hotspot_options = self._two_column_frame(content)
        hotspot_options.pack_configure(pady=(4, 3))
        self._small_label(hotspot_options, "Ring types").grid(
            row=0, column=0, sticky="w", pady=(0, 1)
        )
        self._small_label(hotspot_options, "Commodities").grid(
            row=0, column=1, sticky="w", pady=(0, 1)
        )

        ring_types = (
            ("icy", "Icy"),
            ("metallic", "Metallic"),
            ("metal rich", "Metal Rich"),
            ("rocky", "Rocky"),
        )
        commodities = (
            ("platinum", "Platinum"),
            ("bromellite", "Bromellite"),
            ("monazite", "Monazite"),
        )
        for row, (key, label) in enumerate(ring_types, 1):
            self._grid_check(
                hotspot_options, label, self.ring_vars[key], row, 0
            )
        for row, (key, label) in enumerate(commodities, 1):
            self._grid_check(
                hotspot_options, label, self.material_vars[key], row, 1
            )

        tk.Label(
            content,
            text="PLANETS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(7, 3))

        planet_switches = self._two_column_frame(content)
        self._grid_check(
            planet_switches, "Enable planets", self.planets_enabled, 0, 0
        )
        self._grid_check(
            planet_switches, "Only landables", self.only_landables, 0, 1
        )

        planet_types = self._two_column_frame(content)
        planet_types.pack_configure(pady=(4, 0))
        self._small_label(planet_types, "Planet types").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 1)
        )

        for row, (key, label) in enumerate((
            ("metal rich", "Metal Rich"),
            ("high metal content", "High Metal Content"),
            ("rocky", "Rocky"),
        ), 1):
            self._grid_check(
                planet_types, label, self.planet_type_vars[key], row, 0
            )

        for row, (key, label) in enumerate((
            ("rocky ice", "Rocky Ice"),
            ("icy", "Icy"),
        ), 1):
            self._grid_check(
                planet_types, label, self.planet_type_vars[key], row, 1
            )

        tk.Label(
            content,
            text="RESULTS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(7, 2))

        result_row = self._two_column_frame(content)
        self._grid_check(
            result_row, "Only positive results", self.only_positive, 0, 0
        )

        tk.Label(
            content,
            text="COMMUNITY DEPOSITS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(7, 2))

        community_row = self._two_column_frame(content)
        self._grid_check(
            community_row,
            "Show Community Deposits",
            self.community_deposits_enabled,
            0,
            0,
        )

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
        # block, then place Clear Filters beside Clear Systems.
        FinderV8App._build_systems(self, parent)

        button_row = None
        clear_systems_button = None
        for child in parent.winfo_children():
            if not isinstance(child, tk.Frame):
                continue
            for widget in child.winfo_children():
                if isinstance(widget, tk.Button) and widget.cget("text") == "Clear":
                    button_row = child
                    clear_systems_button = widget
                    break
            if clear_systems_button is not None:
                break

        if clear_systems_button is not None:
            clear_systems_button.configure(text="Clear Systems", padx=8)

        if button_row is not None:
            tk.Button(
                button_row,
                text="Clear Filters",
                command=self._clear_scan_filters,
                bg="#3a4148",
                fg=COLORS["text"],
                activebackground="#46515c",
                activeforeground=COLORS["text"],
                relief="flat",
                padx=8,
            ).pack(side="left", padx=(6, 0))

    def _build_system_filters(self, parent):
        # Give Faction/Power a compact fixed width so Reference System and
        # Max Distance always remain fully visible inside the left panel.
        tk.Label(
            parent,
            text="SYSTEM FILTERS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(4, 2))

        columns = tk.Frame(parent, bg=COLORS["panel"])
        columns.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        columns.columnconfigure(0, weight=0, minsize=SYSTEM_FILTER_LEFT_WIDTH)
        columns.columnconfigure(1, weight=0, minsize=SYSTEM_FILTER_REFERENCE_WIDTH)
        columns.rowconfigure(0, weight=1)

        left_col = tk.Frame(
            columns,
            bg=COLORS["panel"],
            width=SYSTEM_FILTER_LEFT_WIDTH,
        )
        reference_col = tk.Frame(
            columns,
            bg=COLORS["panel"],
            width=SYSTEM_FILTER_REFERENCE_WIDTH,
        )
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        reference_col.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        left_col.grid_propagate(False)
        reference_col.grid_propagate(False)

        self._small_label(left_col, "Faction").pack(anchor="w")
        tk.Entry(
            left_col,
            textvariable=self.faction_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="x", pady=(1, 4), ipady=3)

        self._small_label(left_col, "Power").pack(anchor="w")
        ttk.Combobox(
            left_col,
            textvariable=self.power_var,
            values=[""] + list(legacy_engine.POWER_LIST),
            state="readonly",
        ).pack(fill="x", pady=(1, 3))

        self._small_label(left_col, "Power states").pack(
            anchor="w", pady=(0, 0)
        )
        state_grid = tk.Frame(left_col, bg=COLORS["panel"])
        state_grid.pack(fill="x")
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
        tk.Entry(
            reference_col,
            textvariable=self.reference_system_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="x", pady=(1, 8), ipady=3)

        self._small_label(reference_col, "Max distance (LY)").pack(anchor="w")
        tk.Entry(
            reference_col,
            textvariable=self.max_distance_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        ).pack(fill="x", pady=(1, 0), ipady=3)

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
