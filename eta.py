from .tools import any_type


class ETA_Calculator:
    # 内部缓存：用于在 current 未连接时自动计数 { label: current_value }
    _counter_cache = {}

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "flow": (any_type, {
                    "tooltips": "Any input flow to pass through unchanged."
                }),
                "total": ("INT", {"default": 10, "min": 1}),
                "current": ("INT", {"default": -1, "min": -1,
                                       "tooltips": "Override current count; or set to -1 to auto-increment each time the node is executed."
                                       }),
                "label": ("STRING", {"default": "Job"}),
                "show_with_popup": ("BOOLEAN", {"default": True}),
            },
            "optional": {

            },
        }

    RETURN_TYPES = (any_type, "INT", "STRING", )
    RETURN_NAMES = ("flow", "current", "info_string",)
    FUNCTION = "calculate_eta"
    CATEGORY = "FlowControl/Tools"

    def calculate_eta(self, flow, total, current, label, show_with_popup, ):
        # 逻辑：如果 current 为 -1 (默认值/未连接)，则使用内部计数器自动递增[将在js中处理]

        # Python 不再进行时间计算，仅返回基础字符串和 raw 数据
        # 具体的 ETA、速率、Elapsed 计算全部交由前端 JS 处理
        info_string = f"{label}: {current}/{total}"
        progress = current / total if total > 0 else 0.0

        return {
            "ui": {
                # 传递给前端的数据
                "text": [info_string],
                "progress": [progress],
                "show_popup": [show_with_popup],
                "current": [current],
                "total": [total],
                "label": [label]
            },
            "result": (flow, current, info_string,)
        }