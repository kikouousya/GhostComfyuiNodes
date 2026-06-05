import {app} from "../../scripts/app.js";
import {api} from "../../scripts/api.js";

// --- Configuration ---
const LIMIT_INLINE_PREVIEW = 200; // 低于此数量在节点内显示

// --- CSS Styles ---
const style = document.createElement("style");
style.textContent = `
    /* Modal (全屏) 样式 */
    .xy-grid-modal {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.85); z-index: 9999;
        display: flex; flex-direction: column; overflow: hidden;
        font-family: sans-serif;
    }
    .xy-toolbar {
        height: 40px; background: #222; display: flex; align-items: center;
        padding: 0 10px; justify-content: space-between; border-bottom: 1px solid #444;
    }
    .xy-title { color: #eee; font-weight: bold; }
    .xy-close-btn {
        background: #a00; color: white; border: none; padding: 5px 10px;
        cursor: pointer; border-radius: 4px;
    }
    .xy-viewport {
        flex: 1; overflow: hidden; position: relative; cursor: grab;
        background-color: #111;
        background-image: radial-gradient(#333 1px, transparent 1px);
        background-size: 20px 20px;
    }
    .xy-viewport:active { cursor: grabbing; }
    .xy-content-container {
        position: absolute; transform-origin: 0 0; will-change: transform;
    }

    /* 通用表格样式 */
    .xy-table {
        border-collapse: collapse; margin: 0; padding: 0;
        background: #000; table-layout: fixed;
    }
    .xy-table td, .xy-table th {
        border: 1px solid #444; padding: 4px; text-align: center;
        color: #ccc; vertical-align: middle; min-width: 150px;
    }
    .xy-table th { background: #333; font-weight: bold; font-size: 14px; padding: 10px;}
    
    /* --- 节点内联模式专用样式 --- */
    .xy-inline-wrapper {
        width: 100%;
        overflow: auto;
        background: #151515;
        border: 1px solid #333;
        box-sizing: border-box;
        margin-top: 5px;
        position: relative;
    }
    .xy-inline-wrapper .xy-table {
        width: 100%;
        min-width: fit-content; /* 保证表格不被挤压 */
    }
    /* 表头固定 */
    .xy-inline-wrapper .xy-table th {
        position: sticky; top: 0; z-index: 10;
        font-size: 12px; padding: 6px;
    }
    .xy-inline-wrapper .xy-table td {
        min-width: 80px; /* 节点内稍微紧凑一点 */
    }
    
    /* Batch Grid 样式 */
    .sub-grid-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(60px, 1fr)); 
        gap: 2px; width: 100%; height: 100%;
    }
    .xy-table img {
        display: block; width: 100%; height: auto; 
        transition: transform 0.1s; cursor: zoom-in;
        object-fit: contain; border-radius: 2px;
    }
    .xy-table img:hover { filter: brightness(1.2); }

    /* Lightbox */
    .xy-lightbox {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.95); z-index: 10000;
        display: none; align-items: center; justify-content: center;
    }
    .xy-lightbox.active { display: flex; }
    .xy-lightbox img {
        max-width: 95%; max-height: 95%; 
        box-shadow: 0 0 20px rgba(0,0,0,0.8);
        cursor: grab;
    }
`;
document.head.appendChild(style);

app.registerExtension({
    name: "MyUtils.XYGridPreview",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "Tool_XYGridPreview") {

            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                if (onExecuted) onExecuted.apply(this, arguments);

                if (message && message.xy_preview && message.xy_preview[0]) {
                    this.xyData = message.xy_preview[0];
                    const totalImgs = this.xyData.total_images || 0;

                    // --- 清理旧的 widget (按钮或HTML) ---
                    // 不建议直接重新赋值 this.widgets，容易破坏引用。
                    // 最好是复用或从尾部安全移除。
                    if (this.widgets) {
                        for (let i = this.widgets.length - 1; i >= 0; i--) {
                            const w = this.widgets[i];
                            if (w.name === "preview_btn" || w.name === "xy_grid_inline" || w.name === "hint") {
                                // LiteGraph 原生移除方式
                                this.widgets.splice(i, 1);
                            }
                        }
                    }
                    const btn = this.addWidget("button", "preview_btn", null, () => {
                        createGridModal(this.xyData);
                    });
                    btn.name = `🔍 Open Preview (${totalImgs} imgs)` ;


                    if (totalImgs <= LIMIT_INLINE_PREVIEW) {
                        // === 方案 A: 节点内联显示 ===
                        const div = document.createElement("div");
                        div.className = "xy-inline-wrapper";
                        div.appendChild(generateGridHtml(this.xyData));

                        // 必须设置 pointerEvents 才能滚动
                        div.style.pointerEvents = "auto";

                        // 使用 addDOMWidget
                        const widget = this.addDOMWidget("xy_grid_inline", "div", div, {
                            serialize: false,
                            hideOnZoom: false
                        });

                        // 调整节点尺寸
                        requestAnimationFrame(() => {
                            // 计算内容高度，最大600
                            let contentH = 300;
                            if (div.firstElementChild) {
                                contentH = Math.min(600, div.firstElementChild.scrollHeight + 50);
                            }
                            // 保持一定的宽度
                            const newW = Math.max(this.size[0], 500);
                            this.setSize([newW, contentH + 40]); // +40 给顶部标题栏留空
                            this.setDirtyCanvas(true, true);
                        });

                    } else {
                        // === 方案 B: 超过限制，显示提示文字 ===
                        const hintText = `Total images: ${totalImgs}. Click the button above to open the full preview modal.`;
                        const hintWidget = this.addWidget("text", "hint", hintText, null, {
                            multiline: true,
                            inputMode: true
                        });
                        hintWidget.inputEl.readOnly = true;
                        hintWidget.inputEl.style.opacity = 0.6;


                    }
                }
            };
        }
    }
});

// --- Helper Functions ---

function createImgElement(imgInfo) {
    const url = api.apiURL(`/view?filename=${encodeURIComponent(imgInfo.filename)}&type=${imgInfo.type}&subfolder=${imgInfo.subfolder}`);
    const img = document.createElement("img");
    img.src = url;
    img.title = imgInfo.filename;
    img.loading = "lazy";
    img.onclick = (e) => {
        e.stopPropagation();
        openLightbox(url);
    };
    return img;
}

/**
 * 生成表格 HTML 对象
 */
function generateGridHtml(data) {
    const table = document.createElement("table");
    table.className = "xy-table";

    // Header (X)
    if (data.x_labels && data.x_labels.length > 0) {
        const trHead = document.createElement("tr");
        if (data.y_labels && data.y_labels.length > 0) {
            trHead.appendChild(document.createElement("th")); // Corner
        }
        data.x_labels.forEach(lbl => {
            const th = document.createElement("th");
            th.innerText = lbl;
            trHead.appendChild(th);
        });
        table.appendChild(trHead);
    }

    // Rows (Y)
    data.grid.forEach((rowCells, rowIdx) => {
        const tr = document.createElement("tr");

        // Y Label
        if (data.y_labels && data.y_labels.length > 0) {
            const thY = document.createElement("th");
            thY.innerText = data.y_labels[rowIdx] || `Y-${rowIdx}`;
            tr.appendChild(thY);
        }

        // Cells
        rowCells.forEach(cellData => {
            const td = document.createElement("td");

            if (Array.isArray(cellData) && cellData.length > 0) {
                const subGrid = document.createElement("div");
                subGrid.className = "sub-grid-container";

                // 4张图时强制2x2，其他自适应
                if (cellData.length === 4) {
                    subGrid.style.gridTemplateColumns = "repeat(2, 1fr)";
                }

                cellData.forEach(imgInfo => {
                    subGrid.appendChild(createImgElement(imgInfo));
                });
                td.appendChild(subGrid);
            } else {
                td.innerHTML = "<span style='color:#444; font-size:10px;'>-</span>";
            }
            tr.appendChild(td);
        });
        table.appendChild(tr);
    });
    return table;
}

function createGridModal(data) {
    const existing = document.querySelector(".xy-grid-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.className = "xy-grid-modal";

    // Toolbar
    const toolbar = document.createElement("div");
    toolbar.className = "xy-toolbar";
    toolbar.innerHTML = `
        <span class="xy-title">XY Grid Preview (${data.total_images || 0} imgs)</span>
        <div style="font-size:12px; color:#888;">Scroll to Zoom • Drag to Pan</div>
        <button class="xy-close-btn">Close</button>
    `;
    toolbar.querySelector(".xy-close-btn").onclick = () => modal.remove();
    modal.appendChild(toolbar);

    // Viewport
    const viewport = document.createElement("div");
    viewport.className = "xy-viewport";
    modal.appendChild(viewport);

    const container = document.createElement("div");
    container.className = "xy-content-container";
    viewport.appendChild(container);

    // Render Table
    container.appendChild(generateGridHtml(data));
    document.body.appendChild(modal);

    // Pan/Zoom Logic
    let scale = 1, panX = 50, panY = 50;
    const update = () => container.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    update();

    viewport.addEventListener("wheel", (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        const nextScale = scale * delta;
        if (nextScale < 0.1 || nextScale > 10) return;

        const rect = viewport.getBoundingClientRect();
        const ox = e.clientX - rect.left;
        const oy = e.clientY - rect.top;

        panX = ox - (ox - panX) * delta;
        panY = oy - (oy - panY) * delta;
        scale = nextScale;
        update();
    });

    let isDrag = false, sx, sy, ix, iy;
    viewport.addEventListener("mousedown", e => {
        if (e.target.tagName === 'IMG') return; // 让图片可以点击放大
        isDrag = true;
        sx = e.clientX;
        sy = e.clientY;
        ix = panX;
        iy = panY;
    });
    window.addEventListener("mousemove", e => {
        if (!isDrag) return;
        panX = ix + (e.clientX - sx);
        panY = iy + (e.clientY - sy);
        update();
    });
    window.addEventListener("mouseup", () => isDrag = false);
}

function openLightbox(src) {
    const box = document.createElement("div");
    box.className = "xy-lightbox active";
    const img = document.createElement("img");
    img.src = src;

    let scale = 1, px = 0, py = 0, isD = false, sx, sy;
    const up = () => img.style.transform = `translate(${px}px, ${py}px) scale(${scale})`;

    box.addEventListener("wheel", e => {
        e.preventDefault();
        scale *= e.deltaY > 0 ? 0.9 : 1.1;
        up();
    });
    img.addEventListener("mousedown", e => {
        e.preventDefault();
        isD = true;
        sx = e.clientX - px;
        sy = e.clientY - py;
    });
    window.addEventListener("mousemove", e => {
        if (isD) {
            px = e.clientX - sx;
            py = e.clientY - sy;
            up();
        }
    });
    window.addEventListener("mouseup", () => isD = false);
    box.addEventListener("click", e => {
        if (e.target === box) box.remove();
    });

    box.appendChild(img);
    document.body.appendChild(box);
}