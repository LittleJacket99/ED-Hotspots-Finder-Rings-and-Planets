#!/usr/bin/env python3

"""Final visual patch for the v8 desktop interface.

Keeps the tested visual layer intact while fixing the unified System Filters
card and using a clean text-only header.
"""

import tkinter as tk

from hotspots_finder_gui_v8_visual import FinderV8VisualApp, THEME


class FinderV8FinalApp(FinderV8VisualApp):
    """Small final visual refinements on top of FinderV8VisualApp."""

    SYSTEM_FILTERS_X = 16
    SYSTEM_FILTERS_Y = 575
    SYSTEM_FILTERS_WIDTH = 496
    # Results is y=92, height=650 in the default layout -> bottom edge y=742.
    SYSTEM_FILTERS_HEIGHT = 167

    # Compact the controls upward so the first Faction/Power row sits closer
    # to the SYSTEM FILTERS heading while the lower Power States row still
    # finishes just inside the shared bottom border.
    SYSTEM_FILTERS_TOP_ROW_Y = 610
    SYSTEM_FILTERS_BOTTOM_ROW_Y = 670

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
        """Run the approved theme and then apply the final mockup-like controls."""

        super()._apply_visual_theme()
        self._normalize_system_filters_colors()
        self._style_mockup_controls(self)

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
        """Build small custom checkboxes matching the HTML mockup proportions."""

        if hasattr(self, "_checkbox_unchecked_image"):
            return

        size = 11
        unchecked = tk.PhotoImage(master=self, width=size, height=size)
        checked = tk.PhotoImage(master=self, width=size, height=size)

        # Transparent 11 px canvas, 9 px visible square.
        unchecked.put(THEME["line2"], to=(1, 1, 10, 10))
        unchecked.put(THEME["field"], to=(2, 2, 9, 9))

        checked.put(THEME["accent"], to=(1, 1, 10, 10))
        checked.put(THEME["accent"], to=(2, 2, 9, 9))

        # Compact dark check mark, readable at native size without antialiasing.
        check_color = "#101410"
        for x, y in (
            (3, 5), (3, 6),
            (4, 6), (4, 7),
            (5, 6), (5, 7),
            (6, 5), (6, 6),
            (7, 4), (7, 5),
            (8, 3), (8, 4),
        ):
            checked.put(check_color, (x, y))

        self._checkbox_unchecked_image = unchecked
        self._checkbox_checked_image = checked

    def _style_mockup_controls(self, parent):
        """Give classic buttons/checks the mockup's raised + hover treatment."""

        self._ensure_checkbox_images()

        for widget in parent.winfo_children():
            try:
                if isinstance(widget, tk.Button):
                    self._style_mockup_button(widget)
                elif isinstance(widget, tk.Checkbutton):
                    self._style_mockup_checkbutton(widget)
            except tk.TclError:
                pass

            try:
                self._style_mockup_controls(widget)
            except tk.TclError:
                pass

    def _style_mockup_button(self, button):
        """Raised dark button with brighter hover and pressed depth."""

        text = str(button.cget("text") or "").strip().upper()

        if text == "SCAN":
            base_bg = THEME["accent"]
            hover_bg = THEME["accent2"]
            fg = "#121512"
            active_fg = "#121512"
        elif text == "STOP":
            base_bg = "#3b2d2d"
            hover_bg = "#513838"
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
                relief="raised",
                overrelief="raised",
                bd=1,
                highlightthickness=1,
                highlightbackground=THEME["line"],
                highlightcolor=THEME["line2"],
                cursor="hand2",
            )
        except tk.TclError:
            return

        if getattr(button, "_edhf_mockup_bound", False):
            return
        button._edhf_mockup_bound = True
        button._edhf_base_bg = base_bg
        button._edhf_hover_bg = hover_bg

        def _enter(_event, w=button):
            try:
                if str(w.cget("state")) != "disabled":
                    w.configure(
                        bg=w._edhf_hover_bg,
                        highlightbackground=THEME["line2"],
                        relief="raised",
                    )
            except tk.TclError:
                pass

        def _leave(_event, w=button):
            try:
                w.configure(
                    bg=w._edhf_base_bg,
                    highlightbackground=THEME["line"],
                    relief="raised",
                )
            except tk.TclError:
                pass

        def _press(_event, w=button):
            try:
                if str(w.cget("state")) != "disabled":
                    w.configure(relief="sunken", bg=w._edhf_hover_bg)
            except tk.TclError:
                pass

        def _release(_event, w=button):
            try:
                if str(w.cget("state")) != "disabled":
                    w.configure(relief="raised", bg=w._edhf_hover_bg)
            except tk.TclError:
                pass

        button.bind("<Enter>", _enter, add="+")
        button.bind("<Leave>", _leave, add="+")
        button.bind("<ButtonPress-1>", _press, add="+")
        button.bind("<ButtonRelease-1>", _release, add="+")

    def _style_mockup_checkbutton(self, checkbutton):
        """Use a slightly smaller, cleaner green checkbox like the HTML mockup."""

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
                cursor="hand2",
            )
        except tk.TclError:
            return

        if getattr(checkbutton, "_edhf_hover_bound", False):
            return
        checkbutton._edhf_hover_bound = True
        original_fg = THEME["text"]

        def _enter(_event, w=checkbutton):
            try:
                if str(w.cget("state")) != "disabled":
                    w.configure(fg="#ffffff")
            except tk.TclError:
                pass

        def _leave(_event, w=checkbutton):
            try:
                w.configure(fg=original_fg)
            except tk.TclError:
                pass

        checkbutton.bind("<Enter>", _enter, add="+")
        checkbutton.bind("<Leave>", _leave, add="+")

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
