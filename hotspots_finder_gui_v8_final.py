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
from ui_logo_hd import LOGO_WEBP_BASE64


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

        # Keep only a very small outer margin around the tested controls.
        # This avoids the extra panel-coloured strip that was visible below
        # the System Filters section.
        self._system_filters_backplate.place(
            x=16,
            y=575,
            width=496,
            height=177,
        )
        self._system_filters_backplate.lower()

        # The old title frame must never be used as a second shared background.
        # The parent log-layout layer otherwise re-expands it after idle and
        # produces a second panel-coloured rectangle behind this section.
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
                x=16,
                y=575,
                width=496,
                height=177,
            )
            backplate.lower()

            # Raise the actual filter controls above the single shared card.
            for name in (
                "_faction_box",
                "_power_box",
                "_power_states_box",
                "_reference_box",
                "_distance_box",
            ):
                frame = getattr(self, name, None)
                if frame is not None:
                    frame.lift()

            caption = getattr(self, "_system_filters_caption", None)
            if caption is not None:
                caption.lift()
        except tk.TclError:
            return

    def _apply_brand_header(self):
        """Render the original high-resolution logo smoothly."""

        header = getattr(self, "_header_frame", None)
        if header is None:
            return

        try:
            header.configure(bg=THEME["header"])
            for child in header.winfo_children():
                child.destroy()

            # Use a 192x192 source generated from the original uploaded logo,
            # then downsample once to the exact header size. This avoids the
            # softness caused by enlarging the previous 64x64 embedded asset.
            logo_bytes = base64.b64decode(LOGO_WEBP_BASE64)
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

        except (tk.TclError, ValueError, OSError):
            return


def main():
    app = FinderV8FinalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
