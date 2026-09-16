#!/usr/bin/env python3

"""v8 layout based on the user's latest wireframe."""

import tkinter as tk

from hotspots_finder_gui_v8 import COLORS
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


class FinderV8Layout2App(BasePolishApp):
    def _build_results_options_box(self, parent):
        """Only-positive results was removed from the v8 interface."""
        return None

    def _build_ui(self):
        super()._build_ui()

        # The obsolete RESULTS options frame is never used in this layout.
        self._results_options_box.place_forget()

        # Apply the exact geometry from layout (5).json.
        for attr, (x, y, width, height) in LAYOUT.items():
            getattr(self, attr).place(x=x, y=y, width=width, height=height)

        self._rename_filter_labels()
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
