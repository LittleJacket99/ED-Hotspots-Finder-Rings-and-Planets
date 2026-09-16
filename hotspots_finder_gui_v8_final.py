#!/usr/bin/env python3

"""Final visual patch for the v8 desktop interface.

Keeps the tested visual layer intact while fixing the last header and
System Filters presentation issues found during the real-GUI review.
"""

import base64
import io
import tkinter as tk

from PIL import Image, ImageTk

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

        # Put the single outer card a couple of pixels outside the tested
        # filter geometry so none of the inner frames can split its outline.
        self._system_filters_backplate.place(
            x=16,
            y=575,
            width=496,
            height=182,
        )
        self._system_filters_backplate.lower()

        # The old title lived in its own frame, which visually broke the card.
        # Hide that frame and draw the heading directly inside the unified card.
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

    def _apply_brand_header(self):
        """Render the logo smoothly and keep the two-line title block clean."""

        header = getattr(self, "_header_frame", None)
        if header is None:
            return

        try:
            header.configure(bg=THEME["header"])
            for child in header.winfo_children():
                child.destroy()

            # Tk's zoom() uses nearest-neighbour scaling and produced the
            # pixelated logo seen in the previous build. Decode the same PNG
            # through Pillow and resize it with LANCZOS instead.
            logo_bytes = base64.b64decode(LOGO_PNG_BASE64)
            source_logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

            header_logo = source_logo.resize((76, 76), Image.Resampling.LANCZOS)
            window_icon = source_logo.resize((64, 64), Image.Resampling.LANCZOS)

            self._header_logo_image = ImageTk.PhotoImage(header_logo)
            self._window_icon_image = ImageTk.PhotoImage(window_icon)
            self.iconphoto(True, self._window_icon_image)

            tk.Label(
                header,
                image=self._header_logo_image,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            ).place(x=10, y=3, width=76, height=76)

            title_block = tk.Frame(
                header,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            )
            title_block.place(x=99, y=12, width=360, height=58)

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

        except (tk.TclError, ValueError):
            return


def main():
    app = FinderV8FinalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
