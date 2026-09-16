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
        """Run the approved theme and then normalize the unified filters card."""

        super()._apply_visual_theme()
        self._normalize_system_filters_colors()

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

            # Use a real centered bullet as separator, in its own label, so it
            # stays vertically aligned instead of looking like a low full stop.
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
