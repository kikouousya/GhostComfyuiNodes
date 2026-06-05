import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "MyUtils.CheckpointList",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 确认当前创建的是不是我们的 CheckpointList 节点
        if (nodeData.name === "CheckpointList") {

            // 保存原有的 onNodeCreated 方法
            const onNodeCreated = nodeType.prototype.onNodeCreated;

            // 重写初始化方法
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }

                const node = this;

                // 找到对应的 Widget
                // 注意：这里的名称必须和 Python INPUT_TYPES 里的 key 一致
                const selectWidget = node.widgets.find((w) => w.name === "select_to_add");
                const textWidget = node.widgets.find((w) => w.name === "text");

                if (selectWidget && textWidget) {
                    // 定义回调函数：当下拉框值改变时触发
                    const originalCallback = selectWidget.callback;

                    selectWidget.callback = function (value) {
                        // 执行原有的 callback（如果有）
                        if (originalCallback) {
                            originalCallback.apply(this, arguments);
                        }

                        // 核心逻辑：如果选中的不是提示语，就加到文本框
                        if (value && value !== "👇 Select to add Checkpoint...") {
                            // 检查文本框当前最后是否已经有换行符，没有的话补一个
                            const currentText = textWidget.value;
                            const separator = currentText.length > 0 && !currentText.endsWith("\n") ? "\n" : "";

                            // 追加文本
                            textWidget.value += separator + value + "\n";

                            // 可选：重置下拉框回到提示语，方便下一次选择
                            // 这一步需要一点 hack，因为直接赋值 value 不会更新 UI 显示
                            selectWidget.value = "👇 Select to add Checkpoint...";

                            // 强制刷新画布以更新显示
                            if (app.graph) {
                                app.graph.setDirtyCanvas(true, true);
                            }
                        }
                    };
                }
            };
        }
    },
});