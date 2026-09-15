#!/usr/bin/env python3

"""v8 GUI entry point with Community Deposits support.

Kept as a thin layer over the already-tested v8 interface while features are
being completed. The GUI can be consolidated/refined after functionality is
finished.
"""

import tkinter as tk

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

        tk.Label(
            community,
            text="Reads deposits from the shared Cloudflare database for the selected systems.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            justify="left",
            wraplength=245,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(3, 0))

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


def main():
    app = FinderV8CommunityApp()
    app.mainloop()


if __name__ == "__main__":
    main()
