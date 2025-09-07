# triode/address_bar.py
from PySide6.QtWidgets import QLineEdit
from .url_router import URLRouter
#from .tab_manager import TabManager
from .models.route import URLRoute
from .explorer.tab import ExplorerTab
from .browser.tab import BrowserTab
from .generic_tab import GenericTab
from .terminal.tab import TerminalTab
import os

class AddressBarController:
    def __init__(self, router: URLRouter, tab_manager: "TabManager"):
        self.router = router
        self.tab_manager = tab_manager
        self.line_edit: QLineEdit | None = None

    def bind(self, line_edit: QLineEdit) -> None:
        self.line_edit = line_edit
        self.line_edit.returnPressed.connect(self._on_submit)

    def attach_tab_signals(self, tab):
        if isinstance(tab, BrowserTab):
            tab.url_changed.connect(self._on_tab_url_changed)
        elif hasattr(tab, "path_changed"):
            # This handles both ExplorerTab and TerminalTab
            tab.path_changed.connect(self._on_tab_path_changed)

    def set_route_from_browser(self, url: str):
        print("AddressBarController received url:", url)
        route = URLRoute(scheme="http", path=url)  # or parse scheme dynamically
        self.set_route(route)

    def set_route(self, route: URLRoute) -> None:
        if self.line_edit:
            self.line_edit.setText(self.router.to_text(route))

    def set_route_file(self, path: str) -> None:
        """Update address bar with a file:// or term:// path."""
        if self.line_edit:
            # Check if it's a terminal tab
            print("Setting file path in address bar:", path)
            if isinstance(self.tab_manager.currentWidget(), TerminalTab):
                self.line_edit.setText(f"term://{path}")
                # Messy fix for double term:// bug
                # Listen, if it works, it works
                if self.line_edit.text().startswith("term://term://"):
                    self.line_edit.setText(f"{path}")
            else:
                self.line_edit.setText(f"file://{path}")

    def _on_tab_url_changed(self, url: str):
        if self.line_edit:
            self.line_edit.setText(url)

    def _on_tab_path_changed(self, path: str):
        if self.line_edit:
            # Check if it's a terminal tab
            if isinstance(self.tab_manager.currentWidget(), TerminalTab):
                self.line_edit.setText(f"term://{path}")
            else:
                self.line_edit.setText(f"file://{path}")

    def _on_submit(self) -> None:
        if not self.line_edit:
            return
        text = self.line_edit.text()
        route = self.router.parse(text)
        current_tab = self.tab_manager.currentWidget()
        
        # Prevent creating new terminal if we're already in one
        if isinstance(current_tab, TerminalTab) and route.scheme == "term":
            if route.path:
                current_tab.navigate_to(route.path)
            return
            
        if isinstance(current_tab, ExplorerTab):
            if route.scheme in ("http", "https"):
                newtab = self.tab_manager.create_browser_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)
            elif route.scheme == "file":
                current_tab.navigate_to(route.path)
            elif route.scheme == "term":
                newtab = self.tab_manager.create_terminal_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)

        elif isinstance(current_tab, BrowserTab):
            if route.scheme == "file":
                newtab = self.tab_manager.create_explorer_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)
            elif route.scheme == "term":
                newtab = self.tab_manager.create_terminal_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)
            else:  # http/https
                current_tab.navigate_to(route.path)

        elif isinstance(current_tab, TerminalTab):
            if route.scheme == "file":
                newtab = self.tab_manager.create_explorer_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)
            elif route.scheme in ("http", "https"):
                newtab = self.tab_manager.create_browser_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)
            elif route.scheme == "term":
                current_tab.navigate_to(route.path)

        elif isinstance(current_tab, GenericTab):
            if route.scheme == "file":
                newtab = self.tab_manager.create_explorer_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)
            elif route.scheme in ("http", "https"):
                newtab = self.tab_manager.create_browser_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)
            elif route.scheme == "term":
                newtab = self.tab_manager.create_terminal_tab(route.path)
                self.tab_manager.destroy_tab(current_tab, newtab)

        else:
            print(f"[AddressBar] Unknown tab type: {type(current_tab)}")
        