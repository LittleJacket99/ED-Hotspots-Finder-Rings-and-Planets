from __future__ import annotations

import math
import tkinter as tk
from typing import Any


ACCENT = "#5acd57"
BACKGROUND = "#101410"
TEXT = "#f2f5f2"
MUTED = "#a6b0a6"

HUD_WIDTH = 250
HUD_HEIGHT = 125


def _first(record: dict[str, Any], *keys: str):
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _same_name(a: Any, b: Any) -> bool:
    if not a or not b:
        return False
    return str(a).strip().casefold() == str(b).strip().casefold()


def _compact_body_name(body: Any, system: Any = None) -> str:
    text = str(body or "Unknown").strip()
    system_text = str(system or "").strip()

    if system_text and text.casefold().startswith((system_text + " ").casefold()):
        suffix = text[len(system_text):].strip()
        if suffix:
            return "".join(suffix.split())

    return "".join(text.split())


def surface_distance_and_bearing(
    latitude: float,
    longitude: float,
    target_latitude: float,
    target_longitude: float,
    radius_m: float,
) -> tuple[float, float]:
    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)
    lat2 = math.radians(target_latitude)
    lon2 = math.radians(target_longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    hav = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    central_angle = 2.0 * math.atan2(
        math.sqrt(hav),
        math.sqrt(max(0.0, 1.0 - hav)),
    )
    distance_m = radius_m * central_angle

    y = math.sin(dlon) * math.cos(lat2)
    x = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )
    bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return distance_m, bearing


def signed_heading_delta(target_bearing: float, current_heading: float) -> float:
    return (target_bearing - current_heading + 540.0) % 360.0 - 180.0


def direction_arrow(delta: float) -> str:
    angle = (delta + 360.0) % 360.0
    if angle < 22.5 or angle >= 337.5:
        return "↑"
    if angle < 67.5:
        return "↗"
    if angle < 112.5:
        return "→"
    if angle < 157.5:
        return "↘"
    if angle < 202.5:
        return "↓"
    if angle < 247.5:
        return "↙"
    if angle < 292.5:
        return "←"
    return "↖"


def format_distance(distance_m: float) -> str:
    if distance_m < 1000.0:
        return f"{distance_m:.0f} m"
    return f"{distance_m / 1000.0:.2f} km"


class NavigatorOverlay:
    def __init__(self, master: tk.Misc):
        self.master = master
        self.window: tk.Toplevel | None = None
        self.target: dict[str, Any] | None = None
        self.target_system: str | None = None

        self.title_label: tk.Label | None = None
        self.body_label: tk.Label | None = None
        self.arrow_label: tk.Label | None = None
        self.distance_label: tk.Label | None = None

        self._drag_x = 0
        self._drag_y = 0

    def start(self, record: dict[str, Any], current_system: str | None = None) -> None:
        self.target = dict(record)
        self.target_system = str(
            _first(record, "system", "system_name", "star_system")
            or current_system
            or ""
        ).strip() or None

        self._ensure_window()
        material = _first(record, "commodity", "material") or "Community deposit"
        body = _first(record, "body", "body_name", "planet_name") or "Unknown body"
        display_body = _compact_body_name(body, self.target_system)

        self.title_label.config(text=str(material))
        self.body_label.config(text=f"Body: {display_body}")
        self.arrow_label.config(text="•")
        self.distance_label.config(text="Waiting for position")

        self.window.deiconify()
        self.window.lift()

    def stop(self) -> None:
        self.target = None
        self.target_system = None
        if self.window is not None:
            self.window.withdraw()

    def destroy(self) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None
        self.target = None

    def update_status(
        self,
        status: dict[str, Any],
        *,
        current_system: str | None = None,
        current_body: str | None = None,
    ) -> None:
        if self.target is None or self.window is None:
            return

        target_body = _first(self.target, "body", "body_name", "planet_name")
        status_body = status.get("BodyName") or current_body

        if self.target_system and current_system and not _same_name(
            self.target_system, current_system
        ):
            self.arrow_label.config(text="◎")
            self.distance_label.config(text=f"Travel to {self.target_system}")
            return

        if target_body and status_body and not _same_name(target_body, status_body):
            self.arrow_label.config(text="◎")
            self.distance_label.config(
                text=f"Approach {_compact_body_name(target_body, self.target_system)}"
            )
            return

        latitude = _float(status.get("Latitude"))
        longitude = _float(status.get("Longitude"))
        heading = _float(status.get("Heading"))
        target_lat = _float(_first(self.target, "latitude", "lat"))
        target_lon = _float(_first(self.target, "longitude", "lon", "lng"))
        radius = _float(status.get("PlanetRadius"))
        if radius is None:
            radius = _float(_first(self.target, "planet_radius", "body_radius"))

        if latitude is None or longitude is None:
            self.arrow_label.config(text="•")
            self.distance_label.config(text="Waiting for position")
            return

        if target_lat is None or target_lon is None:
            self.arrow_label.config(text="!")
            self.distance_label.config(text="No target coordinates")
            return

        if radius is None or radius <= 0:
            self.arrow_label.config(text="•")
            self.distance_label.config(text="Waiting for planet radius")
            return

        distance_m, bearing = surface_distance_and_bearing(
            latitude,
            longitude,
            target_lat,
            target_lon,
            radius,
        )

        if heading is None:
            arrow = "↑"
        else:
            delta = signed_heading_delta(bearing, heading)
            arrow = direction_arrow(delta)

        self.arrow_label.config(text=arrow)
        self.distance_label.config(text=format_distance(distance_m))

    def _ensure_window(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            return

        window = tk.Toplevel(self.master)
        self.window = window
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        try:
            window.attributes("-alpha", 0.94)
        except tk.TclError:
            pass
        window.configure(background=BACKGROUND)
        window.geometry(f"{HUD_WIDTH}x{HUD_HEIGHT}+80+120")
        window.resizable(False, False)

        container = tk.Frame(
            window,
            background=BACKGROUND,
            highlightbackground=ACCENT,
            highlightcolor=ACCENT,
            highlightthickness=1,
            padx=9,
            pady=5,
        )
        container.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(container, background=BACKGROUND)
        top.pack(fill=tk.X)

        self.title_label = tk.Label(
            top,
            text="Community deposit",
            background=BACKGROUND,
            foreground=ACCENT,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        close = tk.Label(
            top,
            text="×",
            background=BACKGROUND,
            foreground=MUTED,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=3,
        )
        close.pack(side=tk.RIGHT)
        close.bind("<Button-1>", lambda _event: self.stop())

        self.body_label = tk.Label(
            container,
            text="",
            background=BACKGROUND,
            foreground=MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.body_label.pack(fill=tk.X, pady=(0, 0))

        self.arrow_label = tk.Label(
            container,
            text="•",
            background=BACKGROUND,
            foreground=ACCENT,
            font=("Segoe UI Symbol", 28, "bold"),
        )
        self.arrow_label.pack(pady=(-3, -3))

        self.distance_label = tk.Label(
            container,
            text="",
            background=BACKGROUND,
            foreground=TEXT,
            font=("Segoe UI", 14, "bold"),
        )
        self.distance_label.pack()

        for widget in (window, container, top, self.title_label, self.body_label):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)

    def _drag_start(self, event: tk.Event) -> None:
        if self.window is None:
            return
        self._drag_x = event.x_root - self.window.winfo_x()
        self._drag_y = event.y_root - self.window.winfo_y()

    def _drag_move(self, event: tk.Event) -> None:
        if self.window is None:
            return
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.window.geometry(f"+{x}+{y}")
