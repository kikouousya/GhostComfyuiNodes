import ast
import json

import re
import itertools
import folder_paths


# --- Utilities ---

def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")


# --- Logic for Dynamic Prompt Combinations ---

def parse_combinatorial_prompt(text):
    """
    递归解析Prompt，返回所有可能性的列表。
    处理语法: {num$$sep$$opt1|opt2}
    """
    text += "\n"
    # 只移除单行注释
    text = re.sub(r'#.*$', '', text)

    # 查找最内层的括号 {}
    pattern = re.compile(r'\{([^{}]+)\}')
    match = pattern.search(text)

    if not match:
        # 如果没有括号了，直接返回当前文本（单元素列表）
        return [text]

    full_match = match.group(0)
    content = match.group(1)

    # 解析参数: {2-3$$and$$opt1|opt2}
    # 默认值
    count_min = 1
    count_max = 1
    sep = ","
    options_str = content

    if "$$" in content:
        parts = content.split("$$")
        if len(parts) == 2:  # {count$$options}
            count_part = parts[0]
            options_str = parts[1]
        elif len(parts) == 3:  # {count$$sep$$options}
            count_part = parts[0]
            sep = parts[1]
            options_str = parts[2]

        # 解析数量 count (e.g., "2", "1-3")
        if "-" in count_part:
            c_range = count_part.split("-")
            count_min = int(c_range[0])
            count_max = int(c_range[1])
        else:
            count_min = int(count_part)
            count_max = int(count_part)

    # 解析选项 (去除权重语法 ::，因为这里是穷举所有可能性)
    raw_options = options_str.split("|")
    options = []
    for opt in raw_options:
        # 去除类似 2::Artist 的权重部分，只保留 Artist
        opt_cleaned = re.sub(r'^[\d\.]+::', '', opt).strip()
        options.append(opt_cleaned)

    # 生成当前括号的所有排列组合
    replacements = []
    for r in range(count_min, count_max + 1):
        # 穷举组合
        for combo in itertools.combinations(options, r):
            replacements.append(sep.join(combo))

    # 如果没有生成任何组合（比如选项不够），至少保留空
    if not replacements:
        replacements = [""]

    # 将生成的组合替换回原文本，并递归处理剩余部分
    results = []
    for rep in replacements:
        new_text = text.replace(full_match, rep, 1)
        # 递归调用以处理可能的其他括号
        results.extend(parse_combinatorial_prompt(new_text))

    # 去重
    return list(dict.fromkeys(results))




class FlowControl_StringList:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "ckpt1.safetensors\nckpt2.safetensors"}),
                "ignore_empty_lines": ("BOOLEAN", {"default": True}),
                "delimiter": ("STRING", {"default": "\\n"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "generate_list"
    CATEGORY = "FlowControl/Tools"

    def generate_list(self, text, ignore_empty_lines, delimiter):
        lines = text.split("\n" if delimiter == "\\n" else delimiter)
        if ignore_empty_lines:
            lines = [x.strip() for x in lines if x.strip()]
        else:
            lines = [x.strip() for x in lines]
        return (lines,)


import os
from pathlib import Path

CHECKPOINT_DIR = Path("ComfyUI/models/checkpoints")


class CheckpointList:
    @classmethod
    def INPUT_TYPES(s):
        # 获取模型列表
        ckpt_list = folder_paths.get_filename_list("checkpoints")
        # 在列表头部加一个提示选项，作为默认值
        ckpt_list_with_none = ["👇 Select to add Checkpoint..."] + ckpt_list

        return {
            "required": {
                # 下拉框：作为辅助工具，选中后由 JS 将值填入下方文本框
                "select_to_add": (ckpt_list_with_none,),

                # 文本框：最终的数据来源
                "text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Select from above or type here..."
                }),

                "ignore_empty_lines": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "generate_list"
    CATEGORY = "FlowControl/Tools"

    def generate_list(self, select_to_add, text, ignore_empty_lines):
        # Python 端主要处理 text 文本框的内容
        # 下拉框 (select_to_add) 只是给前端用的，后端可以忽略它的值，
        # 除非你想把当前选中的也加进去（这里我们假设 JS 已经把它加到 text 里了）

        lines = text.split("\n")

        final_list = []
        for x in lines:
            clean_line = x.strip()
            if ignore_empty_lines:
                if clean_line:
                    final_list.append(clean_line)
            else:
                final_list.append(clean_line)

        if not final_list:
            # 如果列表为空，返回空列表防止报错
            print("Warning: CheckpointList is empty.")

        return (final_list,)


class Tool_FirstNonEmpty:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {},
            "optional": {
                "input1": (any_type,),
                "input2": (any_type,),
                "input3": (any_type,),
            }
        }

    RETURN_TYPES = (any_type,)
    FUNCTION = "select"
    CATEGORY = "FlowControl/Tools"

    def select(self, input1=None, input2=None, input3=None):
        if input1 is not None: return (input1,)
        if input2 is not None: return (input2,)
        if input3 is not None: return (input3,)
        return (None,)


class Tool_DynamicPromptExpander:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "{2$$red|green|blue} apple"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "expand"
    CATEGORY = "FlowControl/Tools"

    def expand(self, text):
        results = parse_combinatorial_prompt(text)
        print(f"[DynamicPromptExpander] Generated {len(results)} variations.")
        return (results,)


class TOOL_EVAL:
    @classmethod
    def INPUT_TYPES(s):
        # 预定义 a-z 的可选输入
        # 即使前端动态显示，后端也需要声明这些可能的输入名
        optional_inputs = {
            "expression": ("STRING", {"multiline": True, "dynamicPrompts": False, "default": "a"}),
        }

        # 自动生成 a 到 z 的输入类型
        for i in range(ord('a'), ord('z') + 1):
            char = chr(i)
            optional_inputs[char] = (any_type, {})

        return {
            "required": {},
            "optional": optional_inputs
        }

    RETURN_TYPES = (any_type, "STRING")
    RETURN_NAMES = ("result", "string_cast")
    FUNCTION = "execute_eval"
    CATEGORY = "FlowControl/Logic"

    def execute_eval(self, expression, **kwargs):
        # 1. 准备环境
        # 将传入的 a=1, b="text" 等放入局部变量字典
        local_scope = {}
        input_preview = []

        for key, value in kwargs.items():
            if value is not None:
                local_scope[key] = value
                # 生成预览文本 (截断过长的内容)
                val_str = str(value)
                if len(val_str) > 50: val_str = val_str[:47] + "..."
                input_preview.append(f"{key}: {val_str}")

        # 导入常用模块供 EVAL 内部使用 (可选，根据安全需求调整)
        import math, random, re
        global_scope = {
            "math": math,
            "random": random,
            "re": re,
            "__builtins__": __builtins__  # 警告：这允许完全访问 python 环境
        }

        result = None
        status_text = "Inputs:\n" + "\n".join(input_preview) + "\n\n"

        try:
            # 2. AST 解析以处理 "最后一行求值"
            # 简单的 exec() 无法返回最后一行表达式的值，我们需要手动拆分
            tree = ast.parse(expression)

            if not tree.body:
                result = None
            else:
                last_node = tree.body[-1]

                # 如果最后一行是表达式 (Expression)，则分别执行
                if isinstance(last_node, ast.Expr):
                    # 前面的语句用 exec 执行
                    code_body = tree.body[:-1]
                    if code_body:
                        exec(compile(ast.Module(body=code_body, type_ignores=[]), "<string>", "exec"), global_scope,
                             local_scope)

                    # 最后一行的表达式用 eval 求值
                    result = eval(compile(ast.Expression(body=last_node.value), "<string>", "eval"), global_scope,
                                  local_scope)
                else:
                    # 如果最后一行不是表达式 (比如 assignment, if, loop)，直接全部 exec
                    exec(expression, global_scope, local_scope)
                    result = None  # 或者你可以选择返回 local_scope.get('result')

            status_text += f"Output Type: {type(result).__name__}\nValue: {result}"

        except Exception as e:
            result = f"Error: {str(e)}"
            status_text += f"❌ Exception:\n{str(e)}"

        # 3. 返回结果和 UI 更新数据
        return {
            "ui": {
                "text": [status_text]
            },
            "result": (result, str(result))
        }




import torch
import numpy as np

from PIL import Image


# 辅助函数：单张 Tensor 转 PIL (避免 Batch 维度干扰)
def single_tensor2pil(t):
    # t shape: [H, W, C]
    img_np = np.clip(255. * t.cpu().numpy(), 0, 255).astype(np.uint8)
    return Image.fromarray(img_np)


# 辅助函数：PIL 转 Batch Tensor
def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


class StringConcat:
    @classmethod
    def INPUT_TYPES(s):
        inputs = {
            "required": {
                "separator": ("STRING", {"default": "\\n", "multiline": False}),
            },
            "optional": {
                "text_a": (any_type, {"forceInput": True, "multiline": True}),
            }
        }

        for i in range(ord('b'), ord('z') + 1):
            key = f"text_{chr(i)}"
            inputs["optional"][key] = (any_type, {"forceInput": True, "multiline": True})

        return inputs

    RETURN_TYPES = ("STRING",)
    FUNCTION = "concat_strings"
    CATEGORY = "FlowControl/Tools"

    def concat_strings(self, separator, **kwargs):
        real_separator = separator.replace("\\n", "\n").replace("\\t", "\t")
        sorted_keys = sorted([k for k in kwargs.keys() if k.startswith("text_")])

        values = []
        for key in sorted_keys:
            val = kwargs[key]
            try:
                if isinstance(val, str):
                    values.append(val)
                elif isinstance(val, (int, float, bool)):
                    values.append(str(val))
                else:
                    val = json.dumps(val, indent=4)
                    values.append(str(val))
            except Exception:
                values.append(str(val))

        result = real_separator.join(values)
        return {"ui": {"text": values}, "result": (result,), }

import shutil

class PreviewImagesFromPath:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.input_dir = folder_paths.get_input_directory()
        self.temp_dir = folder_paths.get_temp_directory()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "path_list": ("*", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("path_list",)

    FUNCTION = "preview_images"
    OUTPUT_NODE = True
    CATEGORY = "Custom/PathTools"

    def preview_images(self, path_list):
        # 兼容性处理：确保输入是列表
        if isinstance(path_list, str):
            paths = [path_list]
        elif isinstance(path_list, list):
            paths = path_list
        else:
            paths = []

        images_info = []

        for file_path in paths:
            if not isinstance(file_path, str) or not os.path.exists(file_path):
                continue

            # 过滤非图片文件
            if not file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.gif')):
                continue

            # 获取文件的绝对路径，统一格式
            abs_path = os.path.abspath(file_path)
            filename = os.path.basename(abs_path)

            # --- 智能判断逻辑 ---

            # 1. 检查是否在 Output 目录中
            if self._is_subpath(abs_path, self.output_dir):
                subfolder = self._get_subfolder(abs_path, self.output_dir)
                images_info.append({
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": "output"
                })

            # 2. 检查是否在 Input 目录中
            elif self._is_subpath(abs_path, self.input_dir):
                subfolder = self._get_subfolder(abs_path, self.input_dir)
                images_info.append({
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": "input"
                })

            # 3. 检查是否在 Temp 目录中
            elif self._is_subpath(abs_path, self.temp_dir):
                subfolder = self._get_subfolder(abs_path, self.temp_dir)
                images_info.append({
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": "temp"
                })

            # 4. 都不在：属于外部路径，必须复制
            else:
                try:
                    # 为了避免同名文件覆盖导致显示错误，建议在 temp 中使用唯一文件名
                    # 这里简单处理，直接复制
                    dest_path = os.path.join(self.temp_dir, filename)

                    # 只有当目标文件不存在，或者源文件更新时才复制（可选优化）
                    if not os.path.exists(dest_path) or os.path.getmtime(abs_path) > os.path.getmtime(dest_path):
                        shutil.copy2(abs_path, dest_path)

                    images_info.append({
                        "filename": filename,
                        "subfolder": "",
                        "type": "temp"
                    })
                except Exception as e:
                    print(f"[Preview Path] Copy error: {e}")

        return {
            "ui": {"images": images_info},
            "result": (path_list,)
        }

    def _is_subpath(self, path, parent):
        """判断 path 是否在 parent 目录内"""
        parent = os.path.abspath(parent)
        path = os.path.abspath(path)
        # commonpath 可以判断路径层级关系
        return os.path.commonpath([parent]) == os.path.commonpath([parent, path])

    def _get_subfolder(self, path, parent):
        """获取相对于 parent 的子文件夹路径（不包含文件名）"""
        parent = os.path.abspath(parent)
        path = os.path.abspath(path)
        rel_path = os.path.relpath(path, parent)
        subfolder = os.path.dirname(rel_path)
        if subfolder == ".":
            return ""
        return subfolder
