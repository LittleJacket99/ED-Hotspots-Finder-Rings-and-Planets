#!/usr/bin/env python3

"""Final visual layer for the v8 desktop interface.

This module sits on top of the already-tested layout/functionality layer and
keeps visual changes isolated from scan logic.
"""

import os
import tkinter as tk
from tkinter import ttk

import hotspots_finder_gui_v8_polish as polish_theme
from hotspots_finder_gui_v8 import COLORS
from hotspots_finder_gui_v8_layout2 import FinderV8Layout2App
from ui_logo import LOGO_PNG_BASE64


APP_WINDOW_TITLE = "ED Hotspots Finder — Rings & Planets v8"

THEMES = {
    "deep_black": {
        "bg": "#101214",
        "header": "#15181b",
        "panel": "#1b1f23",
        "panel2": "#252a2f",
        "field": "#111315",
        "line": "#343a40",
        "line2": "#59616b",
        "text": "#e8edf2",
        "muted": "#939ba5",
        "accent": "#5acd57",
        "accent2": "#74db71",
        "hover": "#30363d",
        "selected": "#1d321e",
        "scroll_track": "#121822",
        "scroll_thumb": "#8e939c",
        "scroll_hover": "#a7adb7",
        "scroll_active": "#c3c8cf",
        "scroll_arrow": "#7f8792",
        "scroll_arrow_hover": "#cfd4da",
    },
    "green_warm": {
        "bg": "#171d18",
        "header": "#1d251f",
        "panel": "#242d26",
        "panel2": "#2d392f",
        "field": "#171d18",
        "line": "#3f5542",
        "line2": "#5e7d62",
        "text": "#e8edf2",
        "muted": "#a8b2aa",
        "accent": "#5acd57",
        "accent2": "#74db71",
        "hover": "#334536",
        "selected": "#203724",
        "scroll_track": "#121822",
        "scroll_thumb": "#8e939c",
        "scroll_hover": "#a7adb7",
        "scroll_active": "#c3c8cf",
        "scroll_arrow": "#7f8792",
        "scroll_arrow_hover": "#cfd4da",
    },
}

THEME_NAME = os.environ.get("EDHF_THEME", "deep_black").strip().lower()
if THEME_NAME not in THEMES:
    THEME_NAME = "deep_black"
THEME = THEMES[THEME_NAME]


class FinderV8VisualApp(FinderV8Layout2App):
    """Apply the approved branding and dark-green visual pass."""

    def _configure_styles(self):
        # Update the shared palette before any widgets are created. The active
        # inheritance chain imports the same COLORS dictionary by reference.
        COLORS.update(
            {
                "bg": THEME["bg"],
                "panel": THEME["panel"],
                "panel2": THEME["panel2"],
                "text": THEME["text"],
                "muted": THEME["muted"],
                # Older layers call the accent "orange". Keep the key for
                # compatibility while switching the visible accent to green.
                "orange": THEME["accent"],
                "green": THEME["accent"],
                "border": THEME["line"],
            }
        )

        # The polish layer cached a few colors at import time. Refresh those
        # globals before its widgets are built.
        polish_theme.PANEL = THEME["panel"]
        polish_theme.ENTRY_BG = THEME["field"]
        polish_theme.SCROLL_TRACK = THEME["scroll_track"]
        polish_theme.SCROLL_THUMB = THEME["scroll_thumb"]
        polish_theme.SCROLL_THUMB_ACTIVE = THEME["scroll_active"]

        super()._configure_styles()

        style = ttk.Style(self)
        style.configure(
            "TNotebook",
            background=THEME["panel"],
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=THEME["panel2"],
            foreground=THEME["text"],
            padding=(14, 7),
            borderwidth=1,
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", THEME["field"]),
                ("active", THEME["hover"]),
            ],
            foreground=[("selected", THEME["accent"])],
        )

        style.configure(
            "Treeview",
            background=THEME["field"],
            foreground=THEME["text"],
            fieldbackground=THEME["field"],
            rowheight=25,
            bordercolor=THEME["line"],
            lightcolor=THEME["line"],
            darkcolor=THEME["line"],
        )
        style.map(
            "Treeview",
            background=[("selected", THEME["selected"])],
            foreground=[("selected", THEME["text"])],
        )
        style.configure(
            "Treeview.Heading",
            background=THEME["panel2"],
            foreground=THEME["text"],
            relief="flat",
            bordercolor=THEME["line2"],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", THEME["hover"])],
        )

        style.configure(
            "TCombobox",
            fieldbackground=THEME["field"],
            background=THEME["panel2"],
            foreground=THEME["text"],
            arrowcolor=THEME["muted"],
            bordercolor=THEME["line"],
            lightcolor=THEME["line"],
            darkcolor=THEME["line"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", THEME["field"])],
            foreground=[("readonly", THEME["text"])],
            selectbackground=[("readonly", THEME["field"])],
            selectforeground=[("readonly", THEME["text"])],
        )

        style.configure(
            "TProgressbar",
            background=THEME["accent"],
            troughcolor=THEME["panel2"],
            bordercolor=THEME["panel2"],
            lightcolor=THEME["accent"],
            darkcolor=THEME["accent"],
        )

        # Thin modern scrollbars inspired by the reference image. The polish
        # layer removes arrows, so restore the standard clam elements here and
        # then apply the final palette/hover states.
        for scrollbar_style in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            style.configure(
                scrollbar_style,
                background=THEME["scroll_thumb"],
                troughcolor=THEME["scroll_track"],
                bordercolor=THEME["scroll_track"],
                lightcolor=THEME["scroll_thumb"],
                darkcolor=THEME["scroll_thumb"],
                arrowcolor=THEME["scroll_arrow"],
                relief="flat",
                borderwidth=0,
                width=9,
                arrowsize=7,
            )
            style.map(
                scrollbar_style,
                background=[
                    ("pressed", THEME["scroll_active"]),
                    ("active", THEME["scroll_hover"]),
                ],
                arrowcolor=[
                    ("pressed", THEME["scroll_arrow_hover"]),
                    ("active", THEME["scroll_arrow_hover"]),
                ],
                lightcolor=[
                    ("pressed", THEME["scroll_active"]),
                    ("active", THEME["scroll_hover"]),
                ],
                darkcolor=[
                    ("pressed", THEME["scroll_active"]),
                    ("active", THEME["scroll_hover"]),
                ],
            )

        try:
            style.layout(
                "Vertical.TScrollbar",
                [
                    (
                        "Vertical.Scrollbar.trough",
                        {
                            "sticky": "ns",
                            "children": [
                                (
                                    "Vertical.Scrollbar.uparrow",
                                    {"side": "top", "sticky": "ew"},
                                ),
                                (
                                    "Vertical.Scrollbar.downarrow",
                                    {"side": "bottom", "sticky": "ew"},
                                ),
                                (
                                    "Vertical.Scrollbar.thumb",
                                    {"expand": "1", "sticky": "nswe"},
                                ),
                            ],
                        },
                    )
                ],
            )
            style.layout(
                "Horizontal.TScrollbar",
                [
                    (
                        "Horizontal.Scrollbar.trough",
                        {
                            "sticky": "ew",
                            "children": [
                                (
                                    "Horizontal.Scrollbar.leftarrow",
                                    {"side": "left", "sticky": "ns"},
                                ),
                                (
                                    "Horizontal.Scrollbar.rightarrow",
                                    {"side": "right", "sticky": "ns"},
                                ),
                                (
                                    "Horizontal.Scrollbar.thumb",
                                    {"expand": "1", "sticky": "nswe"},
                                ),
                            ],
                        },
                    )
                ],
            )
        except tk.TclError:
            pass

        self.option_add("*TCombobox*Listbox.background", THEME["panel2"])
        self.option_add("*TCombobox*Listbox.foreground", THEME["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", THEME["selected"])
        self.option_add("*TCombobox*Listbox.selectForeground", THEME["text"])

    def _build_ui(self):
        super()._build_ui()

        self.title(APP_WINDOW_TITLE)
        self._build_system_filters_backplate()
        self._apply_brand_header()
        self._right_align_export_controls()

        # Settings is added by the settings mixin after the main build chain
        # returns, so run the final classic-widget styling after idle.
        self.after_idle(self._apply_visual_theme)

    def _build_system_filters_backplate(self):
        """Draw one continuous card behind all System Filters controls."""

        self._system_filters_backplate = tk.Frame(
            self._stage,
            bg=THEME["panel"],
            highlightthickness=1,
            highlightbackground=THEME["line"],
            bd=0,
        )
        # Covers the title plus both filter columns as one visual card.
        self._system_filters_backplate.place(
            x=18,
            y=577,
            width=492,
            height=178,
        )
        # Existing controls remain fully interactive above the backplate.
        self._system_filters_backplate.lower()

    def _apply_brand_header(self):
        header = getattr(self, "_header_frame", None)
        if header is None:
            return

        try:
            header.configure(bg=THEME["header"])
            for child in header.winfo_children():
                child.destroy()

            self._header_logo_image = tk.PhotoImage(data=LOGO_PNG_BASE64)
            self.iconphoto(True, self._header_logo_image)

            tk.Label(
                header,
                image=self._header_logo_image,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            ).place(x=12, y=5, width=64, height=64)

            tk.Label(
                header,
                text="ED Hotspots Finder",
                bg=THEME["header"],
                fg=THEME["accent"],
                font=("Segoe UI", 17, "bold"),
                anchor="w",
            ).place(x=88, y=10)

            # Keep subtitle + version in one label so they can never overlap.
            tk.Label(
                header,
                text="Rings & Planets · v8",
                bg=THEME["header"],
                fg=THEME["text"],
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).place(x=89, y=42)
        except tk.TclError:
            return

    def _rename_filter_labels(self):
        super()._rename_filter_labels()

        replacements = {
            "Enable hotspots": "Enable Hotspots",
            "Only pristine": "Only Pristine",
            "Enable planets": "Enable Planets",
            "Only landables": "Only Landables",
        }
        for box in (self._hotspots_box, self._planets_box):
            for child in box.winfo_children():
                if not isinstance(child, tk.Checkbutton):
                    continue
                text = str(child.cget("text") or "")
                if text in replacements:
                    child.configure(text=replacements[text])

    def _reflow_systems_contents(self):
        super()._reflow_systems_contents()

        for child in self._systems_panel.winfo_children():
            if not isinstance(child, tk.Label):
                continue
            text = str(child.cget("text") or "")
            if text.startswith("Optional manual input") or text.startswith("Leave empty"):
                child.configure(
                    text="Leave empty to find matches using System Filters.",
                    wraplength=205,
                    justify="left",
                    anchor="nw",
                    font=("Segoe UI", 8),
                )
                child.place_configure(x=9, y=361, width=207, height=38)

    def _make_tree(self, parent):
        """Create result tables with a functional dark classic x-scrollbar."""

        frame = tk.Frame(parent, bg=THEME["panel"])
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, show="headings", selectmode="extended")
        ybar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=tree.yview,
            style="Vertical.TScrollbar",
        )
        xbar = tk.Scrollbar(
            frame,
            orient="horizontal",
            command=tree.xview,
            bg=THEME["scroll_thumb"],
            activebackground=THEME["scroll_hover"],
            troughcolor=THEME["scroll_track"],
            relief="flat",
            activerelief="flat",
            bd=0,
            elementborderwidth=0,
            highlightthickness=0,
            width=9,
        )
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)

        tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=0, minsize=11)
        frame.columnconfigure(0, weight=1)
        return tree

    def _right_align_export_controls(self):
        """Keep Export current tab + CSV/XLSX grouped at the right edge."""

        for child in self._results_panel.winfo_children():
            if not isinstance(child, tk.Frame):
                continue

            widgets = child.winfo_children()
            label = next(
                (
                    widget
                    for widget in widgets
                    if isinstance(widget, tk.Label)
                    and str(widget.cget("text") or "") == "Export current tab:"
                ),
                None,
            )
            if label is None:
                continue

            csv_button = next(
                (
                    widget
                    for widget in widgets
                    if isinstance(widget, tk.Button)
                    and str(widget.cget("text") or "") == "CSV"
                ),
                None,
            )
            xlsx_button = next(
                (
                    widget
                    for widget in widgets
                    if isinstance(widget, tk.Button)
                    and str(widget.cget("text") or "") == "XLSX"
                ),
                None,
            )
            if csv_button is None or xlsx_button is None:
                return

            label.pack_forget()
            csv_button.pack_forget()
            xlsx_button.pack_forget()

            xlsx_button.pack(side="right")
            csv_button.pack(side="right", padx=(0, 6))
            label.pack(side="right", padx=(0, 7))
            return

    def _apply_visual_theme(self):
        self.configure(bg=THEME["bg"])
        self._stage.configure(bg=THEME["bg"])

        card_names = (
            "_hotspots_box",
            "_planets_box",
            "_community_box",
            "_systems_panel",
            "_results_panel",
        )
        for name in card_names:
            frame = getattr(self, name, None)
            if frame is None:
                continue
            try:
                frame.configure(
                    bg=THEME["panel"],
                    highlightthickness=1,
                    highlightbackground=THEME["line"],
                )
            except tk.TclError:
                pass

        # System Filters is one continuous card. Individual subframes must not
        # draw their own borders or the outline looks segmented.
        backplate = getattr(self, "_system_filters_backplate", None)
        if backplate is not None:
            try:
                backplate.configure(
                    bg=THEME["panel"],
                    highlightthickness=1,
                    highlightbackground=THEME["line"],
                )
            except tk.TclError:
                pass

        for name in (
            "_system_filters_title_box",
            "_faction_box",
            "_power_box",
            "_power_states_box",
            "_reference_box",
            "_distance_box",
        ):
            frame = getattr(self, name, None)
            if frame is not None:
                try:
                    frame.configure(bg=THEME["panel"], highlightthickness=0)
                except tk.TclError:
                    pass

        bottom = getattr(self, "_bottom_bar", None)
        if bottom is not None:
            try:
                bottom.configure(bg=THEME["header"])
            except tk.TclError:
                pass

        log_panel = getattr(self, "_log_panel", None)
        if log_panel is not None:
            try:
                log_panel.configure(
                    bg=THEME["panel2"],
                    highlightbackground=THEME["line2"],
                )
            except tk.TclError:
                pass

        self._style_classic_widget_tree(self)

        for menu_name in ("reference_tables_menu", "_result_context_menu"):
            menu = getattr(self, menu_name, None)
            if menu is None:
                continue
            try:
                menu.configure(
                    bg=THEME["panel2"],
                    fg=THEME["text"],
                    activebackground=THEME["hover"],
                    activeforeground=THEME["text"],
                    bd=0,
                )
            except tk.TclError:
                pass

        # Re-assert the branded header after the recursive classic-widget pass.
        self._apply_brand_header()

    def _style_classic_widget_tree(self, parent):
        for widget in parent.winfo_children():
            try:
                if isinstance(widget, tk.Button):
                    if widget is getattr(self, "scan_button", None):
                        widget.configure(
                            bg=THEME["accent"],
                            fg="#101410",
                            activebackground=THEME["accent2"],
                            activeforeground="#101410",
                            relief="flat",
                            bd=0,
                        )
                    elif widget is getattr(self, "stop_button", None):
                        widget.configure(
                            bg="#3b2d2d",
                            fg=THEME["text"],
                            activebackground="#503737",
                            activeforeground=THEME["text"],
                            relief="flat",
                            bd=0,
                        )
                    else:
                        widget.configure(
                            bg=THEME["panel2"],
                            fg=THEME["text"],
                            activebackground=THEME["hover"],
                            activeforeground=THEME["text"],
                            relief="flat",
                            bd=0,
                        )

                elif isinstance(widget, tk.Checkbutton):
                    parent_bg = THEME["panel"]
                    try:
                        parent_bg = str(widget.master.cget("bg"))
                    except tk.TclError:
                        pass
                    widget.configure(
                        bg=parent_bg,
                        fg=THEME["text"],
                        activebackground=parent_bg,
                        activeforeground=THEME["text"],
                        selectcolor=THEME["panel2"],
                    )

                elif isinstance(widget, (tk.Entry, tk.Text)):
                    widget.configure(
                        bg=THEME["field"],
                        fg=THEME["text"],
                        insertbackground=THEME["text"],
                        relief="flat",
                        bd=0,
                        highlightthickness=1,
                        highlightbackground=THEME["line2"],
                        highlightcolor=THEME["accent"],
                    )

                elif isinstance(widget, tk.Scrollbar):
                    widget.configure(
                        bg=THEME["scroll_thumb"],
                        activebackground=THEME["scroll_hover"],
                        troughcolor=THEME["scroll_track"],
                        relief="flat",
                        activerelief="flat",
                        bd=0,
                        elementborderwidth=0,
                        highlightthickness=0,
                        width=9,
                    )
                    if not getattr(widget, "_edhf_scroll_bound", False):
                        widget._edhf_scroll_bound = True

                        def _scroll_press(_event, w=widget):
                            try:
                                w.configure(activebackground=THEME["scroll_active"])
                            except tk.TclError:
                                pass

                        def _scroll_release(_event, w=widget):
                            try:
                                w.configure(activebackground=THEME["scroll_hover"])
                            except tk.TclError:
                                pass

                        widget.bind("<ButtonPress-1>", _scroll_press, add="+")
                        widget.bind("<ButtonRelease-1>", _scroll_release, add="+")

                elif isinstance(widget, tk.Label):
                    # Keep each label's semantic foreground color, but make
                    # hard-coded legacy backgrounds follow its parent panel.
                    try:
                        parent_bg = str(widget.master.cget("bg"))
                        widget.configure(bg=parent_bg)
                    except tk.TclError:
                        pass

                elif isinstance(widget, tk.Frame):
                    current = str(widget.cget("bg")).lower()
                    if widget is getattr(self, "_header_frame", None):
                        widget.configure(bg=THEME["header"])
                    elif widget is getattr(self, "_bottom_bar", None):
                        widget.configure(bg=THEME["header"])
                    elif current in {
                        "#242424",
                        "#2b2b2b",
                        "#333333",
                        "#202326",
                        "#1f1f1f",
                    }:
                        widget.configure(bg=THEME["panel"])
            except tk.TclError:
                pass

            self._style_classic_widget_tree(widget)

    def _open_settings_dialog(self):
        super()._open_settings_dialog()
        window = getattr(self, "_settings_window", None)
        if window is not None:
            self.after_idle(lambda: self._style_classic_widget_tree(window))


def main():
    app = FinderV8VisualApp()
    app.mainloop()


if __name__ == "__main__":
    main()
