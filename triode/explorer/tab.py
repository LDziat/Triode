# triode/explorer/tab.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal
from .actions import list_dir, open_item
import os


class ExplorerTab(QWidget):
    # Signal emitted whenever current_path changes
    path_changed = Signal(str)

    def __init__(self, start_path: str, parent=None):
        super().__init__(parent)
        self.current_path = os.path.abspath(start_path)
        self.layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_double_click)
        self.layout.addWidget(self.list_widget)

        self.setLayout(self.layout)
        self.refresh()

    def refresh(self):
        """Refresh the directory listing."""
        self.list_widget.clear()
        for entry in list_dir(self.current_path):
            item = QListWidgetItem(entry.name)
            item.setData(256, entry.path)  # UserRole = 256
            self.list_widget.addItem(item)

        # Notify listeners (like AddressBarController) of new path
        self.path_changed.emit(self.current_path)

    def on_double_click(self, item: QListWidgetItem):
        """Handle opening directories or files on double click."""
        path = item.data(256)
        if os.path.isdir(path):
            self.current_path = path
            self.refresh()
        else:
            open_item(path)

    def navigate_to(self, path: str):
        """Navigate to a path when AddressBarController tells us to."""
        if os.path.isdir(path):
            self.current_path = path
            self.refresh()
