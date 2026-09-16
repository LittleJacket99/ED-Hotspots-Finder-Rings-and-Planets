#!/usr/bin/env python3

"""v8 layout based on the user's layout (2).json; Only positive is hidden for now."""

import tkinter as tk

from hotspots_finder_gui_v8_polish import FinderV8PolishApp as BasePolishApp


LAYOUT2 = {
    "_hotspots_box": (18, 92, 250, 130),
    "_planets_box": (18, 232, 250, 130),
    "_community_box": (18, 372, 250, 120),
    "_systems_panel": (285, 92, 225, 438),
    "_system_filters_title_box": (18, 502, 160, 38),
    "_faction_box": (17, 545, 225, 55),
    "_power_box": (18, 605, 225, 55),
    "_power_states_box": (18, 665, 225, 70),
    "_reference_box": (285, 605, 225, 55),
    "_distance_box": (285, 665, 225, 55),
    "_results_panel": (525, 92, 815, 650),
}


class FinderV8Layout2App(BasePolishApp):
    def _build_ui(self):
        super()._build_ui()

        # Keep the old logic variable available internally, but remove the
        # whole RESULTS / Only positive box from the interface for now.
        self.only_positive.set(False)
        self._results_options_box.place_forget()

        # Apply the exact geometry from layout (2).json to the remaining boxes.
        for attr, (x, y, width, height) in LAYOUT2.items():
            getattr(self, attr).place(x=x, y=y, width=width, height=height)

        self._reflow_systems_contents()

    def _reflow_systems_contents(self):
        """Fit the Systems controls cleanly inside the 225 x 438 model box."""
        for child in self._systems_panel.winfo_children():
            if isinstance(child, tk.Frame):
                # Text area frame.
                child.place_configure(x=9, y=52, width=207, height=290)
                continue

            if isinstance(child, tk.Button):
                text = str(child.cget("text") or "")
                if text == "Clear Systems":
                    child.place_configure(x=9, y=351, width=91, height=25)
                elif text == "Clear Filters":
                    child.place_configure(x=106, y=351, width=91, height=25)
                continue

            if isinstance(child, tk.Label):
                text = str(child.cget("text") or "")
                if text.startswith("If Faction or Power is set"):
                    child.place_configure(x=9, y=384, width=207, height=45)

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
            self._results_panel.place(x=18, y=92, width=1322, height=650)

            if getattr(self, "_bottom_bar", None) is not None:
                self._bottom_bar.pack_forget()

            self._results_expanded = True
            self.expand_results_button.configure(text="Restore Panels")
            return

        for attr, (x, y, width, height) in LAYOUT2.items():
            getattr(self, attr).place(x=x, y=y, width=width, height=height)

        # Stay hidden after restoring the normal layout.
        self._results_options_box.place_forget()
        self._reflow_systems_contents()

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
