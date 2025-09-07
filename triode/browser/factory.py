# triode/browser/factory.py
import platform
from .backend import BrowserBackend

def _default_engine() -> str:
    if platform.system() in ("Linux", "Darwin"):
        return "qt"
    return "qt"

def get_browser_backend(engine: str | None = None) -> BrowserBackend:
    if engine is None:
        engine = _default_engine()
    engine = engine.lower()
    # Only QT is implemented for now
    if engine == "qt":
        from .qt_backend import QTBackend
        return QTBackend()
    # TODO: CEF implementation pending, might skip and just use QT for chromium 
    if engine == "cef":
        from .cef_backend import CefBackend
        return CefBackend()
    # TODO: WebKitGTK implementation pending, vital for spirit of project, but not in current scope
    if engine == "webkit":
        from .webkit_backend import WebkitBackend
        return WebkitBackend()
    # TODO: GECKO! This is the master goal, but very complex. Not in current scope.
    if engine == "gecko":
        from .gecko_backend import GeckoBackend
        return GeckoBackend()
    raise ValueError(f"Unknown browser engine: {engine}")
