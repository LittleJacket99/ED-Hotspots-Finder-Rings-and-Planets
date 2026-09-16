#!/usr/bin/env python3

"""Final visual patch for the v8 desktop interface.

Keeps the tested visual layer intact while fixing the last header and
System Filters presentation issues found during the real-GUI review.
"""

import base64
import io
import tkinter as tk

from PIL import Image, ImageFilter, ImageTk

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

        self._system_filters_backplate.place(
            x=16,
            y=575,
            width=496,
            height=177,
        )
        self._system_filters_backplate.lower()

        # The old title frame must never be used as a second shared background.
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
        """Use a clean small-format mark instead of squeezing the full wordmark."""

        header = getattr(self, "_header_frame", None)
        if header is None:
            return

        try:
            header.configure(bg=THEME["header"])
            for child in header.winfo_children():
                child.destroy()

            # LOGO_WEBP_BASE64 is already derived from the user's original
            # 1254x1254 artwork. The full badge contains tiny lettering which
            # cannot remain readable in a ~70 px title-bar image, so the header
            # uses the illustrative upper portion only. The original artwork is
            # not altered; this is just a display crop for the compact header.
            logo_bytes = base64.b64decode(LOGO_WEBP_BASE64)
            source_logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")

            width, height = source_logo.size
            icon_source = source_logo.crop(
                (
                    int(width * 0.125),
                    0,
                    int(width * 0.875),
                    int(height * 0.75),
                )
            )

            icon_source = icon_source.filter(
                ImageFilter.UnsharpMask(radius=0.55, percent=55, threshold=2)
            )

            header_logo = icon_source.resize(
                (70, 70),
                Image.Resampling.LANCZOS,
            )
            window_icon = icon_source.resize(
                (64, 64),
                Image.Resampling.LANCZOS,
            )

            self._header_logo_image = ImageTk.PhotoImage(header_logo)
            self._window_icon_image = ImageTk.PhotoImage(window_icon)
            self.iconphoto(True, self._window_icon_image)

            tk.Label(
                header,
                image=self._header_logo_image,
                bg=THEME["header"],
                bd=0,
                highlightthickness=0,
            ).place(x=11, y=3, width=70, height=70)

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
