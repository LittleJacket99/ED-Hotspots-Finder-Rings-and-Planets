#!/usr/bin/env python3

"""Final visual patch for the v8 desktop interface.

Keeps the tested visual layer intact while fixing the last header and
System Filters presentation issues found during the real-GUI review.
"""

import tkinter as tk

from hotspots_finder_gui_v8_visual import FinderV8VisualApp, THEME
from ui_logo import LOGO_PNG_BASE64


class FinderV8FinalApp(FinderV8VisualApp):
    """Small final visual refinements on top of FinderV8VisualApp."""

    def _build_system_filters_backplate(self):
        """Draw one uninterrupted outline around the full System Filters area."""

        self._system_filters_backplate = tk.Frame(
            self._stage,
            bg=THEME["panel"],
            highlightthickness=1,
            highlightbackground=THEME["line"],
            bd=0,
        )

        # The tested filter widgets start at x=18 / y=577 and some of them
        # touch the old card edge exactly. Put the card border two pixels
        # outside that geometry so child frames can no longer cover/split it.
        self._system_filters_backplate.place(
            x=16,
            y=575,
            width=496,
            height=182,
        )
        self._system_filters_backplate.lower()

    def _apply_brand_header(self):
        """Use a larger logo and a non-overlapping two-line title block."""

        header = getattr(self, "_header_frame", None)
        if header is None:
            return

        try:
            header.configure(bg=THEME["header"])
            for child in header.winfo_children():
                child.destroy()

            # Source asset is 64x64. 5/4 gives an 80x80 header version while
            # keeping the original asset embedded and avoiding another file.
            base_logo = tk.PhotoImage(data=LOGO_PNG_BASE64)
            self._window_icon_image = base_logo
            self._header_logo_image = base_logo.zoom(5, 5).subsample(4, 4)
            self.iconphoto(True, self._window_icon_image)

            tk.Label(
                header,
                image=self._header_logo_image,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            ).place(x=8, y=1, width=80, height=80)

            title_block = tk.Frame(
                header,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            )
            title_block.place(x=99, y=12, width=330, height=56)

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
                text="v8",
                bg=THEME["header"],
                fg=THEME["muted"],
                font=("Segoe UI", 8),
                anchor="w",
            ).pack(side="left", padx=(8, 0), pady=(2, 0))

        except tk.TclError:
            return


def main():
    app = FinderV8FinalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
