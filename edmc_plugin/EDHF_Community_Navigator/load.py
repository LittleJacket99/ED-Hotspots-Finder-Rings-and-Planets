from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any

from config import appname, config
from theme import theme

from EDHF_Community_Navigator.community_api import fetch_system_deposits
from EDHF_Community_Navigator.navigator import NavigatorOverlay
from EDHF_Community_Navigator.results_window import DepositsWindow
from EDHF_Community_Navigator.rhinospotter_client import sync_bookmarks


VERSION = "0.1.0"
PLUGIN_NAME = "EDHF Community Navigator"
WORKER_EVENT = "<<EDHFCommunityNavigatorWorker>>"

plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f"{appname}.{plugin_name}")

_plugin_dir = ""
_frame: tk.Frame | None = None
_status: tk.Label | None = None
_sync_button: ttk.Button | None = None
_scan_button: ttk.Button | None = None
_navigator: NavigatorOverlay | None = None
_results_window: DepositsWindow | None = None

_current_system: str | None = None
_current_body: str | None = None
_worker_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
_stopping = False


def plugin_start3(plugin_dir: str) -> str:
    global _plugin_dir
    _plugin_dir = plugin_dir
    logger.info("Starting %s v%s", PLUGIN_NAME, VERSION)
    return PLUGIN_NAME


def plugin_app(parent: tk.Frame) -> tk.Frame:
    global _frame, _status, _sync_button, _scan_button, _navigator

    frame = tk.Frame(parent)
    _frame = frame
    _navigator = NavigatorOverlay(parent)

    heading = tk.Label(
        frame,
        text="Hotspots Finder Community",
        font=("TkDefaultFont", 9, "bold"),
        anchor="w",
    )
    heading.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 3))

    _sync_button = ttk.Button(
        frame,
        text="Sync Bookmarks",
        command=_start_sync,
    )
    _sync_button.grid(row=1, column=0, sticky=tk.EW, padx=(0, 3))

    _scan_button = ttk.Button(
        frame,
        text="Scan Deposits",
        command=_start_scan,
    )
    _scan_button.grid(row=1, column=1, sticky=tk.EW, padx=(3, 0))

    _status = tk.Label(
        frame,
        text="Ready",
        anchor="w",
    )
    _status.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(3, 0))

    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=1)

    frame.bind_all(WORKER_EVENT, _handle_worker_event, add="+")
    theme.update(frame)
    return frame


def plugin_stop() -> None:
    global _stopping
    _stopping = True

    if _navigator is not None:
        _navigator.destroy()

    if _frame is not None:
        try:
            _frame.unbind_all(WORKER_EVENT)
        except tk.TclError:
            pass

    logger.info("Stopped %s", PLUGIN_NAME)


def journal_entry(
    cmdr: str,
    is_beta: bool,
    system: str | None,
    station: str | None,
    entry: dict[str, Any],
    state: dict[str, Any],
) -> str | None:
    del cmdr, is_beta, station, state
    global _current_system, _current_body

    if system:
        _current_system = system

    event = entry.get("event")
    if event in {"FSDJump", "CarrierJump"}:
        _current_system = entry.get("StarSystem") or system or _current_system
        _current_body = None
    elif event == "Location":
        _current_system = entry.get("StarSystem") or system or _current_system
        _current_body = entry.get("Body") or entry.get("BodyName") or _current_body
    elif event in {
        "ApproachBody",
        "Touchdown",
        "SupercruiseExit",
        "Liftoff",
    }:
        _current_body = entry.get("Body") or entry.get("BodyName") or _current_body

    return None


def dashboard_entry(
    cmdr: str,
    is_beta: bool,
    entry: dict[str, Any],
) -> None:
    del cmdr, is_beta
    global _current_body

    if entry.get("BodyName"):
        _current_body = entry.get("BodyName")

    if _navigator is not None:
        _navigator.update_status(
            entry,
            current_system=_current_system,
            current_body=_current_body,
        )


def _set_busy(busy: bool, text: str) -> None:
    state = tk.DISABLED if busy else tk.NORMAL
    if _sync_button is not None:
        _sync_button.config(state=state)
    if _scan_button is not None:
        _scan_button.config(state=state)
    if _status is not None:
        _status.config(text=text)


def _start_sync() -> None:
    if not _plugin_dir:
        _set_busy(False, "Plugin path unavailable")
        return

    _set_busy(True, "Syncing RhinoSpotter bookmarks…")
    threading.Thread(
        target=_sync_worker,
        name="EDHF-RhinoSpotter-Sync",
        daemon=True,
    ).start()


def _start_scan() -> None:
    system = (_current_system or "").strip()
    if not system:
        _set_busy(False, "Current system not available yet")
        return

    _set_busy(True, f"Scanning {system}…")
    threading.Thread(
        target=_scan_worker,
        args=(system,),
        name="EDHF-Community-Scan",
        daemon=True,
    ).start()


def _sync_worker() -> None:
    try:
        summary = sync_bookmarks(_plugin_dir)
    except Exception as exc:
        logger.exception("RhinoSpotter synchronization failed")
        _post_worker_result("sync_error", str(exc))
    else:
        _post_worker_result("sync_ok", summary)


def _scan_worker(system: str) -> None:
    try:
        records = fetch_system_deposits(system)
    except Exception as exc:
        logger.exception("Community Deposits scan failed")
        _post_worker_result("scan_error", (system, str(exc)))
    else:
        _post_worker_result("scan_ok", (system, records))


def _post_worker_result(kind: str, payload: Any) -> None:
    _worker_queue.put((kind, payload))

    if _stopping or config.shutting_down or _frame is None:
        return

    try:
        _frame.event_generate(WORKER_EVENT, when="tail")
    except tk.TclError:
        pass


def _handle_worker_event(_event: tk.Event | None = None) -> None:
    while True:
        try:
            kind, payload = _worker_queue.get_nowait()
        except queue.Empty:
            break

        if kind == "sync_ok":
            _handle_sync_ok(payload)
        elif kind == "sync_error":
            _set_busy(False, f"Sync failed: {payload}")
        elif kind == "scan_ok":
            system, records = payload
            _handle_scan_ok(system, records)
        elif kind == "scan_error":
            system, message = payload
            _set_busy(False, f"{system}: scan failed — {message}")


def _handle_sync_ok(summary: dict[str, Any]) -> None:
    inserted = int(summary.get("inserted", 0) or 0)
    matched = int(summary.get("matched", 0) or 0)
    updated = int(summary.get("updated", 0) or 0)
    errors = int(summary.get("errors", 0) or 0)
    found = int(summary.get("records_found", 0) or 0)

    text = (
        f"Sync: {found} bookmarks · "
        f"{inserted} new · {matched} matched · {updated} updated"
    )
    if errors:
        text += f" · {errors} errors"

    _set_busy(False, text)


def _handle_scan_ok(system: str, records: list[dict[str, Any]]) -> None:
    global _results_window

    _set_busy(False, f"{system}: {len(records)} community deposits")

    if not records or _frame is None:
        return

    try:
        if (
            _results_window is not None
            and _results_window.window.winfo_exists()
        ):
            _results_window.window.destroy()
    except tk.TclError:
        pass

    _results_window = DepositsWindow(
        _frame,
        system=system,
        records=records,
        on_track=lambda record: _track_record(record, system),
    )


def _track_record(record: dict[str, Any], system: str) -> None:
    if _navigator is None:
        return

    enriched = dict(record)
    enriched.setdefault("system", system)
    _navigator.start(enriched, current_system=_current_system)

    material = (
        record.get("commodity")
        or record.get("material")
        or "deposit"
    )
    body = (
        record.get("body")
        or record.get("body_name")
        or record.get("planet_name")
        or "body"
    )
    if _status is not None:
        _status.config(text=f"Tracking {material} on {body}")
