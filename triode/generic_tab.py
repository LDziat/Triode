# triode/generic_tab.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from .browser.factory import get_browser_backend



class GenericTab(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.backend = manager.backend

        layout = QVBoxLayout(self)
        newtab_label = QLabel(
            "<div style='" +
            "font-size: 24pt;" +
            "" +
            "'>" +
            "<h1>Triode Help</h1><hr>" +
            "http:// & https:// - Browser<br>" +
            "file:// - File Explorer<br>" +
            "term:// - Terminal" +
            "</div>"
            )
        
        layout.addWidget(newtab_label)

        #browser_btn = QPushButton("Open Browser")
        #explorer_btn = QPushButton("Open Explorer")
        #terminal_btn = QPushButton("Open Terminal")
        close_btn = QPushButton("Close Tab")

        #browser_btn.clicked.connect(self._open_browser)
        #explorer_btn.clicked.connect(self._open_explorer)
        #terminal_btn.clicked.connect(self._open_terminal)
        close_btn.clicked.connect(self._close_tab)

        #layout.addWidget(browser_btn)
        #layout.addWidget(explorer_btn)
        #layout.addWidget(terminal_btn)
        layout.addWidget(close_btn)

    def _open_browser(self):
        i = self.manager.indexOf(self)
        from .browser.tab import BrowserTab
        url = "http://example.com"


        tab = BrowserTab(url)
        insert_index = 1
        self.manager.insertTab(insert_index, tab, "Browser")
        if self.manager.address_controller:
            
            tab.url_changed.connect(self.manager.address_controller.set_route_from_browser)
        self.manager.removeTab(self.manager.indexOf(self))
        self.manager.setCurrentIndex(insert_index)
        
        

    def _open_explorer(self):
        i = self.manager.indexOf(self)
        from .explorer.tab import ExplorerTab
        new_tab = ExplorerTab("/")
        self.manager.insertTab(i, new_tab, "Explorer")
        self.manager.removeTab(self.manager.indexOf(self))
        self.manager.setCurrentIndex(i)

        

    def _open_terminal(self):
        i = self.manager.indexOf(self)
        from .terminal_tab import TerminalTab
        new_tab = TerminalTab()
        self.manager.insertTab(i, new_tab, "Terminal")
        self.manager.removeTab(self.manager.indexOf(self))
        self.manager.setCurrentIndex(i)

    def _close_tab(self):
        i = self.manager.indexOf(self)
        self.manager.removeTab(i)   