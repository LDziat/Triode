# triode/browser/webkit_backend.py
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView  # fallback if WebKitGTK not found
from .backend import BrowserBackend

# NOTE: PySide6 bundles QtWebEngine by default, so we use this as stand-in
# for WebKitGTK until you install PyGObject + WebKit2GTK.
# Later we can implement a true GtkWidget backend for Unix.

class QTBackend(BrowserBackend):
    def create_view(self, parent: QWidget | None = None) -> QWidget:
        container = QWidget(parent)
        layout = QVBoxLayout(container)
        view = QWebEngineView(container)
        layout.addWidget(view)
        container.setLayout(layout)
        container._view = view
        return container

    def load_url(self, view: QWidget, url: str) -> None:
        view._view.setUrl(url)

    def current_url(self, view: QWidget) -> str:
        return view._view.url().toString()
