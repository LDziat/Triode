# triode/explorer/actions.py
import os
import shutil
import subprocess
import sys
from typing import List

def list_dir(path: str) -> List[os.DirEntry]:
    """Return a sorted list of DirEntry for given path."""
    try:
        return sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
    except FileNotFoundError:
        return []

def copy_items(sources: List[str], dest_dir: str) -> None:
    for src in sources:
        name = os.path.basename(src)
        dst = os.path.join(dest_dir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

def move_items(sources: List[str], dest_dir: str) -> None:
    for src in sources:
        name = os.path.basename(src)
        dst = os.path.join(dest_dir, name)
        shutil.move(src, dst)

def rename_item(path: str, new_name: str) -> None:
    dir_path = os.path.dirname(path)
    new_path = os.path.join(dir_path, new_name)
    os.rename(path, new_path)

def delete_items(paths: List[str]) -> None:
    for path in paths:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

def open_item(path: str) -> str:
    """Open file or directory. Returns path for browser to handle if possible."""
    if os.path.isdir(path):
        # return path for listing in ExplorerTab
        return path
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception:
        pass
    return path
