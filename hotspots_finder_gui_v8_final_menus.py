#!/usr/bin/env python3

"""Preserved final menu/filter visual layer.

This module mirrors the previously active ``hotspots_finder_gui_v8_final.py``
so the public entry point can stay small while we add the last v8 settings
features. It will be folded back into the consolidated final source during the
cleanup pass.
"""

import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import ttk

from hotspots_finder_gui_v8_final_base import FinderV8FinalApp as _BaseFinalApp
from hotspots_finder_gui_v8_visual import THEME


MINERALS_TABLE_URL = "https://docs.google.com/spreadsheets/d/1SVTKW-Uy6sjjR0oFqKjCI5tDvYAu97ORmocXwl1ckU0/edit?gid=0#gid=0"
VOLCANISM_TABLE_URL = "https://wiknow.pages.dev/ref/ground-mining"


class FinderV8FinalMenusApp(_BaseFinalApp):
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
    MENU_SELECTED_BG = "#1d321e"
    MENU_SELECTED_TEXT = "#5acd57"

    FILTER_MENU_MIN_WIDTH = 180
    FILTER_MENU_MAX_WIDTH = 420
    FILTER_MENU_MAX_LIST_HEIGHT = 300
    FILTER_MENU_ROW_HEIGHT = 28

    def _configure_styles(self):
        super()._configure_styles()

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

    def _place_custom_popup(self, popup, x_root, y_root, width, height):
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = min(max(0, int(x_root)), max(0, screen_width - int(width)))
        y = min(max(0, int(y_root)), max(0, screen_height - int(height)))
        geometry = f"{int(width)}x{int(height)}+{x}+{y}"
        popup.geometry(geometry)
        popup.deiconify()
        popup.lift()
        popup.update_idletasks()
        popup.geometry(geometry)

    def _show_custom_popup(self, items, x_root, y_root, *, min_width=0):
        self._dismiss_custom_popup()
        popup = tk.Toplevel(self)
        self._custom_popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(bg=self.MENU_BORDER)

        outer = tk.Frame(popup, bg=self.MENU_BORDER, bd=0, highlightthickness=0)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=self.MENU_BG, bd=0, highlightthickness=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        for item in items:
            if item is None:
                tk.Frame(inner, bg=self.MENU_SEPARATOR, bd=0, highlightthickness=0, height=1).pack(fill="x", padx=7, pady=4)
                continue
            label_text, command, enabled = item
            entry = tk.Label(
                inner, text=label_text, bg=self.MENU_BG,
                fg=self.MENU_TEXT if enabled else self.MENU_MUTED,
                anchor="w", justify="left", padx=10, pady=5,
                bd=0, relief="flat", highlightthickness=0,
                font=("Segoe UI", 9), cursor="hand2" if enabled else "",
            )
            entry.pack(fill="x")
            if enabled:
                entry.bind("<Enter>", lambda _e, w=entry: w.configure(bg=self.MENU_HOVER), add="+")
                entry.bind("<Leave>", lambda _e, w=entry: w.configure(bg=self.MENU_BG), add="+")
                entry.bind("<ButtonRelease-1>", lambda _e, cb=command: self._run_custom_popup_command(cb), add="+")

        popup.update_idletasks()
        width = max(int(min_width), popup.winfo_reqwidth())
        height = popup.winfo_reqheight()
        self._place_custom_popup(popup, x_root, y_root, width, height)
        popup.bind("<Escape>", self._dismiss_custom_popup, add="+")
        popup.bind("<FocusOut>", lambda _e: self.after_idle(self._dismiss_custom_popup), add="+")
        try:
            popup.focus_force()
        except tk.TclError:
            pass
        return popup

    def _build_reference_tables_button(self):
        self.reference_tables_button = tk.Button(
            self._stage, text="Reference Tables ▾", command=self._show_reference_tables_menu,
            bg="#3a4148", fg=self.MENU_TEXT, activebackground="#46515c",
            activeforeground=self.MENU_TEXT, relief="flat", padx=10, pady=3,
            font=("Segoe UI", 9),
        )
        self.reference_tables_button.place(x=1170, y=20, width=170, height=30)

    def _show_reference_tables_menu(self):
        button = self.reference_tables_button
        items = [
            ("Minerals Table", lambda: webbrowser.open(MINERALS_TABLE_URL, new=2), True),
            ("Volcanism Table", lambda: webbrowser.open(VOLCANISM_TABLE_URL, new=2), True),
        ]
        self._show_custom_popup(items, button.winfo_rootx(), button.winfo_rooty() + button.winfo_height(), min_width=button.winfo_width())

    def _build_result_context_menu(self):
        for tree in (self.hotspot_tree, self.planet_tree, self.community_tree, self.systems_result_tree):
            tree.bind("<Button-3>", self._show_result_context_menu, add="+")
            tree.bind("<Control-c>", self._copy_selected_rows_shortcut, add="+")

    def _show_result_context_menu(self, event):
        tree = event.widget
        iid = tree.identify_row(event.y)
        if not iid:
            self._dismiss_custom_popup()
            return "break"
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
            ("Copy row" if row_count == 1 else f"Copy {row_count} rows", self._copy_context_row, bool(row_count)),
            ("Copy system" if system_count <= 1 else f"Copy {system_count} systems", self._copy_context_system, bool(system_count)),
        ]
        if row_count == 1 and system_count == 1:
            items.extend([
                None,
                ("Open system in Inara", lambda: self._open_context_system("inara"), True),
                ("Open system in Spansh", lambda: self._open_context_system("spansh"), True),
                ("Open system in EDSM", lambda: self._open_context_system("edsm"), True),
            ])
        self._show_custom_popup(items, event.x_root, event.y_root, min_width=215)
        return "break"

    def _show_column_filter(self, table, column):
        selected = self._column_filter_state[table].get(column)
        choices = self._choices_for_column(table, column)
        labels = [self._filter_label(value) for value in choices]
        self._dismiss_custom_popup()

        popup = tk.Toplevel(self)
        self._custom_popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(bg=self.MENU_BORDER)
        outer = tk.Frame(popup, bg=self.MENU_BORDER, bd=0, highlightthickness=0)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=self.MENU_BG, bd=0, highlightthickness=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        menu_font = tkfont.Font(family="Segoe UI", size=9)
        longest = max(["All", *labels], key=lambda text: menu_font.measure(text))
        content_width = max(self.FILTER_MENU_MIN_WIDTH, min(self.FILTER_MENU_MAX_WIDTH, menu_font.measure(longest) + 34))

        def choose(value):
            self._dismiss_custom_popup()
            self.after_idle(lambda v=value: self._set_column_filter(table, column, v))

        def make_entry(parent, text, value, is_selected):
            normal_bg = self.MENU_SELECTED_BG if is_selected else self.MENU_BG
            normal_fg = self.MENU_SELECTED_TEXT if is_selected else self.MENU_TEXT
            entry = tk.Label(
                parent, text=text, bg=normal_bg, fg=normal_fg, anchor="w",
                justify="left", padx=12, pady=5, bd=0, relief="flat",
                highlightthickness=0, font=("Segoe UI", 9), cursor="hand2",
            )
            entry.pack(fill="x")
            entry.bind("<Enter>", lambda _e, w=entry, fg=normal_fg: w.configure(bg=self.MENU_HOVER, fg=fg), add="+")
            entry.bind("<Leave>", lambda _e, w=entry, bg=normal_bg, fg=normal_fg: w.configure(bg=bg, fg=fg), add="+")
            entry.bind("<ButtonRelease-1>", lambda _e, v=value: choose(v), add="+")
            return entry

        make_entry(inner, "All", None, selected is None)
        tk.Frame(inner, bg=self.MENU_SEPARATOR, bd=0, highlightthickness=0, height=1).pack(fill="x", padx=7, pady=(3, 4))

        list_height = min(max(self.FILTER_MENU_ROW_HEIGHT, len(choices) * self.FILTER_MENU_ROW_HEIGHT), self.FILTER_MENU_MAX_LIST_HEIGHT)
        needs_scroll = len(choices) * self.FILTER_MENU_ROW_HEIGHT > self.FILTER_MENU_MAX_LIST_HEIGHT

        if choices:
            list_host = tk.Frame(inner, bg=self.MENU_BG, bd=0, highlightthickness=0)
            list_host.pack(fill="both", expand=True)
            canvas = tk.Canvas(list_host, bg=self.MENU_BG, bd=0, highlightthickness=0, relief="flat", width=content_width, height=list_height)
            if needs_scroll:
                scrollbar = ttk.Scrollbar(list_host, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
                canvas.configure(yscrollcommand=scrollbar.set)
                scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            list_frame = tk.Frame(canvas, bg=self.MENU_BG, bd=0, highlightthickness=0)
            window_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")
            for value, label in zip(choices, labels):
                make_entry(list_frame, label, value, value == selected)

            def sync_scroll_region(_event=None):
                try:
                    canvas.configure(scrollregion=canvas.bbox("all"))
                except tk.TclError:
                    pass

            def sync_list_width(event):
                try:
                    canvas.itemconfigure(window_id, width=event.width)
                except tk.TclError:
                    pass

            list_frame.bind("<Configure>", sync_scroll_region, add="+")
            canvas.bind("<Configure>", sync_list_width, add="+")
            sync_scroll_region()
            if needs_scroll:
                def on_mousewheel(event):
                    try:
                        steps = int(-event.delta / 120)
                    except (TypeError, ValueError):
                        steps = 0
                    if steps:
                        canvas.yview_scroll(steps, "units")
                    return "break"
                popup.bind("<MouseWheel>", on_mousewheel, add="+")
        else:
            tk.Label(
                inner, text="(No values)", bg=self.MENU_BG, fg=self.MENU_MUTED,
                anchor="w", justify="left", padx=12, pady=5, bd=0,
                relief="flat", highlightthickness=0, font=("Segoe UI", 9),
            ).pack(fill="x")

        popup.update_idletasks()
        width = content_width + 2
        height = popup.winfo_reqheight()
        self._place_custom_popup(popup, self.winfo_pointerx(), self.winfo_pointery(), width, height)
        popup.bind("<Escape>", self._dismiss_custom_popup, add="+")
        popup.bind("<FocusOut>", lambda _e: self.after_idle(self._dismiss_custom_popup), add="+")
        try:
            popup.focus_force()
        except tk.TclError:
            pass

    def _install_results_outline(self):
        notebook = getattr(self, "notebook", None)
        panel = getattr(self, "_results_panel", None)
        if notebook is None or panel is None:
            return
        if getattr(self, "_results_outline_lines", None):
            self._sync_results_outline()
            return
        try:
            self._results_outline_masks = [tk.Frame(panel, bg=THEME["field"], bd=0, highlightthickness=0) for _ in range(4)]
            self._results_outline_lines = [tk.Frame(panel, bg=self.RESULTS_OUTLINE, bd=0, highlightthickness=0) for _ in range(4)]
        except tk.TclError:
            return
        notebook.bind("<Configure>", lambda _e: self.after_idle(self._sync_results_outline), add="+")
        notebook.bind("<Map>", lambda _e: self.after_idle(self._sync_results_outline), add="+")
        self.bind("<Configure>", lambda _e: self.after_idle(self._sync_results_outline), add="+")
        self._sync_results_outline()

    def _sync_results_outline(self):
        notebook = getattr(self, "notebook", None)
        masks = getattr(self, "_results_outline_masks", None)
        lines = getattr(self, "_results_outline_lines", None)
        if notebook is None or not masks or len(masks) != 4 or not lines or len(lines) != 4:
            return
        try:
            if not notebook.winfo_exists() or not notebook.winfo_ismapped():
                for widget in (*masks, *lines):
                    widget.place_forget()
                return
            x, y = notebook.winfo_x(), notebook.winfo_y()
            width, height = notebook.winfo_width(), notebook.winfo_height()
            t, m = self.RESULTS_OUTLINE_THICKNESS, self.RESULTS_NATIVE_MASK
            if width <= m * 2 or height <= m * 2:
                return
            mask_positions = ((x, y, width, m), (x, y + height - m, width, m), (x, y, m, height), (x + width - m, y, m, height))
            for mask, (lx, ly, lw, lh) in zip(masks, mask_positions):
                mask.place(x=lx, y=ly, width=lw, height=lh)
                mask.lift()
            line_positions = ((x, y, width, t), (x, y + height - t, width, t), (x, y, t, height), (x + width - t, y, t, height))
            for line, (lx, ly, lw, lh) in zip(lines, line_positions):
                line.place(x=lx, y=ly, width=lw, height=lh)
                line.lift()
        except tk.TclError:
            pass


def main():
    app = FinderV8FinalMenusApp()
    app.mainloop()


if __name__ == "__main__":
    main()
