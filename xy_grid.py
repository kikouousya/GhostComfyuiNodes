#  File: xy_grid.py

import os
import datetime
import math
from PIL import Image, ImageDraw, ImageFont
import folder_paths
import torch
import numpy as np
import random
import string


class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")


# --- 辅助函数 ---
def tensor2pil(image):
    return Image.fromarray(np.clip(255. * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))


def create_mini_grid(pil_image_list):
    """
    将一组图片(Batch)拼接成一张缩略图
    """
    count = len(pil_image_list)
    if count == 0: return None

    w, h = pil_image_list[0].size

    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)

    grid_w = cols * w
    grid_h = rows * h

    mini_grid = Image.new("RGB", (grid_w, grid_h), (0, 0, 0))

    for idx, img in enumerate(pil_image_list):
        r = idx // cols
        c = idx % cols
        if img.size != (w, h):
            img = img.resize((w, h))
        mini_grid.paste(img, (c * w, r * h))

    return mini_grid


def get_text_width(font, text):
    """兼容不同版本 Pillow 的文本宽度获取"""
    try:
        return font.getlength(text)
    except:
        return font.getsize(text)[0]


def wrap_text(text, font, max_width):
    """
    根据最大宽度将文本拆分为多行
    """
    lines = []
    if not text:
        return lines

    # 将文本中的强制换行符先处理掉，防止 draw.text 报错
    # 简单的按空格分词
    words = text.replace('\n', ' ').split(' ')
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        w = get_text_width(font, test_line)

        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []

    if current_line:
        lines.append(' '.join(current_line))

    return lines


class Tool_XYGridPreview:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # Moved images to optional to support running with only image_paths
            },
            "optional": {
                "images": ("IMAGE", {"default": None}),
                "image_paths": ("STRING", {"default": None, "forceInput": True,
                                           "tooltip": "Optional: List of paths to previously saved images (avoids resaving temp files)."}),
                "x_labels": ("STRING", {"default": None}),
                "y_labels": ("STRING", {"default": None}),

            },
            "hidden": {"unique_id": "UNIQUE_ID"},

        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "preview_grid"
    CATEGORY = "FlowControl/Tools"
    INPUT_IS_LIST = True

    def preview_grid(self, unique_id, images=None, image_paths=None, x_labels=None, y_labels=None, ):
        # --- 1. 数据解包 ---
        batches = []
        # Store metadata for the UI (filename, type, subfolder) separately from PIL images
        batch_metadata = []

        use_paths = False

        # Determine if we are using paths or tensors
        # Check if image_paths is provided and contains valid data
        if image_paths is not None:
            # Flattener to check if there's actual data inside
            def has_data(obj):
                if isinstance(obj, list):
                    return any(has_data(x) for x in obj)
                return obj is not None

            if has_data(image_paths):
                use_paths = True

        if use_paths:
            # Strategy: Flatten the list structure similar to collected tensors,
            # but treat a list of strings as a single batch (assuming ImageSaver outputs a list of strings per batch)
            def collect_paths(obj):
                if isinstance(obj, list):
                    # Check if this represents a batch of paths (list of strings)
                    if len(obj) > 0 and isinstance(obj[0], str):
                        # This is a batch
                        pil_list = []
                        meta_list = []
                        for p in obj:
                            # Load Image
                            try:
                                pil_img = Image.open(p)
                                pil_list.append(pil_img)

                                # Prepare Metadata for UI
                                # Calculate relative path to output dir to set type='output'
                                output_dir = folder_paths.get_output_directory()
                                abs_path = os.path.abspath(p)

                                if abs_path.startswith(output_dir):
                                    rel_path = os.path.relpath(abs_path, output_dir)
                                    subfolder = os.path.dirname(rel_path)
                                    filename = os.path.basename(rel_path)
                                    meta_list.append({"filename": filename, "type": "output", "subfolder": subfolder})
                                else:
                                    # Fallback for paths outside output dir
                                    meta_list.append(None)
                            except Exception as e:
                                print(f"[XY_Grid] Error loading path {p}: {e}")

                        if pil_list:
                            batches.append(pil_list)
                            batch_metadata.append(meta_list)
                    else:
                        # Recurse
                        for item in obj:
                            collect_paths(item)

            collect_paths(image_paths)

        elif images is not None:
            # Existing Tensor logic
            def collect_batches(obj):
                if isinstance(obj, torch.Tensor):
                    pil_list = [tensor2pil(obj[i]) for i in range(obj.shape[0])]
                    batches.append(pil_list)
                    batch_metadata.append([None] * len(pil_list))  # Placeholder
                elif isinstance(obj, list):
                    for item in obj:
                        collect_batches(item)

            collect_batches(images)

        # Handle case where both inputs are missing
        if not batches:
            return {"ui": {"xy_preview": []}}

        # 处理 Labels
        def flatten_strs(obj):
            res = []
            if isinstance(obj, list):
                for x in obj: res.extend(flatten_strs(x))
            elif isinstance(obj, str):
                res.append(obj)
            return res

        x_str_list = flatten_strs(x_labels) if x_labels and x_labels[0] is not None else []
        y_str_list = flatten_strs(y_labels) if y_labels and y_labels[0] is not None else []

        # --- 2. 确定网格维度 ---
        total_batches = len(batches)

        expected_cells = (len(x_str_list) if x_str_list else 1) * (len(y_str_list) if y_str_list else 1)
        # Reshape batches if total_batches == 1 but we expect multiple cells (Split single batch)
        if total_batches == 1 and expected_cells > 1:
            single_batch = batches[0]
            single_meta = batch_metadata[0]
            total_imgs = len(single_batch)
            imgs_per_cell = total_imgs // expected_cells
            if imgs_per_cell > 0:
                new_batches = []
                new_meta = []
                for i in range(0, total_imgs, imgs_per_cell):
                    new_batches.append(single_batch[i: i + imgs_per_cell])
                    new_meta.append(single_meta[i: i + imgs_per_cell])
                batches = new_batches
                batch_metadata = new_meta
                total_batches = len(batches)

        if len(x_str_list) > 0 and len(y_str_list) > 0:
            cols = len(x_str_list)
            rows = len(y_str_list)
        elif len(x_str_list) > 0:
            cols = len(x_str_list)
            rows = math.ceil(total_batches / cols)
        elif len(y_str_list) > 0:
            rows = len(y_str_list)
            cols = math.ceil(total_batches / rows)
        else:
            cols = math.ceil(math.sqrt(total_batches))
            rows = math.ceil(total_batches / cols)

        # 垂直填充矩阵
        # Grid stores PIL images for the large summary image
        grid_matrix = [[[] for _ in range(cols)] for _ in range(rows)]
        # Meta Grid stores JSON info for the UI
        meta_matrix = [[[] for _ in range(cols)] for _ in range(rows)]

        idx = 0
        for c in range(cols):
            for r in range(rows):
                if idx < len(batches):
                    grid_matrix[r][c] = batches[idx]
                    meta_matrix[r][c] = batch_metadata[idx]
                    idx += 1
                else:
                    grid_matrix[r][c] = []
                    meta_matrix[r][c] = []

        # --- 3. 准备绘图资源 & UI JSON ---
        temp_dir = folder_paths.get_temp_directory()
        rand_prefix = ''.join(random.choices(string.ascii_lowercase, k=6))

        max_w, max_h = 512, 512
        if len(batches) > 0 and len(batches[0]) > 0:
            max_w, max_h = batches[0][0].size

        # 生成 JSON 数据
        json_grid = []
        for r_idx, row in enumerate(grid_matrix):
            json_row = []
            for c_idx, img_list in enumerate(row):
                cell_files = []
                # Check if we have pre-calculated metadata (from paths)
                meta_list = meta_matrix[r_idx][c_idx]

                for b_idx, img in enumerate(img_list):
                    # If we have valid metadata (from paths), use it
                    if meta_list and b_idx < len(meta_list) and meta_list[b_idx] is not None:
                        cell_files.append(meta_list[b_idx])
                    else:
                        # Standard behavior: Save temp file
                        fname = f"xy_{unique_id}_{rand_prefix}_R{r_idx}_C{c_idx}_B{b_idx}.png"
                        img.save(os.path.join(temp_dir, fname))
                        cell_files.append({"filename": fname, "type": "temp", "subfolder": ""})
                json_row.append(cell_files)
            json_grid.append(json_row)

        # --- 4. 拼接大图 & 文本换行处理 ---
        max_batch_size = max([len(b) for b in batches]) if batches else 1
        mini_cols = math.ceil(math.sqrt(max_batch_size))
        mini_rows = math.ceil(max_batch_size / mini_cols)

        cell_w = max_w * mini_cols
        cell_h = max_h * mini_rows

        # 字体设置
        font_size = 50
        try:
            font = ImageFont.load_default(size=font_size)
        except:
            font, font_size = ImageFont.load_default(), 12

        padding = 20
        header_h = (font_size + padding * 2) if x_str_list else 0

        # --- 计算左侧边距 (Left Margin) ---
        left_margin = 0
        max_label_width_limit = 300  # 最大标签宽度

        if y_str_list:
            max_actual_width = 0
            for label in y_str_list:
                lines = wrap_text(str(label), font, max_label_width_limit)
                if not lines: continue

                longest_line_w = 0
                for line in lines:
                    w = get_text_width(font, line)
                    if w > longest_line_w: longest_line_w = w

                if longest_line_w > max_actual_width:
                    max_actual_width = longest_line_w

            left_margin = int(max_actual_width) + padding * 2

        canvas_w = left_margin + cols * cell_w
        canvas_h = header_h + rows * cell_h

        final_img = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
        draw = ImageDraw.Draw(final_img)

        # 绘制 X Labels (顶部) - 手动居中，不使用 anchor="mt"
        if header_h > 0:
            for i, label in enumerate(x_str_list):
                if i >= cols: break
                label_str = str(label)
                text_w = get_text_width(font, label_str)

                # 单元格中心点
                cx = left_margin + i * cell_w + cell_w // 2
                # 实际绘制点 = 中心点 - 文字宽度一半
                draw_x = cx - text_w / 2

                # 移除 anchor 参数
                draw.text((draw_x, padding), label_str, fill=(0, 0, 0), font=font)

        # 绘制 Y Labels (左侧) - 左对齐，不使用 anchor="lt"
        line_height = font_size + 4

        for r in range(rows):
            y_pos = header_h + r * cell_h

            if r < len(y_str_list):
                label_text = str(y_str_list[r])
                lines = wrap_text(label_text, font, max_label_width_limit)

                total_text_h = len(lines) * line_height
                text_start_y = y_pos + (cell_h - total_text_h) // 2

                for i, line in enumerate(lines):
                    # 默认就是左上角，不需要 anchor="lt"
                    draw.text((padding, text_start_y + i * line_height), line, fill=(0, 0, 0), font=font)

            # 绘制图片
            for c in range(cols):
                if c >= len(grid_matrix[r]): break
                pil_list = grid_matrix[r][c]
                if pil_list:
                    mini_img = create_mini_grid(pil_list)
                    if mini_img:
                        rw, rh = mini_img.size
                        scale = min(cell_w / rw, cell_h / rh)
                        new_size = (int(rw * scale), int(rh * scale))
                        mini_img = mini_img.resize(new_size, Image.Resampling.LANCZOS)
                        paste_x = left_margin + c * cell_w + (cell_w - new_size[0]) // 2
                        paste_y = y_pos + (cell_h - new_size[1]) // 2
                        final_img.paste(mini_img, (paste_x, paste_y))

        # 保存
        output_dir = folder_paths.get_output_directory()
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        save_dir = os.path.join(output_dir, "XY_Grid", date_str)
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{datetime.datetime.now().strftime('%H%M%S')}_XY_Grid.png"
        full_path = os.path.join(save_dir, filename)
        final_img.save(full_path)
        print(f"Saved XY Grid to {full_path}")

        ui_data = {
            "grid": json_grid,
            "x_labels": x_str_list,
            "y_labels": y_str_list,
        }

        return {"ui": {"xy_preview": [ui_data]}}