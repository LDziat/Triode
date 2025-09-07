# triode/tab_manager.py
from PySide6.QtWidgets import QTabWidget, QTabBar, QApplication
from .browser.factory import get_browser_backend
from .url_router import URLRouter
from .models.route import URLRoute
from .explorer.tab import ExplorerTab
from .browser.tab import BrowserTab
from .generic_tab import GenericTab
import os

# triode/tab_manager.py
from typing import Optional
import os

from PySide6.QtWidgets import QTabWidget, QWidget, QTabBar
from PySide6.QtCore import Qt

from .browser.factory import get_browser_backend
from .url_router import URLRouter
from .models.route import URLRoute
from .explorer.tab import ExplorerTab
from .browser.tab import BrowserTab
from .generic_tab import GenericTab
from .address_bar import AddressBarController


class TabManager(QTabWidget):
    """
    TabManager keeps a permanent "+" tab at index 0 (no close button).
    All user tabs are inserted at index 1+ (so plus stays at 0).
    """

    PLUS_LABEL = "+"

    def __init__(
        self,
        router: URLRouter,
        settings: dict,
        address_controller = None,
        parent=None,
    ):
        super().__init__(parent)
        self.router = router
        self.settings = settings
        self.address_controller = address_controller
        self.backend = get_browser_backend(settings["browser"]["engine"])
        self.clipboard = None

        # regular tab behavior
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._handle_tab_close)
        self.currentChanged.connect(self._on_current_changed)

        # Create and lock the permanent "+" tab at index 0
        self._plus_widget = QWidget()
        super().insertTab(0, self._plus_widget, self.PLUS_LABEL)
        self._hide_plus_close_button()

        # Start with one content tab optionally
        # (MainWindow can call create_browser_tab/create_explorer_tab as needed)

    # ---------- PLUS TAB helpers ----------
    def _hide_plus_close_button(self) -> None:
        """Remove tab-close buttons from the plus tab (index 0)."""
        plus_index = 0
        # Defensive: if plus isn't at 0, find it and move it
        if self._find_plus_tab_index() != 0:
            self._ensure_plus_tab_at_zero()
        # Remove close buttons for plus
        self.tabBar().setTabButton(plus_index, QTabBar.RightSide, None)
        self.tabBar().setTabButton(plus_index, QTabBar.LeftSide, None)
        # Optional visual: make it disabled so it doesn't look closable
        self.tabBar().setTabEnabled(plus_index, True)

    def _find_plus_tab_index(self) -> int:
        for i in range(self.count()):
            if self.tabText(i) == self.PLUS_LABEL:
                return i
        return -1

    def _ensure_plus_tab_at_zero(self) -> None:
        """If plus somehow moved, re-insert it at 0 (defensive)."""
        idx = self._find_plus_tab_index()
        if idx == -1:
            # recreate plus
            self._plus_widget = QWidget()
            super().insertTab(0, self._plus_widget, self.PLUS_LABEL)
        elif idx != 0:
            widget = self.widget(idx)
            text = self.tabText(idx)
            super().removeTab(idx)
            super().insertTab(0, widget, text)
        # Ensure close button hidden
        self._hide_plus_close_button()

    # ---------- Creation helpers ----------
    def create_generic_tab(self) -> GenericTab:
        """Create a GenericTab at index 1 (right after plus)."""
        tab = GenericTab(self)
        insert_index = 1  # always place after the plus tab
        super().insertTab(insert_index, tab, "New Tab")
        self.setCurrentIndex(insert_index)
        return tab

    def _get_prefix(self, tab_type: str) -> str:
        """Get prefix based on settings and tab type."""
        prefix_style = self.settings.get("tab", {}).get("prefix_style")
        
        if not prefix_style:
            return ""
            
        prefixes = {
            "long": {
                "browser": "Browser - ",
                "explorer": "Explorer - ",
                "terminal": "Terminal - "
            },
            "short": {
                "browser": "B - ",
                "explorer": "E - ",
                "terminal": "T - "
            },
            "icon": {
                "browser": "🌐 ",
                "explorer": "📁 ",
                "terminal": "⌨️ "
            }
        }
        
        style_prefixes = prefixes.get(prefix_style, {})
        return style_prefixes.get(tab_type, "")

    def create_browser_tab(self, url: str = "https://example.com") -> BrowserTab:
        tab = BrowserTab(url)
        insert_index = 1
        prefix = self._get_prefix('browser')
        
        # Insert tab first so indexOf works
        super().insertTab(insert_index, tab, f"{prefix}Loading...")
        
        # Bind title updates
        tab._view.titleChanged.connect(
            lambda title, t=tab: self._apply_title_to_widget(t, title, 'browser')
        )
        
        # Bind URL updates for address bar
        if self.address_controller:
            tab.url_changed.connect(self.address_controller.set_route_from_browser)
            self.address_controller.attach_tab_signals(tab)
        
        self.setCurrentIndex(insert_index)
        return tab


    def create_explorer_tab(self, initial_path: Optional[str] = None) -> ExplorerTab:
        path = initial_path or os.path.expanduser("~")
        tab = ExplorerTab(path)
        insert_index = 1
        prefix = self._get_prefix('explorer')
        
        # Insert tab first
        super().insertTab(insert_index, tab, f"{prefix}{os.path.basename(path)}")
        
        # Bind path updates for title
        tab.path_changed.connect(
            lambda path, t=tab: self._apply_title_to_widget(t, path, 'explorer')
        )
        
        # Bind path updates for address bar
        if self.address_controller:
            tab.path_changed.connect(self.address_controller.set_route_file)
        
        self.setCurrentIndex(insert_index)
        return tab

    def create_terminal_tab(self, initial_path: Optional[str] = None) -> "TerminalTab":
        from .terminal.tab import TerminalTab
        tab = TerminalTab(initial_path)
        insert_index = 1
        prefix = self._get_prefix('terminal')
        
        # Set initial title with prefix
        super().insertTab(insert_index, tab, f"{prefix}Terminal")
        
        # Connect path change signal
        tab.path_changed.connect(
            lambda path: self.setTabText(
                self.indexOf(tab), 
                f"{prefix}{os.path.basename(path)}"
            )
        )
        
        # Connect to address bar
        if self.address_controller:
            tab.path_changed.connect(
                lambda path: self.address_controller.set_route_file(f"term://{path}")
            )
        
        self.setCurrentIndex(insert_index)
        return tab

    # ---------- Close / Destroy ----------
    def _handle_tab_close(self, index: int) -> None:
        """Called by Qt when a tab close button is pressed."""
        # Do not allow closing the plus tab
        if index == 0 and self.tabText(index) == self.PLUS_LABEL:
            return
        widget = self.widget(index)
        if widget:
            self.destroy_tab(widget)

    def destroy_tab(self, widget: QWidget, dest_tab = None) -> None:
        """Safely remove a tab widget and delete it."""
        index = self.indexOf(widget)
        if index == -1:
            return

        # Never destroy the plus widget
        if index == 0 and widget is self._plus_widget:
            return

        # optional cleanup hook on the widget before deletion
        if hasattr(widget, "on_destroy"):
            try:
                widget.on_destroy()
            except Exception as e:
                # keep going; don't crash the UI
                print(f"[TabManager] Error calling on_destroy: {e}")

        super().removeTab(index)
        widget.deleteLater()

        # Focus the next sensible tab (prefer index 1, else 0)
        if dest_tab:
            dest_index = self.indexOf(dest_tab)
            if dest_index != -1:
                self.setCurrentIndex(dest_index)
        elif self.count() > 1:
            # set to the tab that ended up at the same index, or 1
            new_index = min(index, self.count() - 1)
            if new_index == 0:
                new_index = 1 if self.count() > 1 else 0
            self.setCurrentIndex(new_index)
        else:
            # Only plus tab remains; select it
            self.setCurrentIndex(0)



    # ---------- Tab change logic ----------
    def _on_current_changed(self, index: int) -> None:
        """Handle when the current tab changes (update address bar, re-hide plus)."""
        # Defensive: ensure plus still at index 0
        self._ensure_plus_tab_at_zero()
        # If user clicked the "+" tab, spawn a new GenericTab
        if index == 0 and self.tabText(0) == self.PLUS_LABEL:
            if self.count() > 1:
                new_tab = self.create_generic_tab()
                self.setCurrentWidget(new_tab)
            else:
                main_window = self.window()  # returns the top-level window containing this widget
                main_window.close()
            return
        # Update address bar according to the active tab
        self.on_tab_changed(index)


    def on_tab_changed(self, index: int) -> None:
        """Update the address bar using the currently active tab's state."""
        current_tab = self.widget(index)
        if not current_tab or not self.address_controller:
            return

        # BrowserTab (has _view from QWebEngineView or WebKit)
        if hasattr(current_tab, "_view"):
            try:
                url = current_tab._view.url().toString()
                #print(url)
            except Exception:
                url = ""
                #print("url not found error")
            
            if url.startswith(("http://", "https://")):
                scheme = "https" if url.startswith("https://") else "http"
                to_route = URLRoute(scheme=scheme, path=url)
                self.address_controller.set_route(to_route)
            elif url.startswith("file://"):
                # Convert file:// URL to local ExplorerTab
                path = url[7:]  # strip "file://"
                # Create a new ExplorerTab and replace current tab
                new_tab = self.create_explorer_tab(path)
                self.destroy_tab(current_tab, new_tab)
                self.setCurrentWidget(new_tab)
            else:
                # Unknown URL, fallback
                self.address_controller.set_route(URLRoute(scheme="unknown", path=url))
            return

        # ExplorerTab (has current_path attribute)
        if hasattr(current_tab, "current_path"):
            
            if hasattr(current_tab, "current_path"):
                self.address_controller.set_route_file(current_tab.current_path)
                self.address_controller.attach_tab_signals(current_tab)
                return
            return

        # TerminalTab (has cwd attribute)
        if hasattr(current_tab, "cwd"):
            self.address_controller.set_route_file(current_tab.cwd)
            return


        # GenericTab / unknown: leave address bar unchanged
        return

    # ---------- Clipboard helpers ----------
    def set_clipboard(self, action: str, paths: list[str]) -> None:
        """Set app clipboard; action is 'copy' or 'cut'."""
        if action not in ("copy", "cut"):
            raise ValueError("action must be 'copy' or 'cut'")
        self.clipboard = {"action": action, "paths": [str(p) for p in paths]}

    def clear_clipboard(self) -> None:
        self.clipboard = None

    def get_clipboard(self):
        return self.clipboard

        # ---------- Title signal handlers ----------
    def _apply_title_to_widget(self, widget: QWidget, raw_title: str, tab_type: str) -> None:
        """
        Format raw_title with prefix and set the tab text for widget if it still exists.
        raw_title: page title (browser) or path (explorer/terminal) - may be empty.
        tab_type: "browser" | "explorer" | "terminal" | "generic"
        """
        prefix = self._get_prefix(tab_type)
        # Normalize/shorten raw_title for explorer/terminal
        if tab_type == "explorer":
            # raw_title may be a path; show basename
            try:
                raw_title = os.path.basename(os.path.abspath(str(raw_title))).strip() or str(raw_title)
            except Exception:
                raw_title = str(raw_title)
        elif tab_type == "terminal":
            try:
                raw_title = os.path.basename(str(raw_title).rstrip(os.sep)) or str(raw_title)
            except Exception:
                raw_title = str(raw_title)
        else:
            raw_title = (raw_title or "").strip() or ""

        display = f"{prefix}{raw_title}" if prefix else (raw_title or "New Tab")
        idx = self.indexOf(widget)
        if idx != -1:
            self.setTabText(idx, display)
            # Optional: keep full title as tooltip for hover
            try:
                self.setTabToolTip(idx, raw_title)
            except Exception:
                pass

    def _on_tab_title_signal(self, widget: QWidget, emitted_value: str, tab_type: str) -> None:
        """
        Generic slot that handles title/path emitted by a tab signal.
        This is the function we connect to title_changed / path_changed.
        """
        # Safety: widget might have been removed already
        if self.indexOf(widget) == -1:
            return
        # For browser tabs the emitted_value is usually the page <title>.
        # For explorer tabs it is the path; pass it through apply helper.
        self._apply_title_to_widget(widget, emitted_value, tab_type)

    def _bind_tab_title_signals(self, widget: QWidget, kind: str) -> None:
        """
        Attach the widget's signals to TabManager so the tab title updates live.
        kind: 'browser' | 'explorer' | 'terminal' | 'generic'
        """
        # BrowserTab: has title_changed and url_changed (you defined already)
        print("Binding tab signals for", kind)
        if hasattr(widget, "title_changed"):
            try:
                # widget.title_changed emits a str (page title or custom string)
                print("Binding title_changed for", kind)
                widget.title_changed.connect(lambda t, w=widget, k=kind: self._on_tab_title_signal(w, t, k))
            except Exception:
                print("Failed to connect title_changed")
                print(Exception)
                pass


        # Browser fallback: some code emits url_changed instead
        if kind == "browser" and hasattr(widget, "url_changed"):
            try:
                print("Binding url_changed for", kind)
                widget.url_changed.connect(lambda u, w=widget, k=kind: self._on_tab_title_signal(w, widget._view.title() if hasattr(widget, "_view") else u, k))
            except Exception:
                print("Failed to connect url_changed")
                print(Exception)
                pass

        # Explorer emits path_changed (path string)
        if kind == "explorer" and hasattr(widget, "path_changed"):
            try:
                print("Binding path_changed for", kind)
                widget.path_changed.connect(lambda p, w=widget, k=kind: self._on_tab_title_signal(w, p, k))
            except Exception:
                print("Failed to connect path_changed")
                print(Exception)
                pass

        # Terminal would emit title_changed/cwd changes similarly (if present)
        if kind == "terminal" and hasattr(widget, "title_changed"):
            try:
                print("Binding title_changed for", kind)
                widget.title_changed.connect(lambda t, w=widget, k=kind: self._on_tab_title_signal(w, t, k))
            except Exception:
                print("Failed to connect title_changed")
                print(Exception)
                pass
