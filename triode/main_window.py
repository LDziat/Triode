# triode/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget,
    QLineEdit, QTabWidget, QToolBar
)
from .tab_manager import TabManager
from .address_bar import AddressBarController
from .url_router import URLRouter

class MainWindow(QMainWindow):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Triode")
        self.resize(1024, 768)

        # Router + Tab manager
        self.router = URLRouter()
        self.tabs = TabManager(self.router, settings)  # create tabs first

        # Address bar
        self.address_bar = QLineEdit()
        self.address_controller = AddressBarController(self.router, self.tabs)
        self.address_controller.bind(self.address_bar)

        self.tabs.address_controller = self.address_controller

        toolbar = QToolBar()
        toolbar.addWidget(self.address_bar)
        self.addToolBar(toolbar)
        # in MainWindow.__init__ after TabManager and AddressBarController are created
        

        # Central widget
        central = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        central.setLayout(layout)
        self.setCentralWidget(central)

        # Open default tab
        #self.tabs.create_browser_tab("http://example.com")
        #self.tabs.create_explorer_tab()
        self.tabs.create_generic_tab()
