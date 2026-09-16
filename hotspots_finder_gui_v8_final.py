#!/usr/bin/env python3

"""Final v8 UI entry point.

The previous final visual layer is preserved in
``hotspots_finder_gui_v8_final_base.py``. This thin top layer handles the
remaining visual overrides that should not depend on native Windows styling.
"""

import tkinter as tk
import webbrowser
from tkinter import ttk

from hotspots_finder_gui_v8_final_base import FinderV8FinalApp as _BaseFinalApp
from hotspots_finder_gui_v8_visual import THEME


MINERALS_TABLE_URL = "https://docs.google.com/spreadsheets/d/1SVTKW-Uy6sjjR0oFqKjCI5tDvYAu97ORmocXwl1ckU0/edit?gid=0#gid=0"
VOLCANISM_TABLE_URL = "https://wiknow.pages.dev/ref/ground-mining"


class FinderV8FinalApp(_BaseFinalApp):
    """Final visual overrides for Results and popup menus."""

    RESULTS_OUTLINE = "#59616b"
    RESULTS_OUTLINE_THICKNESS = 1
    RESULTS_NATIVE_MASK = 3

    MENU_BG = "#252a2f"
    MENU_HOVER = "#30363d"
    MENU_BORDER = "#59616b"
    MENU_TEXT = "#e8edf2"
    MENU_MUTED = "#939ba5"
    MENU_SEPARATOR = "#59616b"

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
        self._custom_popup = None
        super()._build_ui()
        self.after_idle(self._install_results_outline)

    # ------------------------------------------------------------------
    # Custom popup menus
    # ------------------------------------------------------------------
    def _dismiss_custom_popup(self, _event=None):
        popup = getattr(self, "_custom_popup", None)
        self._custom_popup = None
        if popup is None:
            return
        try:
            if popup.winfo_exists():
                popup.destroy()
        except tk.TclError:
            pass

    def _run_custom_popup_command(self, command):
        self._dismiss_custom_popup()
        if command is not None:
            self.after_idle(command)

    def _show_custom_popup(self, items, x_root, y_root, *, min_width=0):
        """Show a frameless popup with one flat 1 px application border."""

        self._dismiss_custom_popup()

        popup = tk.Toplevel(self)
        self._custom_popup = popup
        popup.overrideredirect(True)
        popup.configure(bg=self.MENU_BORDER)
        try:
            popup.transient(self)
        except tk.TclError:
            pass

        outer = tk.Frame(
            popup,
            bg=self.MENU_BORDER,
            bd=0,
            highlightthickness=0,
        )
        outer.pack(fill="both", expand=True)

        inner = tk.Frame(
            outer,
            bg=self.MENU_BG,
            bd=0,
            highlightthickness=0,
        )
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        for item in items:
            if item is None:
                tk.Frame(
                    inner,
                    bg=self.MENU_SEPARATOR,
                    bd=0,
                    highlightthickness=0,
                    height=1,
                ).pack(fill="x", padx=7, pady=4)
                continue

            label_text, command, enabled = item
            entry = tk.Label(
                inner,
                text=label_text,
                bg=self.MENU_BG,
                fg=self.MENU_TEXT if enabled else self.MENU_MUTED,
                activebackground=self.MENU_HOVER,
                activeforeground=self.MENU_TEXT,
                anchor="w",
                justify="left",
                padx=10,
                pady=5,
                bd=0,
                relief="flat",
                highlightthickness=0,
                font=("Segoe UI", 9),
                cursor="hand2" if enabled else "",
            )
            entry.pack(fill="x")

            if enabled:
                entry.bind(
                    "<Enter>",
                    lambda _event, widget=entry: widget.configure(
                        bg=self.MENU_HOVER
                    ),
                    add="+",
                )
                entry.bind(
                    "<Leave>",
                    lambda _event, widget=entry: widget.configure(
                        bg=self.MENU_BG
                    ),
                    add="+",
                )
                entry.bind(
                    "<ButtonRelease-1>",
                    lambda _event, callback=command: self._run_custom_popup_command(
                        callback
                    ),
                    add="+",
                )

        popup.update_idletasks()
        width = max(int(min_width), popup.winfo_reqwidth())
        height = popup.winfo_reqheight()

        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = min(max(0, int(x_root)), max(0, screen_width - width))
        y = min(max(0, int(y_root)), max(0, screen_height - height))
        popup.geometry(f"{width}x{height}+{x}+{y}")

        popup.bind("<Escape>", self._dismiss_custom_popup, add="+")
        popup.bind(
            "<FocusOut>",
            lambda _event: self.after_idle(self._dismiss_custom_popup),
            add="+",
        )

        popup.lift()
        try:
            popup.focus_force()
        except tk.TclError:
            pass
        return popup

    def _build_reference_tables_button(self):
        """Build Reference Tables without a native tk.Menu."""

        self.reference_tables_button = tk.Button(
            self._stage,
            text="Reference Tables ▾",
            command=self._show_reference_tables_menu,
            bg="#3a4148",
            fg=self.MENU_TEXT,
            activebackground="#46515c",
            activeforeground=self.MENU_TEXT,
            relief="flat",
            padx=10,
            pady=3,
            font=("Segoe UI", 9),
        )
        self.reference_tables_button.place(x=1170, y=20, width=170, height=30)

    def _show_reference_tables_menu(self):
        button = self.reference_tables_button
        items = [
            (
                "Minerals Table",
                lambda: webbrowser.open(MINERALS_TABLE_URL, new=2),
                True,
            ),
            (
                "Volcanism Table",
                lambda: webbrowser.open(VOLCANISM_TABLE_URL, new=2),
                True,
            ),
        ]
        self._show_custom_popup(
            items,
            button.winfo_rootx(),
            button.winfo_rooty() + button.winfo_height(),
            min_width=button.winfo_width(),
        )

    def _build_result_context_menu(self):
        """Bind the Results context actions without creating a native tk.Menu."""

        for tree in (
            self.hotspot_tree,
            self.planet_tree,
            self.community_tree,
            self.systems_result_tree,
        ):
            tree.bind(
                "<Button-3>",
                self._show_result_context_menu,
                add="+",
            )
            tree.bind(
                "<Control-c>",
                self._copy_selected_rows_shortcut,
                add="+",
            )

    def _show_result_context_menu(self, event):
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid:
            self._dismiss_custom_popup()
            return "break"

        # Preserve an existing multi-selection when right-clicking inside it.
        if iid not in tree.selection():
            tree.selection_set(iid)
        tree.focus(iid)
        self._context_tree = tree
        self._context_iid = iid

        selected_iids = self._selected_context_iids()
        selected_systems = self._selected_context_systems()
        row_count = len(selected_iids)
        system_count = len(selected_systems)

        items = [
            (
                "Copy row" if row_count == 1 else f"Copy {row_count} rows",
                self._copy_context_row,
                bool(row_count),
            ),
            (
                "Copy system"
                if system_count <= 1
                else f"Copy {system_count} systems",
                self._copy_context_system,
                bool(system_count),
            ),
        ]

        # Website actions remain available only for exactly one selected system.
        if row_count == 1 and system_count == 1:
            items.extend(
                [
                    None,
                    (
                        "Open system in Inara",
                        lambda: self._open_context_system("inara"),
                        True,
                    ),
                    (
                        "Open system in Spansh",
                        lambda: self._open_context_system("spansh"),
                        True,
                    ),
                    (
                        "Open system in EDSM",
                        lambda: self._open_context_system("edsm"),
                        True,
                    ),
                ]
            )

        self._show_custom_popup(
            items,
            event.x_root,
            event.y_root,
            min_width=215,
        )
        return "break"

    # ------------------------------------------------------------------
    # Results outline
    # ------------------------------------------------------------------
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

            mask_positions = (
                (x, y, width, m),
                (x, y + height - m, width, m),
                (x, y, m, height),
                (x + width - m, y, m, height),
            )
            for mask, (lx, ly, lw, lh) in zip(masks, mask_positions):
                mask.place(x=lx, y=ly, width=lw, height=lh)
                mask.lift()

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
