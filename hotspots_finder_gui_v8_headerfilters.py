#!/usr/bin/env python3

import tkinter as tk

from hotspots_finder_gui_v8_community import FinderV8CommunityApp


class FinderV8HeaderFiltersApp(FinderV8CommunityApp):
    def _build_results(self, parent):
        super()._build_results(parent)

        # Hide the temporary filter bar. Its comboboxes remain alive and are
        # reused internally to keep the already-tested cascading filter logic.
        children = self.community_tab.winfo_children()
        if children:
            children[0].pack_forget()

    def _apply_community_filters(self):
        super()._apply_community_filters()
        self._configure_header_filters()

    def _configure_header_filters(self):
        for column in ("Body", "Commodity"):
            variable = (
                self.community_body_filter
                if column == "Body"
                else self.community_commodity_filter
            )
            active = (variable.get() or "All") != "All"
            marker = " ▼*" if active else " ▼"
            self.community_tree.heading(
                column,
                text=column + marker,
                command=lambda c=column: self._show_header_filter(c),
            )

    def _show_header_filter(self, column):
        if column == "Body":
            variable = self.community_body_filter
            choices = list(self.community_body_combo["values"])
        else:
            variable = self.community_commodity_filter
            choices = list(self.community_commodity_combo["values"])

        menu = tk.Menu(self, tearoff=False)
        for value in choices:
            label = str(value)
            if label == variable.get():
                label = "✓ " + label
            menu.add_command(
                label=label,
                command=lambda v=value, var=variable: self._set_header_filter(var, v),
            )

        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def _set_header_filter(self, variable, value):
        variable.set(value)
        self._community_filter_changed()


def main():
    app = FinderV8HeaderFiltersApp()
    app.mainloop()


if __name__ == "__main__":
    main()
