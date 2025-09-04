# triode/models/route.py
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class URLRoute:
    scheme: str               # 'http' | 'https' | 'file' | 'term'
    path: str                 # normalized absolute path or URL
    query: Dict[str, str] = None
