#!/usr/bin/env python3

"""v8 feature test: fixed compact log overlay aligned right in Results."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import app_settings
import rhinospotter_sync_service
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

        # The final UI provides the shared System Filters panel. Keep this
        # layer decoupled so intermediate classes do not need a legacy title frame.
        refresh_filters = getattr(self, "_refresh_unified_system_filters_panel", None)
        if callable(refresh_filters):
            self.after_idle(refresh_filters)

        expand_button = getattr(self, "expand_results_button", None)
        if expand_button is not None:
            expand_button.bind(
                "<ButtonRelease-1>",
                self._schedule_unified_system_filters_refresh,
                add="+",
            )

    def _open_settings_dialog(self):
        """Extend the base Settings dialog with RhinoSpotter source details."""

        result = super()._open_settings_dialog()
        window = getattr(self, "_settings_window", None)
        if window is None:
            return result
        try:
            if not window.winfo_exists():
                return result
        except tk.TclError:
            return result

        self._enhance_rhino_settings_window(window)
        return result

    def _enhance_rhino_settings_window(self, window):
        """Update the RhinoSpotter panel for the current SQLite data layout."""

        rhino_panel = None
        for child in window.winfo_children():
            if not isinstance(child, tk.Frame):
                continue
            try:
                labels = [
                    widget
                    for widget in child.winfo_children()
                    if isinstance(widget, tk.Label)
                ]
            except tk.TclError:
                continue
            if any(
                str(label.cget("text") or "")
                == "RHINOSPOTTER / COMMUNITY DEPOSITS"
                for label in labels
            ):
                rhino_panel = child
                break

        if rhino_panel is None:
            return

        try:
            children = rhino_panel.winfo_children()
        except tk.TclError:
            return

        path_entry = next(
            (widget for widget in children if isinstance(widget, tk.Entry)),
            None,
        )
        browse_button = next(
            (
                widget
                for widget in children
                if isinstance(widget, tk.Button)
                and str(widget.cget("text") or "") == "Browse..."
            ),
            None,
        )
        auto_button = next(
            (
                widget
                for widget in children
                if isinstance(widget, tk.Button)
                and str(widget.cget("text") or "") == "Auto"
            ),
            None,
        )
        status_label = next(
            (
                widget
                for widget in children
                if isinstance(widget, tk.Label)
                and str(widget.cget("textvariable") or "")
            ),
            None,
        )
        helper_label = next(
            (
                widget
                for widget in children
                if isinstance(widget, tk.Label)
                and str(widget.cget("text") or "").startswith("Auto restores")
            ),
            None,
        )

        if path_entry is None or status_label is None:
            return

        if helper_label is not None:
            try:
                helper_label.configure(
                    text=(
                        "Auto uses %LOCALAPPDATA%\\RhinoSpotter and detects "
                        "db\\rhinospotter.db automatically. Legacy JSON cards "
                        "are still supported."
                    )
                )
            except tk.TclError:
                pass

        def set_status(text, color):
            try:
                variable_name = str(status_label.cget("textvariable") or "")
                if variable_name:
                    window.setvar(variable_name, text)
                else:
                    status_label.configure(text=text)
                status_label.configure(fg=color)
            except tk.TclError:
                pass

        def refresh_rhino_status(_event=None):
            text = str(path_entry.get() or "").strip()
            source = (
                Path(text).expanduser()
                if text
                else app_settings.default_rhinospotter_data_path()
            )
            try:
                info = rhinospotter_sync_service.inspect_source(source)
            except Exception:
                set_status("RhinoSpotter data source not detected", "#ff5f56")
                return

            source_label = (
                "SQLite database"
                if info.get("source_type") == "sqlite"
                else "Legacy JSON cards"
            )
            count = int(info.get("records_found", 0) or 0)
            set_status(
                f"{source_label} detected · {count} bookmarks",
                "#5acd57",
            )

        def browse_rhino():
            current_text = str(path_entry.get() or "").strip()
            current = (
                Path(current_text).expanduser()
                if current_text
                else app_settings.default_rhinospotter_data_path()
            )
            if current.is_dir():
                initial = current
            elif current.parent.is_dir():
                initial = current.parent
            else:
                initial = app_settings.default_rhinospotter_data_path().parent

            selected = filedialog.askdirectory(
                parent=window,
                title="Select RhinoSpotter data folder",
                initialdir=str(initial),
            )
            if selected:
                path_entry.delete(0, "end")
                path_entry.insert(0, selected)
                refresh_rhino_status()

        def use_auto_rhino():
            path_entry.delete(0, "end")
            path_entry.insert(
                0,
                str(app_settings.default_rhinospotter_data_path()),
            )
            refresh_rhino_status()

        try:
            path_entry.bind("<KeyRelease>", refresh_rhino_status)
            path_entry.bind("<FocusOut>", refresh_rhino_status)
            if browse_button is not None:
                browse_button.configure(command=browse_rhino)
            if auto_button is not None:
                auto_button.configure(command=use_auto_rhino)
        except tk.TclError:
            pass

        refresh_rhino_status()

    def _schedule_unified_system_filters_refresh(self, _event=None):
        refresh_filters = getattr(self, "_refresh_unified_system_filters_panel", None)
        if callable(refresh_filters):
            self.after_idle(refresh_filters)

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
