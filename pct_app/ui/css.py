"""前端视觉 CSS — Scientific Minimalism 设计系统 v2.0

基于 ui-ux-pro-max-skill 设计原则重新设计

设计语言:
  风格: Scientific Minimalism + Data Dashboard
  - 专业科研感,清晰的数据层次
  - 科学蓝/青绿主色调,高对比度可访问性
  - 清晰的层级结构 (L0-L4)
  - 精致的微动效和过渡

色彩系统:
  Primary: #1e40af (深蓝,科研可信度)
  Secondary: #0891b2 (青绿,数据可视化)
  Accent: #6366f1 (紫蓝,交互强调)
  Success: #059669 (翠绿,成功状态)
  Warning: #d97706 (琥珀,警告状态)
  Danger: #dc2626 (红色,错误状态)
  
背景层次:
  L0 page: #f8fafc (页面背景,极浅灰蓝)
  L1 card: #ffffff (卡片背景)
  L2 panel: #f1f5f9 (面板背景)
  L3 control: rgba(30, 64, 175, 0.08) (控件聚焦态)
"""

CUSTOM_CSS = r"""
/* ============================================================
   CSS 设计系统变量 — Scientific Minimalism + Glass Touches v3.0
   ============================================================ */
:root {
    /* 主色调 - Scientific Blue */
    --pct-primary: #1e40af;
    --pct-primary-light: #3b82f6;
    --pct-primary-dark: #1e3a8a;
    --pct-primary-alpha: rgba(30, 64, 175, 0.08);

    /* 次要色 - Scientific Teal */
    --pct-secondary: #0891b2;
    --pct-secondary-light: #06b6d4;
    --pct-secondary-dark: #0e7490;

    /* 强调色 - Scientific Indigo */
    --pct-accent: #6366f1;
    --pct-accent-light: #818cf8;

    /* 状态色 */
    --pct-success: #059669;
    --pct-success-light: #10b981;
    --pct-success-bg: #ecfdf5;

    --pct-warning: #d97706;
    --pct-warning-light: #f59e0b;
    --pct-warning-bg: #fffbeb;

    --pct-danger: #dc2626;
    --pct-danger-light: #ef4444;
    --pct-danger-bg: #fef2f2;

    /* 中性色 */
    --pct-text-primary: #0f172a;
    --pct-text-secondary: #475569;
    --pct-text-muted: #94a3b8;
    --pct-border: #e2e8f0;
    --pct-border-light: #f1f5f9;

    /* 背景色 */
    --pct-bg-page: #f8fafc;
    --pct-bg-card: #ffffff;
    --pct-bg-panel: #f1f5f9;
    --pct-bg-hover: #f8fafc;

    /* 阴影系统 — 更细腻的层次 */
    --pct-shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.04);
    --pct-shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03);
    --pct-shadow-md: 0 4px 8px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -1px rgba(15, 23, 42, 0.04);
    --pct-shadow-lg: 0 12px 20px -3px rgba(15, 23, 42, 0.08), 0 4px 8px -2px rgba(15, 23, 42, 0.04);
    --pct-shadow-xl: 0 24px 32px -6px rgba(15, 23, 42, 0.10), 0 10px 14px -4px rgba(15, 23, 42, 0.05);
    --pct-shadow-glow: 0 0 60px rgba(30, 64, 175, 0.18);

    /* 圆角系统 */
    --pct-radius-xs: 4px;
    --pct-radius-sm: 8px;
    --pct-radius-md: 12px;
    --pct-radius-lg: 16px;
    --pct-radius-xl: 24px;

    /* 过渡动画 */
    --pct-transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    --pct-transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    --pct-transition-slow: 0.4s cubic-bezier(0.4, 0, 0.2, 1);

    /* 间距系统 — 8pt 网格 */
    --pct-space-1: 4px;
    --pct-space-2: 8px;
    --pct-space-3: 12px;
    --pct-space-4: 16px;
    --pct-space-5: 24px;
    --pct-space-6: 32px;
    --pct-space-7: 48px;
    --pct-space-8: 64px;
}

/* ============================================================
   全局排版 — 中文优先的字体堆栈 + 更好的可读性
   ============================================================ */
*, *::before, *::after {
    box-sizing: border-box;
}

html, body {
    font-family: "Inter", "PingFang SC", "Microsoft YaHei", -apple-system,
                 BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
                 Arial, sans-serif !important;
    color: var(--pct-text-primary);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}

/* 字体重叠修复 */
.gradio-container, .gradio-container * {
    line-height: 1.55 !important;
}

/* Resilient typography — 防止溢出 */
h1, h2, h3, h4, h5, h6,
.hero-title, .hero-subtitle,
.pct-step-title, .pct-step-body {
    line-height: 1.35 !important;
    word-break: break-word;
    overflow-wrap: break-word;
}

/* 友好文本换行 — 长 URL / 公式等可安全换行 */
code, pre, .pct-csv-pre, .pct-preview-table td {
    word-break: break-all;
    overflow-wrap: anywhere;
    hyphens: auto;
}

/* ============================================================
   容器布局 — 更宽的呼吸空间
   ============================================================ */
.gradio-container {
    max-width: 1480px !important;
    margin: 0 auto !important;
    padding: 28px 36px 56px 36px !important;
    background: var(--pct-bg-page);
}

/* ============================================================
   隐藏 Gradio 默认 footer
   ============================================================ */
footer { display: none !important; }

/* ============================================================
   Hero Banner v3 — Scientific Minimalism + Glass Touch
   ============================================================ */
.hero-banner {
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(at 80% 20%, rgba(8, 145, 178, 0.35) 0%, transparent 50%),
        radial-gradient(at 20% 80%, rgba(99, 102, 241, 0.30) 0%, transparent 50%),
        linear-gradient(135deg, #1e3a5f 0%, #1e40af 50%, #0e7490 100%);
    padding: 64px 56px 56px 56px;
    border-radius: var(--pct-radius-xl);
    color: #fff;
    margin: 8px 0 40px 0;
    box-shadow: var(--pct-shadow-xl), var(--pct-shadow-glow);
}

/* 背景装饰 - 几何网格 */
.hero-banner::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: 
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
}

/* 光晕效果 */
.hero-banner::after {
    content: "";
    position: absolute;
    top: -50%;
    right: -20%;
    width: 60%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(8, 145, 178, 0.25) 0%, transparent 70%);
    pointer-events: none;
}

.hero-title {
    font-size: 38px !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    margin: 0 0 16px 0 !important;
    text-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
    position: relative;
    z-index: 1;
}

.hero-subtitle {
    font-size: 15px !important;
    line-height: 1.7 !important;
    opacity: 0.95;
    max-width: 960px;
    margin: 0 !important;
    position: relative;
    z-index: 1;
}

.hero-tags {
    margin-top: 24px;
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.hero-tag {
    display: inline-block;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border-radius: 20px;
    padding: 6px 14px;
    margin: 0;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
    color: #fff;
    transition: var(--pct-transition-fast);
}

.hero-tag:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(-1px);
}

/* 工作流 5 卡片 - 新设计 */
.workflow-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
    margin-top: 36px;
    position: relative;
    z-index: 1;
}

.workflow-card {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: var(--pct-radius-lg);
    padding: 20px 12px 18px 12px;
    text-align: center;
    transition: var(--pct-transition-normal);
}

.workflow-card:hover {
    background: rgba(255, 255, 255, 0.15);
    transform: translateY(-3px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
}

.workflow-num {
    width: 42px;
    height: 42px;
    background: linear-gradient(135deg, #fff 0%, #e2e8f0 100%);
    color: var(--pct-primary);
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 18px;
    margin-bottom: 10px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.workflow-icon { font-size: 24px; margin: 4px 0 6px 0; }
.workflow-label { font-size: 13px; font-weight: 600; letter-spacing: 0.3px; }

/* ============================================================
   核心: 大步骤卡 (L1) - 视觉锚点 v2
   ============================================================ */
.pct-step {
    position: relative;
    margin: 32px 0 16px 0;
    padding: 0;
    background: transparent;
    border: none;
}

.pct-step-bar {
    /* 顶部彩色进度条 */
    height: 5px;
    background: linear-gradient(90deg, var(--pct-primary) 0%, var(--pct-secondary) 100%);
    border-radius: 5px 5px 0 0;
    margin: 0 -4px;
    box-shadow: 0 2px 12px rgba(30, 64, 175, 0.3);
}

.pct-step-2 .pct-step-bar {
    background: linear-gradient(90deg, var(--pct-secondary) 0%, var(--pct-success) 100%);
    box-shadow: 0 2px 12px rgba(8, 145, 178, 0.3);
}

.pct-step-3 .pct-step-bar {
    background: linear-gradient(90deg, var(--pct-accent) 0%, var(--pct-primary) 100%);
    box-shadow: 0 2px 12px rgba(99, 102, 241, 0.3);
}

.pct-step-4 .pct-step-bar {
    background: linear-gradient(90deg, var(--pct-success) 0%, var(--pct-secondary) 100%);
    box-shadow: 0 2px 12px rgba(5, 150, 105, 0.3);
}

.pct-step-5 .pct-step-bar {
    background: linear-gradient(90deg, var(--pct-warning) 0%, var(--pct-accent) 100%);
    box-shadow: 0 2px 12px rgba(217, 119, 6, 0.3);
}

.pct-step-6 .pct-step-bar {
    background: linear-gradient(90deg, var(--pct-secondary) 0%, var(--pct-primary) 100%);
    box-shadow: 0 2px 12px rgba(8, 145, 178, 0.3);
}

.pct-step-head {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 20px 14px 20px;
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-top: none;
    border-radius: 0 0 var(--pct-radius-lg) var(--pct-radius-lg);
    box-shadow: var(--pct-shadow-md);
    position: relative;
    z-index: 2;
}

.pct-step-num {
    width: 34px;
    height: 34px;
    background: linear-gradient(135deg, var(--pct-primary) 0%, var(--pct-primary-dark) 100%);
    color: white;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 15px;
    box-shadow: 0 4px 12px rgba(30, 64, 175, 0.3);
    flex-shrink: 0;
}

.pct-step-2 .pct-step-num {
    background: linear-gradient(135deg, var(--pct-secondary) 0%, var(--pct-secondary-dark) 100%);
    box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
}

.pct-step-3 .pct-step-num {
    background: linear-gradient(135deg, var(--pct-accent) 0%, var(--pct-primary) 100%);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.pct-step-4 .pct-step-num {
    background: linear-gradient(135deg, var(--pct-success) 0%, var(--pct-secondary) 100%);
    box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
}

.pct-step-5 .pct-step-num {
    background: linear-gradient(135deg, var(--pct-warning) 0%, var(--pct-accent) 100%);
    box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3);
}

.pct-step-6 .pct-step-num {
    background: linear-gradient(135deg, var(--pct-secondary) 0%, var(--pct-primary) 100%);
    box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
}

.pct-step-icon { font-size: 22px; }
.pct-step-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--pct-text-primary);
    letter-spacing: 0.2px;
}
.pct-step-status {
    margin-left: auto;
    color: var(--pct-text-muted);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* 步骤状态动画 */
.pct-step--active .pct-step-status { color: var(--pct-primary); }
.pct-step--active .pct-step-status::before {
    content: "";
    display: inline-block;
    width: 8px;
    height: 8px;
    background: var(--pct-primary);
    border-radius: 50%;
    animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
}

.pct-step--done .pct-step-status {
    color: var(--pct-success);
}
.pct-step--done .pct-step-status::before {
    content: "✓";
    font-weight: 700;
}

.pct-step--error .pct-step-status {
    color: var(--pct-danger);
}
.pct-step--error .pct-step-status::before {
    content: "✗";
    font-weight: 700;
}

.pct-step-body {
    padding: 12px 8px 4px 8px;
    color: var(--pct-text-secondary);
    font-size: 13px;
}

/* ============================================================
   结果面板 (L2) - 子层卡片 v2
   ============================================================ */
.pct-result-panel {
    position: relative;
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 40px 20px 20px 20px;
    margin: 16px 0;
    box-shadow: var(--pct-shadow-md);
    transition: var(--pct-transition-normal);
}

.pct-result-panel:hover {
    box-shadow: var(--pct-shadow-lg);
}

.pct-layer-tag {
    position: absolute;
    top: 12px;
    left: 16px;
    z-index: 2;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: white;
    box-shadow: var(--pct-shadow-sm);
}

.pct-layer-tag-a { 
    background: linear-gradient(135deg, var(--pct-primary) 0%, var(--pct-primary-dark) 100%); 
}
.pct-layer-tag-b { 
    background: linear-gradient(135deg, var(--pct-secondary) 0%, var(--pct-secondary-dark) 100%); 
}
.pct-layer-tag-c { 
    background: linear-gradient(135deg, var(--pct-accent) 0%, var(--pct-primary) 100%); 
}
.pct-layer-tag-d { 
    background: linear-gradient(135deg, var(--pct-success) 0%, var(--pct-secondary) 100%); 
}

/* 层级深度样式 */
.pct-layer-a {
    box-shadow: var(--pct-shadow-lg);
    border-left: 4px solid var(--pct-primary);
}
.pct-layer-b {
    box-shadow: var(--pct-shadow-md);
    border-left: 4px solid var(--pct-secondary);
}
.pct-layer-c {
    box-shadow: var(--pct-shadow-md);
    border-left: 4px solid var(--pct-accent);
}
.pct-layer-d {
    box-shadow: var(--pct-shadow-sm);
    border-left: 4px solid var(--pct-success);
}

/* ============================================================
   主按钮 v2 - Scientific Gradient
   ============================================================ */
.predict-btn {
    background: linear-gradient(135deg, var(--pct-primary) 0%, var(--pct-primary-dark) 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    letter-spacing: 1px;
    border-radius: var(--pct-radius-md) !important;
    box-shadow: 0 6px 20px rgba(30, 64, 175, 0.35) !important;
    padding: 14px 28px !important;
    transition: var(--pct-transition-normal) !important;
}

.predict-btn:hover {
    box-shadow: 0 10px 30px rgba(30, 64, 175, 0.45) !important;
    transform: translateY(-2px);
    filter: brightness(1.08);
}

.batch-btn {
    background: linear-gradient(135deg, var(--pct-secondary) 0%, var(--pct-secondary-dark) 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    letter-spacing: 1px;
    border-radius: var(--pct-radius-md) !important;
    box-shadow: 0 6px 20px rgba(8, 145, 178, 0.35) !important;
    padding: 14px 28px !important;
    transition: var(--pct-transition-normal) !important;
}

.batch-btn:hover {
    box-shadow: 0 10px 30px rgba(8, 145, 178, 0.45) !important;
    transform: translateY(-2px);
    filter: brightness(1.08);
}

/* ============================================================
   示例芯片按钮 v2
   ============================================================ */
.pct-chip {
    background: var(--pct-bg-card) !important;
    border: 1px solid var(--pct-border) !important;
    color: var(--pct-text-primary) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border-radius: var(--pct-radius-sm) !important;
    box-shadow: var(--pct-shadow-sm) !important;
    transition: var(--pct-transition-fast) !important;
    cursor: pointer;
}

.pct-chip:hover {
    background: var(--pct-primary-alpha) !important;
    border-color: var(--pct-primary) !important;
    color: var(--pct-primary) !important;
    transform: translateY(-1px);
    box-shadow: var(--pct-shadow-md) !important;
}

/* ============================================================
   Tabs 选中态 v2
   ============================================================ */
.tabs > .tab-nav > button.selected {
    background: linear-gradient(135deg, var(--pct-primary) 0%, var(--pct-primary-dark) 100%) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow: 0 4px 16px rgba(30, 64, 175, 0.3) !important;
}

.tabs > .tab-nav > button {
    border-radius: var(--pct-radius-md) !important;
    font-weight: 600 !important;
    padding: 10px 18px !important;
    transition: var(--pct-transition-fast) !important;
}

.tabs > .tab-nav > button:hover:not(.selected) {
    background: var(--pct-primary-alpha) !important;
}

/* ============================================================
   输入控件 (L3) v2
   ============================================================ */
.pct-input .gr-input,
.pct-input input[type="text"],
.pct-input textarea,
.pct-input select {
    border-radius: var(--pct-radius-md) !important;
    border: 2px solid var(--pct-border) !important;
    box-shadow: var(--pct-shadow-sm) !important;
    background: var(--pct-bg-card) !important;
    transition: var(--pct-transition-fast) !important;
}

.pct-input input:focus,
.pct-input textarea:focus {
    border-color: var(--pct-primary) !important;
    box-shadow: 0 0 0 4px var(--pct-primary-alpha) !important;
    outline: none !important;
}

/* ============================================================
   图像/绘图 v2
   ============================================================ */
.pct-plot, .pct-plot img,
.gr-image, .gr-image img,
.gr-image-container {
    border-radius: var(--pct-radius-md) !important;
    border: 1px solid var(--pct-border) !important;
    overflow: hidden;
    box-shadow: var(--pct-shadow-sm);
}

/* ============================================================
   表格 v2
   ============================================================ */
.gr-dataframe, table.gr-data-table {
    border-radius: var(--pct-radius-md) !important;
    box-shadow: var(--pct-shadow-sm) !important;
    border: 1px solid var(--pct-border) !important;
    overflow: hidden;
}

.gr-data-table thead th {
    background: linear-gradient(180deg, var(--pct-bg-panel) 0%, var(--pct-border-light) 100%) !important;
    font-weight: 700 !important;
    color: var(--pct-primary) !important;
}

/* ============================================================
   文件上传区 v2
   ============================================================ */
.gr-file, .gr-file-upload, [data-testid="file-upload"] {
    border: 2px dashed var(--pct-border) !important;
    border-radius: var(--pct-radius-lg) !important;
    background: var(--pct-bg-card) !important;
    transition: var(--pct-transition-fast) !important;
}

.gr-file:hover, .gr-file-upload:hover {
    border-color: var(--pct-primary) !important;
    background: var(--pct-primary-alpha) !important;
}

/* ============================================================
   空状态 v2
   ============================================================ */
.pct-empty-wrap {
    height: 100%;
    min-height: 320px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.pct-empty-state {
    width: 100%;
    text-align: center;
    padding: 48px 32px;
    background: linear-gradient(180deg, var(--pct-bg-card) 0%, var(--pct-bg-panel) 100%);
    border: 2px dashed var(--pct-border);
    border-radius: var(--pct-radius-lg);
    color: var(--pct-text-secondary);
    transition: var(--pct-transition-normal);
}

.pct-empty-state:hover {
    border-color: var(--pct-primary);
    box-shadow: var(--pct-shadow-md);
}

.pct-empty-icon { font-size: 56px; margin-bottom: 14px; }
.pct-empty-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--pct-text-primary);
    margin-bottom: 10px;
}
.pct-empty-hint {
    font-size: 13px;
    line-height: 1.7;
    color: var(--pct-text-secondary);
    max-width: 400px;
    margin: 0 auto;
}

.pct-empty-state-error {
    background: linear-gradient(180deg, var(--pct-danger-bg) 0%, #fee2e2 100%);
    border-color: #fca5a5;
}

.pct-empty-state-error .pct-empty-title { color: var(--pct-danger); }

/* ============================================================
   摘要指标网格 (Layer A) v2
   ============================================================ */
.pct-metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 12px 0 20px 0;
}

.pct-metric {
    position: relative;
    padding: 20px 18px;
    border-radius: var(--pct-radius-md);
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    box-shadow: var(--pct-shadow-sm);
    text-align: left;
    overflow: hidden;
    transition: var(--pct-transition-fast);
}

.pct-metric:hover {
    box-shadow: var(--pct-shadow-md);
    transform: translateY(-2px);
}

.pct-metric::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 5px;
    height: 100%;
    background: var(--pct-primary);
}

.pct-metric-ok::before { background: var(--pct-success); }
.pct-metric-fail::before { background: var(--pct-danger); }
.pct-metric-hit::before { background: var(--pct-warning); }
.pct-metric-total::before { background: var(--pct-primary); }

.pct-metric-label {
    font-size: 11px;
    color: var(--pct-text-muted);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}

.pct-metric-value {
    font-size: 32px;
    font-weight: 800;
    color: var(--pct-text-primary);
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}

.pct-metric-ok .pct-metric-value { color: var(--pct-success); }
.pct-metric-fail .pct-metric-value { color: var(--pct-danger); }
.pct-metric-hit .pct-metric-value { color: var(--pct-warning); }

.pct-metric-sub {
    font-size: 11px;
    color: var(--pct-text-muted);
    margin-top: 4px;
}

.pct-range {
    padding: 14px 18px;
    background: linear-gradient(135deg, var(--pct-primary-alpha) 0%, rgba(8, 145, 178, 0.08) 100%);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    font-size: 13px;
    color: var(--pct-text-secondary);
    margin-top: 10px;
}

/* ============================================================
   CSV 预览卡片 v2
   ============================================================ */
.pct-csv-hint {
    margin-top: 16px;
    padding: 16px;
    background: linear-gradient(135deg, var(--pct-primary-alpha) 0%, rgba(8, 145, 178, 0.05) 100%);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    font-size: 13px;
    color: var(--pct-text-secondary);
}

.pct-csv-pre {
    background: var(--pct-bg-card);
    padding: 12px 14px;
    border-radius: var(--pct-radius-sm);
    margin: 10px 0;
    font-size: 12px;
    font-family: "JetBrains Mono", "SF Mono", Consolas, monospace;
    border: 1px solid var(--pct-border);
    overflow-x: auto;
}

.pct-csv-legend {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 12px;
    color: var(--pct-text-secondary);
}

.pct-csv-legend b { color: var(--pct-primary); }

.pct-preview {
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 20px;
    box-shadow: var(--pct-shadow-sm);
}

.pct-preview-meta {
    display: grid;
    grid-template-columns: 1fr 1fr 2fr;
    gap: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--pct-border);
    margin-bottom: 16px;
}

.pct-meta-item { display: flex; flex-direction: column; gap: 4px; }
.pct-meta-label {
    font-size: 11px;
    color: var(--pct-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 700;
}

.pct-meta-value {
    font-size: 24px;
    font-weight: 800;
    color: var(--pct-primary);
}

.pct-meta-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 4px;
}

/* Chip 样式 v2 */
.pct-chip-ok {
    background: var(--pct-success-bg);
    color: var(--pct-success);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 11px;
    font-weight: 700;
}

.pct-chip-fail {
    background: var(--pct-danger-bg);
    color: var(--pct-danger);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 11px;
    font-weight: 700;
}

.pct-chip-warn {
    background: var(--pct-warning-bg);
    color: var(--pct-warning);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 11px;
    font-weight: 700;
}

.pct-chip-info {
    background: var(--pct-primary-alpha);
    color: var(--pct-primary);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 11px;
    font-weight: 700;
}

.pct-preview-table-wrap {
    overflow-x: auto;
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-sm);
}

.pct-preview-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

.pct-preview-table thead th {
    background: var(--pct-bg-panel);
    padding: 10px 12px;
    text-align: left;
    color: var(--pct-primary);
    font-weight: 700;
    border-bottom: 2px solid var(--pct-border);
}

.pct-preview-table tbody td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--pct-border-light);
    color: var(--pct-text-secondary);
}

.pct-preview-table tbody tr:hover { background: var(--pct-bg-hover); }
.pct-preview-foot {
    margin-top: 10px;
    font-size: 11px;
    color: var(--pct-text-muted);
    text-align: right;
}

/* ============================================================
   Footer v2
   ============================================================ */
.app-footer {
    text-align: center;
    color: var(--pct-text-muted);
    padding: 32px 0 16px 0;
    margin-top: 48px;
    border-top: 1px solid var(--pct-border);
    font-size: 12px;
    line-height: 1.8;
    letter-spacing: 0.2px;
}

.app-footer b { color: var(--pct-primary); }

/* ============================================================
   滚动条 v2
   ============================================================ */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--pct-bg-panel); border-radius: 8px; }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--pct-border) 0%, var(--pct-text-muted) 100%);
    border-radius: 8px;
    border: 2px solid var(--pct-bg-panel);
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, var(--pct-text-muted) 0%, var(--pct-text-secondary) 100%);
}

::selection { background: var(--pct-primary-alpha); color: var(--pct-primary-dark); }

/* ============================================================
   周期表 (Composition Space Designer) v2
   ============================================================ */
.pt-wrap {
    background: linear-gradient(180deg, var(--pct-bg-card) 0%, var(--pct-bg-panel) 100%);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-lg);
    padding: 20px;
    margin: 12px 0 16px 0;
    overflow-x: auto;
}

.pt-grid {
    display: grid;
    grid-template-columns: repeat(18, minmax(44px, 1fr));
    grid-auto-rows: minmax(44px, auto);
    gap: 5px;
    margin-bottom: 16px;
    grid-auto-flow: dense;
}

.pt-cell {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4px 2px 3px 2px;
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: 6px;
    cursor: pointer;
    user-select: none;
    font-size: 11px;
    line-height: 1.15 !important;
    color: var(--pct-text-primary);
    transition: all var(--pct-transition-fast);
    box-shadow: var(--pct-shadow-sm);
    min-width: 0;
}

.pt-cell:hover {
    background: var(--pct-primary-alpha);
    border-color: var(--pct-primary-light);
    transform: translateY(-2px);
    box-shadow: var(--pct-shadow-md);
    z-index: 2;
}

.pt-cell.selected {
    background: linear-gradient(135deg, var(--pct-primary) 0%, var(--pct-primary-dark) 100%);
    border-color: transparent;
    color: white;
    box-shadow: 0 6px 16px rgba(30, 64, 175, 0.4);
    transform: translateY(-3px);
}

.pt-cell.selected .pt-z { color: rgba(255, 255, 255, 0.8); }
.pt-sym { font-weight: 800; font-size: 14px; letter-spacing: 0; }
.pt-z {
    position: absolute;
    top: 2px;
    left: 4px;
    font-size: 9px;
    color: var(--pct-text-muted);
    font-weight: 600;
}

/* 类别配色 v2 */
.cat-re {
    background: linear-gradient(180deg, #fdf2f8 0%, #fbcfe8 100%);
    border-color: #f9a8d4;
    color: #9d174d;
}

.cat-re.selected {
    background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
    color: white;
}

.cat-alkali-metal {
    background: var(--pct-warning-bg);
    border-color: #fde68a;
    color: var(--pct-warning);
}

.cat-alkali {
    background: #fef3c7;
    border-color: #fcd34d;
    color: #92400e;
}

.cat-tm {
    background: var(--pct-bg-panel);
    border-color: var(--pct-border);
    color: var(--pct-text-primary);
}

.cat-metalloid {
    background: #ecfeff;
    border-color: #a5f3fc;
    color: #155e75;
}

.cat-halogen {
    background: #fef9c3;
    border-color: #fde047;
    color: #854d0e;
}

.cat-noble {
    background: #ede9fe;
    border-color: #ddd6fe;
    color: #5b21b6;
}

.cat-other {
    background: var(--pct-bg-panel);
    border-color: var(--pct-border);
    color: var(--pct-text-secondary);
}

.pt-row-label {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 8px;
    color: var(--pct-text-secondary);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

.pt-lanthanide-row,
.pt-actinide-row {
    display: grid;
    grid-template-columns: repeat(18, minmax(44px, 1fr));
    grid-auto-flow: dense;
    gap: 5px;
}

.pt-status-row {
    display: flex;
    gap: 16px;
    margin-top: 12px;
    flex-wrap: wrap;
}

.pt-status-box {
    flex: 1 1 300px;
    padding: 12px 16px;
    background: var(--pct-primary-alpha);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    font-size: 12px;
    color: var(--pct-text-primary);
    line-height: 1.6 !important;
}

.pt-status-label {
    font-size: 11px;
    color: var(--pct-primary);
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
    text-transform: uppercase;
}

.pt-current-list {
    font-family: "JetBrains Mono", "SF Mono", Consolas, monospace;
    font-size: 13px !important;
    color: var(--pct-primary);
    font-weight: 700;
    word-break: break-all;
}

/* ============================================================
   隐藏 Gradio 内部隐藏输入框的占位
   ============================================================ */
#pt-hidden-selected textarea {
    background: transparent !important;
    color: transparent !important;
    border: none !important;
    pointer-events: none;
}

/* ============================================================
   Step 1 组份空间设计器 - 布局优化 v2
   ============================================================ */
.pct-step-1-layout {
    margin: 16px 0;
}

.pct-step-1-status-box {
    background: var(--pct-primary-alpha);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    padding: 14px 18px;
    margin-bottom: 14px;
}

.pct-step-1-status-label {
    font-size: 11px;
    color: var(--pct-primary);
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.pct-step-1-controls {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin: 20px 0;
}

.pct-step-1-buttons {
    display: flex;
    gap: 14px;
    margin: 20px 0;
    flex-wrap: wrap;
}

.pct-step-1-preview {
    margin-top: 20px;
}

/* ============================================================
   V0 滑块特殊样式
   ============================================================ */
.send-v0-slider-wrap {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 2px solid #f59e0b;
    border-radius: var(--pct-radius-lg);
    padding: 20px;
    margin: 16px 0;
    box-shadow: var(--pct-shadow-md);
}

.send-v0-label {
    font-size: 14px;
    font-weight: 700;
    color: #92400e;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.send-v0-icon {
    font-size: 20px;
}

/* CSV 上传路径 V0 批量统一设置 - 与周期表V0用同一视觉 */
.pct-csv-v0-wrap {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 2px solid #f59e0b;
    border-radius: var(--pct-radius-lg);
    padding: 16px 20px;
    margin: 12px 0 16px 0;
    box-shadow: var(--pct-shadow-md);
}

.pct-csv-v0-label {
    font-size: 14px;
    font-weight: 700;
    color: #92400e;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.pct-csv-v0-icon {
    font-size: 20px;
}

/* ============================================================
   任务历史管理 v2
   ============================================================ */
.pct-jobs-wrap {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 560px;
    overflow-y: auto;
    padding: 8px 4px;
}

.pct-job-row {
    background: var(--pct-bg-card);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    padding: 14px 16px;
    box-shadow: var(--pct-shadow-sm);
    transition: var(--pct-transition-normal);
}

.pct-job-row:hover {
    box-shadow: var(--pct-shadow-md);
    transform: translateY(-2px);
    border-color: var(--pct-primary-light);
}

.pct-job-row-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.pct-job-id-tag {
    background: linear-gradient(135deg, var(--pct-primary-alpha) 0%, rgba(8, 145, 178, 0.08) 100%);
    color: var(--pct-primary);
    padding: 5px 12px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    font-family: "JetBrains Mono", "SF Mono", Consolas, monospace;
}

.pct-job-mtime {
    font-size: 11px;
    color: var(--pct-text-muted);
}

.pct-job-row-body {
    font-size: 13px;
    color: var(--pct-text-secondary);
    margin: 6px 0 8px 0;
}

.pct-job-row-body b {
    color: var(--pct-text-primary);
    font-size: 15px;
}

.pct-job-row-chips {
    display: flex;
    gap: 8px;
    margin: 8px 0 10px 0;
    flex-wrap: wrap;
}

.pct-job-row-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.pct-job-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    font-size: 12px;
    background: var(--pct-primary-alpha);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-sm);
    color: var(--pct-primary);
    text-decoration: none;
    font-weight: 600;
    transition: var(--pct-transition-fast);
}

.pct-job-link:hover {
    background: var(--pct-primary);
    color: white;
    border-color: var(--pct-primary);
}

.pct-job-del {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    font-size: 12px;
    background: var(--pct-danger-bg);
    border: 1px solid #fca5a5;
    border-radius: var(--pct-radius-sm);
    color: var(--pct-danger);
    text-decoration: none;
    font-weight: 600;
    cursor: pointer;
    transition: var(--pct-transition-fast);
}

.pct-job-del:hover {
    background: var(--pct-danger);
    color: white;
    border-color: var(--pct-danger);
}

.pct-folder-hint {
    background: var(--pct-success-bg);
    border: 1px solid #6ee7b7;
    border-radius: var(--pct-radius-md);
    padding: 8px 12px;
    font-size: 12px;
    color: var(--pct-success);
    margin: 8px 0;
}

.pct-folder-hint code {
    background: rgba(255, 255, 255, 0.5);
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
}

.pct-jobs-toolbar {
    display: flex;
    gap: 12px;
    align-items: center;
    background: var(--pct-primary-alpha);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    padding: 10px 16px;
    margin: 8px 0 12px 0;
}

.pct-job-id-box {
    background: var(--pct-primary-alpha);
    border: 1px solid var(--pct-border);
    border-radius: var(--pct-radius-md);
    padding: 10px 14px;
    margin: 8px 0;
}

.pct-job-id-label {
    font-size: 11px;
    color: var(--pct-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 700;
    display: block;
    margin-bottom: 4px;
}

.pct-job-id {
    font-family: "JetBrains Mono", "SF Mono", Consolas, monospace;
    font-size: 18px;
    font-weight: 700;
    color: var(--pct-primary);
    letter-spacing: 1px;
}

/* 进度条 */
.pct-progress-bar {
    height: 8px;
    background: var(--pct-border);
    border-radius: 4px;
    overflow: hidden;
    margin: 12px 0;
}

.pct-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--pct-primary) 0%, var(--pct-secondary) 100%);
    border-radius: 4px;
    transition: width 0.3s ease;
}

.pct-progress-text {
    font-size: 12px;
    color: var(--pct-text-secondary);
    text-align: center;
}

/* ============================================================
   响应式 v2
   ============================================================ */
@media (max-width: 1024px) {
    .workflow-grid { grid-template-columns: repeat(3, 1fr); }
    .pct-metric-grid { grid-template-columns: repeat(2, 1fr); }
    .pct-preview-meta { grid-template-columns: 1fr 1fr; }
    .gradio-container { padding: 16px 20px 40px 20px !important; }
}

@media (max-width: 768px) {
    .workflow-grid { grid-template-columns: repeat(2, 1fr); }
    .pct-metric-grid { grid-template-columns: 1fr 1fr; }
    .hero-title { font-size: 28px !important; }
    .gradio-container { padding: 12px 16px 32px 16px !important; }
}

@media (max-width: 480px) {
    .workflow-grid { grid-template-columns: 1fr; }
    .pct-metric-grid { grid-template-columns: 1fr; }
    .pct-preview-meta { grid-template-columns: 1fr; }
}

/* ============================================================
   可访问性 & 友好交互 (ui-ux-pro-max 原则)
   ============================================================ */

/* 键盘聚焦态 — 显著可见,所有可点击元素 */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
.pt-cell:focus-visible,
.pct-quick-btn:focus-visible,
.pct-job-link:focus-visible,
.pct-job-del:focus-visible {
    outline: 3px solid var(--pct-primary);
    outline-offset: 3px;
    box-shadow: 0 0 0 6px var(--pct-primary-alpha);
}

/* 鼠标指针 — 所有可交互元素 */
button,
.pct-chip,
.pt-cell,
.pct-quick-btn,
.pct-job-link,
.pct-job-del,
.predict-btn,
.batch-btn {
    cursor: pointer;
}

/* 选中态 */
.pct-cell.pt-selected,
.pt-cell.pt-selected:focus-visible {
    outline: 3px solid #db2777;
    outline-offset: 2px;
}

/* prefers-reduced-motion — 用户偏好减弱动效 */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
    .pct-step--active .pct-step-status::before {
        animation: none;
    }
}

/* 滚动条美化 (webkit) */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track {
    background: var(--pct-bg-panel);
    border-radius: 8px;
}
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--pct-border) 0%, var(--pct-text-muted) 100%);
    border-radius: 8px;
    border: 2px solid var(--pct-bg-panel);
}
::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, var(--pct-text-muted) 0%, var(--pct-text-secondary) 100%);
}

::selection {
    background: var(--pct-primary-alpha);
    color: var(--pct-primary-dark);
}

/* 文本选择优化 */
.pct-job-id-tag,
.pct-job-id,
.pct-current-list {
    user-select: text;
    -webkit-user-select: text;
}

/* 屏幕阅读器专用 */
.sr-only {
    position: absolute !important;
    width: 1px; height: 1px;
    padding: 0; margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* 高对比度模式适配 */
@media (prefers-contrast: more) {
    :root {
        --pct-text-primary: #000000;
        --pct-text-secondary: #1a1a1a;
        --pct-border: #999999;
    }
    .pct-step-title,
    .pct-step-body {
        font-weight: 700;
    }
}
"""

CUSTOM_CSS_FULL = CUSTOM_CSS
