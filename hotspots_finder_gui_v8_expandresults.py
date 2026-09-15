#!/usr/bin/env python3

"""v8 feature test: expand/collapse side panels to maximize results."""

import tkinter as tk

from hotspots_finder_gui_v8_columnfilters import FinderV8ColumnFiltersApp
from hotspots_finder_gui_v8 import COLORS


class FinderV8ExpandResultsApp(FinderV8ColumnFiltersApp):
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

                paned.paneconfigure(left_panel, hide=True)
                paned.paneconfigure(systems_panel, hide=True)
                self._results_expanded = True
                self.expand_results_button.configure(text="Restore Panels")
            else:
                paned.paneconfigure(left_panel, hide=False)
                paned.paneconfigure(systems_panel, hide=False)
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
