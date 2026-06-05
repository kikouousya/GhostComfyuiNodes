"""
Bridge module for importing from ComfyUI-Danbooru-Gallery.

The folder name contains hyphens which are invalid in Python module names.
This bridge installs a custom import finder (sys.meta_path) that maps
the virtual package name 'ghost_danbooru_gallery' to the actual directory
'ComfyUI-Danbooru-Gallery', allowing all relative imports inside that package
to resolve correctly.
"""

import importlib.util
import sys
import os

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DANBOORU_BASE = os.path.join(_PLUGIN_DIR, "ComfyUI-Danbooru-Gallery")

# Virtual package name used for importing
DANBOORU_PKG = "ghost_danbooru_gallery"


class _DanbooruImportFinder:
    """Custom import finder that maps 'ghost_danbooru_gallery.*' to 'ComfyUI-Danbooru-Gallery/*'."""

    def __init__(self, base_dir: str, pkg_name: str):
        self._base = base_dir
        self._pkg = pkg_name

    def find_spec(self, fullname, path, target=None):
        # Only handle our virtual package and its submodules
        if not (fullname == self._pkg or fullname.startswith(self._pkg + ".")):
            return None

        # Compute the relative path within the package
        rel = fullname[len(self._pkg):]
        if rel:
            rel = rel.lstrip(".")
            parts = rel.split(".")
            file_path = os.path.join(self._base, *parts)
        else:
            file_path = self._base

        # Try to find as a package (directory with __init__.py)
        init_path = os.path.join(file_path, "__init__.py")
        if os.path.isfile(init_path):
            return importlib.util.spec_from_file_location(
                fullname,
                init_path,
                submodule_search_locations=[file_path],
            )

        # Try to find as a regular module (.py file)
        py_path = file_path + ".py"
        if os.path.isfile(py_path):
            return importlib.util.spec_from_file_location(fullname, py_path)

        return None


def install():
    """Install the import finder and return the danbooru gallery module."""
    if not os.path.isdir(_DANBOORU_BASE):
        raise FileNotFoundError(
            f"ComfyUI-Danbooru-Gallery directory not found at: {_DANBOORU_BASE}"
        )

    # Avoid registering the finder more than once
    for existing in sys.meta_path:
        if isinstance(existing, _DanbooruImportFinder) and existing._base == _DANBOORU_BASE:
            break
    else:
        finder = _DanbooruImportFinder(_DANBOORU_BASE, DANBOORU_PKG)
        sys.meta_path.insert(0, finder)

    # Import (or return cached) the root package
    if DANBOORU_PKG not in sys.modules:
        import importlib
        return importlib.import_module(DANBOORU_PKG)
    return sys.modules[DANBOORU_PKG]
