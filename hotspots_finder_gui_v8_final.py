#!/usr/bin/env python3

"""Final v8 UI entry point.

Keeps the approved menu/filter visual layer intact while adding the last
application-level settings before the consolidation pass.
"""

import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import app_settings
import hotspots_finder_gui_v8_final_base as final_base_theme
import hotspots_finder_gui_v8_final_menus as menu_theme
import hotspots_finder_gui_v8_visual as visual_theme
from hotspots_finder_gui_v8_final_menus import FinderV8FinalMenusApp as _BaseFinalApp


THEME_LABELS = {
    "Deep Black": "deep_black",
    "Green Warm": "green_warm",
}
THEME_NAMES = {value: label for label, value in THEME_LABELS.items()}
ALLOWED_POWERS = ("Edmund Mahon", "Nakato Kaine")


class FinderV8FinalApp(_BaseFinalApp):
    """Last v8 settings refinements on top of the approved visual layer."""

    def __init__(self):
        # The inherited v8 chain builds several visual layers and schedules
        # after-idle geometry/style passes. Hide the root at the instant Tk
        # creates it so none of those intermediate states can flash on screen.
        original_tk_init = tk.Tk.__init__

        def hidden_tk_init(instance, *args, **kwargs):
            original_tk_init(instance, *args, **kwargs)
            try:
                instance.withdraw()
                # Even if an inherited layer maps the window during startup,
                # keep it compositor-invisible until the final handoff.
                instance.attributes("-alpha", 0.0)
            except tk.TclError:
                pass

        tk.Tk.__init__ = hidden_tk_init
        try:
            super().__init__()
        finally:
            tk.Tk.__init__ = original_tk_init

        self._apply_app_icon(self)

        # Old remembered settings may still contain a Power that is no longer
        # offered. Do not display or silently use an unsupported value.
        current_power = str(self.power_var.get() or "").strip()
        if current_power not in ALLOWED_POWERS:
            self.power_var.set("")

    # ------------------------------------------------------------------
    # Application icon
    # ------------------------------------------------------------------
    @staticmethod
    def _app_icon_path():
        """Return app.ico both from source and from a PyInstaller bundle."""

        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / "app.ico"

    def _apply_app_icon(self, window):
        icon_path = self._app_icon_path()
        if not icon_path.is_file():
            return

        try:
            # ``default`` also makes child Toplevel windows inherit the icon on
            # Windows instead of falling back to Tk's feather icon.
            window.iconbitmap(default=str(icon_path))
        except (tk.TclError, OSError):
            try:
                window.iconbitmap(str(icon_path))
            except (tk.TclError, OSError):
                pass

    # ------------------------------------------------------------------
    # Theme handling
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_theme_name(value):
        key = str(value or "deep_black").strip().lower()
        return key if key in visual_theme.THEMES else "deep_black"

    def _selected_theme_name(self):
        settings = getattr(self, "v8_settings", {}) or {}
        application = settings.get("application", {})
        return self._normalise_theme_name(application.get("theme", "deep_black"))

    def _set_theme_globals(self, theme_name):
        """Point every active visual layer at the same theme dictionary."""

        theme_name = self._normalise_theme_name(theme_name)
        theme = visual_theme.THEMES[theme_name]

        # These modules import THEME directly, so update their module globals as
        # well as the source visual module. This is temporary until consolidation.
        visual_theme.THEME_NAME = theme_name
        visual_theme.THEME = theme
        final_base_theme.THEME = theme
        menu_theme.THEME = theme

        # Popup colours are instance attributes so they change immediately too.
        self.RESULTS_OUTLINE = theme["line2"]
        self.MENU_BG = theme["panel2"]
        self.MENU_HOVER = theme["hover"]
        self.MENU_BORDER = theme["line2"]
        self.MENU_TEXT = theme["text"]
        self.MENU_MUTED = theme["muted"]
        self.MENU_SEPARATOR = theme["line2"]
        self.MENU_SELECTED_BG = theme["selected"]
        self.MENU_SELECTED_TEXT = theme["accent"]
        return theme_name, theme

    def _configure_styles(self):
        # v8 settings are loaded before Tk constructs the controls, so the saved
        # theme can be selected before the rest of the style chain runs.
        self._set_theme_globals(self._selected_theme_name())
        super()._configure_styles()

    def _style_export_controls(self, theme):
        """Repaint the Results export strip during a live theme switch."""

        panel = getattr(self, "_results_panel", None)
        if panel is None:
            return

        try:
            frames = panel.winfo_children()
        except tk.TclError:
            return

        for frame in frames:
            if not isinstance(frame, tk.Frame):
                continue

            try:
                children = frame.winfo_children()
            except tk.TclError:
                continue

            label = next(
                (
                    widget
                    for widget in children
                    if isinstance(widget, tk.Label)
                    and str(widget.cget("text") or "") == "Export current tab:"
                ),
                None,
            )
            if label is None:
                continue

            try:
                frame.configure(bg=theme["panel"])
                label.configure(bg=theme["panel"], fg=theme["muted"])
            except tk.TclError:
                pass

            for widget in children:
                if not isinstance(widget, tk.Button):
                    continue
                try:
                    widget.configure(
                        bg=theme["panel2"],
                        fg=theme["text"],
                        activebackground=theme["hover"],
                        activeforeground=theme["text"],
                        relief="flat",
                        bd=0,
                    )
                except tk.TclError:
                    pass
            return

    def _apply_theme_choice(self, theme_name):
        theme_name, theme = self._set_theme_globals(theme_name)
        self.v8_settings.setdefault("application", {})["theme"] = theme_name

        # Reconfigure ttk styles and repaint the existing classic Tk widgets.
        self._configure_styles()
        self._apply_visual_theme()
        self._style_export_controls(theme)

        for mask in getattr(self, "_results_outline_masks", ()) or ():
            try:
                mask.configure(bg=theme["field"])
            except tk.TclError:
                pass
        for line in getattr(self, "_results_outline_lines", ()) or ():
            try:
                line.configure(bg=theme["line2"])
            except tk.TclError:
                pass

        try:
            self._sync_results_outline()
        except (AttributeError, tk.TclError):
            pass

    # ------------------------------------------------------------------
    # Settings: Application / Theme
    # ------------------------------------------------------------------
    def _center_settings_window(self, window, width=600, height=585):
        """Center Settings over the app and re-assert geometry after mapping."""

        try:
            self.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            x = self.winfo_rootx() + (self.winfo_width() - width) // 2
            y = self.winfo_rooty() + (self.winfo_height() - height) // 2
            x = min(max(0, x), max(0, screen_width - width))
            y = min(max(0, y), max(0, screen_height - height))

            geometry = f"{width}x{height}+{x}+{y}"
            window.geometry(geometry)
            window.update_idletasks()
            window.geometry(geometry)
            return geometry
        except tk.TclError:
            return None

    def _open_settings_dialog(self):
        super()._open_settings_dialog()
        window = getattr(self, "_settings_window", None)
        if window is None or not window.winfo_exists():
            return
        if getattr(window, "_edhf_theme_controls", False):
            return
        window._edhf_theme_controls = True
        self._apply_app_icon(window)

        original_theme = self._selected_theme_name()
        selected_label = THEME_NAMES.get(original_theme, "Deep Black")
        theme_var = tk.StringVar(window, value=selected_label)

        # Find the existing APPLICATION card instead of duplicating it.
        application_panel = None
        update_check = None
        for child in window.winfo_children():
            if not isinstance(child, tk.Frame):
                continue
            for sub in child.winfo_children():
                if (
                    isinstance(sub, tk.Label)
                    and str(sub.cget("text") or "") == "APPLICATION"
                ):
                    application_panel = child
                    break
            if application_panel is not None:
                break

        if application_panel is None:
            return

        for sub in application_panel.winfo_children():
            if (
                isinstance(sub, tk.Checkbutton)
                and "Check for updates" in str(sub.cget("text") or "")
            ):
                update_check = sub
                break

        # Make room for Theme, then centre the enlarged window over the app.
        try:
            width = 600
            height = 585
            self._center_settings_window(window, width, height)
            application_panel.place_configure(height=100)
            if update_check is not None:
                update_check.place_configure(x=12, y=68, width=500, height=20)

            for child in window.winfo_children():
                if isinstance(child, tk.Button):
                    text = str(child.cget("text") or "")
                    if text in {"Reset Defaults", "Cancel", "Save"}:
                        child.place_configure(y=545)

            # Windows can briefly map a Toplevel at 0,0 before respecting the
            # requested geometry, so re-assert the centred position once idle.
            self.after_idle(
                lambda w=window: self._center_settings_window(w, width, height)
            )
        except tk.TclError:
            pass

        theme = visual_theme.THEME
        tk.Label(
            application_panel,
            text="Theme",
            bg=theme["panel"],
            fg=theme["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).place(x=12, y=36, width=50, height=24)

        theme_combo = ttk.Combobox(
            application_panel,
            textvariable=theme_var,
            values=tuple(THEME_LABELS.keys()),
            state="readonly",
            width=18,
        )
        theme_combo.place(x=72, y=34, width=150, height=27)

        def preview_theme(_event=None):
            key = THEME_LABELS.get(str(theme_var.get()), "deep_black")
            self._apply_theme_choice(key)

        theme_combo.bind("<<ComboboxSelected>>", preview_theme, add="+")

        # Reset Defaults also resets the visual theme to Deep Black.
        for child in window.winfo_children():
            if (
                isinstance(child, tk.Button)
                and str(child.cget("text") or "") == "Reset Defaults"
            ):
                child.bind(
                    "<ButtonRelease-1>",
                    lambda _event: (
                        theme_var.set("Deep Black"),
                        self._apply_theme_choice("deep_black"),
                    ),
                    add="+",
                )
                break

        # Theme previews are immediate. If the user cancels the dialog, restore
        # the theme that was active before opening it. If Save was used, the base
        # dialog has already persisted the selected application.theme value.
        def restore_if_cancelled(event):
            if event.widget is not window:
                return
            saved = app_settings.load_settings()
            saved_theme = self._normalise_theme_name(
                saved.get("application", {}).get("theme", "deep_black")
            )
            chosen = THEME_LABELS.get(str(theme_var.get()), "deep_black")
            if saved_theme != chosen:
                self.v8_settings.setdefault("application", {})["theme"] = original_theme
                self._apply_theme_choice(original_theme)

        window.bind("<Destroy>", restore_if_cancelled, add="+")
        self.after_idle(lambda: self._style_classic_widget_tree(window))

    # ------------------------------------------------------------------
    # Power list
    # ------------------------------------------------------------------
    def _configure_power_combobox_behavior(self):
        super()._configure_power_combobox_behavior()
        combo = getattr(self, "power_combo", None)
        if combo is None:
            return
        try:
            combo.configure(values=("", *ALLOWED_POWERS))
        except tk.TclError:
            return


def main():
    from startup_splash import close_startup_splash, show_startup_splash

    splash = show_startup_splash()

    app = None
    try:
        app = FinderV8FinalApp()

        # Keep the root transparent while inherited after-idle/short-delay
        # visual passes settle. This is stronger than withdraw alone because a
        # legacy layer may map the root while it is still being restyled.
        try:
            app.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        settle_until = time.perf_counter() + 0.35
        while time.perf_counter() < settle_until:
            app.update_idletasks()
            app.update()
            if splash is not None:
                try:
                    splash.update_idletasks()
                    splash.update()
                except tk.TclError:
                    splash = None
            time.sleep(0.01)

        # Map and paint the entire application while it is still fully
        # transparent. Some ttk/native Windows elements only finish their first
        # real paint after mapping; doing that invisibly prevents the brief white
        # or partially-styled panels visible in the startup recording.
        app.deiconify()
        app.lift()
        mapped_until = time.perf_counter() + 0.20
        while time.perf_counter() < mapped_until:
            app.update_idletasks()
            app.update()
            if splash is not None:
                try:
                    splash.update_idletasks()
                    splash.update()
                except tk.TclError:
                    splash = None
            time.sleep(0.01)

        # Remove the splash first and flush that removal. Only afterwards make
        # the already-painted application visible, so the logo cannot remain on
        # top of the first visible frame of the app.
        close_startup_splash(splash)
        splash = None
        time.sleep(0.03)

        try:
            app.attributes("-alpha", 1.0)
        except tk.TclError:
            pass
        app.lift()
        app.update_idletasks()
        app.update()
    finally:
        close_startup_splash(splash)

    if app is not None:
        app.mainloop()


if __name__ == "__main__":
    main()
