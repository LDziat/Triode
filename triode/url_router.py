# triode/url_router.py
import os
import urllib.parse
from typing import Dict
from .models.route import URLRoute

class URLRouter:
    SUPPORTED = {"http", "https", "file", "term"}

    def parse(self, text: str) -> URLRoute:
        text = text.strip()
        # If user typed a plain path, treat as file://
        if text.startswith("http://") or text.startswith("https://"):
            return URLRoute(scheme=urllib.parse.urlparse(text).scheme, path=text, query={})
        if text.startswith("file://"):
            path = self._from_file_uri(text)
            return URLRoute(scheme="file", path=path, query={})
        if text.startswith("term://"):
            return URLRoute(scheme="term", path=text[7:])
        # fallback: consider as file path or http (if looks like domain)
        if " " not in text and "." in text and not os.path.exists(text):
            # heuristic: treat as HTTP if contains dot and no local path
            if text.startswith("www."):
                text = "http://" + text
            elif text.startswith("http"):
                pass
            elif text.count(".") >= 1:
                text = "http://" + text
            if text.startswith("http"):
                return URLRoute(scheme=urllib.parse.urlparse(text).scheme, path=text, query={})
        # otherwise treat as file path
        abs_path = os.path.abspath(os.path.expanduser(text))
        return URLRoute(scheme="file", path=abs_path, query={})

    def to_text(self, route: URLRoute) -> str:
        if route.scheme in ("http", "https"):
            return route.path
        if route.scheme == "file":
            return f"file://{route.path}"
        if route.scheme == "term":
            return f"term://{route.path}"
        return route.path

    def _from_file_uri(self, uri: str) -> str:
        # naive but cross-platform enough for Phase-0
        if uri.startswith("file://"):
            path = uri[len("file://"):]
            return os.path.abspath(os.path.expanduser(path))
        return os.path.abspath(os.path.expanduser(uri))
