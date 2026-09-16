#!/usr/bin/env python3

"""Final v8 UI entry point.

The previous final visual layer is preserved in
``hotspots_finder_gui_v8_final_base.py``.  This thin top layer only fixes the
remaining native ttk notebook outline around the Results area.
"""

import tkinter as tk
from tkinter import ttk

from hotspots_finder_gui_v8_final_base import FinderV8FinalApp as _BaseFinalApp
from hotspots_finder_gui_v8_visual import THEME


class FinderV8FinalApp(_BaseFinalApp):
    """Cover the platform-specific Results bevel with one flat uniform outline."""

    RESULTS_OUTLINE = "#59616b"
    RESULTS_OUTLINE_THICKNESS = 1

    def _configure_styles(self):
        super()._configure_styles()

        # The visible light top/left edge comes from the Notebook client element,
        # not from the Treeview. Neutralise every native relief colour here.
        style = ttk.Style(self)
        style.configure(
            "FlatResults.TNotebook",
            background=THEME["field"],
            bordercolor=self.RESULTS_OUTLINE,
            lightcolor=self.RESULTS_OUTLINE,
            darkcolor=self.RESULTS_OUTLINE,
            relief="flat",
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )

    def _build_ui(self):
        super()._build_ui()
        self.after_idle(self._install_results_outline)

    def _install_results_outline(self):
        """Draw one explicit outline over ttk's platform-dependent notebook edge."""

        notebook = getattr(self, "notebook", None)
        panel = getattr(self, "_results_panel", None)
        if notebook is None or panel is None:
            return

        if getattr(self, "_results_outline_lines", None):
            self._sync_results_outline()
            return

        try:
            self._results_outline_lines = [
                tk.Frame(
                    panel,
                    bg=self.RESULTS_OUTLINE,
                    bd=0,
                    highlightthickness=0,
                )
                for _ in range(4)
            ]
        except tk.TclError:
            return

        notebook.bind(
            "<Configure>",
            lambda _event: self.after_idle(self._sync_results_outline),
            add="+",
        )
        notebook.bind(
            "<Map>",
            lambda _event: self.after_idle(self._sync_results_outline),
            add="+",
        )
        self.bind(
            "<Configure>",
            lambda _event: self.after_idle(self._sync_results_outline),
            add="+",
        )

        self._sync_results_outline()

    def _sync_results_outline(self):
        notebook = getattr(self, "notebook", None)
        lines = getattr(self, "_results_outline_lines", None)
        if notebook is None or not lines or len(lines) != 4:
            return

        try:
            if not notebook.winfo_exists() or not notebook.winfo_ismapped():
                for line in lines:
                    line.place_forget()
                return

            x = notebook.winfo_x()
            y = notebook.winfo_y()
            width = notebook.winfo_width()
            height = notebook.winfo_height()
            t = self.RESULTS_OUTLINE_THICKNESS
            if width <= t * 2 or height <= t * 2:
                return

            positions = (
                (x, y, width, t),
                (x, y + height - t, width, t),
                (x, y, t, height),
                (x + width - t, y, t, height),
            )
            for line, (lx, ly, lw, lh) in zip(lines, positions):
                line.place(x=lx, y=ly, width=lw, height=lh)
                line.lift()
        except tk.TclError:
            pass


def main():
    app = FinderV8FinalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
