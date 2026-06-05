from .xy_grid import Tool_XYGridPreview
from .image_saver.image_saver import ImageSaver

from .tools import FlowControl_StringList, Tool_FirstNonEmpty, Tool_DynamicPromptExpander, \
     CheckpointList, TOOL_EVAL, StringConcat, PreviewImagesFromPath
from .eta import ETA_Calculator

# ── Ghost nodes: expose ComfyUI-Danbooru-Gallery through this plugin ──────────
import os as _os
import sys as _sys

_GHOST_CLASS_MAPPINGS = {}
_GHOST_DISPLAY_MAPPINGS = {}

try:
    from . import _danbooru_bridge as _bridge
    _danbooru_mod = _bridge.install()

    # Prefix every danbooru node key with "Ghost" so they are distinct from
    # any separately installed danbooru-gallery plugin.
    for _k, _v in _danbooru_mod.NODE_CLASS_MAPPINGS.items():
        _GHOST_CLASS_MAPPINGS["Ghost" + _k] = _v
    for _k, _v in _danbooru_mod.NODE_DISPLAY_NAME_MAPPINGS.items():
        _GHOST_DISPLAY_MAPPINGS["Ghost" + _k] = "[Ghost] " + _v

    # Register the danbooru gallery JS directory so ComfyUI serves it at
    # /extensions/ComfyUI-Danbooru-Gallery/ (matching the relative imports
    # inside those JS files).
    try:
        import nodes as _comfy_nodes
        _danbooru_js_dir = _os.path.join(
            _os.path.dirname(_os.path.abspath(__file__)),
            "ComfyUI-Danbooru-Gallery", "js"
        )
        if _os.path.isdir(_danbooru_js_dir):
            _comfy_nodes.EXTENSION_WEB_DIRS["ComfyUI-Danbooru-Gallery"] = _danbooru_js_dir
    except Exception as _e:
        print(f"[My_Comfyui_Nodes] Warning: could not register danbooru gallery JS: {_e}")

except Exception as _e:
    print(f"[My_Comfyui_Nodes] Warning: failed to load Ghost (danbooru) nodes: {_e}")
# ── End Ghost nodes ───────────────────────────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    "FlowControl_StringList": FlowControl_StringList,
    "Tool_FirstNonEmpty": Tool_FirstNonEmpty,
    "Tool_DynamicPromptExpander": Tool_DynamicPromptExpander,
    "Tool_XYGridPreview": Tool_XYGridPreview,
    "CheckpointList": CheckpointList,
    "ETA_Calculator": ETA_Calculator,
    "FlowControl_EVAL": TOOL_EVAL,
    "FlowControl_StringConcat": StringConcat,
    "ImageSaver": ImageSaver,
    "PreviewImagesFromPath": PreviewImagesFromPath,
    **_GHOST_CLASS_MAPPINGS,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FlowControl_StringList": "String List (Flow)",
    "Tool_FirstNonEmpty": "First Non-Empty Select",
    "Tool_DynamicPromptExpander": "Dynamic Prompt Combinator",
    "Tool_XYGridPreview": "Simple XY Grid",
    "CheckpointList": "Checkpoint List Selector",
    "ETA_Calculator": "ETA Calculator",
    "FlowControl_EVAL": "EVAL (Py Expression)",
    "FlowControl_StringConcat": "String Concatenator",
    "ImageSaver": "Image Saver",
    "PreviewImagesFromPath": "Preview Images From Path",
    **_GHOST_DISPLAY_MAPPINGS,
}

WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]