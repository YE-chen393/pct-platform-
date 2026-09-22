"""Hero banner + Footer HTML v2 - Scientific Minimalism Design"""

HERO_HTML = """
<div class="hero-banner">
    <div class="hero-title">🧪 稀土储氢合金智能预测平台</div>
    <div class="hero-subtitle">
        基于机器学习的高通量稀土储氢合金热力学参数预测 · 支持单组份深度分析与批量高通量筛选<br>
        输入化学式 → 自动生成 Magpie 特征 → 三模型 (SVR + LightGBM + RandomForest) → van't Hoff / PCT / 结构生成
    </div>
    <div class="hero-tags">
        <span class="hero-tag">🔬 稀土 RE (La/Y/Ce/...)</span>
        <span class="hero-tag">📊 SVR (V5)</span>
        <span class="hero-tag">🌳 LightGBM (V6)</span>
        <span class="hero-tag">🌲 RandomForest (Capacity)</span>
        <span class="hero-tag">⚗️ Matminer · Pymatgen</span>
        <span class="hero-tag">🔗 PhononBench</span>
    </div>
    <div class="workflow-grid">
        <div class="workflow-card">
            <div class="workflow-num">1</div>
            <div class="workflow-icon">🔍</div>
            <div class="workflow-label">候选发现</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">2</div>
            <div class="workflow-icon">⚛️</div>
            <div class="workflow-label">理论验证</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">3</div>
            <div class="workflow-icon">📈</div>
            <div class="workflow-label">热力学预测</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">4</div>
            <div class="workflow-icon">🎯</div>
            <div class="workflow-label">实验决策</div>
        </div>
        <div class="workflow-card">
            <div class="workflow-num">5</div>
            <div class="workflow-icon">🔬</div>
            <div class="workflow-label">实验工具</div>
        </div>
    </div>
</div>
"""

FOOTER_HTML = """
<div class="app-footer">
    <b>稀土储氢合金智能预测平台</b> · La/Y/Ce-Mn-Ni 系稀土储氢合金 van't Hoff 参数机器学习预测<br>
    Models: SVR (V5) · LightGBM (V6) · RandomForest (Capacity) · Magpie features · PhononBench
</div>
"""
