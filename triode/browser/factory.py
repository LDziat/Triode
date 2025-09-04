# triode/browser/factory.py
import platform
from .backend import BrowserBackend

def _default_engine() -> str:
    if platform.system() in ("Linux", "Darwin"):
        return "webkit"
    return "cef"

def get_browser_backend(engine: str | None = None) -> BrowserBackend:
    if engine is None:
        engine = _default_engine()
    engine = engine.lower()
    if engine == "webkit":
        from .webkit_backend import WebKitGTKBackend
        return WebKitGTKBackend()
    if engine == "cef":
        from .cef_backend import CefBackend
        return CefBackend()
    if engine == "qt":
        from .qtwebengine_backend import QtWebEngineBackend
        return QtWebEngineBackend()
    raise ValueError(f"Unknown browser engine: {engine}")
