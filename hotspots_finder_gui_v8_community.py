#!/usr/bin/env python3

"""v8 GUI entry point with Community Deposits support.

Kept as a thin layer over the already-tested v8 interface while features are
being completed. The GUI can be consolidated/refined after functionality is
finished.
"""

import threading
import tkinter as tk
from tkinter import messagebox

import community_deposits
import rhinospotter_sync_service
from hotspots_finder_gui_v8 import APP_TITLE, COLORS, FinderV8App


COMMUNITY_FALLBACK_HEADERS = [
    "System",
    "Body",
    "Commodity",
    "Latitude",
    "Longitude",
    "Reports",
    "Updated",
]


class FinderV8CommunityApp(FinderV8App):
    def _build_ui(self):
        # Tk has already been initialised by FinderV8App.__init__ at this point.
        self.community_deposits_enabled = tk.BooleanVar(master=self, value=False)
        self.rhino_upload_running = False
        super()._build_ui()

    def _build_systems(self, parent):
        super()._build_systems(parent)

        community = tk.Frame(parent, bg=COLORS["panel"])
        community.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(
            community,
            text="COMMUNITY DEPOSITS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        tk.Checkbutton(
            community,
            text="Show Community Deposits",
            variable=self.community_deposits_enabled,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["text"],
            selectcolor="#404040",
            highlightthickness=0,
            bd=0,
            anchor="w",
        ).pack(fill="x")

        self.rhino_upload_button = tk.Button(
            community,
            text="Upload RhinoSpotter Deposits",
            command=self.start_rhino_upload,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            disabledforeground="#777777",
            relief="flat",
            padx=10,
            pady=5,
        )
        self.rhino_upload_button.pack(fill="x", pady=(6, 0))

        tk.Label(
            community,
            text=(
                "Reads deposits from the shared Cloudflare database for the "
                "selected systems. Upload reads RhinoSpotter local bookmarks."
            ),
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            justify="left",
            wraplength=245,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

    def _build_results(self, parent):
        super()._build_results(parent)

        self.community_tab = tk.Frame(self.notebook, bg=COLORS["panel"])
        self.notebook.add(self.community_tab, text="Community Deposits")
        self.community_tree = self._make_tree(self.community_tab)

    def _collect_config(self):
        config = super()._collect_config()
        config["community_deposits_enabled"] = self.community_deposits_enabled.get()
        return config

    def _scan_complete(self, result):
        super()._scan_complete(result)
        self._populate_tree(
            self.community_tree,
            result.get("community_headers") or COMMUNITY_FALLBACK_HEADERS,
            result.get("community_rows", []),
        )

    def start_rhino_upload(self):
        if self.rhino_upload_running:
            return

        if self.running:
            messagebox.showwarning(
                APP_TITLE,
                "Wait for the current scan to finish before uploading RhinoSpotter deposits.",
                parent=self,
            )
            return

        self.rhino_upload_running = True
        self.rhino_upload_button.configure(state="disabled")
        self.scan_button.configure(state="disabled")
        self.progress.start(12)
        self.status_var.set("Uploading RhinoSpotter deposits...")

        systems = self._system_list()
        refresh_after_upload = self.community_deposits_enabled.get() and bool(systems)

        threading.Thread(
            target=self._rhino_upload_worker,
            args=(systems, refresh_after_upload),
            daemon=True,
        ).start()

    def _rhino_upload_worker(self, systems, refresh_after_upload):
        try:
            summary = rhinospotter_sync_service.sync_cards()

            community_headers = []
            community_rows = []
            if refresh_after_upload:
                community_headers, community_rows = (
                    community_deposits.fetch_deposits_for_systems(systems)
                )

            self.after(
                0,
                self._rhino_upload_complete,
                summary,
                community_headers,
                community_rows,
            )
        except Exception as exc:
            self.after(0, self._rhino_upload_failed, str(exc))

    def _rhino_upload_complete(self, summary, community_headers, community_rows):
        if community_headers or community_rows:
            self._populate_tree(
                self.community_tree,
                community_headers or COMMUNITY_FALLBACK_HEADERS,
                community_rows,
            )

        self._finish_rhino_upload("RhinoSpotter upload completed")

        messagebox.showinfo(
            APP_TITLE,
            (
                "RhinoSpotter synchronization completed.\n\n"
                f"JSON files found: {summary.get('files_found', 0)}\n"
                f"Valid records: {summary.get('records_valid', 0)}\n"
                f"New deposits: {summary.get('inserted', 0)}\n"
                "Reports matched to existing deposits: "
                f"{summary.get('matched', 0)}\n"
                f"Updated reports: {summary.get('updated', 0)}\n"
                f"Errors: {summary.get('errors', 0)}"
            ),
            parent=self,
        )

    def _rhino_upload_failed(self, message):
        self._finish_rhino_upload("RhinoSpotter upload error")
        messagebox.showerror(APP_TITLE, message, parent=self)

    def _finish_rhino_upload(self, status):
        self.rhino_upload_running = False
        self.progress.stop()
        self.rhino_upload_button.configure(state="normal")
        self.scan_button.configure(state="normal")
        self.status_var.set(status)


def main():
    app = FinderV8CommunityApp()
    app.mainloop()


if __name__ == "__main__":
    main()
