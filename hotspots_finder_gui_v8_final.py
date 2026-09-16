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
    """Mask the platform Results bevel and draw one crisp 1 px outline."""

    RESULTS_OUTLINE = "#59616b"
    RESULTS_OUTLINE_THICKNESS = 1
    RESULTS_NATIVE_MASK = 3

    def _configure_styles(self):
        super()._configure_styles()

        # The visible light top/left edge comes from the Notebook client element,
        # not from the Treeview. Neutralise every native relief colour here.
        style = ttk.Style(self)
        style.configure(
            "FlatResults.TNotebook",
            background=THEME["field"],
            bordercolor=THEME["field"],
            lightcolor=THEME["field"],
            darkcolor=THEME["field"],
            relief="flat",
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )

    def _build_ui(self):
        super()._build_ui()
        self.after_idle(self._install_results_outline)

    def _install_results_outline(self):
        """Hide ttk's native bevel, then draw one explicit 1 px border."""

        notebook = getattr(self, "notebook", None)
        panel = getattr(self, "_results_panel", None)
        if notebook is None or panel is None:
            return

        if getattr(self, "_results_outline_lines", None):
            self._sync_results_outline()
            return

        try:
            # First cover the platform bevel itself. These strips sit just inside
            # the notebook edge and use the content background, so the old 2/3 px
            # light edge disappears instead of being stacked under our outline.
            self._results_outline_masks = [
                tk.Frame(
                    panel,
                    bg=THEME["field"],
                    bd=0,
                    highlightthickness=0,
                )
                for _ in range(4)
            ]
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
        masks = getattr(self, "_results_outline_masks", None)
        lines = getattr(self, "_results_outline_lines", None)
        if (
            notebook is None
            or not masks
            or len(masks) != 4
            or not lines
            or len(lines) != 4
        ):
            return

        try:
            if not notebook.winfo_exists() or not notebook.winfo_ismapped():
                for widget in (*masks, *lines):
                    widget.place_forget()
                return

            x = notebook.winfo_x()
            y = notebook.winfo_y()
            width = notebook.winfo_width()
            height = notebook.winfo_height()
            t = self.RESULTS_OUTLINE_THICKNESS
            m = self.RESULTS_NATIVE_MASK
            if width <= m * 2 or height <= m * 2:
                return

            # Cover only the native border area just inside the notebook bounds.
            mask_positions = (
                (x, y, width, m),
                (x, y + height - m, width, m),
                (x, y, m, height),
                (x + width - m, y, m, height),
            )
            for mask, (lx, ly, lw, lh) in zip(masks, mask_positions):
                mask.place(x=lx, y=ly, width=lw, height=lh)
                mask.lift()

            # Then place one single-pixel outline on top.
            line_positions = (
                (x, y, width, t),
                (x, y + height - t, width, t),
                (x, y, t, height),
                (x + width - t, y, t, height),
            )
            for line, (lx, ly, lw, lh) in zip(lines, line_positions):
                line.place(x=lx, y=ly, width=lw, height=lh)
                line.lift()
        except tk.TclError:
            pass


def main():
    app = FinderV8FinalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
