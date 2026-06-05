# GhostComfyuiNodes

自定义 ComfyUI 节点集合，包含 Python 后端节点与前端 JS 扩展，覆盖提示词处理、图像缓存、Danbooru 辅助、参数控制、批量执行等常用工作流增强能力。

## 功能概览

- 多类自定义节点入口（`__init__.py`）
- Danbooru 相关桥接与图库增强
- 文本缓存与图像缓存工具节点
- 参数控制、批量执行、分组辅助与通知节点
- JS 前端增强组件（节点面板、编辑器、工具按钮）

## 目录结构（节选）

```text
.
├── __init__.py
├── _danbooru_bridge.py
├── eta.py
├── xy_grid.py
├── js/
├── image_saver/
├── ComfyUI-Danbooru-Gallery/
└── tools/
```

## 安装

1. 进入 ComfyUI 的 `custom_nodes` 目录。
2. 克隆本仓库：

   ```bash
   git clone https://github.com/kikouousya/GhostComfyuiNodes.git
   ```

3. 重启 ComfyUI。
4. 若子模块或插件有额外依赖，请根据其 `requirements.txt` 单独安装。

## 开发说明

- Python 节点实现位于根目录与各子目录的 `py/`、`image_saver/`。
- 前端扩展位于 `js/` 与 `ComfyUI-Danbooru-Gallery/js/`。
- 调试和迁移脚本位于 `tools/`。

建议开发流程：

1. 新建/修改节点逻辑。
2. 在 ComfyUI 中加载并验证节点行为。
3. 提交前执行最小可复现测试（至少验证导入和节点注册）。

## 许可证

如未单独声明，默认沿用各子模块自身许可证；请在发布前按需补充统一 LICENSE。
