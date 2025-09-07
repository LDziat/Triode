# triode/explorer/tab.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QToolBar, QInputDialog, QMessageBox, QFileDialog
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, Qt
from .actions import list_dir, open_item, copy_items, move_items, delete_items, rename_item, make_directory, make_file
from pathlib import Path
import os
import traceback

class ExplorerTab(QWidget):
    path_changed = Signal(str)

    def __init__(self, start_path: str = None, parent=None):
        super().__init__(parent)
        self.current_path = os.path.abspath(start_path or os.path.expanduser("~"))

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # toolbar
        self.toolbar = QToolBar()
        self._add_toolbar_actions()
        self.layout.addWidget(self.toolbar)

        # file list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self.on_double_click)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        self.layout.addWidget(self.list_widget)

        self.setLayout(self.layout)
        self.refresh()

    # ----- toolbar -----
    def _add_toolbar_actions(self):
        act_back = QAction("Up", self)
        act_back.triggered.connect(self.go_up)
        self.toolbar.addAction(act_back)

        act_refresh = QAction("Refresh", self)
        act_refresh.triggered.connect(self.refresh)
        self.toolbar.addAction(act_refresh)

        act_new_dir = QAction("New Folder", self)
        act_new_dir.triggered.connect(self._new_folder)
        self.toolbar.addAction(act_new_dir)

        act_new_file = QAction("New File", self)
        act_new_file.triggered.connect(self._new_file)
        self.toolbar.addAction(act_new_file)

        act_copy = QAction("Copy", self)
        act_copy.triggered.connect(lambda: self._copy_cut("copy"))
        self.toolbar.addAction(act_copy)

        act_cut = QAction("Cut", self)
        act_cut.triggered.connect(lambda: self._copy_cut("cut"))
        self.toolbar.addAction(act_cut)

        act_paste = QAction("Paste", self)
        act_paste.triggered.connect(self._paste)
        self.toolbar.addAction(act_paste)

        act_delete = QAction("Delete", self)
        act_delete.triggered.connect(self._delete)
        self.toolbar.addAction(act_delete)

        act_rename = QAction("Rename", self)
        act_rename.triggered.connect(self._rename)
        self.toolbar.addAction(act_rename)

    # ----- UI helpers -----
    def refresh(self):
        """Refresh listing and emit path_changed."""
        self.list_widget.clear()
        try:
            entries = list_dir(self.current_path)
            for entry in entries:
                item = QListWidgetItem(entry.name)
                item.setData(Qt.ItemDataRole.UserRole, entry.path)
                glyph = "📁" if entry.is_dir() else "📄"
                item.setToolTip(entry.path)
                item.setText(f"{glyph}  {entry.name}")
                self.list_widget.addItem(item)
        except Exception:
            traceback.print_exc()
        self.path_changed.emit(self.current_path)

    def on_double_click(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if os.path.isdir(path):
            self.current_path = path
            self.refresh()
        else:
            open_item(path)

    def navigate_to(self, path: str):
        """Navigate to a path when AddressBarController tells us to."""
        if path.startswith("file://"):
            path = path[len("file://"):]
        if os.path.isdir(path):
            self.current_path = os.path.abspath(path)
            self.refresh()
            self.path_changed.emit(self.current_path)  # Emit after navigation
            print(f"[ExplorerTab] navigated to {self.current_path}")

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent and os.path.isdir(parent):
            self.current_path = parent
            self.refresh()

    def selected_paths(self) -> list[str]:
        items = self.list_widget.selectedItems()
        return [it.data(Qt.ItemDataRole.UserRole) for it in items]

    # ----- context menu -----
    def _on_context_menu(self, pos):
        menu = self.list_widget.createStandardContextMenu()
        # Build our custom menu
        sel = self.selected_paths()
        from PySide6.QtWidgets import QMenu
        m = QMenu(self)
        m.addAction("Open", lambda: self._ctx_open(sel))
        m.addAction("Copy", lambda: self._copy_cut("copy"))
        m.addAction("Cut", lambda: self._copy_cut("cut"))
        m.addAction("Paste", self._paste)
        if len(sel) == 1:
            m.addAction("Rename", self._rename)
        m.addAction("Delete", self._delete)
        m.exec(self.list_widget.mapToGlobal(pos))

    def _ctx_open(self, sel):
        if not sel:
            return
        path = sel[0]
        if os.path.isdir(path):
            self.current_path = path
            self.refresh()
        else:
            open_item(path)

    # ----- actions -----
    def _copy_cut(self, action: str):
        sel = self.selected_paths()
        if not sel:
            return
        manager = getattr(self, "manager", None) or getattr(self.parent(), "manager", None)
        # Prefer TabManager if available (we expect manager to be TabManager)
        tab_manager = getattr(self.parent(), "parent", None)
        # Better: look up the top-level TabManager by walking parents
        tm = self._find_tab_manager()
        if tm is None:
            QMessageBox.warning(self, "Clipboard", "Tab manager not found; copy aborted.")
            return
        tm.set_clipboard(action, sel)

    def _find_tab_manager(self):
        # walk parent hierarchy to find TabManager instance (QTabWidget subclass)
        p = self.parent()
        from PySide6.QtWidgets import QTabWidget
        while p is not None:
            if isinstance(p, QTabWidget):
                return p
            p = p.parent()  # <-- FIX: use p.parent() instead of getattr(p, "parent", None)
        return None

    def _paste(self):
        tm = self._find_tab_manager()
        if tm is None:
            QMessageBox.warning(self, "Paste", "Tab manager not found; cannot paste.")
            return
        clip = tm.get_clipboard()
        if not clip:
            return
        try:
            action = clip["action"]
            paths = clip["paths"]
            if action == "copy":
                copy_items(paths, self.current_path)
            elif action == "cut":
                move_items(paths, self.current_path)
                tm.clear_clipboard()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Paste error", f"{e}")

    def _delete(self):
        sel = self.selected_paths()
        if not sel:
            return
        confirm = QMessageBox.question(
            self, "Delete", f"Delete {len(sel)} item(s)? This is permanent.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_items(sel)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Delete error", f"{e}")

    def _rename(self):
        sel = self.selected_paths()
        if not sel or len(sel) != 1:
            return
        old = sel[0]
        base = os.path.basename(old)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=base)
        if not ok or not new_name:
            return
        try:
            rename_item(old, new_name)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Rename error", f"{e}")

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:", text="new_folder")
        if not ok or not name:
            return
        try:
            make_directory(self.current_path, name)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Create folder failed", f"{e}")

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "New File", "File name:", text="new_file.txt")
        if not ok or not name:
            return
        try:
            make_file(self.current_path, name)
            self.refresh()
        except FileExistsError:
            QMessageBox.warning(self, "File exists", "A file with that name already exists.")
        except Exception as e:
            QMessageBox.critical(self, "Create file failed", f"{e}")
