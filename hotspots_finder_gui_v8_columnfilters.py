#!/usr/bin/env python3

"""v8 feature test: filters directly in result-table column headers."""

import tkinter as tk

from hotspots_finder_gui_v8_community import FinderV8CommunityApp


FILTER_COLUMNS = {
    "community": (
        "System",
        "Body",
        "Commodity",
        "Rigs",
        "Amount",
        "Density",
    ),
    "planets": (
        "System",
        "Status",
        "Planet Type",
        "Landable",
        "Volcanism",
    ),
    "hotspots": (
        "System",
        "Status",
        "Body",
        "Ring Type",
        "Reserve Level",
        "Commodity",
    ),
}


class FinderV8ColumnFiltersApp(FinderV8CommunityApp):
    def _build_ui(self):
        self._column_filter_rows = {}
        self._column_filter_headers = {}
        self._column_filter_state = {
            table: {column: None for column in columns}
            for table, columns in FILTER_COLUMNS.items()
        }
        super()._build_ui()

    def _build_results(self, parent):
        super()._build_results(parent)

        # The old temporary Body/Commodity combobox bar is no longer needed.
        children = self.community_tab.winfo_children()
        if children:
            children[0].pack_forget()

        self._table_trees = {
            "hotspots": self.hotspot_tree,
            "planets": self.planet_tree,
            "community": self.community_tree,
        }

    def _scan_complete(self, result):
        # Display terminology: hotspot "Material" becomes "Commodity".
        mapped = dict(result)
        hotspot_headers = [
            "Commodity" if header == "Material" else header
            for header in result.get("hotspot_headers", [])
        ]
        hotspot_rows = []
        for source in result.get("hotspot_rows", []):
            row = dict(source)
            if "Material" in row:
                row["Commodity"] = row.pop("Material")
            hotspot_rows.append(row)

        mapped["hotspot_headers"] = hotspot_headers
        mapped["hotspot_rows"] = hotspot_rows

        super()._scan_complete(mapped)

        self._set_filter_dataset(
            "hotspots",
            hotspot_headers,
            hotspot_rows,
        )
        self._set_filter_dataset(
            "planets",
            mapped.get("planet_headers", []),
            mapped.get("planet_rows", []),
        )

    def _set_community_results(self, headers, rows):
        # Keep the already-tested Community Deposits storage/upload behavior.
        super()._set_community_results(headers, rows)
        if hasattr(self, "_table_trees"):
            self._set_filter_dataset("community", headers, rows)

    def _set_filter_dataset(self, table, headers, rows):
        headers = list(headers or [])
        rows = [dict(row) for row in (rows or [])]

        self._column_filter_headers[table] = headers
        self._column_filter_rows[table] = self._effective_rows(table, rows)
        self._column_filter_state[table] = {
            column: None for column in FILTER_COLUMNS[table]
        }
        self._render_filtered_table(table)

    def _effective_rows(self, table, rows):
        """Restore repeated values hidden by the compact result display.

        The underlying v8 result tables blank repeated System/Status/ring data
        for readability. Filters need the logical value on every row, so we
        forward-fill those values internally and compact them again only when
        rendering the filtered result.
        """

        if table == "community":
            return rows

        if table == "planets":
            fill_columns = ("System", "Status")
        else:
            fill_columns = (
                "System",
                "Status",
                "Body",
                "Ring",
                "Ring Type",
                "Reserve Level",
                "LS Distance",
            )

        effective = []
        context = {}
        for source in rows:
            row = dict(source)

            # A visible System starts a new logical group. Do not allow ring or
            # planet values from the previous system to leak into the new one.
            if str(row.get("System", "")).strip():
                context = {}

            for column in fill_columns:
                value = row.get(column, "")
                if value not in (None, ""):
                    context[column] = value
                elif column in context:
                    row[column] = context[column]

            effective.append(row)

        return effective

    @staticmethod
    def _filter_value(value):
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _filter_label(value):
        return "(Blank)" if value == "" else value

    def _row_matches(self, table, row, *, skip_column=None):
        for column, selected in self._column_filter_state[table].items():
            if column == skip_column or selected is None:
                continue
            if self._filter_value(row.get(column, "")) != selected:
                return False
        return True

    def _choices_for_column(self, table, column):
        values = {
            self._filter_value(row.get(column, ""))
            for row in self._column_filter_rows.get(table, [])
            if self._row_matches(table, row, skip_column=column)
        }
        return sorted(
            values,
            key=lambda value: (value != "", value.casefold()),
        )

    def _render_filtered_table(self, table):
        tree = self._table_trees[table]
        rows = [
            row for row in self._column_filter_rows.get(table, [])
            if self._row_matches(table, row)
        ]

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

    @staticmethod
    def _compact_planet_rows(rows):
        result = []
        previous_system = None

        for source in rows:
            row = dict(source)
            system = row.get("System", "")
            if system == previous_system:
                row["System"] = ""
                row["Status"] = ""
            else:
                previous_system = system
            result.append(row)

        return result

    @staticmethod
    def _compact_hotspot_rows(rows):
        result = []
        previous_system = None
        previous_ring_key = None

        for source in rows:
            row = dict(source)
            system = row.get("System", "")
            body = row.get("Body", "")
            ring = row.get("Ring", "")
            ring_key = (system, body, ring)

            if system == previous_system:
                row["System"] = ""
            else:
                previous_system = system
                previous_ring_key = None

            if ring and ring_key == previous_ring_key:
                for column in (
                    "Status",
                    "Body",
                    "Ring",
                    "Ring Type",
                    "Reserve Level",
                    "LS Distance",
                ):
                    row[column] = ""
            elif ring:
                previous_ring_key = ring_key

            result.append(row)

        return result

    def _configure_filter_headings(self, table):
        tree = self._table_trees[table]
        filterable = set(FILTER_COLUMNS[table])

        for column in self._column_filter_headers.get(table, []):
            if column in filterable:
                active = self._column_filter_state[table].get(column) is not None
                marker = " ▼*" if active else " ▼"
                tree.heading(
                    column,
                    text=column + marker,
                    command=lambda t=table, c=column: self._show_column_filter(t, c),
                )
            else:
                tree.heading(
                    column,
                    text=column,
                    command=lambda c=column, tr=tree: self._sort_tree(tr, c, False),
                )

    def _show_column_filter(self, table, column):
        tree = self._table_trees[table]
        selected = self._column_filter_state[table].get(column)
        choices = self._choices_for_column(table, column)

        menu = tk.Menu(self, tearoff=False)
        menu.add_command(
            label="Sort A → Z",
            command=lambda: self._sort_tree(tree, column, False),
        )
        menu.add_command(
            label="Sort Z → A",
            command=lambda: self._sort_tree(tree, column, True),
        )
        menu.add_separator()

        all_label = "✓ All" if selected is None else "All"
        menu.add_command(
            label=all_label,
            command=lambda: self._set_column_filter(table, column, None),
        )
        menu.add_separator()

        for index, value in enumerate(choices):
            label = self._filter_label(value)
            if value == selected:
                label = "✓ " + label
            menu.add_command(
                label=label,
                columnbreak=(index > 0 and index % 28 == 0),
                command=lambda v=value: self._set_column_filter(table, column, v),
            )

        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _set_column_filter(self, table, column, value):
        self._column_filter_state[table][column] = value
        self._render_filtered_table(table)


def main():
    app = FinderV8ColumnFiltersApp()
    app.mainloop()


if __name__ == "__main__":
    main()
