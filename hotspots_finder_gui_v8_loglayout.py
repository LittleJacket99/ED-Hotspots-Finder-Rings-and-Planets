#!/usr/bin/env python3

"""v8 feature test: resizable log overlay aligned with Results."""

import tkinter as tk

from hotspots_finder_gui_v8_expandresults import FinderV8ExpandResultsApp


DEFAULT_LOG_PANEL_HEIGHT = 190
MIN_LOG_PANEL_HEIGHT = 120
LOG_PANEL_GAP = 6
RESIZE_HANDLE_HEIGHT = 6


class FinderV8LogLayoutApp(FinderV8ExpandResultsApp):
    def __init__(self):
        self._log_panel_height = DEFAULT_LOG_PANEL_HEIGHT
        self._log_reposition_pending = False
        self._log_resize_start_y = None
        self._log_resize_start_height = None

        super().__init__()

        # The log floats over the Results area rather than taking layout space.
        self._log_panel.configure(
            highlightthickness=1,
            highlightbackground="#46515c",
        )

        self._log_resize_handle = tk.Frame(
            self._log_panel,
            bg="#46515c",
            height=RESIZE_HANDLE_HEIGHT,
            cursor="sb_v_double_arrow",
        )
        self._log_resize_handle.place(
            x=0,
            y=0,
            relwidth=1.0,
            height=RESIZE_HANDLE_HEIGHT,
        )
        self._log_resize_handle.lift()
        self._log_resize_handle.bind("<ButtonPress-1>", self._start_log_resize)
        self._log_resize_handle.bind("<B1-Motion>", self._drag_log_resize)
        self._log_resize_handle.bind("<ButtonRelease-1>", self._end_log_resize)

        self.bind("<Configure>", self._schedule_log_reposition, add="+")

    def _schedule_log_reposition(self, _event=None):
        if not getattr(self, "_log_visible", False):
            return
        if getattr(self, "_results_expanded", False):
            return
        if self._log_reposition_pending:
            return

        self._log_reposition_pending = True
        self.after_idle(self._reposition_log_panel)

    def _max_log_panel_height(self):
        """Largest height that still keeps the log inside the Results area."""
        try:
            self.update_idletasks()
            root_y = self.winfo_rooty()
            results_top = self._results_panel.winfo_rooty() - root_y
            bottom_y = self._bottom_bar.winfo_rooty() - root_y
            return max(
                MIN_LOG_PANEL_HEIGHT,
                bottom_y - results_top - LOG_PANEL_GAP,
            )
        except (AttributeError, tk.TclError):
            return DEFAULT_LOG_PANEL_HEIGHT

    def _reposition_log_panel(self):
        self._log_reposition_pending = False
        if not getattr(self, "_log_visible", False):
            return
        if getattr(self, "_results_expanded", False):
            return

        try:
            self.update_idletasks()

            root_x = self.winfo_rootx()
            root_y = self.winfo_rooty()

            results_x = self._results_panel.winfo_rootx() - root_x
            results_width = max(1, self._results_panel.winfo_width())
            bottom_y = self._bottom_bar.winfo_rooty() - root_y

            max_height = self._max_log_panel_height()
            panel_height = max(
                MIN_LOG_PANEL_HEIGHT,
                min(int(self._log_panel_height), max_height),
            )
            self._log_panel_height = panel_height
            panel_y = bottom_y - panel_height - LOG_PANEL_GAP

            # Float over the Results tab. Increasing the height therefore
            # covers more of Results instead of resizing the whole app.
            self._log_panel.place(
                x=results_x,
                y=panel_y,
                width=results_width,
                height=panel_height,
            )
            self._log_panel.lift()
            self._log_resize_handle.lift()
        except (AttributeError, tk.TclError):
            return

    def _start_log_resize(self, event):
        self._log_resize_start_y = event.y_root
        self._log_resize_start_height = int(self._log_panel_height)

    def _drag_log_resize(self, event):
        if self._log_resize_start_y is None:
            return
        if self._log_resize_start_height is None:
            return

        # Dragging the upper edge upward increases the overlay height.
        delta = self._log_resize_start_y - event.y_root
        requested = self._log_resize_start_height + delta
        self._log_panel_height = max(
            MIN_LOG_PANEL_HEIGHT,
            min(int(requested), self._max_log_panel_height()),
        )
        self._reposition_log_panel()

    def _end_log_resize(self, _event=None):
        self._log_resize_start_y = None
        self._log_resize_start_height = None

    def _show_log_panel(self):
        if self._results_expanded:
            return

        # Never let the parent pack-based layout consume application space.
        try:
            self._log_panel.pack_forget()
        except tk.TclError:
            pass
        self._log_panel.place_forget()

        self._log_visible = True
        self.log_details_button.configure(text="Hide Log Details")
        self._reposition_log_panel()
        self._log_text.see("end")

    def _hide_log_panel(self):
        try:
            self._log_panel.pack_forget()
        except tk.TclError:
            pass
        self._log_panel.place_forget()

        self._log_visible = False
        if hasattr(self, "log_details_button"):
            self.log_details_button.configure(text="Show Log Details")

    def _toggle_results_expansion(self):
        was_expanded = self._results_expanded
        log_was_visible = self._log_visible

        if not was_expanded and log_was_visible:
            # Parent keeps the logical state needed to restore the log later.
            self._log_panel.place_forget()

        super()._toggle_results_expansion()

        if was_expanded:
            # Parent restore uses pack(fill='x'); replace it with our overlay.
            try:
                self._log_panel.pack_forget()
            except tk.TclError:
                pass

            if self._log_was_visible_before_results_expand:
                self._log_visible = False
                self.after_idle(self._show_log_panel)


def main():
    app = FinderV8LogLayoutApp()
    app.mainloop()


if __name__ == "__main__":
    main()
