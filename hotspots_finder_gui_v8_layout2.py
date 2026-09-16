#!/usr/bin/env python3

"""v8 layout based on the user's latest wireframe."""

import threading
import tkinter as tk
from tkinter import messagebox

from hotspots_finder_gui_v8 import APP_TITLE, COLORS
from hotspots_finder_gui_v8_polish import FinderV8PolishApp as BasePolishApp


LAYOUT = {
    "_hotspots_box": (18, 92, 250, 130),
    "_planets_box": (18, 232, 250, 130),
    "_community_box": (18, 372, 250, 195),
    "_systems_panel": (285, 92, 225, 420),
    "_system_filters_title_box": (18, 577, 160, 35),
    "_faction_box": (18, 620, 237, 55),
    "_power_box": (285, 620, 225, 55),
    "_power_states_box": (285, 680, 225, 70),
    "_reference_box": (18, 680, 142, 55),
    "_distance_box": (165, 680, 90, 55),
    "_results_panel": (525, 92, 815, 650),
}

CLEAR_BUTTON_Y = 520
CLEAR_BUTTON_WIDTH = 109
CLEAR_BUTTON_HEIGHT = 27
CLEAR_BUTTON_GAP = 7


class FinderV8Layout2App(BasePolishApp):
    def _build_results_options_box(self, parent):
        """Only-positive results was removed from the v8 interface."""
        return None

    def _build_ui(self):
        super()._build_ui()

        # The obsolete RESULTS options frame is never used in this layout.
        self._results_options_box.place_forget()

        for attr, (x, y, width, height) in LAYOUT.items():
            getattr(self, attr).place(x=x, y=y, width=width, height=height)

        self._rename_filter_labels()
        self._reflow_systems_contents()
        self._reflow_compact_reference_distance()
        self._build_external_clear_buttons()

    def _build_results(self, parent):
        super()._build_results(parent)

        # Fourth result tab: generated system lists live here. The Systems box
        # remains manual input only and is never used as an output container.
        self.systems_result_tab = tk.Frame(self.notebook, bg=COLORS["panel"])
        self.notebook.add(self.systems_result_tab, text="Systems")
        self.systems_result_tree = self._make_tree(self.systems_result_tab)

    def _rename_filter_labels(self):
        # Keep internal filter values unchanged; only change visible labels.
        for child in self._planets_box.winfo_children():
            if isinstance(child, tk.Checkbutton):
                if str(child.cget("text") or "") == "High Metal Content":
                    child.configure(text="HMC")

        for child in self._community_box.winfo_children():
            if isinstance(child, tk.Checkbutton):
                if str(child.cget("text") or "") == "Show Community Deposits":
                    child.configure(text="Enable Community Deposits")

        for child in self._systems_panel.winfo_children():
            if isinstance(child, tk.Label):
                if str(child.cget("text") or "") == "SYSTEMS":
                    child.configure(text="SYSTEM INPUT")

    def start_scan(self):
        """Start the unified SCAN flow with the new system-resolution rules."""
        if self.running:
            return

        config = self._collect_config()
        has_system_selector = bool(
            config.get("systems")
            or config.get("faction_name")
            or config.get("power_name")
            or config.get("reference_system")
        )
        hp_enabled = bool(
            config.get("hotspots_enabled") or config.get("planets_enabled")
        )
        community_enabled = bool(config.get("community_deposits_enabled"))

        if hp_enabled and not has_system_selector:
            messagebox.showwarning(
                APP_TITLE,
                "Hotspots/Planets require manual systems or a System Filter.",
                parent=self,
            )
            return

        if not hp_enabled and not community_enabled and not has_system_selector:
            messagebox.showwarning(
                APP_TITLE,
                "Add at least one manual system or set a System Filter.",
                parent=self,
            )
            return

        self.running = True
        self.cancel_event.clear()
        self.scan_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.rhino_upload_button.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set("Scanning...")

        threading.Thread(
            target=self._scan_worker,
            args=(config,),
            daemon=True,
        ).start()

    def _finish_scan(self, status):
        super()._finish_scan(status)
        if not self.rhino_upload_running:
            self.rhino_upload_button.configure(state="normal")

    def _scan_complete(self, result):
        super()._scan_complete(result)

        headers = list(result.get("system_headers", ["System"]) or ["System"])
        rows = list(result.get("system_rows", []) or [])
        self._populate_tree(self.systems_result_tree, headers, rows)

        # The Systems tab is deliberately a simple result table: direct clicks
        # sort System or Distance without adding another filter layer.
        for header in headers:
            self.systems_result_tree.heading(
                header,
                text=header,
                command=lambda h=header: self._sort_tree(
                    self.systems_result_tree,
                    h,
                    False,
                ),
            )

        if result.get("status") == "SYSTEM_LIST_READY":
            self.notebook.select(self.systems_result_tab)

    def _current_export_source(self):
        if self.notebook.select() == str(self.systems_result_tab):
            return "Systems", self.systems_result_tree
        return super()._current_export_source()

    def _reflow_systems_contents(self):
        """Fit manual Systems input inside the box, leaving Clear buttons outside."""
        for child in self._systems_panel.winfo_children():
            if isinstance(child, tk.Frame):
                child.place_configure(x=9, y=52, width=207, height=300)
                continue

            if isinstance(child, tk.Button):
                child.place_forget()
                continue

            if isinstance(child, tk.Label):
                text = str(child.cget("text") or "")
                if text.startswith("Optional manual input"):
                    child.place_configure(x=9, y=361, width=207, height=50)

    def _reflow_compact_reference_distance(self):
        """Fit Faction, Reference and Max Distance into layout (7) boxes."""
        for child in self._faction_box.winfo_children():
            if isinstance(child, tk.Entry):
                child.place_configure(x=4, y=22, width=229, height=27)

        for child in self._reference_box.winfo_children():
            if isinstance(child, tk.Entry):
                child.place_configure(x=4, y=22, width=134, height=27)

        for child in self._distance_box.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(text="Max LY")
                child.place_configure(x=4, y=3, width=82)
            elif isinstance(child, tk.Entry):
                child.place_configure(x=4, y=22, width=82, height=27)

    def _build_external_clear_buttons(self):
        x = LAYOUT["_systems_panel"][0]
        right_x = x + CLEAR_BUTTON_WIDTH + CLEAR_BUTTON_GAP

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
        self._reflow_compact_reference_distance()
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
