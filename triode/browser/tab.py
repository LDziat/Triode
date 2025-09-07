from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Signal


class BrowserTab(QWidget):
    url_changed = Signal(str)  # Add this signal
    title_changed = Signal(str)  # Add this signal

    def __init__(self, url: str = "https://example.com"):
        super().__init__()
        self._view = QWebEngineView()
        self._view.setUrl(QUrl(url))

        # Connect internal signals
        self._view.urlChanged.connect(self._on_url_changed)
        self._view.titleChanged.connect(self._on_title_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    def navigate_to(self, url: str):
        """Navigate this browser tab to a new URL."""
        self._view.setUrl(QUrl(url))

    def _on_url_changed(self, qurl):
        #print("[SIGNAL]WebView URL changed:", qurl.toString())
        self.url_changed.emit(qurl.toString())

    def _on_title_changed(self, title):
        print("[SIGNAL]WebView title changed:", title)
        self.title_changed.emit(title)

    def current_url(self) -> str:
        """Return the current URL as a string (for address bar updates)."""
        return self._view.url().toString()
