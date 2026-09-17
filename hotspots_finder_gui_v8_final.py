#!/usr/bin/env python3

"""Final v8 desktop entry point.

Application-level settings, DPI handling, proportional UI scaling, icon and
startup splash live here. The approved visual/menu layer is consolidated in
hotspots_finder_gui_v8_ui.py.
"""

import ctypes
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import app_settings
import finder_engine as scan_engine
import hotspots_finder_gui_v8_layout2 as layout_metrics
import hotspots_finder_gui_v8_loglayout as log_layout_metrics
import hotspots_finder_gui_v8_ui as ui_theme
import hotspots_finder_gui_v8_visual as visual_theme
import local_scan
import system_filter_search
import ui_scale_runtime
from hotspots_finder_gui_v8_ui import FinderV8FinalUIApp as _BaseFinalApp


THEME_LABELS = {
    "Deep Black": "deep_black",
    "Green Warm": "green_warm",
}
THEME_NAMES = {value: label for label, value in THEME_LABELS.items()}

UI_SCALE_LABELS = {
    "100%": 1.00,
    "110%": 1.10,
    "115%": 1.15,
    "125%": 1.25,
}
UI_SCALE_NAMES = {value: label for label, value in UI_SCALE_LABELS.items()}
DEFAULT_UI_SCALE = 1.15

ALLOWED_POWERS = (
    "Aisling Duval",
    "Archon Delaine",
    "Arissa Lavigny-Duval",
    "Denton Patreus",
    "Edmund Mahon",
    "Felicia Winters",
    "Jerome Archer",
    "Li Yong-Rui",
    "Nakato Kaine",
    "Pranav Antal",
    "Yuri Grom",
    "Zemina Torval",
)

# The approved v8 layout was authored against the traditional 96-DPI Tk
# baseline. Windows renders at native monitor DPI for sharp text. UI Scale then
# grows both Tk font metrics and the fixed-pixel geometry by the same factor.
TK_UI_SCALING = 96.0 / 72.0

WM_SETREDRAW = 0x000B
RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100
RDW_FRAME = 0x0400
RDW_LAYOUT_TRANSITION = (
    RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW | RDW_FRAME
)


def _enable_windows_dpi_awareness():
    """Render Tk at native monitor DPI instead of Windows bitmap scaling."""

    if sys.platform != "win32":
        return

    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError, ValueError):
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


class FinderV8FinalApp(_BaseFinalApp):
    """Approved v8 UI plus application-level behaviour."""

    def __init__(self):
        saved = app_settings.load_settings()
        application = saved.get("application", {})
        self._ui_scale = ui_scale_runtime.install(
            application.get("ui_scale", DEFAULT_UI_SCALE)
        )
        self._results_transition_pending = False

        original_tk_init = tk.Tk.__init__
        scale = self._ui_scale

        def hidden_tk_init(instance, *args, **kwargs):
            original_tk_init(instance, *args, **kwargs)
            try:
                instance.tk.call("tk", "scaling", TK_UI_SCALING * scale)
                instance.withdraw()
                instance.attributes("-alpha", 0.0)
            except tk.TclError:
                pass

        tk.Tk.__init__ = hidden_tk_init
        try:
            super().__init__()
        finally:
            tk.Tk.__init__ = original_tk_init

        if getattr(tk, "_support_default_root", True):
            tk._default_root = self

        self._apply_scaled_root_geometry()
        self._apply_app_icon(self)

        current_power = str(self.power_var.get() or "").strip()
        if current_power not in ALLOWED_POWERS:
            self.power_var.set("")

    @staticmethod
    def _normalise_ui_scale(value):
        return ui_scale_runtime.normalise_scale(value, DEFAULT_UI_SCALE)

    def _selected_ui_scale(self):
        settings = getattr(self, "v8_settings", {}) or {}
        application = settings.get("application", {})
        return self._normalise_ui_scale(
            application.get("ui_scale", DEFAULT_UI_SCALE)
        )

    def _apply_scaled_root_geometry(self):
        width = ui_scale_runtime.px(layout_metrics.WINDOW_WIDTH)
        height = ui_scale_runtime.px(layout_metrics.WINDOW_HEIGHT)

        try:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")
            self.minsize(width, height)
        except tk.TclError:
            pass

    def _apply_scaled_ttk_metrics(self):
        style = ttk.Style(self)
        try:
            style.configure("Treeview", rowheight=ui_scale_runtime.px(25))
            style.configure(
                "Vertical.TScrollbar",
                width=ui_scale_runtime.px(9),
                arrowsize=ui_scale_runtime.px(7),
            )
            style.configure(
                "Horizontal.TScrollbar",
                width=ui_scale_runtime.px(9),
                arrowsize=ui_scale_runtime.px(7),
            )
            style.configure(
                "TCombobox",
                padding=(
                    ui_scale_runtime.px(4),
                    ui_scale_runtime.px(1),
                    ui_scale_runtime.px(1),
                    ui_scale_runtime.px(1),
                ),
            )
        except tk.TclError:
            pass

    def _apply_responsive_layout(self):
        self._responsive_layout_pending = False

        try:
            width = max(
                layout_metrics.WINDOW_WIDTH,
                ui_scale_runtime.logical_px(self.winfo_width()),
            )
            height = max(
                layout_metrics.WINDOW_HEIGHT,
                ui_scale_runtime.logical_px(self.winfo_height()),
            )
        except (TypeError, ValueError, tk.TclError):
            return

        try:
            self._stage.place_configure(width=width, height=height)
        except tk.TclError:
            pass

        header = getattr(self, "_header_frame", None)
        if header is not None:
            try:
                header.place_configure(width=width)
            except tk.TclError:
                pass

        settings_button = getattr(self, "settings_button", None)
        if settings_button is not None:
            try:
                settings_button.place_configure(x=width - 114, y=20)
            except tk.TclError:
                pass

        reference_button = getattr(self, "reference_tables_button", None)
        if reference_button is not None:
            try:
                reference_button.place_configure(x=width - 294, y=20)
            except tk.TclError:
                pass

        if getattr(self, "_results_expanded", False):
            results_width = max(
                1,
                width
                - layout_metrics.EXPANDED_LEFT_MARGIN
                - layout_metrics.RESULTS_RIGHT_MARGIN,
            )
            results_height = max(
                1,
                height
                - layout_metrics.LAYOUT["_results_panel"][1]
                - layout_metrics.EXPANDED_BOTTOM_MARGIN,
            )
            self._results_panel.place(
                x=layout_metrics.EXPANDED_LEFT_MARGIN,
                y=layout_metrics.LAYOUT["_results_panel"][1],
                width=results_width,
                height=results_height,
            )
            return

        results_x, results_y, base_width, base_height = layout_metrics.LAYOUT[
            "_results_panel"
        ]
        results_width = max(
            base_width,
            width - results_x - layout_metrics.RESULTS_RIGHT_MARGIN,
        )
        results_height = max(
            base_height,
            height - results_y - layout_metrics.RESULTS_BOTTOM_MARGIN,
        )
        self._results_panel.place(
            x=results_x,
            y=results_y,
            width=results_width,
            height=results_height,
        )

    def _suspend_layout_redraw(self):
        if sys.platform != "win32":
            return ()

        try:
            self.update_idletasks()
            user32 = ctypes.windll.user32
        except (AttributeError, OSError, tk.TclError):
            return ()

        handles = []
        for widget in (self, getattr(self, "_stage", None)):
            if widget is None:
                continue
            try:
                hwnd = int(widget.winfo_id())
            except (TypeError, ValueError, tk.TclError):
                continue
            if not hwnd or hwnd in handles:
                continue
            try:
                user32.SendMessageW(ctypes.c_void_p(hwnd), WM_SETREDRAW, 0, 0)
                handles.append(hwnd)
            except (AttributeError, OSError, ValueError):
                continue
        return tuple(handles)

    @staticmethod
    def _resume_layout_redraw(handles):
        if sys.platform != "win32" or not handles:
            return

        try:
            user32 = ctypes.windll.user32
        except (AttributeError, OSError):
            return

        for hwnd in reversed(tuple(handles)):
            try:
                user32.SendMessageW(ctypes.c_void_p(hwnd), WM_SETREDRAW, 1, 0)
                user32.RedrawWindow(
                    ctypes.c_void_p(hwnd),
                    None,
                    None,
                    RDW_LAYOUT_TRANSITION,
                )
            except (AttributeError, OSError, ValueError):
                pass

    def _finish_results_transition(self, handles):
        try:
            if not self.winfo_exists():
                return

            self.update_idletasks()
            self._apply_responsive_layout()

            if not getattr(self, "_results_expanded", False):
                self._reflow_systems_contents()
                try:
                    self._refresh_unified_system_filters_panel()
                except (AttributeError, tk.TclError):
                    pass

            try:
                self._sync_results_outline()
            except (AttributeError, tk.TclError):
                pass

            if (
                getattr(self, "_log_visible", False)
                and not getattr(self, "_results_expanded", False)
            ):
                self._reposition_log_panel()

            self.update_idletasks()
        finally:
            self._resume_layout_redraw(handles)
            self._results_transition_pending = False

    def _toggle_results_expansion(self):
        if self._results_transition_pending:
            return

        self._results_transition_pending = True
        handles = self._suspend_layout_redraw()

        try:
            super()._toggle_results_expansion()
        except Exception:
            self._resume_layout_redraw(handles)
            self._results_transition_pending = False
            raise

        self.after(30, lambda h=handles: self._finish_results_transition(h))

    def _reposition_log_panel(self):
        self._log_reposition_pending = False
        if not getattr(self, "_log_visible", False):
            return
        if getattr(self, "_results_expanded", False):
            return

        try:
            self.update_idletasks()
            root_x = self.winfo_rootx()
            root_y = self.winfo_rooty()

            results_x = self._results_panel.winfo_rootx() - root_x
            results_y = self._results_panel.winfo_rooty() - root_y
            results_width = max(1, self._results_panel.winfo_width())
            bottom_y = self._bottom_bar.winfo_rooty() - root_y

            min_width = ui_scale_runtime.px(log_layout_metrics.LOG_PANEL_MIN_WIDTH)
            gap = ui_scale_runtime.px(log_layout_metrics.LOG_PANEL_GAP)
            max_height = ui_scale_runtime.px(log_layout_metrics.LOG_PANEL_HEIGHT)

            panel_width = min(
                results_width,
                max(
                    min_width,
                    int(results_width * log_layout_metrics.LOG_PANEL_WIDTH_RATIO),
                ),
            )
            available_height = max(1, bottom_y - results_y - gap)
            panel_height = min(max_height, available_height)
            panel_x = results_x + results_width - panel_width
            panel_y = bottom_y - panel_height - gap

            ui_scale_runtime.place_physical(
                self._log_panel,
                x=panel_x,
                y=panel_y,
                width=panel_width,
                height=panel_height,
            )
            self._log_panel.lift()
        except (AttributeError, tk.TclError):
            return

    def _sync_regular_button_border(self, button):
        lines = getattr(button, "_edhf_border_lines", None)
        if not lines or len(lines) != 4:
            return

        try:
            border_color = visual_theme.THEME["line2"]
            for line in lines:
                line.configure(bg=border_color)

            if not button.winfo_exists() or not button.winfo_ismapped():
                for line in lines:
                    line.place_forget()
                return

            x, y = button.winfo_x(), button.winfo_y()
            width, height = button.winfo_width(), button.winfo_height()
            if width < 2 or height < 2:
                return

            positions = (
                (x, y, width, 1),
                (x, y + height - 1, width, 1),
                (x, y, 1, height),
                (x + width - 1, y, 1, height),
            )
            for line, (lx, ly, lw, lh) in zip(lines, positions):
                ui_scale_runtime.place_physical(
                    line,
                    x=lx,
                    y=ly,
                    width=lw,
                    height=lh,
                )
                line.lift(button)
        except tk.TclError:
            pass

    def _sync_results_outline(self):
        notebook = getattr(self, "notebook", None)
        masks = getattr(self, "_results_outline_masks", None)
        lines = getattr(self, "_results_outline_lines", None)
        if (
            notebook is None
            or not masks
            or len(masks) != 4
            or not lines
            or len(lines) != 4
        ):
            return

        try:
            if not notebook.winfo_exists() or not notebook.winfo_ismapped():
                for widget in (*masks, *lines):
                    widget.place_forget()
                return

            x, y = notebook.winfo_x(), notebook.winfo_y()
            width, height = notebook.winfo_width(), notebook.winfo_height()
            t = max(1, ui_scale_runtime.px(self.RESULTS_OUTLINE_THICKNESS))
            m = max(t, ui_scale_runtime.px(self.RESULTS_NATIVE_MASK))
            if width <= m * 2 or height <= m * 2:
                return

            mask_positions = (
                (x, y, width, m),
                (x, y + height - m, width, m),
                (x, y, m, height),
                (x + width - m, y, m, height),
            )
            for mask, (lx, ly, lw, lh) in zip(masks, mask_positions):
                ui_scale_runtime.place_physical(
                    mask,
                    x=lx,
                    y=ly,
                    width=lw,
                    height=lh,
                )
                mask.lift()

            line_positions = (
                (x, y, width, t),
                (x, y + height - t, width, t),
                (x, y, t, height),
                (x + width - t, y, t, height),
            )
            for line, (lx, ly, lw, lh) in zip(lines, line_positions):
                ui_scale_runtime.place_physical(
                    line,
                    x=lx,
                    y=ly,
                    width=lw,
                    height=lh,
                )
                line.lift()
        except tk.TclError:
            pass

    def _ensure_checkbox_images(self):
        width = ui_scale_runtime.px(15)
        height = ui_scale_runtime.px(11)
        theme_key = (
            width,
            height,
            visual_theme.THEME["line2"],
            visual_theme.THEME["field"],
            visual_theme.THEME["accent"],
        )
        if getattr(self, "_checkbox_image_theme_key", None) == theme_key:
            return

        unchecked = getattr(self, "_checkbox_unchecked_image", None)
        checked = getattr(self, "_checkbox_checked_image", None)

        recreate = unchecked is None or checked is None
        if not recreate:
            try:
                recreate = (
                    int(unchecked.width()) != width
                    or int(unchecked.height()) != height
                    or int(checked.width()) != width
                    or int(checked.height()) != height
                )
            except tk.TclError:
                recreate = True

        if recreate:
            unchecked = tk.PhotoImage(master=self, width=width, height=height)
            checked = tk.PhotoImage(master=self, width=width, height=height)
            self._checkbox_unchecked_image = unchecked
            self._checkbox_checked_image = checked

        outer = (
            0,
            ui_scale_runtime.px(1),
            ui_scale_runtime.px(9),
            ui_scale_runtime.px(10),
        )
        inner = (
            ui_scale_runtime.px(1),
            ui_scale_runtime.px(2),
            ui_scale_runtime.px(8),
            ui_scale_runtime.px(9),
        )
        unchecked.put(visual_theme.THEME["line2"], to=outer)
        unchecked.put(visual_theme.THEME["field"], to=inner)
        checked.put(visual_theme.THEME["accent"], to=outer)
        checked.put(visual_theme.THEME["accent"], to=inner)
        self._checkbox_image_theme_key = theme_key

    @staticmethod
    def _app_icon_path():
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / "app.ico"

    def _apply_app_icon(self, window):
        icon_path = self._app_icon_path()
        if not icon_path.is_file():
            return

        try:
            window.iconbitmap(default=str(icon_path))
        except (tk.TclError, OSError):
            pass
        try:
            window.iconbitmap(str(icon_path))
        except (tk.TclError, OSError):
            pass

    @staticmethod
    def _normalise_theme_name(value):
        key = str(value or "deep_black").strip().lower()
        return key if key in visual_theme.THEMES else "deep_black"

    def _selected_theme_name(self):
        settings = getattr(self, "v8_settings", {}) or {}
        application = settings.get("application", {})
        return self._normalise_theme_name(application.get("theme", "deep_black"))

    def _set_theme_globals(self, theme_name):
        theme_name = self._normalise_theme_name(theme_name)
        theme = visual_theme.THEMES[theme_name]

        visual_theme.THEME_NAME = theme_name
        visual_theme.THEME = theme
        ui_theme.THEME = theme

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
        self._set_theme_globals(self._selected_theme_name())
        super()._configure_styles()
        self._apply_scaled_ttk_metrics()

    def _style_export_controls(self, theme):
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

        self._checkbox_image_theme_key = None
        self._ensure_checkbox_images()

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

    def _center_settings_window(self, window, width=600, height=620):
        try:
            self.update_idletasks()
            physical_width = ui_scale_runtime.px(width)
            physical_height = ui_scale_runtime.px(height)
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            x = self.winfo_rootx() + (self.winfo_width() - physical_width) // 2
            y = self.winfo_rooty() + (self.winfo_height() - physical_height) // 2
            x = min(max(0, x), max(0, screen_width - physical_width))
            y = min(max(0, y), max(0, screen_height - physical_height))

            geometry = f"{physical_width}x{physical_height}+{x}+{y}"
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
        original_scale = self._selected_ui_scale()
        theme_var = tk.StringVar(
            window,
            value=THEME_NAMES.get(original_theme, "Deep Black"),
        )
        scale_var = tk.StringVar(
            window,
            value=UI_SCALE_NAMES.get(original_scale, "115%"),
        )

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

        try:
            width = 600
            height = 620
            self._center_settings_window(window, width, height)
            application_panel.place_configure(height=132)
            if update_check is not None:
                update_check.configure(text="Check for updates on startup")
                update_check.place_configure(x=12, y=100, width=320, height=20)

            for child in window.winfo_children():
                if isinstance(child, tk.Button):
                    text = str(child.cget("text") or "")
                    if text in {"Reset Defaults", "Cancel", "Save"}:
                        child.place_configure(y=580)

            self.after_idle(
                lambda w=window: self._center_settings_window(w, width, height)
            )
        except tk.TclError:
            pass

        theme = visual_theme.THEME
        repo_link = tk.Label(
            application_panel,
            text="GitHub Repository  ↗",
            bg=theme["panel"],
            fg=theme["accent"],
            font=("Segoe UI", 9),
            anchor="w",
            cursor="hand2",
            bd=0,
            highlightthickness=0,
        )
        repo_link.place(x=372, y=99, width=172, height=22)
        repo_link.bind(
            "<Button-1>",
            lambda _event: ui_theme.webbrowser.open_new_tab(
                "https://github.com/LittleJacket99/ED-Hotspots-Landables-Finder"
            ),
        )
        repo_link.bind(
            "<Enter>",
            lambda _event, widget=repo_link: widget.configure(
                fg=visual_theme.THEME["accent2"]
            ),
        )
        repo_link.bind(
            "<Leave>",
            lambda _event, widget=repo_link: widget.configure(
                fg=visual_theme.THEME["accent"]
            ),
        )

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

        tk.Label(
            application_panel,
            text="UI Scale",
            bg=theme["panel"],
            fg=theme["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).place(x=12, y=68, width=55, height=24)

        scale_combo = ttk.Combobox(
            application_panel,
            textvariable=scale_var,
            values=tuple(UI_SCALE_LABELS.keys()),
            state="readonly",
            width=18,
        )
        scale_combo.place(x=72, y=66, width=150, height=27)

        tk.Label(
            application_panel,
            text="Applied after restart",
            bg=theme["panel"],
            fg=theme["muted"],
            font=("Segoe UI", 8),
            anchor="w",
        ).place(x=232, y=68, width=150, height=22)

        def preview_theme(_event=None):
            key = THEME_LABELS.get(str(theme_var.get()), "deep_black")
            self._apply_theme_choice(key)

        def stage_scale(_event=None):
            value = UI_SCALE_LABELS.get(str(scale_var.get()), DEFAULT_UI_SCALE)
            self.v8_settings.setdefault("application", {})["ui_scale"] = value

        theme_combo.bind("<<ComboboxSelected>>", preview_theme, add="+")
        scale_combo.bind("<<ComboboxSelected>>", stage_scale, add="+")

        for child in window.winfo_children():
            if (
                isinstance(child, tk.Button)
                and str(child.cget("text") or "") == "Reset Defaults"
            ):
                def reset_application(_event=None):
                    theme_var.set("Deep Black")
                    self._apply_theme_choice("deep_black")
                    scale_var.set("115%")
                    stage_scale()

                child.bind("<ButtonRelease-1>", reset_application, add="+")
                break

        def restore_if_cancelled(event):
            if event.widget is not window:
                return

            saved = app_settings.load_settings()
            saved_application = saved.get("application", {})
            saved_theme = self._normalise_theme_name(
                saved_application.get("theme", "deep_black")
            )
            saved_scale = self._normalise_ui_scale(
                saved_application.get("ui_scale", DEFAULT_UI_SCALE)
            )
            chosen_theme = THEME_LABELS.get(
                str(theme_var.get()),
                "deep_black",
            )

            if saved_theme != chosen_theme:
                self.v8_settings.setdefault("application", {})["theme"] = original_theme
                self._apply_theme_choice(original_theme)

            self.v8_settings.setdefault("application", {})["ui_scale"] = saved_scale

        window.bind("<Destroy>", restore_if_cancelled, add="+")
        self.after_idle(lambda: self._style_classic_widget_tree(window))

    def _reflow_systems_contents(self):
        panel = getattr(self, "_systems_panel", None)
        text = getattr(self, "systems_text", None)
        if panel is None or text is None:
            return

        theme = visual_theme.THEME
        text_frame = text.master
        helper_label = next(
            (
                child
                for child in panel.winfo_children()
                if isinstance(child, tk.Label)
                and str(child.cget("text") or "").startswith("Leave empty")
            ),
            None,
        )

        try:
            text_frame.configure(bg=theme["panel"])
            text_frame.place_configure(x=9, y=52, width=207, height=300)
            self._style_mockup_text(text)
            self._style_classic_widget_tree(text_frame)
        except (AttributeError, tk.TclError):
            pass

        if helper_label is not None:
            try:
                helper_label.configure(
                    bg=theme["panel"],
                    fg=theme["muted"],
                    wraplength=ui_scale_runtime.px(205),
                    justify="left",
                    anchor="nw",
                    font=("Segoe UI", 8),
                )
                helper_label.place_configure(x=9, y=361, width=207, height=38)
            except tk.TclError:
                pass

    def _configure_power_combobox_behavior(self):
        super()._configure_power_combobox_behavior()
        combo = getattr(self, "power_combo", None)
        if combo is None:
            return
        try:
            combo.configure(values=("", *ALLOWED_POWERS))
        except tk.TclError:
            pass

    def _canonicalize_manual_systems(self, systems):
        canonical_systems = []
        seen = set()

        for entered in systems or []:
            scan_engine.check_cancel(self.cancel_event)
            entered = str(entered or "").strip()
            if not entered:
                continue

            canonical = system_filter_search.canonicalize_system_name(
                entered,
                cancel_event=self.cancel_event,
            )
            key = scan_engine.norm(canonical)
            if key in seen:
                continue

            seen.add(key)
            canonical_systems.append(canonical)
            if canonical != entered:
                print(f'Manual system normalized: "{entered}" -> "{canonical}"')

        return canonical_systems

    def _scan_worker(self, config):
        try:
            normalized_config = dict(config or {})
            normalized_config["systems"] = self._canonicalize_manual_systems(
                normalized_config.get("systems", [])
            )
            result = local_scan.run_local_scan(
                normalized_config,
                cancel_event=self.cancel_event,
            )
            self.after(0, self._scan_complete, result)
        except scan_engine.ScanCancelled:
            self.after(0, self._scan_cancelled)
        except Exception as exc:
            self.after(0, self._scan_failed, str(exc))

    def _scan_complete(self, result):
        try:
            return super()._scan_complete(result)
        except Exception:
            try:
                self._finish_scan("Error")
            except Exception:
                pass
            raise


def main():
    _enable_windows_dpi_awareness()

    from startup_splash import close_startup_splash, show_startup_splash

    splash = show_startup_splash()
    app = None

    try:
        app = FinderV8FinalApp()

        # Build and settle the complete UI while the main window remains truly
        # withdrawn. This avoids mapping a transparent HWND whose non-client
        # border can briefly flash as thin lines on Windows/DWM.
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

        # Make the fully-built app opaque while it is still withdrawn, then
        # remove the splash and map the main window only once.
        try:
            app.attributes("-alpha", 1.0)
        except tk.TclError:
            pass
        app.update_idletasks()

        close_startup_splash(splash)
        splash = None

        app.deiconify()
        app._apply_app_icon(app)
        app.lift()
        app.update_idletasks()
        app.update()
    finally:
        close_startup_splash(splash)

    if app is not None:
        app.mainloop()


if __name__ == "__main__":
    main()
