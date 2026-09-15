#!/usr/bin/env python3

"""v8 feature test: expand/collapse panels to maximize results."""

import tkinter as tk

from hotspots_finder_gui_v8_columnfilters import FinderV8ColumnFiltersApp
from hotspots_finder_gui_v8 import COLORS


class FinderV8ExpandResultsApp(FinderV8ColumnFiltersApp):
    def __init__(self):
        super().__init__()
        # Treat Community Deposits like Hotspots and Planets: enabled by default.
        self.community_deposits_enabled.set(True)

    def _build_filters(self, parent):
        super()._build_filters(parent)

        # Add a Clear button at the bottom of the existing scrollable filters
        # panel without changing the current layout yet.
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
