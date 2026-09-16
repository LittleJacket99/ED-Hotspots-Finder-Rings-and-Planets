#!/usr/bin/env python3

"""v8 layout based on the user's latest wireframe."""

import threading
import tkinter as tk
from tkinter import messagebox

import community_deposits
import system_filter_search
from hotspots_finder_gui_v8 import APP_TITLE, COLORS
from hotspots_finder_gui_v8_polish import FinderV8PolishApp as BasePolishApp


LAYOUT = {
    "_hotspots_box": (18, 92, 250, 130),
    "_planets_box": (18, 232, 250, 130),
    "_community_box": (18, 372, 250, 140),
    "_systems_panel": (285, 92, 225, 420),
    "_system_filters_title_box": (18, 517, 160, 38),
    "_faction_box": (17, 560, 225, 55),
    "_power_box": (18, 620, 225, 55),
    "_power_states_box": (18, 680, 225, 70),
    "_reference_box": (285, 560, 225, 55),
    "_distance_box": (285, 620, 225, 55),
    "_results_panel": (525, 92, 815, 650),
}

CLEAR_BUTTON_Y = 520
CLEAR_BUTTON_WIDTH = 109
CLEAR_BUTTON_HEIGHT = 27
CLEAR_BUTTON_GAP = 7
DISTANCE_COLUMN = "Distance (LY)"


class FinderV8Layout2App(BasePolishApp):
    def _build_results_options_box(self, parent):
        """Only-positive results was removed from the v8 interface."""
        return None

    def _build_ui(self):
        self.database_load_running = False
        super()._build_ui()

        # The obsolete RESULTS options frame is never used in this layout.
        self._results_options_box.place_forget()

        # Apply the exact geometry from layout (5).json.
        for attr, (x, y, width, height) in LAYOUT.items():
            getattr(self, attr).place(x=x, y=y, width=width, height=height)

        self._rename_filter_labels()
        self._build_load_database_button()
        self._reflow_systems_contents()
        self._build_external_clear_buttons()

    def _rename_filter_labels(self):
        # Keep the internal Spansh filter value "high metal content" unchanged;
        # only shorten the visible label.
        for child in self._planets_box.winfo_children():
            if isinstance(child, tk.Checkbutton):
                if str(child.cget("text") or "") == "High Metal Content":
                    child.configure(text="HMC")

        for child in self._community_box.winfo_children():
            if isinstance(child, tk.Checkbutton):
                if str(child.cget("text") or "") == "Show Community Deposits":
                    child.configure(text="Enable Community Deposits")

    def _build_load_database_button(self):
        """Add a direct database browser action below RhinoSpotter upload."""
        self.load_database_button = tk.Button(
            self._community_box,
            text="Load Database Deposits",
            command=self.start_database_load,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            disabledforeground="#777777",
            relief="flat",
            padx=8,
            pady=2,
            font=("Segoe UI", 9),
        )
        self.load_database_button.place(x=7, y=94, width=170, height=30)

    def start_database_load(self):
        if self.database_load_running:
            return

        if self.running or self.rhino_upload_running:
            messagebox.showwarning(
                APP_TITLE,
                "Wait for the current scan or RhinoSpotter upload to finish.",
                parent=self,
            )
            return

        # Read Tk variables on the GUI thread, then hand only plain values to
        # the worker thread.
        config = self._collect_config()

        self.database_load_running = True
        self.load_database_button.configure(state="disabled")
        self.rhino_upload_button.configure(state="disabled")
        self.scan_button.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set("Loading database deposits...")

        threading.Thread(
            target=self._database_load_worker,
            args=(config,),
            daemon=True,
        ).start()

    @staticmethod
    def _database_system_key(value):
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def _filter_database_rows_by_systems(cls, rows, systems):
        allowed = {
            cls._database_system_key(system)
            for system in systems
            if str(system or "").strip()
        }
        return [
            row
            for row in rows
            if cls._database_system_key(row.get("System", "")) in allowed
        ]

    @classmethod
    def _add_database_distances(cls, headers, rows, distances):
        headers = [header for header in list(headers or []) if header != DISTANCE_COLUMN]
        try:
            system_index = headers.index("System")
        except ValueError:
            headers.insert(0, DISTANCE_COLUMN)
        else:
            headers.insert(system_index, DISTANCE_COLUMN)

        mapped_rows = []
        for source in rows:
            row = dict(source)
            distance = distances.get(cls._database_system_key(row.get("System", "")))
            if distance in (None, ""):
                row[DISTANCE_COLUMN] = ""
            else:
                try:
                    row[DISTANCE_COLUMN] = (
                        f"{float(distance):.2f}".rstrip("0").rstrip(".")
                    )
                except (TypeError, ValueError):
                    row[DISTANCE_COLUMN] = str(distance)
            mapped_rows.append(row)

        return headers, mapped_rows

    def _database_load_worker(self, config):
        try:
            headers, rows = community_deposits.fetch_all_deposits()

            faction_name = str(config.get("faction_name", "") or "").strip()
            power_name = str(config.get("power_name", "") or "").strip()
            manual_systems = list(config.get("systems", []) or [])
            reference_system = str(
                config.get("reference_system", "") or ""
            ).strip()

            selected_power_states = [
                state
                for state, enabled in dict(config.get("power_states", {})).items()
                if enabled
            ]

            # Match normal SCAN semantics: Faction / Power generate the system
            # set and replace any manually-entered SYSTEMS for this operation.
            if faction_name or power_name:
                max_distance_raw = str(
                    config.get("max_distance_ly", "50") or "50"
                ).strip()
                try:
                    max_distance_ly = float(max_distance_raw.replace(",", "."))
                except ValueError as exc:
                    raise ValueError("Max Distance (LY) must be a number.") from exc
                if max_distance_ly <= 0:
                    raise ValueError("Max Distance (LY) must be greater than 0.")

                systems, distances = system_filter_search.search_systems_by_filters(
                    faction_name,
                    power_name,
                    selected_power_states if power_name else [],
                    reference_system=reference_system,
                    max_distance_ly=max_distance_ly,
                    include_distances=True,
                )
                rows = self._filter_database_rows_by_systems(rows, systems)

                if reference_system:
                    headers, rows = self._add_database_distances(
                        headers,
                        rows,
                        distances,
                    )

            elif manual_systems:
                rows = self._filter_database_rows_by_systems(rows, manual_systems)

            # Reference System alone intentionally does not alter the database
            # load yet. We first reuse the same Reference behaviour as SCAN:
            # it constrains a Faction / Power generated search.

            self.after(0, self._database_load_complete, headers, rows)
        except Exception as exc:
            self.after(0, self._database_load_failed, str(exc))

    def _database_load_complete(self, headers, rows):
        try:
            self._autosize_next_populate.add(self.community_tree)
        except AttributeError:
            pass

        self._set_community_results(headers, rows)
        self.notebook.select(self.community_tab)
        self._finish_database_load(f"Loaded {len(rows)} database deposits")

    def _database_load_failed(self, message):
        if hasattr(self, "_append_log_line"):
            self._append_log_line("ERROR", f"Database load failed: {message}")
        self._finish_database_load("Database load error")
        messagebox.showerror(APP_TITLE, message, parent=self)

    def _finish_database_load(self, status):
        self.database_load_running = False
        self.progress.stop()
        self.load_database_button.configure(state="normal")
        self.rhino_upload_button.configure(state="normal")
        self.scan_button.configure(state="normal")
        self.status_var.set(status)

    def _collect_config(self):
        config = super()._collect_config()
        # Remove the obsolete results filter from the scan configuration too.
        config.pop("only_positive_results", None)
        return config

    def _reflow_systems_contents(self):
        """Fit Systems content inside the box, leaving Clear buttons outside."""
        for child in self._systems_panel.winfo_children():
            if isinstance(child, tk.Frame):
                # Systems text/list area.
                child.place_configure(x=9, y=52, width=207, height=300)
                continue

            if isinstance(child, tk.Button):
                # The original buttons belong to the Systems box. Hide them;
                # replacements are created directly on the main stage below it.
                child.place_forget()
                continue

            if isinstance(child, tk.Label):
                text = str(child.cget("text") or "")
                if text.startswith("If Faction or Power is set"):
                    child.place_configure(x=9, y=361, width=207, height=50)

    def _build_external_clear_buttons(self):
        x = LAYOUT["_systems_panel"][0]
        right_x = x + CLEAR_BUTTON_WIDTH + CLEAR_BUTTON_GAP

        # 109 + 7 + 109 = 225 px, exactly matching the Systems box width.
        self._external_clear_filters_button = tk.Button(
            self._stage,
            text="Clear Filters",
            command=self._clear_scan_filters,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            relief="flat",
            font=("Segoe UI", 8),
        )
        self._external_clear_filters_button.place(
            x=x,
            y=CLEAR_BUTTON_Y,
            width=CLEAR_BUTTON_WIDTH,
            height=CLEAR_BUTTON_HEIGHT,
        )

        self._external_clear_systems_button = tk.Button(
            self._stage,
            text="Clear Systems",
            command=self._clear_systems,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            relief="flat",
            font=("Segoe UI", 8),
        )
        self._external_clear_systems_button.place(
            x=right_x,
            y=CLEAR_BUTTON_Y,
            width=CLEAR_BUTTON_WIDTH,
            height=CLEAR_BUTTON_HEIGHT,
        )

    def _hide_external_clear_buttons(self):
        self._external_clear_systems_button.place_forget()
        self._external_clear_filters_button.place_forget()

    def _show_external_clear_buttons(self):
        x = LAYOUT["_systems_panel"][0]
        right_x = x + CLEAR_BUTTON_WIDTH + CLEAR_BUTTON_GAP

        self._external_clear_filters_button.place(
            x=x,
            y=CLEAR_BUTTON_Y,
            width=CLEAR_BUTTON_WIDTH,
            height=CLEAR_BUTTON_HEIGHT,
        )
        self._external_clear_systems_button.place(
            x=right_x,
            y=CLEAR_BUTTON_Y,
            width=CLEAR_BUTTON_WIDTH,
            height=CLEAR_BUTTON_HEIGHT,
        )

    def _toggle_results_expansion(self):
        if not self._results_expanded:
            self._log_was_visible_before_results_expand = self._log_visible
            if self._log_visible:
                self._log_panel.place_forget()

            for attr in (
                "_hotspots_box",
                "_planets_box",
                "_community_box",
                "_systems_panel",
                "_system_filters_title_box",
                "_faction_box",
                "_power_box",
                "_power_states_box",
                "_reference_box",
                "_distance_box",
            ):
                getattr(self, attr).place_forget()

            self._results_options_box.place_forget()
            self._hide_external_clear_buttons()
            self._results_panel.place(x=18, y=92, width=1322, height=650)

            if getattr(self, "_bottom_bar", None) is not None:
                self._bottom_bar.pack_forget()

            self._results_expanded = True
            self.expand_results_button.configure(text="Restore Panels")
            return

        for attr, (x, y, width, height) in LAYOUT.items():
            getattr(self, attr).place(x=x, y=y, width=width, height=height)

        self._results_options_box.place_forget()
        self._reflow_systems_contents()
        self._show_external_clear_buttons()

        if getattr(self, "_bottom_bar", None) is not None:
            self._bottom_bar.pack(fill="x", side="bottom")

        self._results_expanded = False
        self.expand_results_button.configure(text="Expand Results")

        if self._log_was_visible_before_results_expand:
            self._log_visible = False
            self.after_idle(self._show_log_panel)


def main():
    app = FinderV8Layout2App()
    app.mainloop()


if __name__ == "__main__":
    main()
