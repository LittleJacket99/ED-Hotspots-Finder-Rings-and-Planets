#!/usr/bin/env python3

"""v8 feature test: fixed compact log overlay aligned right in Results."""

import tkinter as tk

from hotspots_finder_gui_v8_expandresults import FinderV8ExpandResultsApp
from hotspots_finder_gui_v8_settings import FinderV8SettingsMixin


LOG_PANEL_HEIGHT = 400
LOG_PANEL_WIDTH_RATIO = 0.50
LOG_PANEL_MIN_WIDTH = 360
LOG_PANEL_GAP = 6


class FinderV8LogLayoutApp(FinderV8SettingsMixin, FinderV8ExpandResultsApp):
    def __init__(self):
        self._log_reposition_pending = False
        self._load_v8_settings_state()
        super().__init__()

        # Apply startup defaults only after all Tk variables in the complete
        # active GUI chain have been created.
        self._apply_startup_settings()
        self._build_settings_button()
        self.protocol("WM_DELETE_WINDOW", self._on_v8_close)

        # The log is a fixed-size overlay over the right side of Results.
        self._log_panel.configure(
            highlightthickness=1,
            highlightbackground="#46515c",
        )

        self.bind("<Configure>", self._schedule_log_reposition, add="+")

        # In the active layout the System Filters controls are separate frames
        # placed over the root stage. Reuse the title frame as one shared panel
        # behind them so the whole filter area reads visually as a single box.
        self.after_idle(self._refresh_unified_system_filters_panel)

        # Layout2 restores its original pixel geometry after Restore Panels.
        # Re-apply the shared System Filters background after the button command
        # has completed.
        expand_button = getattr(self, "expand_results_button", None)
        if expand_button is not None:
            expand_button.bind(
                "<ButtonRelease-1>",
                self._schedule_unified_system_filters_refresh,
                add="+",
            )

    def _schedule_unified_system_filters_refresh(self, _event=None):
        self.after_idle(self._refresh_unified_system_filters_panel)

    def _refresh_unified_system_filters_panel(self):
        if getattr(self, "_results_expanded", False):
            return

        title_box = getattr(self, "_system_filters_title_box", None)
        if title_box is None:
            return

        boxes = [
            getattr(self, name, None)
            for name in (
                "_system_filters_title_box",
                "_faction_box",
                "_power_box",
                "_power_states_box",
                "_reference_box",
                "_distance_box",
            )
        ]
        boxes = [box for box in boxes if box is not None]
        if not boxes:
            return

        try:
            left = min(box.winfo_x() for box in boxes)
            top = min(box.winfo_y() for box in boxes)
            right = max(box.winfo_x() + box.winfo_width() for box in boxes)
            bottom = max(box.winfo_y() + box.winfo_height() for box in boxes)

            title_box.place(
                x=left,
                y=top,
                width=max(1, right - left),
                height=max(1, bottom - top),
            )
            title_box.lower()

            # Keep the actual controls above the shared background panel.
            for box in boxes[1:]:
                box.lift()
        except tk.TclError:
            return

    def _scan_complete(self, result):
        super()._scan_complete(result)

        # Layout2 performs a final pass that keeps columns scrollable but also
        # applies generous fallback widths. Run one final content fit after the
        # complete scan chain returns, including the Systems result tab.
        self.after_idle(self._autofit_all_result_columns)

    def _set_community_results(self, headers, rows):
        super()._set_community_results(headers, rows)
        self.after_idle(self._autofit_all_result_columns)

    def _autofit_all_result_columns(self):
        trees = []
        for name in (
            "hotspot_tree",
            "planet_tree",
            "community_tree",
            "systems_result_tree",
        ):
            tree = getattr(self, name, None)
            if tree is not None:
                trees.append(tree)

        for tree in trees:
            try:
                columns = list(tree["columns"])
            except tk.TclError:
                continue

            for column in columns:
                try:
                    # Use the existing content-aware autosizer so headings,
                    # filter markers and actual values all contribute to width.
                    self._autosize_single_column(tree, column)
                    tree.heading(column, anchor="w")
                except (AttributeError, tk.TclError, TypeError, ValueError):
                    continue

            try:
                tree.xview_moveto(0)
            except tk.TclError:
                pass

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
            results_y = self._results_panel.winfo_rooty() - root_y
            results_width = max(1, self._results_panel.winfo_width())
            bottom_y = self._bottom_bar.winfo_rooty() - root_y

            panel_width = min(
                results_width,
                max(LOG_PANEL_MIN_WIDTH, int(results_width * LOG_PANEL_WIDTH_RATIO)),
            )

            available_height = max(1, bottom_y - results_y - LOG_PANEL_GAP)
            panel_height = min(LOG_PANEL_HEIGHT, available_height)

            # Keep the overlay flush with the right edge of Results.
            panel_x = results_x + results_width - panel_width
            panel_y = bottom_y - panel_height - LOG_PANEL_GAP

            self._log_panel.place(
                x=panel_x,
                y=panel_y,
                width=panel_width,
                height=panel_height,
            )
            self._log_panel.lift()
        except (AttributeError, tk.TclError):
            return

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
