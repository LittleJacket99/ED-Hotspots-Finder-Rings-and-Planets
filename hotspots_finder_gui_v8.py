#!/usr/bin/env python3

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import finder_engine as legacy_engine
import local_scan


APP_TITLE = "Hotspots & Landables Finder v8"

COLORS = {
    "bg": "#1f1f1f",
    "panel": "#2b2b2b",
    "panel2": "#333333",
    "text": "#f1f1f1",
    "muted": "#b5b5b5",
    "orange": "#ffa500",
    "green": "#5acd57",
    "red": "#ff2a2a",
    "border": "#4d4d4d",
}


class FinderV8App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1320x820")
        self.minsize(1120, 700)
        self.configure(bg=COLORS["bg"])

        self.running = False
        self.cancel_event = threading.Event()

        self.hotspots_enabled = tk.BooleanVar(value=True)
        self.planets_enabled = tk.BooleanVar(value=True)
        self.only_pristine = tk.BooleanVar(value=False)
        self.only_landables = tk.BooleanVar(value=False)

        self.ring_vars = {
            "icy": tk.BooleanVar(value=False),
            "metallic": tk.BooleanVar(value=False),
            "metal rich": tk.BooleanVar(value=False),
            "rocky": tk.BooleanVar(value=False),
        }

        self.material_vars = {
            "platinum": tk.BooleanVar(value=False),
            "bromellite": tk.BooleanVar(value=False),
            "monazite": tk.BooleanVar(value=False),
        }

        self.planet_type_vars = {
            "icy": tk.BooleanVar(value=False),
            "metal rich": tk.BooleanVar(value=False),
            "high metal content": tk.BooleanVar(value=False),
            "rocky": tk.BooleanVar(value=False),
            "rocky ice": tk.BooleanVar(value=False),
        }

        self.power_state_vars = {
            "Unoccupied": tk.BooleanVar(value=False),
            "Exploited": tk.BooleanVar(value=False),
            "Fortified": tk.BooleanVar(value=False),
            "Stronghold": tk.BooleanVar(value=False),
        }

        self.faction_var = tk.StringVar()
        self.power_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.system_count_var = tk.StringVar(value="0 systems")

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Dark.TFrame",
            background=COLORS["bg"],
        )
        style.configure(
            "Panel.TFrame",
            background=COLORS["panel"],
        )
        style.configure(
            "Dark.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
        )
        style.configure(
            "Panel.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["text"],
        )
        style.configure(
            "Muted.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
        )
        style.configure(
            "Section.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "TCheckbutton",
            background=COLORS["panel"],
            foreground=COLORS["text"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", COLORS["panel"])],
            foreground=[("disabled", "#777777")],
        )
        style.configure(
            "TNotebook",
            background=COLORS["bg"],
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=COLORS["panel2"],
            foreground=COLORS["text"],
            padding=(14, 7),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLORS["panel"])],
            foreground=[("selected", COLORS["orange"])],
        )
        style.configure(
            "Treeview",
            background="#242424",
            foreground=COLORS["text"],
            fieldbackground="#242424",
            rowheight=25,
            bordercolor=COLORS["border"],
        )
        style.configure(
            "Treeview.Heading",
            background="#333333",
            foreground=COLORS["text"],
            relief="flat",
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#414141")],
        )

    def _build_ui(self):
        header = tk.Frame(self, bg="#242424", height=76)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Hotspots & Landables Finder",
            bg="#242424",
            fg=COLORS["orange"],
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", padx=18, pady=(12, 0))

        tk.Label(
            header,
            text="v8 local interface · Spansh · no Google Sheets",
            bg="#242424",
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=19, pady=(0, 8))

        main = tk.PanedWindow(
            self,
            orient="horizontal",
            bg=COLORS["bg"],
            sashwidth=5,
            bd=0,
            relief="flat",
        )
        main.pack(fill="both", expand=True, padx=10, pady=10)

        filters = tk.Frame(main, bg=COLORS["panel"], width=275)
        systems = tk.Frame(main, bg=COLORS["panel"], width=285)
        results = tk.Frame(main, bg=COLORS["panel"], width=700)

        main.add(filters, minsize=250)
        main.add(systems, minsize=260)
        main.add(results, minsize=520)

        self._build_filters(filters)
        self._build_systems(systems)
        self._build_results(results)
        self._build_bottom_bar()

    def _section(self, parent, title):
        tk.Label(
            parent,
            text=title,
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(11, 4))

    def _check(self, parent, text, variable, *, indent=12):
        widget = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["text"],
            selectcolor="#404040",
            highlightthickness=0,
            bd=0,
            anchor="w",
        )
        widget.pack(fill="x", padx=(indent, 8), pady=1)
        return widget

    def _build_filters(self, parent):
        canvas = tk.Canvas(
            parent,
            bg=COLORS["panel"],
            highlightthickness=0,
            bd=0,
        )
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS["panel"])

        inner.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(
                    int(-event.delta / 120),
                    "units",
                )
            return "break"

        canvas.bind(
            "<Enter>",
            lambda _e: canvas.bind_all(
                "<MouseWheel>",
                _on_mousewheel,
            ),
        )

        canvas.bind(
            "<Leave>",
            lambda _e: canvas.unbind_all(
                "<MouseWheel>"
            ),
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._section(inner, "HOTSPOTS")
        self._check(inner, "Enable hotspots", self.hotspots_enabled)

        tk.Label(
            inner,
            text="Ring types",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=24, pady=(5, 1))
        for key, label in (
            ("icy", "Icy"),
            ("metallic", "Metallic"),
            ("metal rich", "Metal Rich"),
            ("rocky", "Rocky"),
        ):
            self._check(inner, label, self.ring_vars[key], indent=28)

        tk.Label(
            inner,
            text="Materials",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=24, pady=(5, 1))
        for key, label in (
            ("platinum", "Platinum"),
            ("bromellite", "Bromellite"),
            ("monazite", "Monazite"),
        ):
            self._check(inner, label, self.material_vars[key], indent=28)

        self._check(inner, "Only pristine", self.only_pristine, indent=24)

        self._section(inner, "PLANETS")
        self._check(inner, "Enable planets", self.planets_enabled)
        self._check(inner, "Only landables", self.only_landables, indent=24)

        tk.Label(
            inner,
            text="Planet types",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=24, pady=(5, 1))
        for key, label in (
            ("icy", "Icy"),
            ("metal rich", "Metal Rich"),
            ("high metal content", "High Metal Content"),
            ("rocky", "Rocky"),
            ("rocky ice", "Rocky Ice"),
        ):
            self._check(inner, label, self.planet_type_vars[key], indent=28)

        self._section(inner, "SYSTEM FILTERS")

        tk.Label(
            inner,
            text="Faction",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=12)
        faction = tk.Entry(
            inner,
            textvariable=self.faction_var,
            bg="#3b3b3b",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
        )
        faction.pack(fill="x", padx=12, pady=(2, 8), ipady=5)

        tk.Label(
            inner,
            text="Power",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=12)
        power = ttk.Combobox(
            inner,
            textvariable=self.power_var,
            values=[""] + list(legacy_engine.POWER_LIST),
            state="readonly",
        )
        power.pack(fill="x", padx=12, pady=(2, 6))

        tk.Label(
            inner,
            text="Power states",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=12, pady=(3, 1))

        for state in ("Unoccupied", "Exploited", "Fortified", "Stronghold"):
            self._check(inner, state, self.power_state_vars[state], indent=24)

        tk.Frame(inner, bg=COLORS["panel"], height=12).pack()

    def _build_systems(self, parent):
        tk.Label(
            parent,
            text="SYSTEMS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(11, 0))

        tk.Label(
            parent,
            textvariable=self.system_count_var,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
        ).pack(anchor="w", padx=12, pady=(0, 7))

        text_frame = tk.Frame(parent, bg=COLORS["panel"])
        text_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.systems_text = tk.Text(
            text_frame,
            bg="#242424",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            wrap="none",
            font=("Consolas", 10),
            undo=True,
        )
        scroll_y = tk.Scrollbar(text_frame, orient="vertical", command=self.systems_text.yview)
        scroll_x = tk.Scrollbar(text_frame, orient="horizontal", command=self.systems_text.xview)
        self.systems_text.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )
        self.systems_text.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.systems_text.bind("<KeyRelease>", lambda _e: self._refresh_system_count())

        buttons = tk.Frame(parent, bg=COLORS["panel"])
        buttons.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            buttons,
            text="Clear",
            command=self._clear_systems,
            bg="#3a4148",
            fg=COLORS["text"],
            activebackground="#46515c",
            activeforeground=COLORS["text"],
            relief="flat",
            padx=12,
        ).pack(side="left")

        tk.Label(
            parent,
            text=(
                "Optional manual input. System Filters narrow this list; "
                "scan results stay in Results."
            ),
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            justify="left",
            wraplength=245,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=(0, 12))

    def _build_results(self, parent):
        tk.Label(
            parent,
            text="RESULTS",
            bg=COLORS["panel"],
            fg=COLORS["orange"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(11, 7))

        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.hotspot_tab = tk.Frame(self.notebook, bg=COLORS["panel"])
        self.planet_tab = tk.Frame(self.notebook, bg=COLORS["panel"])

        self.notebook.add(self.hotspot_tab, text="Hotspots")
        self.notebook.add(self.planet_tab, text="Planets")

        self.hotspot_tree = self._make_tree(self.hotspot_tab)
        self.planet_tree = self._make_tree(self.planet_tab)

    def _make_tree(self, parent):
        frame = tk.Frame(parent, bg=COLORS["panel"])
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, show="headings", selectmode="extended")
        ybar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)

        tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def _build_bottom_bar(self):
        bar = tk.Frame(self, bg="#242424", height=58)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.scan_button = tk.Button(
            bar,
            text="SCAN",
            command=self.start_scan,
            bg=COLORS["orange"],
            fg="#1f1f1f",
            activebackground="#ffb326",
            activeforeground="#1f1f1f",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            width=12,
        )
        self.scan_button.pack(side="left", padx=(14, 6), pady=12)

        self.stop_button = tk.Button(
            bar,
            text="STOP",
            command=self.stop_scan,
            bg="#4b3333",
            fg=COLORS["text"],
            activebackground="#603d3d",
            activeforeground=COLORS["text"],
            disabledforeground="#777777",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            width=10,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=6, pady=12)

        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=190)
        self.progress.pack(side="left", padx=14, pady=18)

        tk.Label(
            bar,
            textvariable=self.status_var,
            bg="#242424",
            fg=COLORS["text"],
            font=("Segoe UI", 10),
        ).pack(side="left", padx=8)

    def _system_list(self):
        lines = self.systems_text.get("1.0", "end").splitlines()
        seen = set()
        systems = []
        for line in lines:
            value = line.strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            systems.append(value)
        return systems

    def _refresh_system_count(self):
        self.system_count_var.set(f"{len(self._system_list())} systems")

    def _clear_systems(self):
        self.systems_text.delete("1.0", "end")
        self._refresh_system_count()

    def _collect_config(self):
        return {
            "systems": self._system_list(),
            "hotspots_enabled": self.hotspots_enabled.get(),
            "planets_enabled": self.planets_enabled.get(),
            "ring_types": {
                key: var.get()
                for key, var in self.ring_vars.items()
            },
            "materials": {
                key: var.get()
                for key, var in self.material_vars.items()
            },
            "only_pristine": self.only_pristine.get(),
            "only_landables": self.only_landables.get(),
            "planet_types": {
                key: var.get()
                for key, var in self.planet_type_vars.items()
            },
            "faction_name": self.faction_var.get().strip(),
            "power_name": self.power_var.get().strip(),
            "power_states": {
                key: var.get()
                for key, var in self.power_state_vars.items()
            },
        }

    def start_scan(self):
        if self.running:
            return

        config = self._collect_config()
        if (
            not config["systems"]
            and not config["faction_name"]
            and not config["power_name"]
        ):
            messagebox.showwarning(
                APP_TITLE,
                "Add at least one system, or enter a Faction or Power.",
                parent=self,
            )
            return

        self.running = True
        self.cancel_event.clear()
        self.scan_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress.start(12)
        self.status_var.set("Scanning...")

        threading.Thread(
            target=self._scan_worker,
            args=(config,),
            daemon=True,
        ).start()

    def stop_scan(self):
        if not self.running:
            return
        self.cancel_event.set()
        self.stop_button.configure(state="disabled")
        self.status_var.set("Stopping...")

    def _scan_worker(self, config):
        try:
            result = local_scan.run_local_scan(
                config,
                cancel_event=self.cancel_event,
            )
            self.after(0, self._scan_complete, result)
        except legacy_engine.ScanCancelled:
            self.after(0, self._scan_cancelled)
        except Exception as exc:
            self.after(0, self._scan_failed, str(exc))

    def _scan_complete(self, result):
        self._populate_tree(
            self.hotspot_tree,
            result.get("hotspot_headers", legacy_engine.HOTSPOT_HEADERS),
            result.get("hotspot_rows", []),
        )
        self._populate_tree(
            self.planet_tree,
            result.get("planet_headers", legacy_engine.PLANET_HEADERS),
            result.get("planet_rows", []),
        )

        status = result.get("status", "COMPLETED")
        self._finish_scan(status.replace("_", " ").title())

    def _scan_cancelled(self):
        self._finish_scan("Cancelled")

    def _scan_failed(self, message):
        self._finish_scan("Error")
        messagebox.showerror(APP_TITLE, message, parent=self)

    def _finish_scan(self, status):
        self.running = False
        self.progress.stop()
        self.scan_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_var.set(status)

    def _populate_tree(self, tree, headers, rows):
        tree.delete(*tree.get_children())
        tree["columns"] = list(headers)

        for header in headers:
            tree.heading(
                header,
                text=header,
                command=lambda h=header, t=tree: self._sort_tree(t, h, False),
            )
            tree.column(header, width=125, minwidth=80, stretch=True)

        for row in rows:
            values = [row.get(header, "") for header in headers]
            tree.insert("", "end", values=values)

    def _sort_tree(self, tree, column, reverse):
        items = []
        for iid in tree.get_children(""):
            value = tree.set(iid, column)
            try:
                key = float(value)
            except (TypeError, ValueError):
                key = str(value).casefold()
            items.append((key, iid))

        try:
            items.sort(reverse=reverse)
        except TypeError:
            items.sort(key=lambda pair: str(pair[0]).casefold(), reverse=reverse)

        for index, (_value, iid) in enumerate(items):
            tree.move(iid, "", index)

        tree.heading(
            column,
            command=lambda: self._sort_tree(tree, column, not reverse),
        )


def main():
    app = FinderV8App()
    app.mainloop()


if __name__ == "__main__":
    main()
