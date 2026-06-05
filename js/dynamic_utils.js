// File: js/dynamic_utils.js

/**
 * 设置动态输入端口的通用逻辑
 * @param {object} nodeType - 节点原型
 * @param {object} config - 配置项
 * @param {string} config.prefix - 端口前缀 (例如 "text_" 或 "")
 * @param {string} config.inputType - 端口类型 (通常为 "*")
 */
export function setupDynamicInputs(nodeType, config) {
    const prefix = config.prefix || "";
    const inputType = config.inputType || "*";

    // 构造正则：匹配前缀 + 单个小写字母 (a-z)
    const dynamicInputRegex = new RegExp(`^${prefix}([a-z])$`);

    function getName(char) {
        return `${prefix}${char}`;
    }

    // --- 核心逻辑：清理并维护“唯一”空闲端口 ---
    nodeType.prototype.cleanupDynamicInputs = function() {
        if (!this.inputs) return;

        // 1. 扫描当前状态：找到“字母序最大”的“已连接”端口
        let lastConnectedCharCode = 0; // 0 表示还没找到任何连接

        for (const input of this.inputs) {
            const match = input.name.match(dynamicInputRegex);
            if (match && input.link) {
                const charCode = match[1].charCodeAt(0);
                if (charCode > lastConnectedCharCode) {
                    lastConnectedCharCode = charCode;
                }
            }
        }

        // 2. 计算目标端口字符
        // 如果没有任何连接，目标是 'a' (97)
        // 如果最后一个连接是 'a' (97)，目标是 'b' (98)
        // 最大限制是 'z' (122)
        const startCharCode = 'a'.charCodeAt(0);
        let targetCharCode;

        if (lastConnectedCharCode === 0) {
            targetCharCode = startCharCode; // 'a'
        } else {
            targetCharCode = lastConnectedCharCode + 1;
        }

        // 防止超过 'z'
        if (targetCharCode > 'z'.charCodeAt(0)) {
            targetCharCode = 'z'.charCodeAt(0);
        }

        // 3. 执行清理：移除所有 > targetCharCode 的动态端口
        // 倒序遍历，防止移除时索引错位
        for (let i = this.inputs.length - 1; i >= 0; i--) {
            const input = this.inputs[i];
            const match = input.name.match(dynamicInputRegex);

            if (match) {
                const currentCharCode = match[1].charCodeAt(0);

                // 逻辑：如果当前端口 晚于 我们的目标空闲端口，删掉它
                // 比如：连接了 a，目标是 b。此时如果存在 c, d, e... 全部删除。
                // 注意：这里不会删除 targetCharCode 本身，也不会删除已连接的端口(因为它们肯定 <= lastConnected)
                if (currentCharCode > targetCharCode) {
                    this.removeInput(i);
                }
            }
        }

        // 4. 执行添加：确保 targetCharCode 存在
        // 比如：连接了 a，清理掉了 c, d... 现在检查 b 是否存在，不存在就加上
        const targetName = getName(String.fromCharCode(targetCharCode));
        const exists = this.inputs.find(i => i.name === targetName);

        if (!exists) {
            this.addInput(targetName, inputType);
        }
    };

    // --- 1. 节点创建时 ---
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
        if (onNodeCreated) onNodeCreated.apply(this, arguments);

        // 推迟执行，等待 ComfyUI 补全后端定义的端口
        setTimeout(() => {
            this.cleanupDynamicInputs();
        }, 0);
    };

    // --- 2. 页面加载/刷新恢复数据时 ---
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function() {
        if (onConfigure) onConfigure.apply(this, arguments);

        // 推迟执行，等待连线数据恢复
        setTimeout(() => {
            this.cleanupDynamicInputs();
        }, 0);
    };

    // --- 3. 连线发生变化时 (连接或断开) ---
    const onConnectionsChange = nodeType.prototype.onConnectionsChange;
    nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info, slot) {
        if (onConnectionsChange) onConnectionsChange.apply(this, arguments);

        // 只关注输入端口的变化
        if (type === 1) {
            // 无论连接还是断开，都重新计算布局
            // 使用 setTimeout 确保 ComfyUI 内部状态已更新
            setTimeout(() => {
                this.cleanupDynamicInputs();
            }, 0);
        }
    };
}