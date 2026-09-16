#!/usr/bin/env python3

"""Final visual patch for the v8 desktop interface.

Keeps the tested visual layer intact while fixing the unified System Filters
card and using the HTML mockup as the visual source of truth.
"""

import tkinter as tk
from tkinter import ttk

from hotspots_finder_gui_v8_visual import FinderV8VisualApp, THEME


class FinderV8FinalApp(FinderV8VisualApp):
    """Small final visual refinements on top of FinderV8VisualApp."""

    SYSTEM_FILTERS_X = 16
    SYSTEM_FILTERS_Y = 575
    SYSTEM_FILTERS_WIDTH = 496
    # Results is y=92, height=650 in the default layout -> bottom edge y=742.
    SYSTEM_FILTERS_HEIGHT = 167

    SYSTEM_FILTERS_TOP_ROW_Y = 610
    SYSTEM_FILTERS_BOTTOM_ROW_Y = 670

    def _configure_styles(self):
        """Keep ttk content flat; result tabs are rendered by our own bar."""

        style = ttk.Style(self)
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass

        super()._configure_styles()

        # Native notebook tabs are hidden later and replaced by classic Tk
        # labels so we can match the HTML mockup exactly instead of inheriting
        # platform-specific bevels from ttk themes.
        style = ttk.Style(self)
        style.configure(
            "FlatResults.TNotebook",
            background=THEME["field"],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        try:
            style.layout("FlatResults.TNotebook.Tab", [])
        except tk.TclError:
            pass

        # Power uses the same light one-pixel outline as text fields/buttons,
        # with a small internal left inset so its text does not touch the edge.
        style.configure(
            "TCombobox",
            fieldbackground=THEME["field"],
            background=THEME["panel2"],
            foreground=THEME["text"],
            arrowcolor=THEME["muted"],
            bordercolor=THEME["line2"],
            lightcolor=THEME["line2"],
            darkcolor=THEME["line2"],
            borderwidth=1,
            relief="flat",
            padding=(4, 1, 1, 1),
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", THEME["field"])],
            foreground=[("readonly", THEME["text"])],
            selectbackground=[("readonly", THEME["field"])],
            selectforeground=[("readonly", THEME["text"])],
        )

    def _build_ui(self):
        super()._build_ui()
        # Clicking anywhere that is not another text input releases the current
        # Entry/Text/Combobox focus. This also removes the green focus outline.
        self.bind_all("<Button-1>", self._clear_input_focus_on_click, add="+")
        self.after_idle(self._install_flat_result_tabs)

    @staticmethod
    def _is_text_input_widget(widget):
        return isinstance(widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox))

    def _clear_input_focus(self, clicked_widget=None):
        """Release focus from text-entry controls after clicking elsewhere."""

        try:
            focused = self.focus_get()
        except tk.TclError:
            return

        if focused is None or not self._is_text_input_widget(focused):
            return
        if clicked_widget is not None and self._is_text_input_widget(clicked_widget):
            return

        try:
            target = clicked_widget.winfo_toplevel() if clicked_widget is not None else self
            target.focus_set()
        except tk.TclError:
            try:
                self.focus_set()
            except tk.TclError:
                pass

    def _clear_input_focus_on_click(self, event):
        self._clear_input_focus(getattr(event, "widget", None))

    def _install_flat_result_tabs(self):
        """Replace ttk's native tabs with a mockup-like flat tab strip."""

        notebook = getattr(self, "notebook", None)
        panel = getattr(self, "_results_panel", None)
        if notebook is None or panel is None:
            return

        if getattr(self, "_flat_tabs_bar", None) is not None:
            return

        try:
            notebook.configure(style="FlatResults.TNotebook")
            if notebook.winfo_manager() == "pack":
                notebook.pack_configure(pady=(31, 8))
        except tk.TclError:
            pass

        self._flat_tabs_bar = tk.Frame(
            panel,
            bg=THEME["panel"],
            bd=0,
            highlightthickness=0,
        )
        self._flat_tabs_bar.place(x=12, y=43, height=31)

        self._flat_tab_widgets = {}
        self._rebuild_flat_result_tabs()
        notebook.bind("<<NotebookTabChanged>>", self._on_flat_tab_changed, add="+")
        self._schedule_flat_tab_sync()

    def _rebuild_flat_result_tabs(self):
        bar = getattr(self, "_flat_tabs_bar", None)
        notebook = getattr(self, "notebook", None)
        if bar is None or notebook is None:
            return

        for child in bar.winfo_children():
            child.destroy()
        self._flat_tab_widgets = {}

        try:
            tabs = list(notebook.tabs())
        except tk.TclError:
            return

        for tab_id in tabs:
            try:
                text = str(notebook.tab(tab_id, "text") or "")
            except tk.TclError:
                text = ""

            label = tk.Label(
                bar,
                text=text,
                bg=THEME["panel2"],
                fg=THEME["text"],
                font=("Segoe UI", 9),
                padx=12,
                pady=6,
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground=THEME["line"],
                highlightcolor=THEME["line2"],
                cursor="hand2",
            )
            label.pack(side="left", padx=(0, 2))
            label.bind(
                "<Button-1>",
                lambda _event, tab=tab_id: self._select_flat_tab(tab),
            )
            label.bind(
                "<Enter>",
                lambda _event, tab=tab_id: self._hover_flat_tab(tab, True),
            )
            label.bind(
                "<Leave>",
                lambda _event, tab=tab_id: self._hover_flat_tab(tab, False),
            )
            self._flat_tab_widgets[tab_id] = label

        self._refresh_flat_tab_states()

    def _select_flat_tab(self, tab_id):
        notebook = getattr(self, "notebook", None)
        if notebook is None:
            return
        try:
            notebook.select(tab_id)
        except tk.TclError:
            return
        self._refresh_flat_tab_states()

    def _hover_flat_tab(self, tab_id, entering):
        notebook = getattr(self, "notebook", None)
        label = getattr(self, "_flat_tab_widgets", {}).get(tab_id)
        if notebook is None or label is None:
            return

        try:
            selected = notebook.select()
        except tk.TclError:
            selected = ""

        if tab_id == selected:
            return

        try:
            label.configure(
                bg=THEME["hover"] if entering else THEME["panel2"],
                highlightbackground=THEME["line2"] if entering else THEME["line"],
            )
        except tk.TclError:
            pass

    def _on_flat_tab_changed(self, _event=None):
        self._refresh_flat_tab_states()

    def _refresh_flat_tab_states(self):
        notebook = getattr(self, "notebook", None)
        widgets = getattr(self, "_flat_tab_widgets", {})
        if notebook is None or not widgets:
            return

        try:
            selected = notebook.select()
        except tk.TclError:
            selected = ""

        for tab_id, label in widgets.items():
            try:
                label.configure(
                    bg=THEME["field"] if tab_id == selected else THEME["panel2"],
                    fg=THEME["accent"] if tab_id == selected else THEME["text"],
                    highlightbackground=(
                        THEME["line2"] if tab_id == selected else THEME["line"]
                    ),
                )
            except tk.TclError:
                pass

    def _schedule_flat_tab_sync(self):
        """Keep dynamic tab text such as Systems (N) synchronized."""

        if not self.winfo_exists():
            return

        notebook = getattr(self, "notebook", None)
        widgets = getattr(self, "_flat_tab_widgets", {})
        if notebook is not None and widgets:
            try:
                tabs = list(notebook.tabs())
            except tk.TclError:
                tabs = []

            if set(tabs) != set(widgets):
                self._rebuild_flat_result_tabs()
            else:
                for tab_id in tabs:
                    label = widgets.get(tab_id)
                    if label is None:
                        continue
                    try:
                        text = str(notebook.tab(tab_id, "text") or "")
                        if str(label.cget("text")) != text:
                            label.configure(text=text)
                    except tk.TclError:
                        pass
                self._refresh_flat_tab_states()

        self.after(250, self._schedule_flat_tab_sync)

    def _position_system_filter_controls(self):
        """Apply the compact final geometry for the System Filters controls."""

        placements = {
            "_faction_box": (18, self.SYSTEM_FILTERS_TOP_ROW_Y, 237, 55),
            "_power_box": (285, self.SYSTEM_FILTERS_TOP_ROW_Y, 225, 55),
            "_reference_box": (18, self.SYSTEM_FILTERS_BOTTOM_ROW_Y, 142, 55),
            "_distance_box": (165, self.SYSTEM_FILTERS_BOTTOM_ROW_Y, 90, 55),
            "_power_states_box": (285, self.SYSTEM_FILTERS_BOTTOM_ROW_Y, 225, 70),
        }

        for name, (x, y, width, height) in placements.items():
            frame = getattr(self, name, None)
            if frame is None:
                continue
            try:
                frame.place(x=x, y=y, width=width, height=height)
                frame.lift()
            except tk.TclError:
                pass

    def _build_system_filters_backplate(self):
        """Draw one uninterrupted outline around the full System Filters area."""

        self._system_filters_backplate = tk.Frame(
            self._stage,
            bg=THEME["panel"],
            highlightthickness=1,
            highlightbackground=THEME["line"],
            bd=0,
        )

        self._system_filters_backplate.place(
            x=self.SYSTEM_FILTERS_X,
            y=self.SYSTEM_FILTERS_Y,
            width=self.SYSTEM_FILTERS_WIDTH,
            height=self.SYSTEM_FILTERS_HEIGHT,
        )
        self._system_filters_backplate.lower()

        old_title_box = getattr(self, "_system_filters_title_box", None)
        if old_title_box is not None:
            try:
                old_title_box.place_forget()
            except tk.TclError:
                pass

        self._system_filters_caption = tk.Label(
            self._system_filters_backplate,
            text="SYSTEM FILTERS",
            bg=THEME["panel"],
            fg=THEME["accent"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            bd=0,
            highlightthickness=0,
        )
        self._system_filters_caption.place(x=10, y=7, width=160, height=25)

        self._position_system_filter_controls()

    def _refresh_unified_system_filters_panel(self):
        """Keep only the final backplate; disable the legacy shared title panel."""

        old_title_box = getattr(self, "_system_filters_title_box", None)
        if old_title_box is not None:
            try:
                old_title_box.place_forget()
            except tk.TclError:
                pass

        backplate = getattr(self, "_system_filters_backplate", None)
        if backplate is None or getattr(self, "_results_expanded", False):
            return

        try:
            backplate.place(
                x=self.SYSTEM_FILTERS_X,
                y=self.SYSTEM_FILTERS_Y,
                width=self.SYSTEM_FILTERS_WIDTH,
                height=self.SYSTEM_FILTERS_HEIGHT,
            )
            backplate.lower()
            self._position_system_filter_controls()

            caption = getattr(self, "_system_filters_caption", None)
            if caption is not None:
                caption.lift()
        except tk.TclError:
            return

        self._normalize_system_filters_colors()

    def _apply_visual_theme(self):
        """Run the approved theme and then apply HTML-mockup-like controls."""

        super()._apply_visual_theme()
        self._normalize_system_filters_colors()
        self._style_mockup_controls(self)
        self._refresh_flat_tab_states()

    def _normalize_system_filters_colors(self):
        """Remove any legacy differently-coloured rectangle inside System Filters."""

        backplate = getattr(self, "_system_filters_backplate", None)
        if backplate is not None:
            try:
                backplate.configure(bg=THEME["panel"])
            except tk.TclError:
                pass

        for name in (
            "_faction_box",
            "_power_box",
            "_power_states_box",
            "_reference_box",
            "_distance_box",
        ):
            frame = getattr(self, name, None)
            if frame is None:
                continue

            try:
                frame.configure(bg=THEME["panel"], highlightthickness=0, bd=0)
            except tk.TclError:
                pass

            for child in frame.winfo_children():
                try:
                    if isinstance(child, (tk.Label, tk.Checkbutton)):
                        child.configure(bg=THEME["panel"])
                except tk.TclError:
                    pass

        caption = getattr(self, "_system_filters_caption", None)
        if caption is not None:
            try:
                caption.configure(bg=THEME["panel"])
            except tk.TclError:
                pass

    def _ensure_checkbox_images(self):
        """Build compact on/off squares: green when on, dark when off."""

        if hasattr(self, "_checkbox_unchecked_image"):
            return

        width = 15
        height = 11
        unchecked = tk.PhotoImage(master=self, width=width, height=height)
        checked = tk.PhotoImage(master=self, width=width, height=height)

        unchecked.put(THEME["line2"], to=(0, 1, 9, 10))
        unchecked.put(THEME["field"], to=(1, 2, 8, 9))

        checked.put(THEME["accent"], to=(0, 1, 9, 10))
        checked.put(THEME["accent"], to=(1, 2, 8, 9))

        self._checkbox_unchecked_image = unchecked
        self._checkbox_checked_image = checked

    def _style_mockup_controls(self, parent):
        """Style classic controls to follow ui_mockup_v8.html."""

        self._ensure_checkbox_images()

        for widget in parent.winfo_children():
            try:
                if isinstance(widget, tk.Button):
                    self._style_mockup_button(widget)
                elif isinstance(widget, tk.Checkbutton):
                    self._style_mockup_checkbutton(widget)
                elif isinstance(widget, tk.Entry):
                    self._style_mockup_entry(widget)
                elif isinstance(widget, tk.Text):
                    self._style_mockup_text(widget)
            except tk.TclError:
                pass

            try:
                self._style_mockup_controls(widget)
            except tk.TclError:
                pass

    def _style_mockup_entry(self, entry):
        """Give every text input the shared outline plus a small left inset."""

        try:
            entry.configure(
                bg=THEME["field"],
                fg=THEME["text"],
                insertbackground=THEME["text"],
                relief="flat",
                # A flat classic Entry still reserves border width internally;
                # use it as a small, consistent text inset for every field,
                # including the RhinoSpotter data folder path.
                bd=3,
                highlightthickness=1,
                highlightbackground=THEME["line2"],
                highlightcolor=THEME["accent"],
            )
        except tk.TclError:
            pass

    def _style_mockup_text(self, text_widget):
        """Match text areas to entries; pad only the manual System Input box."""

        is_system_input = text_widget is getattr(self, "systems_text", None)
        try:
            text_widget.configure(
                bg=THEME["field"],
                fg=THEME["text"],
                insertbackground=THEME["text"],
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=THEME["line2"],
                highlightcolor=THEME["accent"],
                padx=4 if is_system_input else 0,
                pady=2 if is_system_input else 0,
            )
        except tk.TclError:
            pass

    def _sync_button_outline(self, button):
        """Keep an explicit one-pixel frame exactly around a regular button."""

        outline = getattr(button, "_edhf_outline_frame", None)
        if outline is None:
            return
        try:
            if not button.winfo_exists() or not button.winfo_ismapped():
                outline.place_forget()
                return
            x = button.winfo_x()
            y = button.winfo_y()
            width = button.winfo_width()
            height = button.winfo_height()
            if width <= 1 or height <= 1:
                return
            outline.place(
                x=x - 1,
                y=y - 1,
                width=width + 2,
                height=height + 2,
            )
            outline.lower(button)
        except tk.TclError:
            pass

    def _ensure_button_outline(self, button):
        """Use a real frame border so Windows cannot suppress Tk's highlight ring."""

        outline = getattr(button, "_edhf_outline_frame", None)
        if outline is None:
            try:
                outline = tk.Frame(
                    button.master,
                    bg=THEME["line2"],
                    bd=0,
                    highlightthickness=0,
                )
            except tk.TclError:
                return
            button._edhf_outline_frame = outline

            button.bind(
                "<Configure>",
                lambda _event, w=button: self.after_idle(
                    lambda: self._sync_button_outline(w)
                ),
                add="+",
            )
            button.bind(
                "<Map>",
                lambda _event, w=button: self.after_idle(
                    lambda: self._sync_button_outline(w)
                ),
                add="+",
            )
            button.bind(
                "<Unmap>",
                lambda _event, f=outline: f.place_forget(),
                add="+",
            )

        self.after_idle(lambda w=button: self._sync_button_outline(w))

    @staticmethod
    def _remove_button_outline(button):
        outline = getattr(button, "_edhf_outline_frame", None)
        if outline is None:
            return
        try:
            outline.destroy()
        except tk.TclError:
            pass
        button._edhf_outline_frame = None

    def _style_mockup_button(self, button):
        """Flat buttons; regular actions use the exact text-field outline."""

        text = str(button.cget("text") or "").strip().upper()
        outlined = text not in {"SCAN", "STOP"}

        if text == "SCAN":
            base_bg = THEME["accent"]
            hover_bg = THEME["accent2"]
            fg = "#121512"
            active_fg = "#121512"
        elif text == "STOP":
            base_bg = "#3b2d2d"
            hover_bg = "#503737"
            fg = "#d9bcbc"
            active_fg = "#f0d6d6"
        else:
            base_bg = THEME["panel2"]
            hover_bg = THEME["hover"]
            fg = THEME["text"]
            active_fg = THEME["text"]

        try:
            button.configure(
                bg=base_bg,
                fg=fg,
                activebackground=hover_bg,
                activeforeground=active_fg,
                relief="flat",
                overrelief="flat",
                bd=0,
                # The visible regular-button border is the explicit frame below;
                # disabling the native highlight prevents Windows from drawing a
                # different-looking ring on some buttons.
                highlightthickness=0,
                cursor="hand2",
            )
        except tk.TclError:
            return

        if outlined:
            self._ensure_button_outline(button)
        else:
            self._remove_button_outline(button)

        if getattr(button, "_edhf_mockup_bound", False):
            return
        button._edhf_mockup_bound = True
        button._edhf_base_bg = base_bg
        button._edhf_hover_bg = hover_bg

        def _press(event, w=button):
            self._clear_input_focus(w)

        def _enter(_event, w=button):
            try:
                if str(w.cget("state")) != "disabled":
                    w.configure(bg=w._edhf_hover_bg)
            except tk.TclError:
                pass

        def _leave(_event, w=button):
            try:
                w.configure(bg=w._edhf_base_bg)
            except tk.TclError:
                pass

        button.bind("<Button-1>", _press, add="+")
        button.bind("<Enter>", _enter, add="+")
        button.bind("<Leave>", _leave, add="+")

    def _style_mockup_checkbutton(self, checkbutton):
        """Compact flat checkbox with green/dark state and no pressed text effect."""

        try:
            bg = str(checkbutton.cget("bg") or THEME["panel"])
            checkbutton.configure(
                image=self._checkbox_unchecked_image,
                selectimage=self._checkbox_checked_image,
                indicatoron=False,
                compound="left",
                bg=bg,
                fg=THEME["text"],
                activebackground=bg,
                activeforeground=THEME["text"],
                selectcolor=bg,
                relief="flat",
                overrelief="flat",
                offrelief="flat",
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=0,
                cursor="arrow",
            )
        except tk.TclError:
            return

        if getattr(checkbutton, "_edhf_mockup_bound", False):
            return
        checkbutton._edhf_mockup_bound = True

        def _click(_event, w=checkbutton):
            self._clear_input_focus(w)
            try:
                if str(w.cget("state")) != "disabled":
                    w.invoke()
            except tk.TclError:
                pass
            return "break"

        checkbutton.bind("<Button-1>", _click)

    def _open_settings_dialog(self):
        """Apply the final mockup styling after the settings widgets exist."""

        super()._open_settings_dialog()
        window = getattr(self, "_settings_window", None)
        if window is not None:
            self.after_idle(lambda: self._style_mockup_controls(window))

    def _apply_brand_header(self):
        """Use a clean text-only header; the window icon can stay separate later."""

        header = getattr(self, "_header_frame", None)
        if header is None:
            return

        try:
            header.configure(bg=THEME["header"])
            for child in header.winfo_children():
                child.destroy()

            title_block = tk.Frame(
                header,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            )
            title_block.place(x=24, y=12, width=390, height=58)

            tk.Label(
                title_block,
                text="ED Hotspots Finder",
                bg=THEME["header"],
                fg=THEME["accent"],
                font=("Segoe UI", 17, "bold"),
                anchor="w",
            ).pack(anchor="w")

            subtitle_row = tk.Frame(
                title_block,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            )
            subtitle_row.pack(anchor="w", fill="x", pady=(2, 0))

            tk.Label(
                subtitle_row,
                text="Rings & Planets",
                bg=THEME["header"],
                fg=THEME["text"],
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(side="left")

            tk.Label(
                subtitle_row,
                text="•",
                bg=THEME["header"],
                fg=THEME["muted"],
                font=("Segoe UI", 8, "bold"),
                anchor="center",
            ).pack(side="left", padx=(7, 6), pady=(1, 0))

            tk.Label(
                subtitle_row,
                text="v8",
                bg=THEME["header"],
                fg=THEME["muted"],
                font=("Segoe UI", 8),
                anchor="w",
            ).pack(side="left", pady=(1, 0))

        except tk.TclError:
            return


def main():
    app = FinderV8FinalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
