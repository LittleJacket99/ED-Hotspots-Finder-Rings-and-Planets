#!/usr/bin/env python3

"""v8 feature test: expand/collapse panels to maximize results."""

import tkinter as tk

from hotspots_finder_gui_v8_columnfilters import FinderV8ColumnFiltersApp
from hotspots_finder_gui_v8 import COLORS


DISTANCE_COLUMN = "Distance (LY)"


class FinderV8ExpandResultsApp(FinderV8ColumnFiltersApp):
    def __init__(self):
        super().__init__()
        # Treat Community Deposits like Hotspots and Planets: enabled by default.
        self.community_deposits_enabled.set(True)

    def _build_ui(self):
        self.reference_system_var = tk.StringVar(master=self, value="")
        self.max_distance_var = tk.StringVar(master=self, value="50")
        self._distance_sort_state = {
            "hotspots": None,
            "planets": None,
            "community": None,
        }
        super()._build_ui()

    def _build_filters(self, parent):
        super()._build_filters(parent)

        # Add Reference System / Max Distance beneath the existing Faction,
        # Power and Power State controls. Layout will be reorganized later.
        canvas = next(
            (
                child
                for child in parent.winfo_children()
                if isinstance(child, tk.Canvas)
            ),
            None,
        )
        if canvas is None:
            return

        children = canvas.winfo_children()
        if not children:
            return

        inner = children[0]

        tk.Label(
            inner,
            text="Reference system",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=12, pady=(2, 0))

        reference_entry = tk.Entry(
            inner,
            textvariable=self.reference_system_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        )
        reference_entry.pack(fill="x", padx=12, pady=(2, 8), ipady=5)

        tk.Label(
            inner,
            text="Max distance (LY)",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=12)

        max_distance_entry = tk.Entry(
            inner,
            textvariable=self.max_distance_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        )
        max_distance_entry.pack(fill="x", padx=12, pady=(2, 8), ipady=5)

        buttons = tk.Frame(inner, bg=COLORS["panel"])
        buttons.pack(fill="x", padx=12, pady=(2, 12))

        tk.Button(
            buttons,
            text="Clear",
            command=self._clear_scan_filters,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            relief="flat",
            padx=12,
        ).pack(side="left")

    def _collect_config(self):
        config = super()._collect_config()

        max_distance = self.max_distance_var.get().strip()
        if not max_distance:
            max_distance = "50"
            self.max_distance_var.set(max_distance)

        config["reference_system"] = self.reference_system_var.get().strip()
        config["max_distance_ly"] = max_distance
        return config

    def _clear_scan_filters(self):
        # Keep the feature switches unchanged: Enable hotspots,
        # Enable planets and Show Community Deposits.
        for variables in (
            self.ring_vars,
            self.material_vars,
            self.planet_type_vars,
            self.power_state_vars,
        ):
            for variable in variables.values():
                variable.set(False)

        self.only_pristine.set(False)
        self.only_landables.set(False)
        self.only_positive.set(False)
        self.faction_var.set("")
        self.power_var.set("")
        self.reference_system_var.set("")
        self.max_distance_var.set("50")

    @staticmethod
    def _move_distance_before_system(headers):
        headers = list(headers or [])
        if DISTANCE_COLUMN not in headers:
            return headers

        headers.remove(DISTANCE_COLUMN)
        try:
            system_index = headers.index("System")
        except ValueError:
            headers.insert(0, DISTANCE_COLUMN)
        else:
            headers.insert(system_index, DISTANCE_COLUMN)
        return headers

    def _scan_complete(self, result):
        # Keep Distance immediately before System in all result tabs.
        mapped = dict(result)
        for key in (
            "hotspot_headers",
            "planet_headers",
            "community_headers",
        ):
            mapped[key] = self._move_distance_before_system(
                result.get(key, [])
            )

        super()._scan_complete(mapped)

    def _set_filter_dataset(self, table, headers, rows):
        # A new result set that contains distances starts nearest-first.
        if DISTANCE_COLUMN in list(headers or []):
            self._distance_sort_state[table] = "asc"
        else:
            self._distance_sort_state[table] = None
        super()._set_filter_dataset(table, headers, rows)

    @staticmethod
    def _numeric_distance(row):
        value = row.get(DISTANCE_COLUMN, "")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _sort_rows_by_distance(self, table, rows):
        direction = self._distance_sort_state.get(table)
        if direction not in ("asc", "desc"):
            return rows

        with_distance = []
        without_distance = []
        for row in rows:
            distance = self._numeric_distance(row)
            if distance is None:
                without_distance.append(row)
            else:
                with_distance.append((distance, row))

        with_distance.sort(
            key=lambda item: item[0],
            reverse=(direction == "desc"),
        )
        return [row for _distance, row in with_distance] + without_distance

    def _render_filtered_table(self, table):
        tree = self._table_trees[table]
        rows = [
            row for row in self._column_filter_rows.get(table, [])
            if self._row_matches(table, row)
        ]
        rows = self._sort_rows_by_distance(table, rows)

        if table == "hotspots":
            display_rows = self._compact_hotspot_rows(rows)
        elif table == "planets":
            display_rows = self._compact_planet_rows(rows)
        else:
            display_rows = rows

        self._populate_tree(
            tree,
            self._column_filter_headers.get(table, []),
            display_rows,
        )
        self._configure_filter_headings(table)

    def _configure_filter_headings(self, table):
        super()._configure_filter_headings(table)

        headers = self._column_filter_headers.get(table, [])
        if DISTANCE_COLUMN not in headers:
            return

        direction = self._distance_sort_state.get(table) or "asc"
        marker = " ▲" if direction == "asc" else " ▼"
        tree = self._table_trees[table]
        tree.heading(
            DISTANCE_COLUMN,
            text=DISTANCE_COLUMN + marker,
            command=lambda t=table: self._toggle_distance_sort(t),
        )

    def _toggle_distance_sort(self, table):
        current = self._distance_sort_state.get(table)
        self._distance_sort_state[table] = (
            "desc" if current == "asc" else "asc"
        )
        self._render_filtered_table(table)

    def _autosize_single_column(self, tree, column, rows=None):
        super()._autosize_single_column(tree, column, rows=rows)
        if column == DISTANCE_COLUMN:
            try:
                current_width = int(tree.column(column, "width"))
                tree.column(column, width=current_width + 18)
            except (tk.TclError, TypeError, ValueError):
                pass

    def _build_results(self, parent):
        super()._build_results(parent)

        self._results_panel = parent
        self._results_expanded = False
        self._saved_sashes = None

        self.expand_results_button = tk.Button(
            parent,
            text="Expand Results",
            command=self._toggle_results_expansion,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            relief="flat",
            padx=10,
            pady=3,
        )
        self.expand_results_button.place(relx=1.0, x=-14, y=8, anchor="ne")

    def _build_bottom_bar(self):
        """Build the normal SCAN/STOP bar and keep a reference to it."""
        before = set(self.winfo_children())
        super()._build_bottom_bar()
        created = [child for child in self.winfo_children() if child not in before]
        self._bottom_bar = created[-1] if created else None

    def _toggle_results_expansion(self):
        try:
            paned = self._results_panel.master
            panes = list(paned.panes())
            if len(panes) < 3:
                return

            left_panel = panes[0]
            systems_panel = panes[1]

            if not self._results_expanded:
                try:
                    self._saved_sashes = (
                        paned.sash_coord(0)[0],
                        paned.sash_coord(1)[0],
                    )
                except tk.TclError:
                    self._saved_sashes = None

                # Horizontal expansion: hide Filters and Systems.
                paned.paneconfigure(left_panel, hide=True)
                paned.paneconfigure(systems_panel, hide=True)

                # Vertical expansion: remove the SCAN / STOP / status bar.
                if getattr(self, "_bottom_bar", None) is not None:
                    self._bottom_bar.pack_forget()

                self._results_expanded = True
                self.expand_results_button.configure(text="Restore Panels")
            else:
                paned.paneconfigure(left_panel, hide=False)
                paned.paneconfigure(systems_panel, hide=False)

                if getattr(self, "_bottom_bar", None) is not None:
                    self._bottom_bar.pack(fill="x", side="bottom")

                self._results_expanded = False
                self.expand_results_button.configure(text="Expand Results")

                if self._saved_sashes:
                    first_x, second_x = self._saved_sashes

                    def _restore_sashes():
                        try:
                            paned.sash_place(0, first_x, 0)
                            paned.sash_place(1, second_x, 0)
                        except tk.TclError:
                            pass

                    self.after_idle(_restore_sashes)

        except (AttributeError, tk.TclError):
            return


def main():
    app = FinderV8ExpandResultsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
