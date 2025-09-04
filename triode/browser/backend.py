# triode/browser/backend.py
from abc import ABC, abstractmethod
from typing import Optional
from PySide6.QtWidgets import QWidget

class BrowserBackend(ABC):
    @abstractmethod
    def create_view(self, parent: Optional[QWidget] = None) -> QWidget:
        raise NotImplementedError

    @abstractmethod
    def load_url(self, view: QWidget, url: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def current_url(self, view: QWidget) -> str:
        raise NotImplementedError
