#!/usr/bin/env python3

import contextlib
import ctypes
import queue
import re
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import font as tkfont

from PIL import Image, ImageTk

import hotspots_engine as engine


APP_TITLE = "Hotspots & Landables Finder"
TEMPLATE_URL = (
    "https://docs.google.com/spreadsheets/d/"
    f"{engine.MASTER_TEMPLATE_SPREADSHEET_ID}/copy"
)

# Visual reference: definitive HTML mock-up supplied by the user.
WINDOW_W = 392
WINDOW_H = 530
WINDOW_H_DETAILS = 705
COMPACT_WINDOW_H = 163



UI_SCALE = 1.0

def enable_windows_high_dpi():
    """Enable native high-DPI rendering before Tk creates the root window."""
    if sys.platform != "win32":
        return
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def detect_ui_scale():
    """Return Windows display scaling relative to 96 DPI (1.0 = 100%).

    The HTML mock-up uses CSS pixels, which Windows/browser scaling turns into
    physical pixels.  Once the Python process is DPI-aware we reproduce that
    same physical size ourselves, avoiding Windows bitmap upscaling/blurring.
    """
    if sys.platform != "win32":
        return 1.0
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        if dpi:
            return max(1.0, float(dpi) / 96.0)
    except Exception:
        pass
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        LOGPIXELSX = 88
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, LOGPIXELSX)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        if dpi:
            return max(1.0, float(dpi) / 96.0)
    except Exception:
        pass
    return 1.0


def px(value):
    return int(round(float(value) * UI_SCALE))


def scaled_font(font):
    if not isinstance(font, tuple) or len(font) < 2:
        return font
    parts = list(font)
    size = parts[1]
    if isinstance(size, (int, float)):
        # Negative Tk font sizes are pixel sizes: ideal for exact visual scaling.
        parts[1] = -max(1, px(abs(size))) if size < 0 else max(1, px(size))
    return tuple(parts)


COLORS = {
    "bg": "#1f1f1f",
    "page": "#151515",
    "panel": "#2b2b2b",
    "panel2": "#333333",
    "slate": "#3a4148",
    "slate_hover": "#424b54",
    "border": "#4d4d4d",
    "button_border": "#525c66",
    "button_border_hover": "#64707c",
    "text": "#f1f1f1",
    "muted": "#b5b5b5",
    "orange": "#ffa500",
    "orange_hover": "#ffb326",
    "orange_border": "#c98300",
    "green": "#5acd57",
    "blue": "#43b5eb",
    "red": "#ff2a2a",
    "progress_trough": "#1c1c1c",
    "details_bg": "#1b1b1b",
    "details_head": "#242424",
}


def resource_path(name: str) -> Path:
    """Return a resource path that also works when bundled with PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def _blend(c1, c2, t):
    a = _hex_to_rgb(c1)
    b = _hex_to_rgb(c2)
    return _rgb_to_hex(tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def rounded_rect(canvas, x1, y1, x2, y2, radius, *, fill, outline=None, width=1, tags=None):
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=24,
        fill=fill,
        outline=outline or fill,
        width=width,
        tags=tags,
    )


class QueueWriter:
    def __init__(self, app):
        self.app = app
        self.buffer = ""

    def write(self, text):
        if not text:
            return
        self.buffer += str(text)
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self.app.events.put(("log", line))

    def flush(self):
        if self.buffer:
            self.app.events.put(("log", self.buffer))
            self.buffer = ""


class CanvasButton(tk.Canvas):
    def __init__(
        self,
        parent,
        *,
        text,
        command,
        width,
        height,
        bg,
        hover_bg,
        border,
        hover_border=None,
        text_color=COLORS["text"],
        hover_text=None,
        accent=None,
        border_width=1,
        radius=7,
        font=("Segoe UI", -10, "bold"),
        align="left",
        left_padding=12,
    ):
        width = px(width)
        height = px(height)
        border_width = max(1, px(border_width))
        radius = px(radius)
        left_padding = px(left_padding)
        font = scaled_font(font)
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            relief="flat",
            cursor="hand2",
        )
        self._canvas_width = width
        self._canvas_height = height
        self._text = text
        self._command = command
        self._bg_normal = bg
        self._bg_hover = hover_bg
        self._border_normal = border
        self._border_hover = hover_border or border
        self._text_normal = text_color
        self._text_hover = hover_text or text_color
        self._accent = accent
        self._border_width = border_width
        self._radius = radius
        self._font = font
        self._align = align
        self._left_padding = left_padding
        self._state = "normal"
        self._hover = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", lambda _e: None)
        self._redraw()

    def _on_enter(self, _event):
        if self._state == "normal":
            self._hover = True
            self._redraw()

    def _on_leave(self, _event):
        self._hover = False
        self._redraw()

    def _on_click(self, _event):
        if self._state == "normal" and self._command:
            self._command()

    def _redraw(self):
        self.delete("all")
        disabled = self._state != "normal"
        if disabled:
            fill = "#30343a"
            border = "#444a50"
            text_color = "#777d82"
            accent = "#565b60"
        elif self._hover:
            fill = self._bg_hover
            border = self._border_hover
            text_color = self._text_hover
            accent = self._accent
        else:
            fill = self._bg_normal
            border = self._border_normal
            text_color = self._text_normal
            accent = self._accent

        rounded_rect(
            self,
            1,
            1,
            self._canvas_width - 1,
            self._canvas_height - 1,
            self._radius,
            fill=fill,
            outline=border,
            width=self._border_width,
        )

        if accent:
            self.create_line(
                px(2),
                px(5),
                px(2),
                self._canvas_height - px(5),
                fill=accent,
                width=max(1, px(3)),
                capstyle="round",
            )

        if self._align == "center":
            x = self._canvas_width / 2
            anchor = "center"
        else:
            x = self._left_padding
            anchor = "w"

        self.create_text(
            x,
            self._canvas_height / 2,
            text=self._text,
            fill=text_color,
            font=self._font,
            anchor=anchor,
        )

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "text" in kwargs:
            self._text = str(kwargs.pop("text"))
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            self.configure(cursor="hand2" if self._state == "normal" else "arrow")
        if kwargs:
            return super().configure(**kwargs)
        self._redraw()

    config = configure


class StatusChip(tk.Canvas):
    def __init__(self, parent, width=104, height=25):
        width = px(width)
        height = px(height)
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
        )
        self._canvas_width = width
        self._canvas_height = height
        self._text = "Not connected"
        self._color = COLORS["orange"]
        self._redraw()

    def _redraw(self):
        self.delete("all")
        is_green = self._color.lower() == COLORS["green"].lower()
        fill = "#304331" if is_green else "#443a28"
        outline = "#456d44" if is_green else "#765f31"
        rounded_rect(
            self, px(1), px(1), self._canvas_width - px(1), self._canvas_height - px(1), px(12),
            fill=fill, outline=outline, width=max(1, px(1)),
        )
        self.create_oval(px(9), px(9), px(15), px(15), fill=self._color, outline=self._color)
        self.create_text(
            px(20),
            self._canvas_height / 2,
            text=self._text,
            fill=self._color,
            font=scaled_font(("Segoe UI", -10, "bold")),
            anchor="w",
        )

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "text" in kwargs:
            text = str(kwargs.pop("text"))
            # Keep the compact visual chip from the final mock-up.
            self._text = "Connected" if text.lower().startswith("connected") else text
        if "foreground" in kwargs:
            self._color = kwargs.pop("foreground")
        if kwargs:
            super().configure(**kwargs)
        self._redraw()

    config = configure


class ProgressBar(tk.Canvas):
    def __init__(self, parent, width=344, height=7):
        width = px(width)
        height = px(height)
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
        )
        self._canvas_width = width
        self._canvas_height = height
        self._value = 0.0
        self._redraw()

    def _redraw(self):
        self.delete("all")
        rounded_rect(
            self, 0, 0, self._canvas_width, self._canvas_height, self._canvas_height / 2,
            fill=COLORS["progress_trough"], outline="#3b3b3b", width=1,
        )
        if self._value > 0:
            fill_w = max(self._canvas_height, (self._canvas_width - 2) * min(100.0, max(0.0, self._value)) / 100.0)
            rounded_rect(
                self, 1, 1, min(self._canvas_width - 1, fill_w), self._canvas_height - 1, (self._canvas_height - 2) / 2,
                fill=COLORS["orange"], outline=COLORS["orange"], width=0,
            )

    def configure(self, cnf=None, **kwargs):
        if cnf:
            kwargs.update(cnf)
        if "value" in kwargs:
            self._value = float(kwargs.pop("value"))
        # ttk compatibility: ignore these if passed.
        kwargs.pop("maximum", None)
        kwargs.pop("mode", None)
        if kwargs:
            super().configure(**kwargs)
        self._redraw()

    config = configure


class RoundedCard(tk.Canvas):
    def __init__(self, parent, *, width, height, bg=COLORS["panel"], radius=12):
        width = px(width)
        height = px(height)
        radius = px(radius)
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
        )
        self._canvas_width = width
        self._canvas_height = height
        self._bg = bg
        rounded_rect(
            self, 1, 1, width - 1, height - 1, radius,
            fill=bg, outline=COLORS["border"], width=1,
        )
        self.inner = tk.Frame(self, bg=bg, bd=0, highlightthickness=0)
        self.create_window(px(12), px(12), window=self.inner, anchor="nw", width=width - px(24), height=height - px(24))


class HotspotsFinderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(f"{px(WINDOW_W)}x{px(WINDOW_H)}")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])

        self.events = queue.Queue()
        self.running = False
        self.cancel_event = threading.Event()
        self.details_visible = False
        self.compact_mode = False
        self._details_before_compact = False

        self._fonts = {}
        self._build_fonts()
        self._build_ui()
        self._refresh_connection_state()

        self.after(100, self._process_events)

        # Keep the main window above normal desktop windows.  On Windows the
        # native HWND is promoted to TOPMOST after Tk has finished creating it;
        # this is more reliable than setting -topmost immediately after Tk().
        self.bind("<Map>", self._on_window_mapped, add="+")
        self.after(250, self._force_topmost)

    def _on_window_mapped(self, event=None):
        # Re-apply TOPMOST after restoring the app from the taskbar.
        if event is None or event.widget is self:
            self.after_idle(self._force_topmost)

    def _force_topmost(self):
        try:
            if not self.winfo_exists():
                return

            self.attributes("-topmost", True)
            self.lift()
            self.update_idletasks()
        except Exception:
            return

        if sys.platform == "win32":
            try:
                user32 = ctypes.windll.user32
                hwnd = self.winfo_id()

                # Resolve the native top-level wrapper used by Tk when needed.
                GA_ROOT = 2
                root_hwnd = user32.GetAncestor(hwnd, GA_ROOT)
                if root_hwnd:
                    hwnd = root_hwnd

                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOACTIVATE = 0x0010
                SWP_SHOWWINDOW = 0x0040

                user32.SetWindowPos(
                    hwnd,
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
                )
            except Exception:
                pass

    def _build_fonts(self):
        self._fonts["title"] = tkfont.Font(family="Segoe UI", size=-px(16), weight="bold")
        self._fonts["subtitle"] = tkfont.Font(family="Segoe UI", size=-px(11))
        self._fonts["card_title"] = tkfont.Font(family="Segoe UI", size=-px(14), weight="bold")
        self._fonts["card_sub"] = tkfont.Font(family="Segoe UI", size=-px(10))
        self._fonts["progress"] = tkfont.Font(family="Segoe UI", size=-px(11))
        self._fonts["details_title"] = tkfont.Font(family="Segoe UI", size=-px(11), weight="bold")
        self._fonts["details_hint"] = tkfont.Font(family="Segoe UI", size=-px(10))
        self._fonts["log"] = tkfont.Font(family="Consolas", size=-px(10))

    def _build_ui(self):
        self._build_header()
        self._build_sheet_card()
        self._build_scan_card()
        self._build_details_card()

    def _build_header(self):
        header_h = px(150)
        self.header = tk.Canvas(
            self,
            width=px(WINDOW_W),
            height=header_h,
            bg="#242424",
            highlightthickness=0,
            bd=0,
        )
        self.header.place(x=0, y=0, width=px(WINDOW_W), height=header_h)

        for y in range(header_h):
            color = _blend("#292929", "#222222", y / max(1, header_h - 1))
            self.header.create_line(0, y, px(WINDOW_W), y, fill=color)
        self.header.create_line(0, header_h - 1, px(WINDOW_W), header_h - 1, fill="#353535")

        logo_file = resource_path("logo.png")
        try:
            image = Image.open(logo_file).convert("RGBA")
            image = image.resize((px(152), px(152)), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(image)
            # Approximate the final CSS transform: scale(1.15) translateX(12px) translateY(4px)
            self.header.create_image(px(87), px(80), image=self.logo_image, anchor="center")

            icon = Image.open(logo_file).convert("RGBA").resize((px(64), px(64)), Image.Resampling.LANCZOS)
            self.icon_image = ImageTk.PhotoImage(icon)
            self.iconphoto(True, self.icon_image)
        except Exception:
            self.logo_image = None

        self.header.create_text(
            px(152),
            px(54),
            text=APP_TITLE,
            fill=COLORS["orange"],
            font=self._fonts["title"],
            anchor="w",
        )
        self.header.create_text(
            px(152),
            px(77),
            text="Elite Dangerous · Spansh → Google Sheets",
            fill=COLORS["muted"],
            font=self._fonts["subtitle"],
            anchor="w",
        )

    def _build_sheet_card(self):
        self.sheet_card = RoundedCard(self, width=368, height=182)
        self.sheet_card.place(x=px(12), y=px(166))
        inner = self.sheet_card.inner

        tk.Label(
            inner,
            text="Google Sheet",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=self._fonts["card_title"],
            bd=0,
        ).place(x=px(0), y=px(0))

        tk.Label(
            inner,
            text="Connection and maintenance",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=self._fonts["card_sub"],
            bd=0,
        ).place(x=px(0), y=px(21))

        self.sheet_status = StatusChip(inner, width=104, height=25)
        self.sheet_status.place(x=px(240), y=px(0))

        btn_w = 167
        btn_h = 34
        left_x = 0
        right_x = 177
        start_y = 41
        row_step = 41

        self.template_btn = CanvasButton(
            inner, text="Open Template", command=self.open_template,
            width=btn_w, height=btn_h,
            bg=COLORS["slate"], hover_bg=COLORS["slate_hover"],
            border=COLORS["button_border"], hover_border=COLORS["button_border_hover"],
            accent=COLORS["blue"], font=("Segoe UI", -10, "bold"),
        )
        self.template_btn.place(x=px(left_x), y=px(start_y))

        self.connect_btn = CanvasButton(
            inner, text="Connect / Change Sheet", command=self.connect_sheet,
            width=btn_w, height=btn_h,
            bg=COLORS["slate"], hover_bg=COLORS["slate_hover"],
            border=COLORS["button_border"], hover_border=COLORS["button_border_hover"],
            accent=COLORS["blue"], font=("Segoe UI", -10, "bold"),
        )
        self.connect_btn.place(x=px(left_x), y=px(start_y + row_step))

        self.open_sheet_btn = CanvasButton(
            inner, text="Open My Sheet", command=self.open_sheet,
            width=btn_w, height=btn_h,
            bg=COLORS["slate"], hover_bg=COLORS["slate_hover"],
            border=COLORS["button_border"], hover_border=COLORS["button_border_hover"],
            accent=COLORS["blue"], font=("Segoe UI", -10, "bold"),
        )
        self.open_sheet_btn.place(x=px(left_x), y=px(start_y + row_step * 2))

        self.restore_style_btn = CanvasButton(
            inner, text="Restore Official Style", command=self.restore_official_style,
            width=btn_w, height=btn_h,
            bg=COLORS["slate"], hover_bg=COLORS["slate_hover"],
            border=COLORS["button_border"], hover_border=COLORS["button_border_hover"],
            accent=COLORS["green"], font=("Segoe UI", -10, "bold"),
        )
        self.restore_style_btn.place(x=px(right_x), y=px(start_y))

        self.repair_sheet_btn = CanvasButton(
            inner, text="Repair Sheet", command=self.repair_sheet,
            width=btn_w, height=btn_h,
            bg=COLORS["slate"], hover_bg=COLORS["slate_hover"],
            border=COLORS["button_border"], hover_border=COLORS["button_border_hover"],
            accent=COLORS["green"], font=("Segoe UI", -10, "bold"),
        )
        self.repair_sheet_btn.place(x=px(right_x), y=px(start_y + row_step))

        self.save_style_btn = CanvasButton(
            inner, text="Save Current Style", command=self.save_current_style,
            width=btn_w, height=btn_h,
            bg=COLORS["slate"], hover_bg=COLORS["slate_hover"],
            border=COLORS["button_border"], hover_border=COLORS["button_border_hover"],
            accent=COLORS["green"], font=("Segoe UI", -10, "bold"),
        )
        self.save_style_btn.place(x=px(right_x), y=px(start_y + row_step * 2))

    def _build_scan_card(self):
        self.scan_card = RoundedCard(self, width=368, height=139)
        self.scan_card.place(x=px(12), y=px(364))
        inner = self.scan_card.inner

        # Hidden at rest. During a scan it appears at the far left while
        # Show details stays exactly in its final validated position.
        self.stop_btn = CanvasButton(
            inner,
            text="STOP",
            command=self.stop_scan,
            width=56,
            height=24,
            bg="#2d2d2d",
            hover_bg="#352c2c",
            border="#b53a3a",
            hover_border="#ff4b4b",
            text_color="#ff5a5a",
            hover_text="#ff7373",
            font=("Segoe UI", -11, "bold"),
            align="center",
            left_padding=0,
            radius=7,
        )
        self.stop_btn.place(x=px(0), y=px(0))
        self.stop_btn.place_forget()

        self.details_btn = CanvasButton(
            inner,
            text="Show details",
            command=self.toggle_details,
            width=84,
            height=24,
            bg="#303030",
            hover_bg="#383838",
            border="#565656",
            hover_border="#6b6b6b",
            font=("Segoe UI", -11, "bold"),
            align="center",
            left_padding=0,
            radius=7,
        )
        self.details_btn.place(x=px(260), y=px(0))

        self.run_btn = CanvasButton(
            inner,
            text="SCAN",
            command=self.run_finder,
            width=344,
            height=44,
            bg="#2d2d2d",
            hover_bg="#34312c",
            border=COLORS["orange_border"],
            hover_border=COLORS["orange"],
            text_color=COLORS["orange"],
            hover_text=COLORS["orange_hover"],
            border_width=2,
            font=("Segoe UI", -19, "bold"),
            align="center",
            radius=8,
        )
        self.run_btn.place(x=px(0), y=px(32))

        self.progress = ProgressBar(inner, width=344, height=7)
        self.progress.place(x=px(0), y=px(85))

        # Status and percentage stay together on the lower-left, e.g.
        # "Ready to scan  |  0%". Compact/Expand occupies the former
        # percentage position on the lower-right.
        self.progress_line = tk.Frame(inner, bg=COLORS["panel"], bd=0, highlightthickness=0)
        self.progress_line.place(x=px(0), y=px(97))

        self.progress_text = tk.Label(
            self.progress_line,
            text="Ready to scan",
            bg=COLORS["panel"],
            fg="#929292",
            font=self._fonts["progress"],
            bd=0,
        )
        self.progress_text.pack(side="left")

        self.progress_sep = tk.Label(
            self.progress_line,
            text="  |  ",
            bg=COLORS["panel"],
            fg="#686868",
            font=self._fonts["progress"],
            bd=0,
        )
        self.progress_sep.pack(side="left")

        self.progress_pct = tk.Label(
            self.progress_line,
            text="0%",
            bg=COLORS["panel"],
            fg="#929292",
            font=self._fonts["progress"],
            bd=0,
        )
        self.progress_pct.pack(side="left")

        self.compact_btn = CanvasButton(
            inner,
            text="Compact",
            command=self.toggle_compact,
            width=54,
            height=16,
            bg="#303030",
            hover_bg="#383838",
            border="#565656",
            hover_border="#6b6b6b",
            font=("Segoe UI", -8, "bold"),
            align="center",
            left_padding=0,
            radius=4,
        )
        # Keep the right edge aligned with the scan/progress area, but make the
        # control genuinely smaller and vertically centred on the status row.
        self.compact_btn.place(x=px(290), y=px(98))

    def _build_details_card(self):
        self.log_card = RoundedCard(self, width=368, height=169, bg=COLORS["details_bg"], radius=10)
        inner = self.log_card.inner

        # Header strip visually close to the HTML details panel.
        header = tk.Frame(inner, bg=COLORS["details_head"], bd=0, highlightthickness=0)
        header.place(x=px(-11), y=px(-11), width=px(366), height=px(32))

        tk.Label(
            header,
            text="Technical details",
            bg=COLORS["details_head"],
            fg=COLORS["text"],
            font=self._fonts["details_title"],
            bd=0,
        ).place(x=px(10), y=px(8))

        tk.Label(
            header,
            text="activity log",
            bg=COLORS["details_head"],
            fg="#747474",
            font=self._fonts["details_hint"],
            bd=0,
        ).place(x=px(332), y=px(9), anchor="ne")

        log_frame = tk.Frame(inner, bg=COLORS["details_bg"], bd=0, highlightthickness=0)
        log_frame.place(x=px(-1), y=px(27), width=px(346), height=px(120))

        self.log = tk.Text(
            log_frame,
            bg=COLORS["details_bg"],
            fg="#d6d6d6",
            insertbackground="white",
            relief="flat",
            font=self._fonts["log"],
            wrap="word",
            state="disabled",
            bd=0,
            padx=1,
            pady=1,
        )
        scrollbar = tk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log.yview,
            bg="#303030",
            troughcolor=COLORS["details_bg"],
            activebackground="#444444",
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._append_log("Google Sheet connection state will appear here.")

    def toggle_details(self):
        # Technical details are part of the full layout. If an error or another
        # caller requests them while Compact Mode is active, return to full mode
        # first and then open the log panel.
        if self.compact_mode:
            self._exit_compact(restore_details=False)

        self.details_visible = not self.details_visible
        if self.details_visible:
            self.log_card.place(x=px(12), y=px(513))
            self.details_btn.configure(text="Hide details")
            self.geometry(f"{px(WINDOW_W)}x{px(WINDOW_H_DETAILS)}")
        else:
            self.log_card.place_forget()
            self.details_btn.configure(text="Show details")
            self.geometry(f"{px(WINDOW_W)}x{px(WINDOW_H)}")
        self.after_idle(self._force_topmost)

    def toggle_compact(self):
        if self.compact_mode:
            self._exit_compact(restore_details=True)
        else:
            self._enter_compact()

    def _enter_compact(self):
        if self.compact_mode:
            return

        self.compact_mode = True
        self._details_before_compact = self.details_visible
        self.details_visible = False

        # Compact Mode keeps only the complete scan card visible. This means a
        # running scan, STOP, progress and status remain fully usable.
        self.header.place_forget()
        self.sheet_card.place_forget()
        self.log_card.place_forget()
        self.details_btn.place_forget()

        self.compact_btn.configure(text="Expand")
        self.compact_btn.place(x=px(290), y=px(98))
        self.scan_card.place(x=px(12), y=px(12))
        self.geometry(f"{px(WINDOW_W)}x{px(COMPACT_WINDOW_H)}")
        self.after_idle(self._force_topmost)

    def _exit_compact(self, *, restore_details=True):
        if not self.compact_mode:
            return

        self.compact_mode = False

        self.header.place(x=0, y=0, width=px(WINDOW_W), height=px(150))
        self.sheet_card.place(x=px(12), y=px(166))
        self.scan_card.place(x=px(12), y=px(364))

        self.compact_btn.configure(text="Compact")
        self.compact_btn.place(x=px(290), y=px(98))
        self.details_btn.place(x=px(260), y=px(0))

        should_restore_details = restore_details and self._details_before_compact
        self._details_before_compact = False
        self.details_visible = bool(should_restore_details)

        if self.details_visible:
            self.log_card.place(x=px(12), y=px(513))
            self.details_btn.configure(text="Hide details")
            self.geometry(f"{px(WINDOW_W)}x{px(WINDOW_H_DETAILS)}")
        else:
            self.log_card.place_forget()
            self.details_btn.configure(text="Show details")
            self.geometry(f"{px(WINDOW_W)}x{px(WINDOW_H)}")

        self.after_idle(self._force_topmost)

    # ========================================================
    # CONFIG / CONNECTION
    # ========================================================

    def _config(self):
        return engine.load_config()

    def _spreadsheet_id(self):
        return self._config().get("spreadsheet_id", "").strip()

    def _refresh_connection_state(self):
        spreadsheet_id = self._spreadsheet_id()
        if spreadsheet_id:
            self.sheet_status.configure(text="Connected", foreground=COLORS["green"])
            self.open_sheet_btn.configure(state="normal")
            self.repair_sheet_btn.configure(state="normal")
            self.save_style_btn.configure(state="normal")
            self.restore_style_btn.configure(state="normal")
        else:
            self.sheet_status.configure(text="Not connected", foreground=COLORS["orange"])
            self.open_sheet_btn.configure(state="disabled")
            self.repair_sheet_btn.configure(state="disabled")
            self.save_style_btn.configure(state="disabled")
            self.restore_style_btn.configure(state="disabled")

    def open_template(self):
        webbrowser.open(TEMPLATE_URL)

    def connect_sheet(self):
        current = self._spreadsheet_id()
        value = simpledialog.askstring(
            APP_TITLE,
            "Paste the Google Sheet link:",
            initialvalue=(
                f"https://docs.google.com/spreadsheets/d/{current}/edit"
                if current else ""
            ),
            parent=self,
        )
        if not value:
            return

        try:
            spreadsheet_id = engine.extract_spreadsheet_id(value)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        config = self._config()
        config["spreadsheet_id"] = spreadsheet_id
        engine.save_config(config)

        self._refresh_connection_state()
        self._set_status("Connecting...")
        self._append_log("Connecting to Google Sheet...")

        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        writer = QueueWriter(self)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                engine.init_local_google(ensure_references=True)
                title, _ = engine.get_hotspots_sheet_properties()
            self.events.put(("connected", title))
        except Exception as exc:
            self.events.put(("error", f"Connection error: {exc}"))
        finally:
            writer.flush()

    def open_sheet(self):
        spreadsheet_id = self._spreadsheet_id()
        if not spreadsheet_id:
            messagebox.showwarning(APP_TITLE, "No Google Sheet connected.")
            return
        webbrowser.open(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")

    def repair_sheet(self):
        if self.running:
            return
        if not self._spreadsheet_id():
            messagebox.showwarning(APP_TITLE, "Connect a Google Sheet first.")
            return

        self._set_status("Repairing...")
        self.repair_sheet_btn.configure(state="disabled")
        self._append_log("Repairing sheet structure and formatting...")
        threading.Thread(target=self._repair_sheet_worker, daemon=True).start()

    def _repair_sheet_worker(self):
        writer = QueueWriter(self)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                engine.init_local_google()
                title = engine.repair_sheet_formatting()
            self.events.put(("repaired", title))
        except Exception as exc:
            self.events.put(("error", f"Repair error: {exc}"))
        finally:
            writer.flush()

    def save_current_style(self):
        if self.running:
            return
        if not self._spreadsheet_id():
            messagebox.showwarning(APP_TITLE, "Connect a Google Sheet first.")
            return

        self._set_status("Saving style...")
        self.save_style_btn.configure(state="disabled")
        self.restore_style_btn.configure(state="disabled")
        self.repair_sheet_btn.configure(state="disabled")
        self._append_log("Saving current sheet appearance...")
        threading.Thread(target=self._save_style_worker, daemon=True).start()

    def _save_style_worker(self):
        writer = QueueWriter(self)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                engine.init_local_google()
                engine.save_current_style()
            self.events.put(("style_saved", None))
        except Exception as exc:
            self.events.put(("error", f"Save style error: {exc}"))
        finally:
            writer.flush()

    def restore_official_style(self):
        if self.running:
            return
        if not self._spreadsheet_id():
            messagebox.showwarning(APP_TITLE, "Connect a Google Sheet first.")
            return

        confirmed = messagebox.askyesno(
            APP_TITLE,
            "Restore the official style?\n\n"
            "Data, filters, systems and notes will not be deleted.",
            parent=self,
        )
        if not confirmed:
            return

        self._set_status("Restoring style...")
        self.save_style_btn.configure(state="disabled")
        self.restore_style_btn.configure(state="disabled")
        self.repair_sheet_btn.configure(state="disabled")
        self._append_log("Restoring official sheet appearance...")
        threading.Thread(target=self._restore_style_worker, daemon=True).start()

    def _restore_style_worker(self):
        writer = QueueWriter(self)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                engine.init_local_google()
                engine.restore_official_style()
            self.events.put(("style_restored", None))
        except Exception as exc:
            self.events.put(("error", f"Restore style error: {exc}"))
        finally:
            writer.flush()

    # ========================================================
    # RUN
    # ========================================================

    def run_finder(self):
        if self.running:
            return
        if not self._spreadsheet_id():
            messagebox.showwarning(APP_TITLE, "Connect a Google Sheet first.")
            return

        self.running = True
        self.cancel_event.clear()
        self.stop_btn.configure(state="normal")
        self.stop_btn.place(x=px(0), y=px(0))
        self.run_btn.configure(state="disabled")
        self.connect_btn.configure(state="disabled")
        self.repair_sheet_btn.configure(state="disabled")
        self.save_style_btn.configure(state="disabled")
        self.restore_style_btn.configure(state="disabled")
        self.progress.configure(value=0)
        self.progress_pct.configure(text="0%")
        self._set_status("Scanning...")
        self._append_log("")
        self._append_log("=" * 55)
        self._append_log("Starting Hotspots & Landables Finder...")

        threading.Thread(target=self._run_worker, daemon=True).start()

    def stop_scan(self):
        if not self.running or self.cancel_event.is_set():
            return

        self.cancel_event.set()
        self.stop_btn.configure(state="disabled")
        self._set_status("Stopping...", COLORS["red"])
        self._append_log("Stop requested. Waiting for the current Spansh request to finish...")

    def _run_worker(self):
        writer = QueueWriter(self)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                engine.init_local_google()
                engine.repair_sheet_formatting()
                engine.update_finder_status("RUNNING")
                engine.main(cancel_event=self.cancel_event)
                engine.update_finder_status("COMPLETED")
                engine.repair_sheet_formatting()
                engine.auto_resize_result_columns()
            self.events.put(("completed", None))
        except engine.ScanCancelled:
            try:
                if engine.SHEETS_SERVICE and engine.SPREADSHEET_ID:
                    engine.update_finder_status("")
            except Exception:
                pass
            self.events.put(("cancelled", None))
        except Exception as exc:
            try:
                if engine.SHEETS_SERVICE and engine.SPREADSHEET_ID:
                    engine.update_finder_status("ERROR")
            except Exception:
                pass
            self.events.put(("error", str(exc)))
        finally:
            writer.flush()

    # ========================================================
    # GUI EVENTS
    # ========================================================

    def _process_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()

                if event == "log":
                    self._handle_log_line(value)

                elif event == "connected":
                    self._refresh_connection_state()
                    self.sheet_status.configure(text="Connected", foreground=COLORS["green"])
                    self._set_status("Ready to scan")
                    self._append_log("Google Sheet connected.")
                    if value:
                        self._append_log(f"Spreadsheet: {value}")

                elif event == "repaired":
                    self.repair_sheet_btn.configure(state="normal")
                    self._set_status("Ready to scan")
                    if value:
                        self.sheet_status.configure(text="Connected", foreground=COLORS["green"])
                        self._append_log(f"Spreadsheet: {value}")
                    self._append_log("Sheet formatting repaired.")

                elif event == "style_saved":
                    self.save_style_btn.configure(state="normal")
                    self.restore_style_btn.configure(state="normal")
                    self.repair_sheet_btn.configure(state="normal")
                    self._set_status("Ready to scan")
                    self._append_log("Current appearance saved as default.")

                elif event == "style_restored":
                    self.save_style_btn.configure(state="normal")
                    self.restore_style_btn.configure(state="normal")
                    self.repair_sheet_btn.configure(state="normal")
                    self._set_status("Ready to scan")
                    self._append_log("Official appearance restored.")

                elif event == "completed":
                    self.running = False
                    self.cancel_event.clear()
                    self.stop_btn.place_forget()
                    self.run_btn.configure(state="normal")
                    self.connect_btn.configure(state="normal")
                    self.repair_sheet_btn.configure(state="normal")
                    self.save_style_btn.configure(state="normal")
                    self.restore_style_btn.configure(state="normal")
                    self.progress.configure(value=100)
                    self.progress_pct.configure(text="100%")
                    self._set_status("Scan completed", COLORS["green"])
                    self._append_log("Hotspots & Landables Finder completed successfully.")

                elif event == "cancelled":
                    self.running = False
                    self.cancel_event.clear()
                    self.stop_btn.place_forget()
                    self.run_btn.configure(state="normal")
                    self.connect_btn.configure(state="normal")
                    self.repair_sheet_btn.configure(state="normal")
                    self.save_style_btn.configure(state="normal")
                    self.restore_style_btn.configure(state="normal")
                    self._set_status("Scan cancelled", COLORS["red"])
                    self._append_log("Scan cancelled by user. No partial result table was written.")

                elif event == "error":
                    self.running = False
                    self.cancel_event.clear()
                    self.stop_btn.place_forget()
                    self.run_btn.configure(state="normal")
                    self.connect_btn.configure(state="normal")
                    self.repair_sheet_btn.configure(state="normal")
                    self.save_style_btn.configure(state="normal")
                    self.restore_style_btn.configure(state="normal")
                    self._set_status("Error", COLORS["red"])
                    self._append_log(f"ERROR: {value}")
                    if not self.details_visible:
                        self.toggle_details()
                    messagebox.showerror(APP_TITLE, value)

        except queue.Empty:
            pass

        self.after(100, self._process_events)

    def _handle_log_line(self, line):
        self._append_log(line)

        if line.strip().startswith("Writing results to Google Sheet"):
            self.stop_btn.configure(state="disabled")

        match = re.search(r"\[(\d+)/(\d+)\]\s+Querying", line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if total:
                percent = current / total * 100
                self.progress.configure(value=percent)
                self.progress_pct.configure(text=f"{round(percent):d}%")
                if self.running:
                    self._set_status("Scanning...")

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", str(text) + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, text, color="#929292"):
        self.progress_text.configure(text=text, fg=color)


if __name__ == "__main__":
    enable_windows_high_dpi()
    UI_SCALE = detect_ui_scale()
    app = HotspotsFinderApp()
    app.mainloop()
