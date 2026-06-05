// File: js/eval_node.js

import { app } from "../../scripts/app.js";
import { setupDynamicInputs } from "./dynamic_utils.js";

app.registerExtension({
    name: "FlowControl.EVAL",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "FlowControl_EVAL") {

            // 1. 应用动态输入逻辑 (处理 a, b, c...)
            // 正则会自动匹配 "a", "b"... 并忽略 "expression"
            setupDynamicInputs(nodeType, {
                prefix: "",
                inputType: "*"
            });

            // 2. 其他初始化 (UI Widget 等)
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                // 先执行 setupDynamicInputs 注入的清理逻辑
                if (onNodeCreated) onNodeCreated.apply(this, arguments);

                const node = this;
                node.setSize([300, 200]);

                const widgetName = "display_result";
                if (!node.widgets || !node.widgets.find(w => w.name === widgetName)) {
                    const w = this.addWidget("text", widgetName, "Result will appear here...", () => {}, {
                        multiline: true,
                    });
                    if (w.inputEl) {
                        w.inputEl.readOnly = true;
                        w.inputEl.style.opacity = 0.6;
                    }
                }
            };

            // 3. 结果显示逻辑
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                if (onExecuted) onExecuted.apply(this, arguments);

                if (message && message.text) {
                    const resultWidget = this.widgets.find(w => w.name === "display_result");
                    if (resultWidget) {
                        resultWidget.value = message.text[0];
                        this.setDirtyCanvas(true);
                    }
                }
            };
        }
    },
});