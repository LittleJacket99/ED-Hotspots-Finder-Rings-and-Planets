#!/usr/bin/env python3

"""v8 feature test: narrower log panel aligned with Results."""

import re
import tkinter as tk

from hotspots_finder_gui_v8_expandresults import FinderV8ExpandResultsApp


LOG_PANEL_HEIGHT = 190
LOG_PANEL_GAP = 6


class FinderV8LogLayoutApp(FinderV8ExpandResultsApp):
    def __init__(self):
        self._log_added_height = 0
        self._log_reposition_pending = False
        super().__init__()
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
            results_width = max(420, self._results_panel.winfo_width())

            bottom_y = self._bottom_bar.winfo_rooty() - root_y
            panel_y = max(0, bottom_y - LOG_PANEL_HEIGHT - LOG_PANEL_GAP)

            # Keep the log visually attached to the Results area rather than
            # spanning underneath Filters and Systems.
            self._log_panel.place(
                x=results_x,
                y=panel_y,
                width=results_width,
                height=LOG_PANEL_HEIGHT,
            )
            self._log_panel.lift()
        except (AttributeError, tk.TclError):
            return

    @staticmethod
    def _parse_geometry(geometry):
        match = re.match(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", geometry)
        if not match:
            return None
        return tuple(int(value) for value in match.groups())

    def _grow_for_log(self):
        self.update_idletasks()

        current_width = self.winfo_width()
        current_height = self.winfo_height()
        x = self.winfo_x()
        y = self.winfo_y()

        screen_height = self.winfo_screenheight()
        available_height = max(current_height, screen_height - max(y, 0) - 40)
        target_height = min(current_height + LOG_PANEL_HEIGHT + LOG_PANEL_GAP, available_height)
        added = max(0, target_height - current_height)

        if added:
            self.geometry(f"{current_width}x{target_height}+{x}+{y}")
            self._log_added_height = added
            self.update_idletasks()
        else:
            self._log_added_height = 0

    def _shrink_after_log(self):
        added = int(getattr(self, "_log_added_height", 0) or 0)
        self._log_added_height = 0
        if added <= 0:
            return

        self.update_idletasks()
        width = self.winfo_width()
        height = max(self.minsize()[1], self.winfo_height() - added)
        x = self.winfo_x()
        y = self.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.update_idletasks()

    def _show_log_panel(self):
        if self._results_expanded:
            return

        # The old implementation used pack(fill='x'), which consumed the full
        # application width and reduced the existing Results height. Instead,
        # grow the window and place the panel only under the Results column.
        try:
            self._log_panel.pack_forget()
        except tk.TclError:
            pass
        self._log_panel.place_forget()

        self._grow_for_log()
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

        self._shrink_after_log()

    def _toggle_results_expansion(self):
        was_expanded = self._results_expanded
        log_was_visible = self._log_visible

        if not was_expanded and log_was_visible:
            # Preserve the logical visible state so the parent implementation
            # knows it should restore the log later, but remove its placed UI
            # and the extra window height before maximizing Results.
            self._log_panel.place_forget()
            self._shrink_after_log()

        super()._toggle_results_expansion()

        if was_expanded:
            # Parent restore uses pack(fill='x'). Replace it immediately with
            # the narrow Results-aligned layout.
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
