import {app} from "../../scripts/app.js";
import {api} from "../../scripts/api.js";

// --- 样式定义 ---
if (!document.getElementById("comfy-eta-style")) {
    const styleElement = document.createElement("style");
    styleElement.id = "comfy-eta-style";
    styleElement.textContent = `
        #comfy-eta-popup {
            position: fixed;
            z-index: 10000;
            background-color: #222;
            border: 1px solid #444;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            color: #ddd;
            font-family: monospace;
            font-size: 13px;
            width: 300px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            user-select: none;
            transition: height 0.2s ease;
        }
        #comfy-eta-popup.minimized { height: auto !important; }
        #comfy-eta-popup.minimized .eta-body { display: none; }
        .eta-header {
            background-color: #333; padding: 6px 10px; cursor: grab;
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid #444;
        }
        .eta-header:active { cursor: grabbing; }
        .eta-title { font-weight: bold; color: #00ffcc; }
        .eta-controls { display: flex; gap: 6px; }
        .eta-btn {
            background: transparent; border: none; color: #888;
            cursor: pointer; font-weight: bold; padding: 0 4px; border-radius: 3px;
        }
        .eta-btn:hover { background-color: #555; color: #fff; }
        .eta-btn.close:hover { background-color: #a00; }
        .eta-body {
            padding: 10px; background-color: rgba(20, 20, 30, 0.95);
            display: flex; flex-direction: column; gap: 8px;
        }
        .eta-text { white-space: pre-wrap; line-height: 1.4; }
        .eta-progress-bg {
            height: 8px; background-color: #444; border-radius: 4px;
            overflow: hidden; width: 100%;
        }
        .eta-progress-fill {
            height: 100%; width: 0%; background-color: #00aa00;
            transition: width 0.3s ease, background-color 0.3s ease;
        }
    `;
    document.head.appendChild(styleElement);
}

// --- 辅助函数：格式化时间 HH:MM:SS ---
function formatSeconds(sec) {
    if (sec < 0) sec = 0;
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    return `${h}:` + [m, s].map(v => v < 10 ? "0" + v : v).join(":");
}

// --- 悬浮窗逻辑 ---
const ETAPopup = {
    id: "comfy-eta-popup",
    element: null,
    textEl: null,
    barEl: null,

    // 计时与历史记录
    tickerInterval: null,
    tickerData: null,

    // 速率计算专用：历史数据 [{time: ms, current: int}]
    history: [],
    startTime: null, // 记录本次大循环的起始时间

    // 状态标记
    hasError: false,

    state: {
        x: window.innerWidth / 2 - 150,
        y: 60,
        minimized: false,
        closedByUser: false
    },
    lsKey: "Comfy.MyUtils.ETAWindow",
    current: 0,

    init() {
        const saved = localStorage.getItem(this.lsKey);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                if (parsed.x < 0) parsed.x = 0;
                if (parsed.y < 0) parsed.y = 0;
                if (parsed.x > window.innerWidth - 50) parsed.x = window.innerWidth - 300;
                this.state = {...this.state, ...parsed};
                this.state.closedByUser = false;
            } catch (e) {
            }
        }
        if (!this.element) this.createDOM();
        this.applyState();
    },

    createDOM() {
        const el = document.createElement("div");
        el.id = this.id;

        const header = document.createElement("div");
        header.className = "eta-header";
        header.innerHTML = `
            <span class="eta-title">ETA Monitor</span>
            <div class="eta-controls">
                <button class="eta-btn" id="eta-min">_</button>
                <button class="eta-btn close" id="eta-close">X</button>
            </div>`;

        const body = document.createElement("div");
        body.className = "eta-body";
        body.innerHTML = `
            <div class="eta-text">Waiting...</div>
            <div class="eta-progress-bg"><div class="eta-progress-fill"></div></div>`;

        el.appendChild(header);
        el.appendChild(body);
        document.body.appendChild(el);
        this.element = el;
        this.textEl = body.querySelector(".eta-text");
        this.barEl = body.querySelector(".eta-progress-fill");

        header.querySelector("#eta-min").onclick = (e) => {
            e.stopPropagation();
            this.toggleMinimize();
        };
        header.querySelector("#eta-close").onclick = (e) => {
            e.stopPropagation();
            this.close();
        };
        this.setupDrag(header);
    },

    setupDrag(headerEl) {
        let isDragging = false;
        let offsetX, offsetY;

        headerEl.addEventListener("mousedown", (e) => {
            isDragging = true;
            offsetX = e.clientX - this.element.offsetLeft;
            offsetY = e.clientY - this.element.offsetTop;
            this.element.style.transition = "none";
        });

        document.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            let newX = e.clientX - offsetX;
            let newY = e.clientY - offsetY;
            newX = Math.max(0, Math.min(window.innerWidth - this.element.offsetWidth, newX));
            newY = Math.max(0, Math.min(window.innerHeight - this.element.offsetHeight, newY));
            this.element.style.left = newX + "px";
            this.element.style.top = newY + "px";
            this.state.x = newX;
            this.state.y = newY;
        });

        document.addEventListener("mouseup", () => {
            if (isDragging) {
                isDragging = false;
                this.element.style.transition = "";
                this.saveState();
            }
        });
    },

    // --- 新增：初始化显示（Dummy Window） ---
    onStartNewRound() {
        if (!this.element) this.init();
        if (this.state.closedByUser) return;

        // 重置 UI
        this.element.style.display = "flex";
        this.hasError = false;
        this.textEl.innerText = "Initializing Run...";
        this.barEl.style.width = "0%";
        this.barEl.style.backgroundColor = "#555";

        // 重置内部数据
        this.stopTicker();
        this.history = [];
        this.startTime = null;
        this.tickerData = null;
        this.current = 0;

    },

    update(message) {
        if (!this.element) this.init();

        const showRequest = message.show_popup ? message.show_popup[0] : false;
        let current = message.current ? message.current[0] : 0;
        if (current === -1) {
            // 自动current+1
            current = this.current + 1
        }
        this.current = current;
        const total = message.total ? message.total[0] : 1;
        const label = message.label ? message.label[0] : "Job";

        // 1. 显示控制
        if (showRequest && !this.state.closedByUser) {
            this.element.style.display = "flex";
        } else if (!showRequest) {
            this.element.style.display = "none";
            this.stopTicker();
            return;
        }

        this.hasError = false;
        const now = Date.now();

        // 2. 检测进度重置 (Reset Detection)
        // 如果 current 变小了，说明可能开始了新的循环
        let lastCurrent = -1;
        if (this.history.length > 0) {
            lastCurrent = this.history[this.history.length - 1].current;
        }

        if (current < lastCurrent) {
            // 重置统计
            this.history = [];
            this.startTime = now;
        }

        // 3. 记录历史数据
        this.history.push({time: now, current: current});

        // 4. 清理旧数据 (保留最近60秒)
        const cutoff = now - 60000;
        this.history = this.history.filter(h => h.time >= cutoff);

        // 5. 确保 StartTime
        if (!this.startTime) {
            // 如果是第一次收到数据，或者刚刚重置过
            this.startTime = now;
        } else if (this.history.length > 0) {
            // 如果历史数据被完全清空过(极少情况)，校准 startTime
            if (this.startTime > this.history[0].time) {
                this.startTime = this.history[0].time;
            }
        }

        // 6. UI 更新
        const progress = Math.max(0, Math.min(100, (current / total) * 100));
        this.barEl.style.width = progress + "%";

        if (current >= total) {
            this.stopTicker();
            // 完成时立即刷新一次 Text
            this.tickerData = {total, label, current};
            this.tick(true);
            this.barEl.style.backgroundColor = "#44ff44"; // Green
        } else {
            this.startTicker({total, label, current});
            this.barEl.style.backgroundColor = "#566fc9"; // Blue
        }
    },

    startTicker(data) {
        this.tickerData = data;
        if (!this.tickerInterval) {
            this.tickerInterval = setInterval(() => {
                this.tick();
            }, 1000);
            this.tick(); // 立即执行一次
        }
    },

    stopTicker() {
        if (this.tickerInterval) {
            clearInterval(this.tickerInterval);
            this.tickerInterval = null;
        }
    },

    reset(isError = false) {
        if (isError) {
            this.stopTicker();
            this.hasError = true;
            if (this.element) {
                this.textEl.innerText += "\n[Stopped / Error]";
                this.barEl.style.backgroundColor = "#aa0000";
            }
            return;
        }

        if (this.hasError) return;

        this.stopTicker();

        // 检查是否是手动取消
        if (this.element && this.tickerData) {
            const {current, total} = this.tickerData;
            // 如果进度未满就收到停止信号，判定为 Cancel
            if (current < total) {
                this.textEl.innerText += "\n[Cancelled]";
                this.barEl.style.backgroundColor = "#ddaa00";
            } else {
                // 正常完成
                if (this.barEl.style.width !== "0%") {
                    this.barEl.style.width = "100%";
                    this.barEl.style.backgroundColor = "#44ff44";
                }
            }
        }
    },

    tick(isFinal = false) {
        if (!this.tickerData) return;

        const {total, label, current} = this.tickerData;
        const now = Date.now();

        // --- 核心速率计算 (基于最近1分钟) ---
        let speed = 0; // items/sec
        let validRate = false;

        if (this.history.length >= 2) {
            const first = this.history[0];
            const last = this.history[this.history.length - 1];

            const timeDiff = (last.time - first.time) / 1000; // seconds
            const countDiff = last.current - first.current;

            if (timeDiff > 0.1 && countDiff > 0) {
                speed = countDiff / timeDiff;
                validRate = true;
            }
        }

        // 运行总耗时
        const runElapsed = this.startTime ? (now - this.startTime) / 1000 : 0;

        // ETA 计算
        let etaSec = 0;
        let speedStr = "Calculating...";

        if (validRate && speed > 0) {
            const remaining = total - current;
            etaSec = remaining / speed;

            if (speed >= 1.0) {
                speedStr = `${speed.toFixed(2)}it/s`;
            } else {
                speedStr = `${(1.0 / speed).toFixed(2)}s/it`;
            }
        } else if (current === 0) {
            speedStr = "Waiting...";
        }

        if (current >= total || isFinal) {
            etaSec = 0;
            speedStr = "Done";
        }

        const pct = ((current / total) * 100).toFixed(1);
        const elapsedStr = formatSeconds(runElapsed);
        const etaStr = formatSeconds(etaSec);

        const newText = `${label}: ${current}/${total} (${pct}%) ${speedStr}\nRun: ${elapsedStr} | ETA: ${etaStr}`;
        this.textEl.innerText = newText;
    },

    toggleMinimize() {
        this.state.minimized = !this.state.minimized;
        this.applyState();
        this.saveState();
    },

    close() {
        this.element.style.display = "none";
        this.state.closedByUser = true;
        this.stopTicker();
    },

    applyState() {
        if (!this.element) return;
        this.element.style.left = this.state.x + "px";
        this.element.style.top = this.state.y + "px";
        if (this.state.minimized) this.element.classList.add("minimized");
        else this.element.classList.remove("minimized");
    },

    saveState() {
        localStorage.setItem(this.lsKey, JSON.stringify({
            x: this.state.x,
            y: this.state.y,
            minimized: this.state.minimized
        }));
    }
};

app.registerExtension({
    name: "FlowControl.ETA_Visual",

    async setup() {
        // 1. 监听报错，变红
        api.addEventListener("execution_error", () => {
            ETAPopup.reset(true);
        });

        // 2. 监听开始，显示 Dummy Window
        api.addEventListener("execution_start", (e) => {
            ETAPopup.onStartNewRound();
        });

        // 3. 监听结束 (Success or Cancel)
        api.addEventListener("executing", (e) => {
            // e.detail !== null 代表某个节点正在运行
            if (e.detail !== null) {
                ETAPopup.hasError = false;
            } else {
                // null 代表整个流程结束
                ETAPopup.reset(false);
            }
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "ETA_Calculator") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) onNodeCreated.apply(this, arguments);
                this.eta_progress = 0.0;
                const widgetName = "Status_Display";
                if (!this.widgets?.find(w => w.name === widgetName)) {
                    const w = this.addWidget("text", widgetName, "Waiting...", () => {
                    }, {multiline: true, serialize: false});
                    w.disabled = true;
                }
                this.setSize([260, 100]);
            };

            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                if (onExecuted) onExecuted.apply(this, arguments);

                // 接收 Python 传来的 ui 数据
                if (message && message.text) {
                    const w = this.widgets.find(w => w.name === "Status_Display");
                    if (w) w.value = message.text[0];

                    this.eta_progress = message.progress ? message.progress[0] : 0;

                    // 直接传入 message，而不是 message.ui
                    ETAPopup.update(message);
                    this.setDirtyCanvas(true);
                }
            };

            const onDrawForeground = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function (ctx) {
                if (onDrawForeground) onDrawForeground.apply(this, arguments);
                if (this.flags.collapsed) return;
                const progress = this.eta_progress || 0;
                if (progress > 0) {
                    ctx.save();
                    const h = 6;
                    const w = this.size[0];
                    const x = 0;
                    const y = this.size[1] - h;
                    ctx.fillStyle = "#111";
                    ctx.fillRect(x, y, w, h);
                    ctx.fillStyle = progress < 1.0 ? "#00AA00" : "#44FF44";
                    ctx.fillRect(x, y, w * progress, h);
                    ctx.restore();
                }
            };
        }
    },
});