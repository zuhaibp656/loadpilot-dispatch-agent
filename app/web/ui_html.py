"""Single-Page Application HTML/CSS/JS generator for FleetFlow Supply Chain Control Tower & 3D Load Studio.

Designed for both non-technical supply chain operators and enterprise architects:
  * Fluid, uncluttered workspace inspired by Accenture Control Tower, EasyCargo 3D, and Locus.
  * Direct integration with `engine.js` (`window.mountFleetFlowEngine`) for 60fps 2D road maps and 3D LIFO bays.
  * Interactive dropdowns, truck calculators, custom carton packers, dock QR scanner, driver portals,
    and live GCP BigQuery / Vertex AI / Model Armor telemetry.
"""

from __future__ import annotations

from pathlib import Path

from app.render.anim_html import _CSS as ANIM_CSS

_ENGINE_JS = (Path(__file__).resolve().parents[1] / "render" / "anim" / "engine.js").read_text(encoding="utf-8")

_UI_HTML = r"""<!DOCTYPE html>
<html lang="en" class="theme-dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FleetFlow Control Tower · Autonomous Supply Chain & 3D Load Studio</title>
  <meta name="description" content="Enterprise Supply Chain Control Tower, 3D LIFO Truck Load Studio, and Route Optimization powered by Google Cloud, BigQuery, Vertex AI, and Google Maps Platform.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..800;1,9..40,400..700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    /* ── Engine Base CSS ── */
    __ANIM_CSS__

    /* ── Control Tower Design System (Fluid, Vibrant, Uncluttered) ── */
    :root, html.theme-dark {
      --bg-canvas: #060a14;
      --bg-elevated: #0c1324;
      --bg-card: rgba(15, 23, 42, 0.82);
      --bg-card-hover: rgba(22, 34, 62, 0.92);
      --bg-input: rgba(9, 14, 28, 0.9);
      --bg-glass: rgba(12, 19, 36, 0.86);
      --border-subtle: rgba(148, 163, 184, 0.14);
      --border-focus: rgba(56, 189, 248, 0.55);
      --text-main: #f8fafc;
      --text-secondary: #cbd5e1;
      --text-muted: #94a3b8;
      --accent-cyan: #00e5ff;
      --accent-blue: #38bdf8;
      --accent-amber: #ffab00;
      --accent-emerald: #10b981;
      --accent-rose: #f43f5e;
      --shadow-soft: 0 12px 32px -8px rgba(0, 0, 0, 0.55);
      --shadow-glow: 0 0 24px rgba(56, 189, 248, 0.18);
      --font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    html.theme-light {
      --bg-canvas: #f4f6fb;
      --bg-elevated: #ffffff;
      --bg-card: rgba(255, 255, 255, 0.94);
      --bg-card-hover: #ffffff;
      --bg-input: #f8fafc;
      --bg-glass: rgba(255, 255, 255, 0.92);
      --border-subtle: rgba(15, 23, 42, 0.11);
      --border-focus: rgba(2, 132, 199, 0.6);
      --text-main: #0f172a;
      --text-secondary: #334155;
      --text-muted: #64748b;
      --accent-cyan: #0284c7;
      --accent-blue: #0369a1;
      --accent-amber: #d97706;
      --accent-emerald: #059669;
      --accent-rose: #e11d48;
      --shadow-soft: 0 10px 28px -6px rgba(15, 23, 42, 0.08);
      --shadow-glow: 0 0 20px rgba(2, 132, 199, 0.12);
    }

    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      padding: 0;
      height: 100%;
      width: 100%;
      background: var(--bg-canvas);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 14px;
      line-height: 1.45;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }

    /* App Shell Layout */
    .ct-shell {
      display: flex;
      flex-direction: column;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
      background:
        radial-gradient(circle at 12% 8%, rgba(0, 229, 255, 0.06), transparent 32%),
        radial-gradient(circle at 88% 12%, rgba(255, 171, 0, 0.05), transparent 32%),
        var(--bg-canvas);
    }

    /* ── Top Header Bar ── */
    .ct-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 10px 20px;
      background: var(--bg-glass);
      backdrop-filter: blur(18px);
      border-bottom: 1px solid var(--border-subtle);
      z-index: 30;
      flex-shrink: 0;
    }

    .ct-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }

    .ct-logo-mark {
      width: 38px;
      height: 38px;
      border-radius: 11px;
      background: linear-gradient(135deg, #00e5ff 0%, #2979ff 55%, #ffab00 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 4px 14px rgba(0, 229, 255, 0.3);
    }

    .ct-brand-title {
      font-size: 18px;
      font-weight: 800;
      letter-spacing: -0.4px;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .ct-brand-badge {
      font-family: var(--font-mono);
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(16, 185, 129, 0.16);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }

    .ct-brand-sub {
      font-size: 11.5px;
      color: var(--text-muted);
      font-weight: 500;
    }

    /* Main Workspace Navigation Pills */
    .ct-nav-tabs {
      display: flex;
      align-items: center;
      gap: 5px;
      background: var(--bg-input);
      padding: 4px;
      border-radius: 14px;
      border: 1px solid var(--border-subtle);
    }

    .ct-nav-btn {
      background: transparent;
      color: var(--text-muted);
      border: none;
      border-radius: 10px;
      padding: 8px 14px;
      font-family: var(--font-sans);
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
      white-space: nowrap;
    }

    .ct-nav-btn:hover {
      color: var(--text-main);
      background: rgba(56, 189, 248, 0.08);
    }

    .ct-nav-btn.active {
      background: linear-gradient(135deg, rgba(0, 229, 255, 0.2), rgba(41, 121, 255, 0.22));
      color: var(--accent-cyan);
      box-shadow: inset 0 0 0 1px rgba(0, 229, 255, 0.4), 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    /* Global Quick Selectors in Header */
    .ct-header-controls {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: nowrap;
    }

    .ct-select-group {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .ct-select-lbl {
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      padding-left: 4px;
    }

    .ct-select, .ct-input {
      background: var(--bg-input);
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 6px 11px;
      font-family: var(--font-sans);
      font-size: 12.5px;
      font-weight: 600;
      outline: none;
      cursor: pointer;
      transition: border-color 0.18s, box-shadow 0.18s;
    }

    .ct-select:hover, .ct-input:hover, .ct-select:focus, .ct-input:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
    }

    .ct-btn-primary {
      background: linear-gradient(135deg, #00e5ff 0%, #2563eb 100%);
      color: #fff;
      border: none;
      border-radius: 11px;
      padding: 9px 16px;
      font-family: var(--font-sans);
      font-size: 13px;
      font-weight: 800;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      box-shadow: 0 4px 16px rgba(0, 229, 255, 0.28);
      transition: transform 0.16s ease, box-shadow 0.18s ease, opacity 0.18s;
      white-space: nowrap;
    }

    .ct-btn-primary:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 22px rgba(0, 229, 255, 0.42);
    }

    .ct-btn-primary:active {
      transform: translateY(0);
    }

    .ct-btn-secondary {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 7px 12px;
      font-family: var(--font-sans);
      font-size: 12.5px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.18s;
      text-decoration: none;
    }

    .ct-btn-secondary:hover {
      border-color: var(--border-focus);
      background: var(--bg-card-hover);
    }

    /* ── Main Content Body ── */
    .ct-main {
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
      padding: 12px 20px 8px;
      gap: 10px;
      overflow: hidden;
    }

    /* KPI Ribbon */
    .ct-kpi-ribbon {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      flex-shrink: 0;
    }

    .ct-kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      box-shadow: var(--shadow-soft);
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .ct-kpi-card:hover {
      transform: translateY(-2px);
      border-color: var(--border-focus);
    }

    .ct-kpi-card::before {
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      background: var(--kpi-color, var(--accent-cyan));
    }

    .ct-kpi-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .ct-kpi-val {
      font-size: 21px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: var(--text-main);
      margin-top: 1px;
    }

    .ct-kpi-sub {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-secondary);
      margin-top: 2px;
    }

    .ct-kpi-badge {
      font-family: var(--font-mono);
      font-size: 11.5px;
      font-weight: 700;
      padding: 4px 9px;
      border-radius: 8px;
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
      white-space: nowrap;
    }

    /* Workspace Views */
    .ct-view {
      display: none;
      flex: 1;
      min-height: 0;
      gap: 14px;
      animation: viewFade 0.26s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .ct-view.active {
      display: flex;
    }

    @keyframes viewFade {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Glass Panels & Sidebars */
    .ct-stage {
      flex: 1;
      min-width: 0;
      min-height: 0;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: var(--shadow-soft);
    }

    .ct-sidebar {
      width: 370px;
      flex-shrink: 0;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 14px;
      gap: 14px;
      box-shadow: var(--shadow-soft);
    }

    .ct-panel-title {
      font-size: 13.5px;
      font-weight: 800;
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 6px;
    }

    .ct-panel-sub {
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 10px;
    }

    /* Quick Scope Bar (1, 3, All Trucks) */
    .ct-scope-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 8px 14px;
      background: var(--bg-elevated);
      border-bottom: 1px solid var(--border-subtle);
      flex-wrap: wrap;
    }

    .ct-scope-group {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .ct-scope-btn {
      background: var(--bg-input);
      color: var(--text-secondary);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.16s;
    }

    .ct-scope-btn:hover {
      border-color: var(--border-focus);
      color: var(--text-main);
    }

    .ct-scope-btn.active {
      background: var(--accent-cyan);
      color: #060a14;
      border-color: var(--accent-cyan);
      box-shadow: 0 0 12px rgba(0, 229, 255, 0.35);
    }

    .ct-engine-mount {
      flex: 1;
      min-height: 0;
      width: 100%;
      position: relative;
      display: flex;
      flex-direction: column;
    }

    /* Card blocks inside sidebars */
    .ct-box {
      background: var(--bg-elevated);
      border: 1px solid var(--border-subtle);
      border-radius: 13px;
      padding: 12px;
    }

    .ct-form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .ct-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .ct-field label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    /* Progress & Gauge Bars */
    .ct-gauge-track {
      height: 8px;
      background: rgba(148, 163, 184, 0.15);
      border-radius: 999px;
      overflow: hidden;
      margin-top: 4px;
    }

    .ct-gauge-fill {
      height: 100%;
      border-radius: 999px;
      transition: width 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Route & Fleet Cards */
    .ct-route-item {
      background: var(--bg-input);
      border: 1px solid var(--border-subtle);
      border-left: 4px solid var(--route-c, #38bdf8);
      border-radius: 11px;
      padding: 10px 12px;
      cursor: pointer;
      transition: all 0.18s;
      margin-bottom: 8px;
    }

    .ct-route-item:hover {
      border-color: var(--border-focus);
      transform: translateX(2px);
    }

    .ct-route-item.dimmed {
      opacity: 0.42;
    }

    .ct-route-item.selected {
      background: rgba(56, 189, 248, 0.12);
      border-color: var(--accent-cyan);
    }

    /* Tables */
    .ct-table-wrap {
      overflow: auto;
      flex: 1;
    }

    .ct-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .ct-table th {
      text-align: left;
      padding: 10px 12px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      background: var(--bg-elevated);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 5;
    }

    .ct-table td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text-secondary);
    }

    .ct-table tr:hover td {
      background: rgba(56, 189, 248, 0.05);
      color: var(--text-main);
    }

    /* ── Bottom AI Copilot Bar ── */
    .ct-copilot-dock {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 20px;
      background: var(--bg-glass);
      backdrop-filter: blur(18px);
      border-top: 1px solid var(--border-subtle);
      flex-shrink: 0;
      z-index: 25;
    }

    .ct-copilot-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 800;
      color: var(--accent-cyan);
      white-space: nowrap;
    }

    .ct-copilot-input {
      flex: 1;
      background: var(--bg-input);
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      padding: 8px 16px;
      font-family: var(--font-sans);
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
    }

    .ct-copilot-input:focus {
      border-color: var(--accent-cyan);
      box-shadow: 0 0 0 2px rgba(0, 229, 255, 0.18);
    }

    .ct-quick-chips {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      max-width: 48vw;
    }

    .ct-chip-btn {
      background: var(--bg-card);
      color: var(--text-secondary);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      padding: 5px 11px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }

    .ct-chip-btn:hover {
      border-color: var(--accent-cyan);
      color: var(--accent-cyan);
    }

    /* Toast / AI Reply Banner */
    .ct-toast {
      position: fixed;
      bottom: 62px;
      right: 24px;
      max-width: 520px;
      background: rgba(12, 19, 36, 0.96);
      backdrop-filter: blur(16px);
      border: 1px solid var(--accent-cyan);
      border-left: 4px solid var(--accent-cyan);
      border-radius: 14px;
      padding: 12px 16px;
      color: #f8fafc;
      font-size: 13px;
      box-shadow: 0 20px 45px rgba(0, 0, 0, 0.65);
      z-index: 100;
      display: none;
      animation: viewFade 0.22s ease;
    }

    /* Photo Gallery Grid */
    .ct-photo-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }

    .ct-photo-card {
      background: var(--bg-input);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.18s;
    }

    .ct-photo-card:hover, .ct-photo-card.active {
      border-color: var(--accent-cyan);
      box-shadow: 0 0 14px rgba(0, 229, 255, 0.25);
    }

    .ct-photo-card img {
      width: 100%;
      height: 115px;
      object-fit: cover;
      display: block;
    }

    .ct-photo-card div {
      padding: 6px 10px;
      font-size: 11.5px;
      font-weight: 700;
      color: var(--text-secondary);
    }

    @media (max-width: 1200px) {
      .ct-kpi-ribbon { grid-template-columns: repeat(3, 1fr); }
      .ct-sidebar { width: 320px; }
    }
  </style>
</head>
<body>
<div class="ct-shell">

  <!-- ═══════════════ TOP COMMAND HEADER ═══════════════ -->
  <header class="ct-header">
    <div class="ct-brand">
      <div class="ct-logo-mark">🚚</div>
      <div>
        <div class="ct-brand-title">
          FleetFlow
          <span class="ct-brand-badge">GCP Control Tower</span>
        </div>
        <div class="ct-brand-sub">Autonomous Route VRPTW &amp; 3D LIFO Load Studio</div>
      </div>
    </div>

    <!-- 5 Fluid Workspace Tabs -->
    <nav class="ct-nav-tabs" id="mainNavTabs">
      <button class="ct-nav-btn active" data-view="tower" onclick="switchWorkspace('tower')">
        <span>🗺️</span> Dispatch &amp; Map
      </button>
      <button class="ct-nav-btn" data-view="studio3d" onclick="switchWorkspace('studio3d')">
        <span>📦</span> 3D Load Studio
      </button>
      <button class="ct-nav-btn" data-view="simulator" onclick="switchWorkspace('simulator')">
        <span>🚛</span> Fleet &amp; Cost Simulator
      </button>
      <button class="ct-nav-btn" data-view="intake" onclick="switchWorkspace('intake')">
        <span>📸</span> Dock QR &amp; Intake
      </button>
      <button class="ct-nav-btn" data-view="gcp" onclick="switchWorkspace('gcp')">
        <span>☁️</span> Driver Hub &amp; GCP SQL
      </button>
    </nav>

    <!-- Global Controls -->
    <div class="ct-header-controls">
      <div class="ct-select-group">
        <span class="ct-select-lbl">Distribution Hub</span>
        <select id="selHub" class="ct-select" onchange="triggerPlanUpdate()">
          <option value="BHW-DC">Mumbai · Bhiwandi DC (BHW-DC)</option>
          <option value="TLJ-DC">Mumbai · Taloja DC (TLJ-DC)</option>
          <option value="BLR-NLG">Bengaluru · Nelamangala (BLR-NLG)</option>
          <option value="BLR-EC">Bengaluru · Electronic City (BLR-EC)</option>
        </select>
      </div>

      <div class="ct-select-group">
        <span class="ct-select-lbl">Optimization Goal</span>
        <select id="selObjective" class="ct-select" onchange="triggerPlanUpdate()">
          <option value="lowest_cost">Lowest Cost (₹)</option>
          <option value="fewest_trucks">Fewest Trucks</option>
          <option value="balanced">Balanced Fleet</option>
          <option value="fastest_finish">Fastest Completion</option>
        </select>
      </div>

      <div class="ct-select-group">
        <span class="ct-select-lbl">Data Source</span>
        <select id="selSource" class="ct-select" onchange="triggerPlanUpdate()">
          <option value="demo">Live Order Book</option>
          <option value="bigquery">BigQuery Warehouse</option>
          <option value="photos">Scanned Dock QR</option>
        </select>
      </div>

      <button class="ct-btn-primary" id="btnOptimize" onclick="triggerPlanUpdate()">
        <span>⚡</span> Optimize
      </button>

      <a href="/deck" target="_blank" class="ct-btn-secondary" title="Open Executive Presentation Deck">
        📊 Deck
      </a>

      <button class="ct-btn-secondary" onclick="toggleCtTheme()" title="Switch Dark / Light Mode">
        🌓
      </button>
    </div>
  </header>

  <!-- ═══════════════ MAIN WORKSPACE BODY ═══════════════ -->
  <main class="ct-main">

    <!-- ── Top KPI Ribbon ── -->
    <section class="ct-kpi-ribbon">
      <div class="ct-kpi-card" style="--kpi-color:#00e5ff">
        <div>
          <div class="ct-kpi-label">Fleet Right-Sized</div>
          <div class="ct-kpi-val" id="kpiTrucks">10 → 7 Trucks</div>
          <div class="ct-kpi-sub" id="kpiStopsSub">70 stops · 1,260 cartons</div>
        </div>
        <div class="ct-kpi-badge" id="kpiTrucksBadge">-3 trucks</div>
      </div>

      <div class="ct-kpi-card" style="--kpi-color:#10b981">
        <div>
          <div class="ct-kpi-label">Daily Net Savings</div>
          <div class="ct-kpi-val" id="kpiSavings">₹21,194 / day</div>
          <div class="ct-kpi-sub" id="kpiCostCompare">₹64,345 → ₹43,151</div>
        </div>
        <div class="ct-kpi-badge" id="kpiSavingsPct">-33.0%</div>
      </div>

      <div class="ct-kpi-card" style="--kpi-color:#ffab00">
        <div>
          <div class="ct-kpi-label">3D Bay Utilization</div>
          <div class="ct-kpi-val" id="kpiFill">78.4% Vol</div>
          <div class="ct-kpi-sub" id="kpiWeightSub">Payload fill: 81.2%</div>
        </div>
        <div class="ct-kpi-badge">100% LIFO</div>
      </div>

      <div class="ct-kpi-card" style="--kpi-color:#38bdf8">
        <div>
          <div class="ct-kpi-label">Axle Physics &amp; Safety</div>
          <div class="ct-kpi-val" id="kpiCmvr">CMVR Rule 93</div>
          <div class="ct-kpi-sub">Steer 34–42% · Drive 58–66%</div>
        </div>
        <div class="ct-kpi-badge">CERTIFIED</div>
      </div>

      <div class="ct-kpi-card" style="--kpi-color:#34d399">
        <div>
          <div class="ct-kpi-label">Green Logistics ESG</div>
          <div class="ct-kpi-val" id="kpiCo2">112 kg CO₂</div>
          <div class="ct-kpi-sub" id="kpiDieselSub">42.1 L diesel saved today</div>
        </div>
        <div class="ct-kpi-badge" id="kpiTreesBadge">1,540 trees/yr</div>
      </div>
    </section>

    <!-- ═══════════════ VIEW 1: CONTROL TOWER & ROUTE MAP ═══════════════ -->
    <section class="ct-view active" id="view-tower">
      <div class="ct-stage">
        <!-- Scope Filter Bar (All / 1 Truck / 3 Trucks / Specific Truck Dropdown) -->
        <div class="ct-scope-bar">
          <div class="ct-scope-group">
            <span style="font-size:11.5px;font-weight:800;color:var(--text-muted);text-transform:uppercase;margin-right:4px">🎯 Fleet Focus:</span>
            <button class="ct-scope-btn active" id="scopeAllBtn" onclick="applyTruckScope('all')">All Fleet</button>
            <button class="ct-scope-btn" id="scope1Btn" onclick="applyTruckScope('1')">1 Truck Only</button>
            <button class="ct-scope-btn" id="scope3Btn" onclick="applyTruckScope('3')">Top 3 Trucks</button>
            <select id="selFocusTruckMap" class="ct-select" style="padding:4px 10px;font-size:12px" onchange="applySingleTruckDropdown(this.value)">
              <option value="all">Select specific truck / driver...</option>
            </select>
          </div>
          <div class="ct-scope-group">
            <button class="ct-btn-secondary" style="padding:4px 10px;font-size:11.5px" onclick="switchWorkspace('studio3d')">
              📦 Open Focused Truck in 3D Studio →
            </button>
          </div>
        </div>

        <!-- Interactive Road Map Canvas Mount -->
        <div id="ct-map-mount" class="ct-engine-mount">
          <div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:13px;gap:10px">
            <span>⚡ Initializing OR-Tools VRPTW &amp; 3D LIFO Packing Engine...</span>
          </div>
        </div>
      </div>

      <!-- Right Sidebar: Corridor Assignment & Active Fleet List -->
      <aside class="ct-sidebar">
        <div class="ct-box">
          <div class="ct-panel-title">
            <span>🧭 Driver Corridor Pinning</span>
            <span style="font-size:11px;color:var(--accent-cyan);font-family:var(--font-mono)">Trunk &amp; Branch</span>
          </div>
          <div class="ct-panel-sub">Assign a driver to a preferred highway sector; remaining volume splits around them automatically.</div>
          <div class="ct-form-grid">
            <div class="ct-field">
              <label>Driver</label>
              <select id="selClaimDriver" class="ct-select"></select>
            </div>
            <div class="ct-field">
              <label>Compass Sector</label>
              <select id="selClaimCorridor" class="ct-select"></select>
            </div>
          </div>
          <div style="display:flex;gap:8px;margin-top:10px">
            <button class="ct-btn-primary" style="flex:1;justify-content:center;padding:8px" onclick="submitCorridorClaim()">
              📌 Pin &amp; Re-Optimize
            </button>
            <button class="ct-btn-secondary" onclick="clearCorridorClaims()" title="Clear all corridor claims">
              Reset
            </button>
          </div>
          <div id="activeClaimsPills" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px"></div>
        </div>

        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:12px;font-weight:800;text-transform:uppercase;color:var(--text-muted)">🚚 Dispatched Fleet Routes</span>
          <span id="routeCountLbl" style="font-size:11.5px;color:var(--accent-cyan);font-weight:700"></span>
        </div>
        <div id="towerRoutesList" style="flex:1;overflow-y:auto"></div>
      </aside>
    </section>

    <!-- ═══════════════ VIEW 2: 3D LOAD STUDIO & CALCULATOR ═══════════════ -->
    <section class="ct-view" id="view-studio3d">
      <div class="ct-stage">
        <div class="ct-scope-bar">
          <div class="ct-scope-group">
            <span style="font-size:12px;font-weight:800;color:var(--accent-cyan)">📦 3D LIFO Cargo Studio</span>
            <span style="font-size:12px;color:var(--text-muted)">Last delivery loaded first at cab wall (X=0) · Stop 1 right at rear roll-up door</span>
          </div>
          <div class="ct-scope-group">
            <span id="studioBannerBadge" class="ct-kpi-badge">LIFO &amp; CMVR Verified</span>
          </div>
        </div>
        <div id="ct-load-mount" class="ct-engine-mount"></div>
      </div>

      <!-- Right Sidebar: Interactive Truck & Carton Calculator -->
      <aside class="ct-sidebar">
        <div class="ct-box">
          <div class="ct-panel-title">
            <span>🧮 Truck Type Calculator</span>
            <span style="font-size:11px;color:var(--accent-amber);font-family:var(--font-mono)">What-If Simulator</span>
          </div>
          <div class="ct-panel-sub">Select any dispatched route and test packing its cartons into different vehicle sizes in real time.</div>
          <div class="ct-field" style="margin-bottom:8px">
            <label>1. Select Route / Driver Consignment</label>
            <select id="selStudioRoute" class="ct-select" onchange="onStudioRouteSelect(this.value)"></select>
          </div>
          <div class="ct-field" style="margin-bottom:10px">
            <label>2. Test Vehicle Class (Body Dimensions &amp; Payload)</label>
            <select id="selStudioTruckType" class="ct-select" onchange="runStudioRepack()"></select>
          </div>
          <button class="ct-btn-primary" style="width:100%;justify-content:center" onclick="runStudioRepack()">
            🔄 Recalculate 3D Load &amp; Axle Physics
          </button>
        </div>

        <!-- Live Physics & Utilization Readout -->
        <div class="ct-box" id="studioStatsCard">
          <div class="ct-panel-title">
            <span>⚖️ Load &amp; Axle Telemetry</span>
            <span id="stLifoStatus" class="ct-kpi-badge" style="font-size:10.5px">LIFO OK</span>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px">
            <div>
              <div style="font-size:11px;color:var(--text-muted)">Volume Fill</div>
              <div style="font-size:17px;font-weight:800" id="stVolFill">78.5%</div>
              <div class="ct-gauge-track"><div id="stVolBar" class="ct-gauge-fill" style="width:78%;background:var(--accent-cyan)"></div></div>
            </div>
            <div>
              <div style="font-size:11px;color:var(--text-muted)">Payload Fill</div>
              <div style="font-size:17px;font-weight:800" id="stWtFill">82.1%</div>
              <div class="ct-gauge-track"><div id="stWtBar" class="ct-gauge-fill" style="width:82%;background:var(--accent-amber)"></div></div>
            </div>
          </div>
          <div style="margin-top:10px">
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted)">
              <span>Steer Axle: <b id="stFrontAxle" style="color:var(--text-main)">38%</b></span>
              <span>Drive Axle: <b id="stRearAxle" style="color:var(--text-main)">62%</b></span>
            </div>
            <div class="ct-gauge-track" style="height:10px;background:#1e293b">
              <div id="stAxleBar" class="ct-gauge-fill" style="width:38%;background:linear-gradient(90deg,#10b981,#00e5ff)"></div>
            </div>
            <div id="stCmvrNote" style="font-size:11px;color:#34d399;margin-top:4px;font-weight:600">✓ CMVR Rule 93 Balanced</div>
          </div>
          <div id="stOverflowWarn" style="display:none;margin-top:8px;padding:8px;border-radius:8px;background:rgba(244,63,94,0.15);border:1px solid rgba(244,63,94,0.4);color:#fda4af;font-size:11.5px;font-weight:700"></div>
        </div>

        <!-- Add Custom Cartons to 3D Truck -->
        <div class="ct-box">
          <div class="ct-panel-title">
            <span>➕ Add Custom Cartons</span>
            <button class="ct-btn-secondary" style="padding:2px 8px;font-size:10.5px" onclick="clearCustomBoxes()">Clear Added</button>
          </div>
          <div class="ct-field" style="margin-bottom:8px">
            <label>SKU Preset (or Custom Size below)</label>
            <select id="selCustomSku" class="ct-select" onchange="onCustomSkuChange(this.value)"></select>
          </div>
          <div class="ct-form-grid" style="margin-bottom:8px">
            <div class="ct-field">
              <label>Quantity</label>
              <input type="number" id="inpCustomQty" class="ct-input" value="4" min="1" max="40">
            </div>
            <div class="ct-field">
              <label>Delivery Stop #</label>
              <input type="number" id="inpCustomStop" class="ct-input" value="1" min="1" max="20">
            </div>
          </div>
          <div class="ct-form-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:10px">
            <div class="ct-field"><label>L (cm)</label><input type="number" id="inpCustomL" class="ct-input" value="34"></div>
            <div class="ct-field"><label>W (cm)</label><input type="number" id="inpCustomW" class="ct-input" value="34"></div>
            <div class="ct-field"><label>H (cm)</label><input type="number" id="inpCustomH" class="ct-input" value="38"></div>
            <div class="ct-field"><label>Kg</label><input type="number" id="inpCustomKg" class="ct-input" value="24"></div>
          </div>
          <button class="ct-btn-secondary" style="width:100%;justify-content:center;border-color:var(--accent-cyan);color:var(--accent-cyan)" onclick="addCustomBoxAndPack()">
            + Pack into 3D Cargo Bay
          </button>
          <div id="addedCustomBoxesList" style="margin-top:8px;font-size:11.5px;color:var(--text-muted)"></div>
        </div>
      </aside>
    </section>

    <!-- ═══════════════ VIEW 3: FLEET & COST SIMULATOR ═══════════════ -->
    <section class="ct-view" id="view-simulator">
      <aside class="ct-sidebar" style="width:400px">
        <div class="ct-box">
          <div class="ct-panel-title">
            <span>🚛 Available Fleet Mix at Hub</span>
            <span style="font-size:11px;color:var(--accent-cyan)">OR-Tools VRPTW</span>
          </div>
          <div class="ct-panel-sub">Adjust how many vehicles of each class are available on the dock today and re-solve the MIP.</div>
          <div id="fleetControlsContainer" style="display:flex;flex-direction:column;gap:8px"></div>
        </div>

        <div class="ct-box">
          <div class="ct-panel-title"><span>⛽ Operating Cost Parameters</span></div>
          <div class="ct-form-grid">
            <div class="ct-field">
              <label>Diesel Price (₹ / Litre)</label>
              <input type="number" id="inpSimFuel" class="ct-input" value="92" step="1">
            </div>
            <div class="ct-field">
              <label>Driver Bata (₹ / Day)</label>
              <input type="number" id="inpSimDriverCost" class="ct-input" value="1100" step="50">
            </div>
          </div>
          <button class="ct-btn-primary" style="width:100%;justify-content:center;margin-top:12px" onclick="runSimulatorOptimization()">
            ⚡ Re-Solve Fleet &amp; Cost Matrix
          </button>
        </div>
      </aside>

      <div class="ct-stage" style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <div>
            <div style="font-size:16px;font-weight:800">Dispatch Schedule, Fill Rates &amp; Route Cost Ledger</div>
            <div style="font-size:12px;color:var(--text-muted)">Atomic copy-ready table for Google Sheets / ERP export</div>
          </div>
          <div style="display:flex;gap:8px">
            <button class="ct-btn-secondary" onclick="copyScheduleTable()">📋 Copy for Google Sheets</button>
            <button class="ct-btn-secondary" onclick="exportScheduleCsv()">⬇ Export CSV</button>
          </div>
        </div>
        <div class="ct-table-wrap">
          <table class="ct-table" id="simScheduleTable">
            <thead>
              <tr>
                <th>Truck ID</th>
                <th>Vehicle Class</th>
                <th>Driver</th>
                <th>Corridor / Branch</th>
                <th>Stops</th>
                <th>Cartons</th>
                <th>Vol Fill</th>
                <th>Wt Fill</th>
                <th>Distance</th>
                <th>Shift</th>
                <th>Route Cost</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="simScheduleBody"></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- ═══════════════ VIEW 4: DOCK QR SCANNER & SMART ORDER INTAKE ═══════════════ -->
    <section class="ct-view" id="view-intake">
      <!-- Left: Dock Camera QR & Thermal Label Vision Scanner -->
      <div class="ct-stage" style="padding:16px;overflow-y:auto">
        <div class="ct-panel-title" style="font-size:16px">
          <span>📸 Warehouse Dock QR &amp; Vision Carton Scanner</span>
          <span class="ct-kpi-badge">OpenCV + Gemini Vision</span>
        </div>
        <div class="ct-panel-sub">Click any staging floor photo below (or upload your own smartphone carton photo) to decode QR labels, match SKU dimensions, and add cartons into today's 3D load plan.</div>

        <div style="margin-bottom:12px;display:flex;gap:10px;align-items:center">
          <label class="ct-btn-secondary" style="cursor:pointer">
            📤 Upload Custom Carton Photo
            <input type="file" accept="image/*" style="display:none" onchange="uploadCustomPhoto(this)">
          </label>
          <span id="scanStatusText" style="font-size:12.5px;color:var(--accent-cyan);font-weight:700"></span>
        </div>

        <div class="ct-photo-grid" id="samplePhotosGrid"></div>

        <div class="ct-box" style="margin-top:14px" id="scanResultBox">
          <div class="ct-panel-title"><span>🔍 Decoded Carton Manifest</span></div>
          <div id="scanResultContent" style="font-family:var(--font-mono);font-size:12px;color:var(--text-secondary)">
            Select a staging floor photo above to run live QR &amp; label recognition.
          </div>
        </div>
      </div>

      <!-- Right: Unstructured Order List / Email / CSV Intake -->
      <div class="ct-stage" style="padding:16px;overflow-y:auto">
        <div class="ct-panel-title" style="font-size:16px">
          <span>📝 Unstructured ERP, Email &amp; WhatsApp Order Intake</span>
          <span class="ct-kpi-badge">Auto-Geocode + SKU Match</span>
        </div>
        <div class="ct-panel-sub">Load a preset dealer order manifest or paste raw text/CSV from an email or WhatsApp message to build a fresh route &amp; 3D load plan.</div>

        <div id="sampleOrdersBtns" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px"></div>

        <textarea id="inpOrderText" class="ct-input" style="width:100%;height:230px;font-family:var(--font-mono);font-size:12px;line-height:1.5;resize:vertical" placeholder="Paste dealer orders here (e.g. Store name, locality, SKU codes and carton quantities)..."></textarea>

        <div style="display:flex;gap:10px;margin-top:10px">
          <button class="ct-btn-primary" onclick="submitOrderText()">
            ⚡ Parse Orders &amp; Build Dispatch Plan
          </button>
          <button class="ct-btn-secondary" onclick="resetToDefaultDemo()">
            🔄 Reset to Full 70-Stop Demo Book
          </button>
        </div>

        <div class="ct-box" style="margin-top:14px">
          <div class="ct-panel-title"><span>📋 Intake &amp; Geocoding Summary</span></div>
          <div id="ingestResultContent" style="font-size:12.5px;color:var(--text-secondary)">
            Ready to ingest unstructured dealer orders.
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════════ VIEW 5: DRIVER DISPATCH HUB & GCP BIGQUERY STUDIO ═══════════════ -->
    <section class="ct-view" id="view-gcp">
      <!-- Left: Driver Mobile Portal & Google Maps Live Navigation Hub -->
      <div class="ct-stage" style="padding:16px;overflow-y:auto;flex:0.95">
        <div class="ct-panel-title" style="font-size:16px">
          <span>📱 Driver Mobile Portal, Google Maps &amp; WhatsApp Hub</span>
          <span class="ct-kpi-badge">Zero-Login Edge</span>
        </div>
        <div class="ct-panel-sub">Select any driver to launch 1-tap Google Maps turn-by-turn navigation with live traffic, send a 1-click WhatsApp dispatch, or preview their standalone mobile run sheet &amp; printable LR Challan.</div>

        <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
          <select id="selPortalTruck" class="ct-select" style="flex:1" onchange="updateDriverHubPreview(this.value)"></select>
          <a id="btnOpenMapsNav" href="#" target="_blank" class="ct-btn-primary" style="text-decoration:none;background:linear-gradient(135deg,#22c55e,#16a34a)">
            🗺️ 1-Tap Google Maps Nav
          </a>
          <a id="btnOpenWhatsApp" href="#" target="_blank" class="ct-btn-secondary" style="color:#4ade80;border-color:rgba(74,222,128,0.4)">
            💬 WhatsApp Driver
          </a>
          <a id="btnOpenPortalTab" href="#" target="_blank" class="ct-btn-secondary">
            ↗ Full Screen / Print LR
          </a>
        </div>

        <div style="flex:1;min-height:380px;border:1px solid var(--border-subtle);border-radius:14px;overflow:hidden;background:#0a0f1d">
          <iframe id="driverPortalIframe" style="width:100%;height:100%;border:none" title="Driver Mobile Portal Preview"></iframe>
        </div>
      </div>

      <!-- Right: GCP Cloud Architecture & Live BigQuery SQL Studio -->
      <div class="ct-stage" style="padding:16px;overflow-y:auto;flex:1.05">
        <div class="ct-panel-title" style="font-size:16px">
          <span>☁️ Google Cloud Infrastructure &amp; BigQuery Analytics Studio</span>
          <span class="ct-kpi-badge">Cloud Run · BigQuery · Model Armor</span>
        </div>
        <div id="gcpServiceGrid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px"></div>

        <!-- Live BigQuery SQL Runner -->
        <div class="ct-box" style="display:flex;flex-direction:column;gap:8px;flex:1">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
            <span style="font-size:13px;font-weight:800;color:var(--accent-cyan)">📊 BigQuery SQL Studio (zuhaibp-ai.loadpilot_demo)</span>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <button class="ct-chip-btn" onclick="loadBqPreset(0)">Corridor Cost &amp; Fill</button>
              <button class="ct-chip-btn" onclick="loadBqPreset(1)">SKU Volume Breakdown</button>
              <button class="ct-chip-btn" onclick="loadBqPreset(2)">Fragile Cargo Audit</button>
            </div>
          </div>
          <textarea id="inpBqSql" class="ct-input" style="width:100%;height:86px;font-family:var(--font-mono);font-size:11.5px"></textarea>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span id="bqEngineStatus" style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">Ready</span>
            <button class="ct-btn-primary" style="padding:6px 14px;font-size:12px" onclick="executeBqQuery()">▶ Run BigQuery SQL</button>
          </div>
          <div class="ct-table-wrap" style="max-height:195px;border:1px solid var(--border-subtle);border-radius:10px">
            <table class="ct-table" id="bqResultTable">
              <thead id="bqResultHead"></thead>
              <tbody id="bqResultBody"></tbody>
            </table>
          </div>
        </div>

        <!-- Model Armor & DLP Live Security Audit Stream -->
        <div class="ct-box" style="margin-top:10px">
          <div class="ct-panel-title" style="margin-bottom:4px">
            <span>🛡️ Model Armor, Cloud DLP &amp; Enclave Telemetry</span>
            <span style="font-family:var(--font-mono);font-size:10.5px;color:#34d399">ZERO-TRUST ACTIVE</span>
          </div>
          <div id="securityAuditList" style="font-family:var(--font-mono);font-size:11px;color:var(--text-secondary);max-height:90px;overflow-y:auto"></div>
        </div>
      </div>
    </section>

  </main>

  <!-- ═══════════════ BOTTOM AI COPILOT COMMAND BAR ═══════════════ -->
  <footer class="ct-copilot-dock">
    <div class="ct-copilot-pill">
      <span>✨</span> FleetFlow AI Agent
    </div>
    <input
      type="text"
      id="inpAgentPrompt"
      class="ct-copilot-input"
      placeholder="Ask the same backend agent: 'Show only Ravi's truck', 'Highlight 3 trucks', 'Pin Suresh to South corridor', 'Switch to Bengaluru'..."
      onkeydown="if(event.key==='Enter') sendAgentPrompt()"
    >
    <button class="ct-btn-primary" style="padding:7px 14px;border-radius:999px" onclick="sendAgentPrompt()">
      Send ↵
    </button>
    <div class="ct-quick-chips">
      <button class="ct-chip-btn" onclick="quickPrompt('Only show Ravi')">Only Ravi (1 Truck)</button>
      <button class="ct-chip-btn" onclick="quickPrompt('Show 3 trucks')">Top 3 Trucks</button>
      <button class="ct-chip-btn" onclick="quickPrompt('Show all trucks')">All Fleet</button>
      <button class="ct-chip-btn" onclick="quickPrompt('Pin Suresh to South corridor')">Pin Suresh → South</button>
      <button class="ct-chip-btn" onclick="quickPrompt('Switch to Bengaluru Nelamangala hub')">Bengaluru Hub</button>
    </div>
  </footer>

  <!-- Toast Notification for AI Copilot & Re-Optimization -->
  <div id="ctToast" class="ct-toast"></div>

</div>

<!-- Engine JS (Exposes window.mountFleetFlowEngine) -->
<script>
__ENGINE_JS__
</script>

<!-- Control Tower SPA Application Logic -->
<script>
let META = null;
let CURRENT_BUNDLE = null;
let ACTIVE_VIEW = 'tower';
let CUSTOM_BOXES = [];
let CORRIDOR_CLAIMS = {};
let FLEET_COUNTS = {};

const BQ_PRESETS = [
  `SELECT corridor, COUNT(*) AS trucks, SUM(stops) AS total_stops, SUM(cartons) AS total_cartons, ROUND(AVG(volume_fill_pct), 1) AS avg_vol_fill_pct, SUM(cost_inr) AS total_cost_inr\nFROM \`zuhaibp-ai.loadpilot_demo.routes\`\nGROUP BY corridor\nORDER BY total_cost_inr DESC`,
  `SELECT sku, description, category, COUNT(*) AS carton_count, ROUND(SUM(weight_kg), 1) AS total_weight_kg\nFROM \`zuhaibp-ai.loadpilot_demo.cartons\`\nGROUP BY sku, description, category\nORDER BY carton_count DESC\nLIMIT 10`,
  `SELECT s.sales_area, COUNT(DISTINCT s.stop_id) AS outlets, SUM(c.fragile) AS fragile_cartons, ROUND(SUM(c.weight_kg), 1) AS total_kg\nFROM \`zuhaibp-ai.loadpilot_demo.stores\` s\nJOIN \`zuhaibp-ai.loadpilot_demo.cartons\` c USING (stop_id)\nGROUP BY s.sales_area\nORDER BY fragile_cartons DESC`
];

function showToast(htmlMsg, durationMs = 4800) {
  const el = document.getElementById('ctToast');
  el.innerHTML = htmlMsg;
  el.style.display = 'block';
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.style.display = 'none'; }, durationMs);
}

function toggleCtTheme() {
  const h = document.documentElement;
  const isDark = h.classList.contains('theme-dark');
  h.classList.toggle('theme-dark', !isDark);
  h.classList.toggle('theme-light', isDark);
}

function switchWorkspace(viewId) {
  ACTIVE_VIEW = viewId;
  document.querySelectorAll('.ct-view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById('view-' + viewId);
  if (target) target.classList.add('active');
  document.querySelectorAll('#mainNavTabs .ct-nav-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === viewId);
  });
  if (CURRENT_BUNDLE) {
    requestAnimationFrame(() => renderActiveCanvases());
  }
}

function renderActiveCanvases() {
  if (!CURRENT_BUNDLE || !CURRENT_BUNDLE.anim_data) return;
  if (ACTIVE_VIEW === 'tower') {
    window.mountFleetFlowEngine('ct-map-mount', CURRENT_BUNDLE.anim_data, 'routes');
  } else if (ACTIVE_VIEW === 'studio3d') {
    window.mountFleetFlowEngine('ct-load-mount', CURRENT_BUNDLE.anim_data, 'load');
  }
}

window.LPgoLoad = function(truckId, stopSeq) {
  switchWorkspace('studio3d');
  const sel = document.getElementById('selStudioRoute');
  if (sel && truckId) {
    sel.value = truckId;
    onStudioRouteSelect(truckId);
  }
};

async function initControlTower() {
  try {
    const res = await fetch('/api/meta');
    META = await res.json();
    FLEET_COUNTS = {};
    META.truck_types.forEach(t => { FLEET_COUNTS[t.code] = t.default_count; });

    populateStaticDropdowns();
    if (META.initial_plan) {
      applyBundle(META.initial_plan);
    }
    loadBqPreset(0);
    executeBqQuery();
  } catch (err) {
    console.error('Failed to initialize Control Tower:', err);
  }
}

function populateStaticDropdowns() {
  // Corridor claims dropdowns
  const drvSel = document.getElementById('selClaimDriver');
  drvSel.innerHTML = META.drivers.map(d => `<option value="${d}">${d}</option>`).join('');

  const corSel = document.getElementById('selClaimCorridor');
  corSel.innerHTML = META.corridors.map(c => `<option value="${c.code}">${c.code} · ${c.name}</option>`).join('');

  // Studio 3D truck type dropdown
  const ttSel = document.getElementById('selStudioTruckType');
  ttSel.innerHTML = META.truck_types.map(t =>
    `<option value="${t.code}">${t.code} · ${t.name} (${t.inner_l_cm}×${t.inner_w_cm}×${t.inner_h_cm}cm · ${t.payload_kg}kg)</option>`
  ).join('');

  // Custom SKU dropdown
  const skuSel = document.getElementById('selCustomSku');
  skuSel.innerHTML = META.skus.map(s =>
    `<option value="${s.sku}">${s.sku} · ${s.description} (${s.l_cm}×${s.w_cm}×${s.h_cm}cm · ${s.weight_kg}kg)</option>`
  ).join('');

  // Fleet Simulator steppers
  renderFleetSteppers();

  // Sample dock photos
  const pg = document.getElementById('samplePhotosGrid');
  pg.innerHTML = META.sample_photos.map(p => `
    <div class="ct-photo-card" onclick="scanSamplePhoto('${p.filename}', this)">
      <img src="${p.url}" alt="${p.label}" loading="lazy">
      <div>📷 ${p.label}</div>
    </div>
  `).join('');

  // Sample order buttons
  const ob = document.getElementById('sampleOrdersBtns');
  ob.innerHTML = META.sample_orders.map((o, idx) => `
    <button class="ct-chip-btn" onclick="loadSampleOrder(${idx})">📄 ${o.label}</button>
  `).join('');

  // GCP Service Cards
  const gg = document.getElementById('gcpServiceGrid');
  gg.innerHTML = META.gcp_services.map(s => `
    <div class="ct-box" style="padding:10px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:800;font-size:12.5px">${s.icon} ${s.name}</span>
        <span class="ct-kpi-badge" style="font-size:9.5px;padding:2px 6px">${s.status}</span>
      </div>
      <div style="font-size:11px;color:var(--accent-cyan);font-weight:600;margin-top:2px">${s.role}</div>
      <div style="font-size:11px;color:var(--text-muted);margin-top:3px">${s.detail}</div>
    </div>
  `).join('');
}

function renderFleetSteppers() {
  const c = document.getElementById('fleetControlsContainer');
  c.innerHTML = META.truck_types.map(t => {
    const cnt = FLEET_COUNTS[t.code] ?? t.default_count;
    return `
      <div style="display:flex;align-items:center;justify-content:space-between;background:var(--bg-input);padding:8px 12px;border-radius:10px;border:1px solid var(--border-subtle);border-left:4px solid ${t.color}">
        <div>
          <div style="font-weight:800;font-size:13px">${t.code} · ${t.name}</div>
          <div style="font-size:11px;color:var(--text-muted)">${t.volume_m3} m³ · ${t.payload_kg} kg · ₹${t.fixed_daily_cost_inr}/day + ₹${t.cost_per_km_inr}/km</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <button class="ct-btn-secondary" style="padding:3px 9px" onclick="adjFleetCount('${t.code}', -1)">−</button>
          <span id="fc-${t.code}" style="font-family:var(--font-mono);font-size:14px;font-weight:800;min-width:20px;text-align:center">${cnt}</span>
          <button class="ct-btn-secondary" style="padding:3px 9px" onclick="adjFleetCount('${t.code}', 1)">+</button>
        </div>
      </div>
    `;
  }).join('');
}

function adjFleetCount(code, delta) {
  FLEET_COUNTS[code] = Math.max(0, Math.min(12, (FLEET_COUNTS[code] || 0) + delta));
  const el = document.getElementById('fc-' + code);
  if (el) el.textContent = FLEET_COUNTS[code];
}

function applyBundle(b) {
  CURRENT_BUNDLE = b;
  const k = b.kpi;

  // Sync top selectors
  if (b.hub && b.hub.hub_id) document.getElementById('selHub').value = b.hub.hub_id;
  if (b.objective) document.getElementById('selObjective').value = b.objective;
  if (b.order_source && ['demo', 'bigquery', 'photos'].includes(b.order_source)) {
    document.getElementById('selSource').value = b.order_source;
  }

  // Update KPI Ribbon
  document.getElementById('kpiTrucks').textContent = `${k.baseline_trucks} → ${k.optimized_trucks} Trucks`;
  document.getElementById('kpiStopsSub').textContent = `${k.stops} stops · ${k.cartons.toLocaleString('en-IN')} cartons (${k.weight_tonnes} t)`;
  document.getElementById('kpiTrucksBadge').textContent = k.trucks_saved > 0 ? `-${k.trucks_saved} trucks` : `${k.optimized_trucks} active`;

  document.getElementById('kpiSavings').textContent = `₹${k.savings_inr.toLocaleString('en-IN')} / day`;
  document.getElementById('kpiCostCompare').textContent = `₹${k.baseline_cost_inr.toLocaleString('en-IN')} → ₹${k.optimized_cost_inr.toLocaleString('en-IN')}`;
  document.getElementById('kpiSavingsPct').textContent = `-${k.savings_pct}%`;

  document.getElementById('kpiFill').textContent = `${k.avg_vol_fill_pct}% Vol`;
  document.getElementById('kpiWeightSub').textContent = `Payload fill: ${k.avg_wt_fill_pct}%`;

  document.getElementById('kpiCo2').textContent = `${k.co2_saved_kg} kg CO₂`;
  document.getElementById('kpiDieselSub').textContent = `${k.diesel_saved_litres} L diesel saved (${k.km_saved} km less)`;
  document.getElementById('kpiTreesBadge').textContent = `${k.trees_offset} trees/yr`;

  // Populate Truck Focus Dropdown on Map
  const mapSel = document.getElementById('selFocusTruckMap');
  mapSel.innerHTML = `<option value="all">All Fleet (${b.routes.length} trucks)</option>` +
    b.routes.map(r => `<option value="${r.truck_id}" ${b.active_trucks && b.active_trucks.length===1 && b.active_trucks[0]===r.truck_id ? 'selected' : ''}>${r.truck_id} · ${r.driver} (${r.corridor} · ${r.stops_count} stops)</option>`).join('');

  // Update Scope Buttons highlight
  const actLen = b.active_trucks ? b.active_trucks.length : 0;
  document.getElementById('scopeAllBtn').classList.toggle('active', !b.active_trucks);
  document.getElementById('scope1Btn').classList.toggle('active', actLen === 1);
  document.getElementById('scope3Btn').classList.toggle('active', actLen === 3);

  // Render active corridor claims pills
  CORRIDOR_CLAIMS = b.corridor_claims || {};
  const cp = document.getElementById('activeClaimsPills');
  cp.innerHTML = Object.entries(CORRIDOR_CLAIMS).map(([drv, cor]) =>
    `<span class="ct-kpi-badge" style="font-size:10.5px">📌 ${drv} → ${cor}</span>`
  ).join('');

  // Render Right Sidebar Route List
  document.getElementById('routeCountLbl').textContent = b.active_trucks
    ? `${b.active_trucks.length} highlighted / ${b.routes.length} total`
    : `${b.routes.length} active`;

  const rl = document.getElementById('towerRoutesList');
  rl.innerHTML = b.routes.map(r => `
    <div class="ct-route-item ${r.active ? '' : 'dimmed'}" style="--route-c:${r.color}" onclick="applySingleTruckDropdown('${r.truck_id}')">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:800;font-size:13.5px;color:var(--text-main)">${r.truck_id} · ${r.driver}</span>
        <span style="font-family:var(--font-mono);font-size:11px;color:${r.color};font-weight:700">${r.corridor} (${r.branch})</span>
      </div>
      <div style="font-size:11.5px;color:var(--text-muted);margin-top:2px">${r.truck_name}</div>
      <div style="display:flex;gap:10px;margin-top:6px;font-size:11.5px;color:var(--text-secondary);flex-wrap:wrap">
        <span>📍 <b>${r.stops_count}</b> stops</span>
        <span>📦 <b>${r.cartons_count}</b> boxes</span>
        <span>📊 <b>${r.volume_fill_pct}%</b> vol</span>
        <span>🛣️ <b>${r.km}</b> km</span>
        <span>₹<b>${r.cost_total.toLocaleString('en-IN')}</b></span>
      </div>
    </div>
  `).join('');

  // Populate Studio 3D Route Selector
  const stRouteSel = document.getElementById('selStudioRoute');
  stRouteSel.innerHTML = b.routes.map(r =>
    `<option value="${r.truck_id}" ${r.truck_id === b.focus_truck_id ? 'selected' : ''}>${r.truck_id} · ${r.driver} (${r.truck_code} · ${r.cartons_count} cartons)</option>`
  ).join('');
  const focusRoute = b.routes.find(r => r.truck_id === b.focus_truck_id) || b.routes[0];
  if (focusRoute) {
    document.getElementById('selStudioTruckType').value = focusRoute.truck_code;
    updateStudioTelemetryFromRoute(focusRoute);
  }

  // Populate Simulator Schedule Table
  const tb = document.getElementById('simScheduleBody');
  tb.innerHTML = b.routes.map(r => `
    <tr>
      <td><b style="color:${r.color}">${r.truck_id}</b></td>
      <td>${r.truck_name}</td>
      <td><b>${r.driver}</b></td>
      <td>${r.corridor_name} <small style="color:var(--text-muted)">(${r.branch})</small></td>
      <td>${r.stops_count}</td>
      <td>${r.cartons_count}</td>
      <td><b style="color:var(--accent-cyan)">${r.volume_fill_pct}%</b></td>
      <td>${r.weight_fill_pct}%</td>
      <td>${r.km} km</td>
      <td>${r.leave}–${r.back}</td>
      <td><b>₹${r.cost_total.toLocaleString('en-IN')}</b></td>
      <td>
        <div style="display:flex;gap:4px">
          <button class="ct-chip-btn" onclick="window.LPgoLoad('${r.truck_id}', 1)">3D Load</button>
          <button class="ct-chip-btn" onclick="openDriverHubFor('${r.truck_id}')">Portal</button>
        </div>
      </td>
    </tr>
  `).join('');

  // Populate Driver Hub Selector
  const pSel = document.getElementById('selPortalTruck');
  pSel.innerHTML = b.routes.map(r =>
    `<option value="${r.truck_id}" ${r.truck_id === b.focus_truck_id ? 'selected' : ''}>${r.truck_id} · ${r.driver} (${r.corridor_name} · ${r.stops_count} stops)</option>`
  ).join('');
  if (focusRoute) {
    updateDriverHubPreview(focusRoute.truck_id);
  }

  // Render Audit Log
  renderAuditLog(b.audit_log);

  // Mount / refresh active 2D/3D canvas
  renderActiveCanvases();
}

function renderAuditLog(logs) {
  if (!logs || !logs.length) return;
  const el = document.getElementById('securityAuditList');
  el.innerHTML = logs.map(a => `
    <div style="padding:4px 0;border-bottom:1px dashed var(--border-subtle)">
      <span style="color:var(--accent-cyan)">[${a.ts}]</span>
      <b>${a.tool}</b> (${a.latency_ms}ms) · ${a.detail}
      <span style="color:#34d399"> · 🛡️ ${a.model_armor} · ${a.cloud_dlp}</span>
    </div>
  `).join('');
}

async function triggerPlanUpdate(scopeOverride = null, focusOverride = null) {
  const btn = document.getElementById('btnOptimize');
  btn.textContent = '⏳ Optimizing...';
  try {
    const payload = {
      hub_id: document.getElementById('selHub').value,
      objective: document.getElementById('selObjective').value,
      order_source: document.getElementById('selSource').value,
      corridor_claims: CORRIDOR_CLAIMS,
      scope: scopeOverride || 'all',
      focus_truck_id: focusOverride || ''
    };
    const res = await fetch('/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const bundle = await res.json();
    applyBundle(bundle);
  } finally {
    btn.innerHTML = '<span>⚡</span> Optimize';
  }
}

function applyTruckScope(scopeMode) {
  if (!CURRENT_BUNDLE) return;
  const focusId = document.getElementById('selFocusTruckMap').value;
  const focus = (focusId && focusId !== 'all') ? focusId : (CURRENT_BUNDLE.routes[0]?.truck_id || '');
  triggerPlanUpdate(scopeMode, focus);
}

function applySingleTruckDropdown(truckId) {
  if (!truckId || truckId === 'all') {
    triggerPlanUpdate('all', '');
  } else {
    document.getElementById('selFocusTruckMap').value = truckId;
    triggerPlanUpdate(truckId, truckId);
  }
}

async function submitCorridorClaim() {
  const drv = document.getElementById('selClaimDriver').value;
  const cor = document.getElementById('selClaimCorridor').value;
  CORRIDOR_CLAIMS[drv] = cor;
  await triggerPlanUpdate('all', '');
  showToast(`📌 Pinned <b>${drv}</b> to corridor <b>${cor}</b> with automatic trunk-and-branch splitting.`);
}

async function clearCorridorClaims() {
  CORRIDOR_CLAIMS = {};
  await triggerPlanUpdate('all', '');
  showToast(`Cleared all driver corridor claims.`);
}

/* ── 3D Load Studio & What-If Truck Calculator ── */
function onStudioRouteSelect(truckId) {
  if (!CURRENT_BUNDLE) return;
  const r = CURRENT_BUNDLE.routes.find(x => x.truck_id === truckId);
  if (r) {
    document.getElementById('selStudioTruckType').value = r.truck_code;
    CUSTOM_BOXES = [];
    document.getElementById('addedCustomBoxesList').textContent = '';
    runStudioRepack();
  }
}

function updateStudioTelemetryFromRoute(r) {
  document.getElementById('stVolFill').textContent = r.volume_fill_pct + '%';
  document.getElementById('stVolBar').style.width = Math.min(100, r.volume_fill_pct) + '%';
  document.getElementById('stWtFill').textContent = r.weight_fill_pct + '%';
  document.getElementById('stWtBar').style.width = Math.min(100, r.weight_fill_pct) + '%';
  document.getElementById('stFrontAxle').textContent = r.front_axle_pct + '%';
  document.getElementById('stRearAxle').textContent = r.rear_axle_pct + '%';
  document.getElementById('stAxleBar').style.width = Math.min(100, r.front_axle_pct) + '%';
  document.getElementById('stCmvrNote').textContent = '✓ ' + r.cmvr_status;
  document.getElementById('stLifoStatus').textContent = r.lifo_ok ? '100% LIFO OK' : 'OVERFLOW';
  document.getElementById('stOverflowWarn').style.display = 'none';
}

function onCustomSkuChange(skuCode) {
  if (!META) return;
  const s = META.skus.find(x => x.sku === skuCode);
  if (s) {
    document.getElementById('inpCustomL').value = s.l_cm;
    document.getElementById('inpCustomW').value = s.w_cm;
    document.getElementById('inpCustomH').value = s.h_cm;
    document.getElementById('inpCustomKg').value = s.weight_kg;
  }
}

function addCustomBoxAndPack() {
  const sku = document.getElementById('selCustomSku').value;
  const qty = parseInt(document.getElementById('inpCustomQty').value || '1', 10);
  const stop_seq = parseInt(document.getElementById('inpCustomStop').value || '1', 10);
  const l_cm = parseFloat(document.getElementById('inpCustomL').value || '34');
  const w_cm = parseFloat(document.getElementById('inpCustomW').value || '34');
  const h_cm = parseFloat(document.getElementById('inpCustomH').value || '38');
  const weight_kg = parseFloat(document.getElementById('inpCustomKg').value || '20');

  CUSTOM_BOXES.push({ sku, qty, stop_seq, l_cm, w_cm, h_cm, weight_kg });
  document.getElementById('addedCustomBoxesList').innerHTML =
    CUSTOM_BOXES.map(b => `<span class="ct-kpi-badge" style="margin:2px;display:inline-block">+${b.qty}× ${b.sku} (Stop #${b.stop_seq})</span>`).join('');
  runStudioRepack();
}

function clearCustomBoxes() {
  CUSTOM_BOXES = [];
  document.getElementById('addedCustomBoxesList').innerHTML = '';
  runStudioRepack();
}

async function runStudioRepack() {
  const source_truck_id = document.getElementById('selStudioRoute').value;
  const target_truck_code = document.getElementById('selStudioTruckType').value;

  const res = await fetch('/api/repack-truck', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_truck_id,
      target_truck_code,
      extra_boxes: CUSTOM_BOXES
    })
  });
  const out = await res.json();
  const st = out.stats;

  document.getElementById('stVolFill').textContent = st.volume_fill_pct + '%';
  document.getElementById('stVolBar').style.width = Math.min(100, st.volume_fill_pct) + '%';
  document.getElementById('stWtFill').textContent = st.weight_fill_pct + '%';
  document.getElementById('stWtBar').style.width = Math.min(100, st.weight_fill_pct) + '%';
  document.getElementById('stFrontAxle').textContent = st.front_axle_pct + '%';
  document.getElementById('stRearAxle').textContent = st.rear_axle_pct + '%';
  document.getElementById('stAxleBar').style.width = Math.min(100, st.front_axle_pct) + '%';
  document.getElementById('stCmvrNote').textContent = (st.cmvr_compliant ? '✓ ' : '⚠️ ') + st.cmvr_status + ` · Est. ₹${st.estimated_day_cost_inr.toLocaleString('en-IN')}/day`;
  document.getElementById('stLifoStatus').textContent = st.lifo_ok ? '100% LIFO OK' : `${st.unplaced_count} OVERFLOW`;

  const warnEl = document.getElementById('stOverflowWarn');
  if (st.unplaced_count > 0) {
    warnEl.style.display = 'block';
    warnEl.textContent = `⚠️ ${st.unplaced_count} cartons did not fit inside ${st.truck_name} (${st.inner_cm}). Select a larger truck class from the dropdown!`;
  } else {
    warnEl.style.display = 'none';
  }

  // Update the 3D engine canvas with this repacked truck first in list
  if (CURRENT_BUNDLE && CURRENT_BUNDLE.anim_data) {
    const otherTrucks = (CURRENT_BUNDLE.anim_data.trucks || []).filter(t => t.id !== source_truck_id && t.id !== out.truck_anim.id);
    const updatedAnim = Object.assign({}, CURRENT_BUNDLE.anim_data, {
      trucks: [out.truck_anim, ...otherTrucks]
    });
    window.mountFleetFlowEngine('ct-load-mount', updatedAnim, 'load');
  }
  if (out.audit_log) renderAuditLog(out.audit_log);
}

/* ── Fleet & Cost Simulator ── */
async function runSimulatorOptimization() {
  const fuel_price = parseFloat(document.getElementById('inpSimFuel').value || '92');
  const driver_day_cost = parseFloat(document.getElementById('inpSimDriverCost').value || '1100');
  const res = await fetch('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hub_id: document.getElementById('selHub').value,
      objective: document.getElementById('selObjective').value,
      truck_counts: FLEET_COUNTS,
      fuel_price,
      driver_day_cost
    })
  });
  const bundle = await res.json();
  applyBundle(bundle);
  showToast(`⚡ Fleet simulation complete: <b>${bundle.kpi.optimized_trucks} trucks</b> dispatched at <b>₹${bundle.kpi.optimized_cost_inr.toLocaleString('en-IN')}/day</b>.`);
}

function copyScheduleTable() {
  if (!CURRENT_BUNDLE) return;
  const header = ['Truck ID', 'Vehicle Class', 'Driver', 'Corridor', 'Branch', 'Stops', 'Cartons', 'Vol Fill %', 'Wt Fill %', 'Distance km', 'Shift', 'Cost INR'].join('\t');
  const rows = CURRENT_BUNDLE.routes.map(r =>
    [r.truck_id, r.truck_name, r.driver, r.corridor, r.branch, r.stops_count, r.cartons_count, r.volume_fill_pct, r.weight_fill_pct, r.km, `${r.leave}-${r.back}`, r.cost_total].join('\t')
  );
  navigator.clipboard.writeText([header, ...rows].join('\n'));
  showToast('📋 Schedule table copied to clipboard (ready to paste into Google Sheets)!');
}

function exportScheduleCsv() {
  if (!CURRENT_BUNDLE) return;
  const header = ['Truck ID', 'Vehicle Class', 'Driver', 'Corridor', 'Branch', 'Stops', 'Cartons', 'Vol Fill %', 'Wt Fill %', 'Distance km', 'Shift', 'Cost INR'].join(',');
  const rows = CURRENT_BUNDLE.routes.map(r =>
    [r.truck_id, `"${r.truck_name}"`, r.driver, r.corridor, `"${r.branch}"`, r.stops_count, r.cartons_count, r.volume_fill_pct, r.weight_fill_pct, r.km, `${r.leave}-${r.back}`, r.cost_total].join(',')
  );
  const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `fleetflow_schedule_${CURRENT_BUNDLE.plan_id}.csv`;
  a.click();
}

/* ── Dock QR Scanner & Order Intake ── */
async function scanSamplePhoto(filename, cardEl) {
  document.querySelectorAll('.ct-photo-card').forEach(c => c.classList.remove('active'));
  if (cardEl) cardEl.classList.add('active');
  document.getElementById('scanStatusText').textContent = `⏳ Scanning ${filename}...`;
  const res = await fetch('/api/scan-photo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sample_name: filename, auto_replan: true })
  });
  const data = await res.json();
  const s = data.scan;
  document.getElementById('scanStatusText').textContent = `✓ Decoded ${s.cartons_read || 0} cartons`;
  document.getElementById('scanResultContent').innerHTML = `
    <div style="color:#34d399;font-weight:700;margin-bottom:6px">✓ QR &amp; Label Scan Complete: ${s.cartons_read || 0} cartons across ${Object.keys(s.by_stop || {}).length} stores (${s.fragile || 0} fragile)</div>
    <div>${(s.sample || []).map(x => `<div>• ${x}</div>`).join('')}</div>
  `;
  if (data.bundle) applyBundle(data.bundle);
  showToast(`📷 Scanned <b>${s.cartons_read || 0} cartons</b> from dock photo and refreshed 3D load plan!`);
}

function uploadCustomPhoto(inputEl) {
  const file = inputEl.files && inputEl.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async function(ev) {
    document.getElementById('scanStatusText').textContent = `⏳ Scanning ${file.name}...`;
    const res = await fetch('/api/scan-photo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: ev.target.result, mime_type: file.type, auto_replan: true })
    });
    const data = await res.json();
    const s = data.scan;
    document.getElementById('scanStatusText').textContent = `✓ Decoded ${s.cartons_read || 0} cartons`;
    document.getElementById('scanResultContent').innerHTML = `
      <div style="color:#34d399;font-weight:700;margin-bottom:6px">✓ Custom Photo Decoded: ${s.cartons_read || 0} cartons</div>
      <div>${(s.sample || []).map(x => `<div>• ${x}</div>`).join('')}</div>
    `;
    if (data.bundle) applyBundle(data.bundle);
  };
  reader.readAsDataURL(file);
}

function loadSampleOrder(idx) {
  if (!META || !META.sample_orders[idx]) return;
  const o = META.sample_orders[idx];
  document.getElementById('inpOrderText').value = o.preview;
}

async function submitOrderText() {
  const text = document.getElementById('inpOrderText').value;
  if (!text.trim()) return;
  const res = await fetch('/api/ingest-orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, auto_replan: true })
  });
  const data = await res.json();
  const ing = data.ingest;
  if (ing.status === 'ok') {
    document.getElementById('ingestResultContent').innerHTML = `
      <div style="color:#34d399;font-weight:700">✓ Geocoded ${ing.stops} dealer outlets · ${ing.cartons} cartons (${ing.volume_m3} m³ · ${ing.weight_kg} kg)</div>
      <div style="margin-top:4px;font-size:11.5px">${(ing.outlets || []).join(' · ')}</div>
    `;
    if (data.bundle) applyBundle(data.bundle);
    showToast(`📝 Parsed <b>${ing.stops} stops (${ing.cartons} cartons)</b> and re-optimized routes &amp; 3D loads!`);
  } else {
    document.getElementById('ingestResultContent').textContent = ing.message || 'Could not parse orders.';
  }
}

async function resetToDefaultDemo() {
  await quickPrompt('Reset to default demo order book');
}

/* ── Driver Hub & BigQuery Studio ── */
function openDriverHubFor(truckId) {
  switchWorkspace('gcp');
  document.getElementById('selPortalTruck').value = truckId;
  updateDriverHubPreview(truckId);
}

function updateDriverHubPreview(truckId) {
  if (!CURRENT_BUNDLE) return;
  const r = CURRENT_BUNDLE.routes.find(x => x.truck_id === truckId) || CURRENT_BUNDLE.routes[0];
  if (!r) return;
  document.getElementById('btnOpenMapsNav').href = r.gmaps_nav_url;
  document.getElementById('btnOpenWhatsApp').href = r.whatsapp_url;
  document.getElementById('btnOpenPortalTab').href = r.driver_portal_url;
  document.getElementById('driverPortalIframe').src = r.driver_portal_url;
}

function loadBqPreset(idx) {
  document.getElementById('inpBqSql').value = BQ_PRESETS[idx] || BQ_PRESETS[0];
}

async function executeBqQuery() {
  const sql = document.getElementById('inpBqSql').value;
  document.getElementById('bqEngineStatus').textContent = '⏳ Running BigQuery job...';
  const res = await fetch('/api/bigquery/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql, use_live_bq: true })
  });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById('bqEngineStatus').textContent = '⚠️ ' + (data.detail || 'SQL error');
    return;
  }
  document.getElementById('bqEngineStatus').textContent = `✓ ${data.engine} · ${data.row_count} rows (${data.latency_ms} ms)`;
  const cols = data.columns || [];
  document.getElementById('bqResultHead').innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr>`;
  document.getElementById('bqResultBody').innerHTML = (data.rows || []).map(row =>
    `<tr>${cols.map(c => `<td>${row[c] ?? ''}</td>`).join('')}</tr>`
  ).join('');
}

/* ── Bottom AI Copilot Command Bar ── */
async function quickPrompt(text) {
  document.getElementById('inpAgentPrompt').value = text;
  await sendAgentPrompt();
}

async function sendAgentPrompt() {
  const inp = document.getElementById('inpAgentPrompt');
  const prompt = inp.value.trim();
  if (!prompt) return;
  showToast(`🤖 <b>FleetFlow Agent executing:</b> "${prompt}"...`, 10000);
  const res = await fetch('/api/agent-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt })
  });
  const data = await res.json();
  if (data.bundle) {
    applyBundle(data.bundle);
  }
  const formatted = (data.reply || '').replace(/\*\*(.*?)\*\*/g, '<b style="color:var(--accent-cyan)">$1</b>');
  showToast(`
    <div style="font-family:var(--font-mono);font-size:10.5px;color:#34d399;margin-bottom:4px">
      ▸ ${data.tool_called} (${data.latency_ms}ms) · 🛡️ Model Armor &amp; DLP Verified
    </div>
    <div>${formatted}</div>
  `, 7000);
}

document.addEventListener('DOMContentLoaded', initControlTower);
</script>
</body>
</html>
"""


def build_control_tower_html() -> str:
    """Return the complete, self-contained Control Tower & 3D Load Studio HTML application."""
    engine_js = (Path(__file__).resolve().parents[1] / "render" / "anim" / "engine.js").read_text(encoding="utf-8")
    return (
        _UI_HTML
        .replace("__ANIM_CSS__", ANIM_CSS)
        .replace("__ENGINE_JS__", engine_js)
    )
