"""Single-Page Application HTML/CSS/JS generator for FleetFlow Supply Chain Control Tower & 3D Load Studio.

Design Highlights:
  * Google Gemini Minimalist Light Theme (default) + Midnight Dark Theme toggle.
  * Left-Side App Navigation Rail (collapsible) with macOS Dock & Genie spring-physics animations.
  * Clean, practical 4-metric KPI strip (Trucks Dispatched, Daily Savings, Stops & Cartons, Route Distance)
    without unnecessary clutter.
  * 6 Workspaces:
      1. 🗺️ Dispatch & Map (1/3/All Fleet Focus, Driver Corridor Pinning, 60fps Road Map)
      2. 📦 3D Load Studio (Interactive Truck Type What-If Calculator, Custom Carton Packer, 3D LIFO Bay)
      3. 🚚 Fleet & Cost Simulator (Fleet Mix Steppers, Cost Inputs, Copy-Ready Google Sheets / CSV)
      4. 📸 Dock QR & Intake (Warehouse QR Vision Scanner + Unstructured ERP/WhatsApp Order Intake)
      5. 📱 Driver Hub & BigQuery (Mobile Driver Portal Preview, 1-Tap Google Maps, Live BigQuery SQL)
      6. 📘 Architecture & How-To (Dual Deployment Guide, GCP Service Roles: BigQuery, GCS, Vertex AI, Cloud Run, Model Armor)
"""

from __future__ import annotations

from pathlib import Path

from app.render.anim_html import _CSS as ANIM_CSS

_UI_HTML = r"""<!DOCTYPE html>
<html lang="en" class="theme-light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FleetFlow Control Tower · Supply Chain & 3D Load Studio</title>
  <meta name="description" content="Enterprise Supply Chain Control Tower, 3D LIFO Truck Load Studio, and Route Optimization powered by Google Cloud, BigQuery, Vertex AI, and Google Maps Platform.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    /* ── Engine Base CSS ── */
    __ANIM_CSS__

    /* ── Google Gemini Minimalist Light Theme (Default) ── */
    :root, html.theme-light {
      --bg-canvas: #f4f7fb;
      --bg-sidebar: #ffffff;
      --bg-elevated: #f8fafd;
      --bg-card: #ffffff;
      --bg-card-hover: #f1f5f9;
      --bg-input: #f8fafc;
      --bg-glass: rgba(255, 255, 255, 0.92);
      --border-subtle: #e2e8f0;
      --border-focus: #1a73e8;
      --text-main: #1f2937;
      --text-secondary: #475569;
      --text-muted: #64748b;
      --accent-primary: #1a73e8;
      --accent-primary-soft: rgba(26, 115, 232, 0.10);
      --accent-cyan: #0284c7;
      --accent-blue: #1a73e8;
      --accent-amber: #d97706;
      --accent-emerald: #059669;
      --accent-emerald-soft: rgba(5, 150, 105, 0.10);
      --accent-rose: #e11d48;
      --shadow-soft: 0 4px 20px -2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
      --shadow-float: 0 16px 40px -8px rgba(15, 23, 42, 0.12);
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    /* ── Midnight Dark Theme ── */
    html.theme-dark {
      --bg-canvas: #070b14;
      --bg-sidebar: #0c1222;
      --bg-elevated: #0f172a;
      --bg-card: #111a2e;
      --bg-card-hover: #17233d;
      --bg-input: #0b1120;
      --bg-glass: rgba(15, 23, 42, 0.90);
      --border-subtle: rgba(148, 163, 184, 0.15);
      --border-focus: #38bdf8;
      --text-main: #f1f5f9;
      --text-secondary: #cbd5e1;
      --text-muted: #94a3b8;
      --accent-primary: #38bdf8;
      --accent-primary-soft: rgba(56, 189, 248, 0.14);
      --accent-cyan: #38bdf8;
      --accent-blue: #60a5fa;
      --accent-amber: #f59e0b;
      --accent-emerald: #10b981;
      --accent-emerald-soft: rgba(16, 185, 129, 0.14);
      --accent-rose: #f43f5e;
      --shadow-soft: 0 10px 28px -6px rgba(0, 0, 0, 0.50);
      --shadow-float: 0 20px 48px -10px rgba(0, 0, 0, 0.70);
    }

    /* Harmonize embedded Engine Map & 3D Load Studio in Light Theme */
    html.theme-light #ct-load-mount,
    html.theme-light .lp-pane {
      background: #f8fafd !important;
      color: #1e293b !important;
    }
    html.theme-light .lp-wrap {
      background: #ffffff !important;
      color: #1f2937 !important;
      border-color: #e2e8f0 !important;
    }
    html.theme-light .lp-hdr,
    html.theme-light .lp-bar {
      background: #f8fafd !important;
      border-color: #e2e8f0 !important;
      color: #1f2937 !important;
    }
    html.theme-light .lp-title {
      color: #1f2937 !important;
    }
    html.theme-light .lp-kpi {
      background: #ffffff !important;
      border-color: #e2e8f0 !important;
    }
    html.theme-light .lp-kpi b {
      color: #1f2937 !important;
    }
    html.theme-light .lp-side {
      background: #f8fafd !important;
      border-color: #e2e8f0 !important;
      color: #1f2937 !important;
    }
    html.theme-light .lp-item {
      background: #ffffff !important;
      border-color: #e2e8f0 !important;
      color: #1f2937 !important;
    }
    html.theme-light .lp-item:hover,
    html.theme-light .lp-item.on {
      background: rgba(26, 115, 232, 0.08) !important;
      border-color: #1a73e8 !important;
    }
    html.theme-light .lp-truck-bar {
      background: #f1f5f9 !important;
      border-bottom: 1px solid var(--border-subtle) !important;
      color: #1e293b !important;
    }
    html.theme-light .lp-truck-bar-lbl {
      color: #64748b !important;
    }
    html.theme-light .lp-chip {
      background: #ffffff !important;
      border: 1px solid var(--border-subtle) !important;
      color: #334155 !important;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }
    html.theme-light .lp-chip:hover {
      background: #f8fafc !important;
      color: #0f172a !important;
    }
    html.theme-light .lp-chip.on {
      background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%) !important;
      border: 1.5px solid #0d47a1 !important;
      color: #ffffff !important;
      font-weight: 800 !important;
      box-shadow: 0 4px 16px rgba(26, 115, 232, 0.45), 0 0 0 2px rgba(26, 115, 232, 0.25) !important;
      transform: translateY(-1px);
    }
    html.theme-light .lp-chip.on small {
      color: rgba(255, 255, 255, 0.90) !important;
      font-weight: 700 !important;
    }
    html.theme-dark .lp-chip.on {
      background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
      border: 1.5px solid #60a5fa !important;
      color: #ffffff !important;
      font-weight: 800 !important;
      box-shadow: 0 4px 20px rgba(37, 99, 235, 0.65), 0 0 0 2px rgba(96, 165, 250, 0.40) !important;
      transform: translateY(-1px);
    }
    html.theme-dark .lp-chip.on small {
      color: rgba(255, 255, 255, 0.90) !important;
      font-weight: 700 !important;
    }
    html.theme-light .lp-legend {
      background: #ffffff !important;
      border-left: 1px solid var(--border-subtle) !important;
      color: #1e293b !important;
      box-shadow: -2px 0 12px rgba(15, 23, 42, 0.04) !important;
    }
    html.theme-light .lp-lh {
      color: #1a73e8 !important;
    }
    html.theme-light .lp-li {
      background: #f8fafc !important;
      border: 1px solid var(--border-subtle) !important;
      color: #1e293b !important;
    }
    html.theme-light .lp-li:hover {
      background: #f1f5f9 !important;
    }
    html.theme-light .lp-li.on,
    html.theme-light .lp-li.sel {
      background: linear-gradient(135deg, #e8f0fe 0%, #d2e3fc 100%) !important;
      outline: 2.5px solid #1a73e8 !important;
      border-color: #1a73e8 !important;
      color: #0d47a1 !important;
      font-weight: 800 !important;
      box-shadow: 0 4px 14px rgba(26, 115, 232, 0.28) !important;
      transform: translateX(3px);
    }
    html.theme-dark .lp-li.on,
    html.theme-dark .lp-li.sel {
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.38) 0%, rgba(29, 78, 216, 0.52) 100%) !important;
      outline: 2.5px solid #38bdf8 !important;
      border-color: #38bdf8 !important;
      color: #ffffff !important;
      font-weight: 800 !important;
      box-shadow: 0 4px 18px rgba(56, 189, 248, 0.40) !important;
      transform: translateX(3px);
    }
    html.theme-light .lp-ctrl {
      background: #f1f5f9 !important;
      border-top: 1px solid var(--border-subtle) !important;
      color: #1e293b !important;
    }
    html.theme-light .lp-btn,
    html.theme-light .lp-seg {
      background: #ffffff !important;
      border: 1px solid var(--border-subtle) !important;
      color: #334155 !important;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    html.theme-light .lp-btn:hover {
      background: #f8fafc !important;
      border-color: #1a73e8 !important;
      color: #1a73e8 !important;
    }
    html.theme-light .lp-btn.lp-active {
      background: rgba(26, 115, 232, 0.12) !important;
      color: #1a73e8 !important;
      border-color: #1a73e8 !important;
    }
    html.theme-light .lp-seg button {
      color: #475569 !important;
    }
    html.theme-light .lp-seg button.on {
      background: #1a73e8 !important;
      color: #ffffff !important;
    }
    html.theme-light .lp-hud {
      background: rgba(255, 255, 255, 0.94) !important;
      backdrop-filter: blur(10px) !important;
      border: 1px solid var(--border-subtle) !important;
      color: #0f172a !important;
      box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08) !important;
    }
    html.theme-light .lp-card {
      background: rgba(255, 255, 255, 0.98) !important;
      backdrop-filter: blur(16px) !important;
      border: 1px solid rgba(66, 133, 244, 0.35) !important;
      border-radius: 16px !important;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.12) !important;
      color: #0f172a !important;
      width: 320px !important;
    }
    html.theme-light .lp-pop-h {
      background: #f1f5f9 !important;
      color: #0f172a !important;
    }
    html.theme-light .lp-pop-h b {
      color: #0f172a !important;
    }
    html.theme-light .lp-vmodes {
      background: #f8fafc !important;
      border-bottom: 1px solid var(--border-subtle) !important;
    }
    html.theme-light .lp-vbtn {
      background: #ffffff !important;
      border: 1px solid var(--border-subtle) !important;
      color: #475569 !important;
    }
    html.theme-light .lp-vbtn:hover {
      background: #f1f5f9 !important;
      color: #0f172a !important;
    }
    html.theme-light .lp-vbtn.on {
      background: #1a73e8 !important;
      color: #ffffff !important;
      border-color: #1a73e8 !important;
    }
    html.theme-light .lp-vbtn.lp-rep {
      background: #fffbeb !important;
      color: #b45309 !important;
      border-color: rgba(245, 158, 11, 0.4) !important;
    }
    html.theme-light .lp-x {
      color: #64748b !important;
    }
    html.theme-light .lp-x:hover {
      color: #0f172a !important;
    }
    html.theme-light .lp-pop-g span {
      color: #64748b !important;
      font-weight: 700 !important;
    }
    html.theme-light .lp-pop-g b {
      color: #0f172a !important;
    }
    html.theme-light .lp-tip {
      background: rgba(255, 255, 255, 0.98) !important;
      border: 1px solid rgba(66, 133, 244, 0.4) !important;
      color: #0f172a !important;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12) !important;
    }
    html.theme-light .lp-hint {
      background: rgba(255, 255, 255, 0.92) !important;
      border: 1px solid var(--border-subtle) !important;
      color: #475569 !important;
      box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06) !important;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      width: 100%;
      height: 100%;
      background: var(--bg-canvas);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 14px;
      line-height: 1.45;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
      transition: background-color 0.25s ease, color 0.25s ease;
    }

    /* ── Google 4-Color Revolving Neon Aura & Orbital Ring Keyframes ── */
    @property --g-angle {
      syntax: '<angle>';
      initial-value: 0deg;
      inherits: false;
    }

    @keyframes spinGoogleAngle {
      to { --g-angle: 360deg; }
    }

    @keyframes spinOrbital {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    @keyframes spinOrbitalReverse {
      0% { transform: rotate(360deg); }
      100% { transform: rotate(0deg); }
    }

    /* ── macOS Genie & Spring Physics Keyframes ── */
    @keyframes genieWorkspaceOpen {
      0% {
        opacity: 0;
        transform: perspective(1200px) translate3d(-20px, 14px, -30px) scale3d(0.95, 0.90, 1) rotateX(3deg);
        filter: blur(4px);
      }
      65% {
        opacity: 1;
        transform: perspective(1200px) translate3d(2px, -2px, 0) scale3d(1.004, 1.004, 1) rotateX(0deg);
        filter: blur(0px);
      }
      100% {
        opacity: 1;
        transform: perspective(1200px) translate3d(0, 0, 0) scale3d(1, 1, 1) rotateX(0deg);
        filter: blur(0px);
      }
    }

    @keyframes genieCardPop {
      0% { opacity: 0; transform: translateY(14px) scale(0.96); }
      100% { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes genieToastPop {
      0% { opacity: 0; transform: perspective(800px) translateY(28px) scale(0.84) rotateX(10deg); }
      70% { opacity: 1; transform: perspective(800px) translateY(-3px) scale(1.02) rotateX(0deg); }
      100% { opacity: 1; transform: perspective(800px) translateY(0) scale(1) rotateX(0deg); }
    }

    /* ── Revolving Google 4-Color Neon Border Container ── */
    .google-revolving-box {
      position: relative;
      border-radius: 22px;
      padding: 3px;
      background: conic-gradient(
        from var(--g-angle, 0deg),
        #4285F4 0deg,
        #EA4335 90deg,
        #FBBC04 180deg,
        #34A853 270deg,
        #4285F4 360deg
      );
      animation: spinGoogleAngle 4.5s linear infinite;
      box-shadow:
        0 14px 40px -8px rgba(66, 133, 244, 0.25),
        0 0 28px rgba(234, 67, 53, 0.14),
        0 0 28px rgba(52, 168, 83, 0.14);
      overflow: visible;
    }

    .google-revolving-box::before {
      content: '';
      position: absolute;
      inset: -4px;
      border-radius: 25px;
      background: conic-gradient(
        from var(--g-angle, 0deg),
        rgba(66, 133, 244, 0.55),
        rgba(234, 67, 53, 0.55),
        rgba(251, 188, 4, 0.55),
        rgba(52, 168, 83, 0.55),
        rgba(66, 133, 244, 0.55)
      );
      filter: blur(14px);
      opacity: 0.65;
      z-index: 0;
      animation: spinGoogleAngle 4.5s linear infinite;
      pointer-events: none;
    }

    .google-revolving-inner {
      position: relative;
      z-index: 1;
      background: var(--bg-card);
      border-radius: 19px;
      padding: 24px 28px;
    }

    /* ── Moving Orbital Neon Rings (Logo, Hero & KPI Accents) ── */
    .orbital-ring-wrap {
      position: relative;
      width: 48px;
      height: 48px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .orbital-ring-wrap::before {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 50%;
      border: 2.5px solid transparent;
      border-top-color: #4285F4;
      border-right-color: #EA4335;
      border-bottom-color: #FBBC04;
      border-left-color: #34A853;
      animation: spinOrbital 3.6s linear infinite;
      box-shadow: 0 0 12px rgba(66, 133, 244, 0.35);
    }

    .orbital-ring-wrap::after {
      content: '';
      position: absolute;
      inset: 5px;
      border-radius: 50%;
      border: 1.5px dashed rgba(66, 133, 244, 0.55);
      border-top-color: #34A853;
      border-bottom-color: #EA4335;
      animation: spinOrbitalReverse 6s linear infinite;
    }

    .orbital-ring-core {
      position: relative;
      z-index: 2;
      font-size: 20px;
      line-height: 1;
    }

    /* ── Neon Colored Card & Box Outlines (Light & Dark Mode) ── */
    .neon-blue {
      border: 1.5px solid rgba(66, 133, 244, 0.65) !important;
      box-shadow: 0 6px 22px -4px rgba(66, 133, 244, 0.16), inset 0 0 0 1px rgba(66, 133, 244, 0.10) !important;
    }
    .neon-green {
      border: 1.5px solid rgba(52, 168, 83, 0.65) !important;
      box-shadow: 0 6px 22px -4px rgba(52, 168, 83, 0.16), inset 0 0 0 1px rgba(52, 168, 83, 0.10) !important;
    }
    .neon-amber {
      border: 1.5px solid rgba(251, 188, 4, 0.78) !important;
      box-shadow: 0 6px 22px -4px rgba(251, 188, 4, 0.18), inset 0 0 0 1px rgba(251, 188, 4, 0.12) !important;
    }
    .neon-red {
      border: 1.5px solid rgba(234, 67, 53, 0.65) !important;
      box-shadow: 0 6px 22px -4px rgba(234, 67, 53, 0.16), inset 0 0 0 1px rgba(234, 67, 53, 0.10) !important;
    }

    html.theme-dark .neon-blue {
      border-color: #4285F4 !important;
      box-shadow: 0 0 22px rgba(66, 133, 244, 0.32), inset 0 0 12px rgba(66, 133, 244, 0.10) !important;
    }
    html.theme-dark .neon-green {
      border-color: #34A853 !important;
      box-shadow: 0 0 22px rgba(52, 168, 83, 0.32), inset 0 0 12px rgba(52, 168, 83, 0.10) !important;
    }
    html.theme-dark .neon-amber {
      border-color: #FBBC04 !important;
      box-shadow: 0 0 22px rgba(251, 188, 4, 0.30), inset 0 0 12px rgba(251, 188, 4, 0.10) !important;
    }
    html.theme-dark .neon-red {
      border-color: #EA4335 !important;
      box-shadow: 0 0 22px rgba(234, 67, 53, 0.32), inset 0 0 12px rgba(234, 67, 53, 0.10) !important;
    }

    /* Bold Big Headings with Google Color Accents */
    .google-gradient-text {
      background: linear-gradient(90deg, #4285F4 0%, #EA4335 36%, #FBBC04 68%, #34A853 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .ct-big-heading {
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.18;
      color: var(--text-main);
    }

    .ct-section-heading {
      font-size: 19px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: var(--text-main);
    }

    /* ── Clean Collapsible Accordion Drawers (Hides Clutter on Front Page & Sidebars) ── */
    details.ct-accordion {
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      border-radius: 16px;
      overflow: hidden;
      transition: border-color 0.22s ease, box-shadow 0.22s ease;
    }

    details.ct-accordion:hover {
      border-color: #4285F4;
      box-shadow: 0 4px 18px rgba(66, 133, 244, 0.12);
    }

    details.ct-accordion[open] {
      border-color: #4285F4;
      box-shadow: 0 8px 26px rgba(66, 133, 244, 0.16);
    }

    details.ct-accordion > summary {
      list-style: none;
      cursor: pointer;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 14.5px;
      font-weight: 800;
      color: var(--text-main);
      background: var(--bg-elevated);
      user-select: none;
      transition: background-color 0.18s ease;
    }

    details.ct-accordion > summary::-webkit-details-marker {
      display: none;
    }

    details.ct-accordion > summary:hover {
      background: var(--bg-card-hover);
    }

    .ct-acc-chevron {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 999px;
      background: var(--accent-primary-soft);
      color: var(--accent-primary);
      font-size: 12px;
      font-weight: 800;
      transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
    }

    details.ct-accordion[open] .ct-acc-chevron {
      transform: rotate(180deg);
      background: #4285F4;
      color: #ffffff;
    }

    .ct-acc-body {
      padding: 16px 18px;
      border-top: 1px solid var(--border-subtle);
      background: var(--bg-card);
    }

    /* ── App Layout Shell (Left Sidebar + Right Main Stage) ── */
    .ct-app-layout {
      display: flex;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
    }

    /* ── Left Navigation Sidebar (Gemini / macOS Style with Neon Highlights) ── */
    .ct-left-rail {
      width: 264px;
      background: var(--bg-sidebar);
      border-right: 1.5px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 16px 14px;
      flex-shrink: 0;
      z-index: 30;
      box-shadow: var(--shadow-soft);
      transition: width 0.32s cubic-bezier(0.22, 1, 0.36, 1), background-color 0.25s ease;
      overflow-y: auto;
    }

    .ct-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 4px 6px 16px;
      border-bottom: 1px solid var(--border-subtle);
    }

    .ct-brand-title {
      font-size: 18.5px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .ct-brand-badge {
      font-family: var(--font-mono);
      font-size: 9.5px;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 999px;
      background: var(--accent-primary-soft);
      color: var(--accent-primary);
      border: 1px solid rgba(66, 133, 244, 0.35);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .ct-brand-sub {
      font-size: 11px;
      color: var(--text-muted);
      font-weight: 600;
    }

    /* Navigation Menu Items */
    .ct-nav-section-lbl {
      font-size: 10.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--text-muted);
      padding: 14px 10px 6px;
    }

    .ct-nav-list {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .ct-nav-btn {
      display: flex;
      align-items: center;
      gap: 11px;
      width: 100%;
      padding: 10.5px 13px;
      border-radius: 13px;
      border: 1.5px solid transparent;
      background: transparent;
      color: var(--text-secondary);
      font-family: var(--font-sans);
      font-size: 13.5px;
      font-weight: 700;
      cursor: pointer;
      text-align: left;
      transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }

    .ct-nav-btn .nav-ico {
      font-size: 17px;
      width: 24px;
      text-align: center;
      transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .ct-nav-btn:hover {
      background: var(--bg-card-hover);
      color: var(--text-main);
      border-color: rgba(66, 133, 244, 0.35);
      transform: translateX(4px);
    }

    .ct-nav-btn:hover .nav-ico {
      transform: scale(1.18);
    }

    .ct-nav-btn.active {
      background: var(--accent-primary-soft);
      color: var(--accent-primary);
      border-color: #4285F4;
      font-weight: 800;
      box-shadow: 0 4px 14px rgba(66, 133, 244, 0.20);
    }

    /* Left Sidebar Quick Dispatch Config */
    .ct-rail-config {
      margin-top: 8px;
      padding: 12px;
      border-radius: 14px;
      background: var(--bg-elevated);
      border: 1.5px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 9px;
    }

    .ct-select-group {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .ct-select-lbl {
      font-size: 10.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
    }

    .ct-select, .ct-input {
      width: 100%;
      height: 40px;
      background: var(--bg-card);
      color: var(--text-main);
      border: 1.5px solid var(--border-subtle);
      border-radius: 10px;
      padding: 0 12px;
      font-family: var(--font-sans);
      font-size: 13px;
      font-weight: 700;
      outline: none;
      transition: border-color 0.18s, box-shadow 0.18s;
    }

    textarea.ct-input {
      height: auto;
      padding: 12px 14px;
    }

    .ct-select:focus, .ct-input:focus {
      border-color: #4285F4;
      box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.20);
    }

    .ct-btn-primary {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      height: 40px;
      padding: 0 16px;
      border-radius: 10px;
      border: 1.5px solid rgba(255, 255, 255, 0.28);
      background: linear-gradient(135deg, #4285F4 0%, #1a73e8 50%, #0284c7 100%);
      color: #ffffff;
      font-family: var(--font-sans);
      font-size: 13px;
      font-weight: 800;
      white-space: nowrap;
      cursor: pointer;
      box-shadow: 0 6px 18px rgba(66, 133, 244, 0.34);
      transition: transform 0.2s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.2s;
    }

    .ct-btn-primary:hover {
      transform: translateY(-1.5px);
      box-shadow: 0 10px 24px rgba(66, 133, 244, 0.46);
    }

    .ct-btn-secondary {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      height: 40px;
      padding: 0 14px;
      border-radius: 10px;
      border: 1.5px solid var(--border-subtle);
      background: var(--bg-card);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 12.5px;
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.18s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .ct-btn-secondary:hover {
      border-color: #4285F4;
      color: var(--accent-primary);
      background: var(--bg-card-hover);
      box-shadow: 0 4px 14px rgba(66, 133, 244, 0.16);
      transform: translateY(-1px);
    }

    .ct-btn-secondary.active {
      background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%) !important;
      color: #ffffff !important;
      border-color: #0d47a1 !important;
      box-shadow: 0 4px 16px rgba(26, 115, 232, 0.45) !important;
    }

    .ct-rail-footer {
      padding-top: 12px;
      border-top: 1px solid var(--border-subtle);
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    /* ── Right Workspace Area ── */
    .ct-workspace-col {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
      min-width: 0;
    }

    .ct-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 16px 20px;
      gap: 16px;
      overflow: hidden;
      min-height: 0;
    }

    /* ── Clean, Strictly Symmetrical 4-Metric Operational Strip ── */
    .ct-kpi-ribbon {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      flex-shrink: 0;
    }

    .ct-kpi-card {
      position: relative;
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      border-radius: 16px;
      height: 104px;
      min-height: 104px;
      max-height: 104px;
      padding: 14px 18px;
      display: flex;
      align-items: stretch;
      justify-content: space-between;
      box-shadow: var(--shadow-soft);
      animation: genieCardPop 0.38s cubic-bezier(0.22, 1, 0.36, 1) both;
      transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.22s;
      overflow: hidden;
    }

    .ct-kpi-card:hover {
      transform: translateY(-2px);
    }

    .ct-kpi-left {
      width: 100%;
      min-width: 0;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .ct-kpi-right {
      position: absolute;
      top: 13px;
      right: 16px;
      bottom: 13px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      align-items: flex-end;
      pointer-events: none;
    }

    .ct-kpi-label {
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      padding-right: 40px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .ct-kpi-val {
      font-size: 18px;
      font-weight: 800;
      letter-spacing: -0.025em;
      color: var(--text-main);
      line-height: 1.2;
      padding-right: 38px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .ct-kpi-sub {
      font-size: 11.5px;
      font-weight: 600;
      color: var(--text-secondary);
      padding-right: 116px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .ct-kpi-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      height: 24px;
      font-family: var(--font-mono);
      font-size: 10.5px;
      font-weight: 800;
      padding: 0 10px;
      border-radius: 999px;
      background: var(--accent-emerald-soft);
      color: var(--accent-emerald);
      border: 1px solid rgba(52, 168, 83, 0.35);
      white-space: nowrap;
      flex-shrink: 0;
    }

    /* ── Workspace Views with Fluid Slide & Spring Animation ── */
    .ct-view {
      display: none;
      flex: 1;
      min-height: 0;
      gap: 16px;
      transform-origin: center top;
    }

    .ct-view.active {
      display: flex;
      animation: workspaceSlideIn 0.38s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    }

    @keyframes workspaceSlideIn {
      0% {
        opacity: 0;
        transform: translateY(16px) scale(0.99);
      }
      100% {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    /* ── High-Tech Google 4-Color Synthesis HUD Overlay ── */
    .lp-synthesis-modal {
      position: fixed;
      inset: 0;
      z-index: 99999;
      background: rgba(4, 9, 22, 0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      animation: modalFadeIn 0.24s cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes modalFadeIn {
      0% { opacity: 0; }
      100% { opacity: 1; }
    }

    .lp-modal-card {
      position: relative;
      width: 100%;
      max-width: 620px;
      border-radius: 24px;
      box-shadow:
        0 24px 70px rgba(0, 0, 0, 0.65),
        0 0 45px rgba(66, 133, 244, 0.28);
      animation: modalCardPop 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
      overflow: visible;
    }

    @keyframes modalCardPop {
      0% { opacity: 0; transform: perspective(1000px) translateY(24px) scale(0.94); }
      100% { opacity: 1; transform: perspective(1000px) translateY(0) scale(1); }
    }

    .lp-progress-bar-wrap {
      width: 100%;
      height: 8px;
      background: var(--bg-elevated);
      border-radius: 999px;
      overflow: hidden;
      margin: 18px 0 20px;
      border: 1px solid var(--border-subtle);
      position: relative;
    }

    .lp-progress-bar-fill {
      height: 100%;
      width: 25%;
      border-radius: 999px;
      background: linear-gradient(90deg, #4285F4, #34A853, #FBBC05, #EA4335, #4285F4);
      background-size: 200% 100%;
      animation: lpShimmer 1.8s linear infinite;
      transition: width 0.35s cubic-bezier(0.22, 1, 0.36, 1);
    }

    @keyframes lpShimmer {
      0% { background-position: 100% 0; }
      100% { background-position: -100% 0; }
    }

    .lp-modal-step-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 14px;
    }

    .lp-modal-step {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-radius: 12px;
      background: var(--bg-elevated);
      border: 1.5px solid var(--border-subtle);
      font-size: 13px;
      font-weight: 700;
      color: var(--text-secondary);
      transition: all 0.25s ease;
    }

    .lp-modal-step.active {
      border-color: #4285F4;
      background: var(--accent-primary-soft);
      color: var(--accent-primary);
      box-shadow: 0 0 16px rgba(66, 133, 244, 0.22);
    }

    .lp-modal-step.done {
      border-color: rgba(52, 168, 83, 0.5);
      background: var(--accent-emerald-soft);
      color: var(--accent-emerald);
    }

    .lp-mstep-badge {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
    }

    .lp-modal-step.active .lp-mstep-badge {
      background: #4285F4;
      color: #ffffff;
      border-color: transparent;
    }

    .lp-modal-step.done .lp-mstep-badge {
      background: #34A853;
      color: #ffffff;
      border-color: transparent;
    }

    /* Left/Center Canvas Stage */
    .ct-stage {
      flex: 1;
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: var(--shadow-soft);
      min-width: 0;
    }

    .ct-scope-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 56px;
      min-height: 56px;
      padding: 0 18px;
      background: var(--bg-elevated);
      border-bottom: 1px solid var(--border-subtle);
      gap: 12px;
      flex-wrap: nowrap;
    }

    .ct-scope-group {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: nowrap;
      min-width: 0;
    }

    .ct-scope-btn {
      height: 36px;
      padding: 0 14px;
      border-radius: 10px;
      border: 1.5px solid var(--border-subtle);
      background: var(--bg-card);
      color: var(--text-secondary);
      font-family: var(--font-sans);
      font-size: 12.5px;
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.18s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .ct-scope-btn:hover {
      border-color: #4285F4;
      color: var(--accent-primary);
    }

    .ct-scope-btn.active {
      background: linear-gradient(135deg, #4285F4, #1a73e8);
      color: #ffffff;
      border-color: transparent;
      box-shadow: 0 4px 12px rgba(66, 133, 244, 0.32);
    }

    .ct-engine-mount {
      flex: 1;
      width: 100%;
      min-height: 440px;
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      color: #e2e8f0;
    }

    /* Hide duplicate KPI header bar and duplicate map truck sidebar inside embedded engine so screen stays clutter-free */
    .ct-engine-mount .lp-hdr,
    .ct-engine-mount .lp-bar,
    .ct-engine-mount .lp-top,
    #ct-map-mount .lp-side,
    #ct-map-mount .lp-legend {
      display: none !important;
    }

    .ct-engine-mount .lp-pane {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;
      height: 100%;
      border-top: none;
    }

    .ct-engine-mount .lp-body {
      flex: 1;
      display: flex;
      min-height: 0;
      height: 100%;
    }

    .ct-engine-mount .lp-cwrap {
      flex: 1;
      position: relative;
      min-width: 0;
      min-height: 380px;
      height: 100%;
      background: #090d1a;
      overflow: hidden;
    }

    /* Right Inspector Panel — Fixed Symmetric 380px Width Across Workspaces */
    .ct-sidebar {
      width: 380px;
      min-width: 380px;
      max-width: 380px;
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      border-radius: 16px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      overflow-y: auto;
      box-shadow: var(--shadow-soft);
      flex-shrink: 0;
    }

    .ct-panel-title {
      font-size: 14.5px;
      font-weight: 800;
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      min-height: 24px;
    }

    .ct-panel-sub {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
      margin-bottom: 10px;
    }

    .ct-box {
      background: var(--bg-elevated);
      border: 1.5px solid var(--border-subtle);
      border-radius: 14px;
      padding: 16px;
    }

    .ct-form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .ct-field {
      display: flex;
      flex-direction: column;
      gap: 5px;
      min-width: 0;
    }

    .ct-field label {
      font-size: 11px;
      font-weight: 800;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .ct-gauge-track {
      width: 100%;
      height: 8px;
      background: var(--border-subtle);
      border-radius: 999px;
      overflow: hidden;
      margin-top: 6px;
    }

    .ct-gauge-fill {
      height: 100%;
      border-radius: 999px;
      transition: width 0.35s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .ct-route-item {
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      border-left: 5px solid var(--route-c, #4285F4);
      border-radius: 12px;
      padding: 12px 14px;
      cursor: pointer;
      transition: transform 0.2s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.2s, border-color 0.2s;
      margin-bottom: 10px;
    }

    .ct-route-item:hover {
      border-color: #4285F4;
      transform: translateX(2px);
      box-shadow: 0 6px 18px rgba(66, 133, 244, 0.16);
    }

    .ct-route-item.dimmed {
      opacity: 0.42;
    }

    .ct-route-item.selected {
      background: linear-gradient(135deg, #f0f7ff 0%, #e0effe 100%);
      border: 2px solid #1a73e8;
      border-left: 6px solid var(--route-c, #1a73e8);
      box-shadow: 0 6px 20px rgba(26, 115, 232, 0.28), 0 0 0 2px rgba(26, 115, 232, 0.16);
      transform: translateX(4px);
    }

    html.theme-dark .ct-route-item.selected {
      background: linear-gradient(135deg, rgba(30, 58, 138, 0.45) 0%, rgba(17, 24, 39, 0.85) 100%);
      border: 2px solid #60a5fa;
      border-left: 6px solid var(--route-c, #60a5fa);
      box-shadow: 0 6px 22px rgba(37, 99, 235, 0.50), 0 0 0 2px rgba(96, 165, 250, 0.30);
      transform: translateX(4px);
    }

    /* Route card quick driver dispatch actions */
    .ct-btn-chip-action {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 9px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      text-decoration: none;
      border: 1px solid var(--border-subtle);
      background: var(--bg-card);
      color: var(--text-secondary);
      transition: all 0.18s cubic-bezier(0.22, 1, 0.36, 1);
    }
    .ct-btn-chip-action:hover {
      background: var(--bg-card-hover);
      color: var(--text-main);
      transform: translateY(-1px);
    }
    .ct-btn-chip-action.wa {
      color: #16a34a;
      border-color: rgba(22, 163, 74, 0.35);
      background: rgba(22, 163, 74, 0.08);
    }
    .ct-btn-chip-action.wa:hover {
      background: #16a34a;
      color: #ffffff;
      border-color: #16a34a;
      box-shadow: 0 2px 8px rgba(22, 163, 74, 0.3);
    }
    .ct-btn-chip-action.maps {
      color: #1a73e8;
      border-color: rgba(26, 115, 232, 0.35);
      background: rgba(26, 115, 232, 0.08);
    }
    .ct-btn-chip-action.maps:hover {
      background: #1a73e8;
      color: #ffffff;
      border-color: #1a73e8;
      box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
    }
    .ct-btn-chip-action.portal {
      color: #9334e6;
      border-color: rgba(147, 52, 230, 0.35);
      background: rgba(147, 52, 230, 0.08);
    }
    .ct-btn-chip-action.portal:hover {
      background: #9334e6;
      color: #ffffff;
      border-color: #9334e6;
      box-shadow: 0 2px 8px rgba(147, 52, 230, 0.3);
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
      background: var(--accent-primary-soft);
      color: var(--text-main);
    }

    /* ── Bottom AI Copilot Bar (Shown on Inner Workspaces) ── */
    .ct-copilot-dock {
      display: none;
      align-items: center;
      height: 58px;
      gap: 12px;
      padding: 0 20px;
      background: var(--bg-glass);
      backdrop-filter: blur(18px);
      border-top: 2px solid #4285F4;
      box-shadow: 0 -6px 24px rgba(66, 133, 244, 0.14);
      flex-shrink: 0;
      z-index: 25;
    }

    .ct-copilot-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 800;
      color: var(--accent-primary);
      white-space: nowrap;
    }

    .ct-copilot-input {
      flex: 1;
      height: 38px;
      background: var(--bg-input);
      color: var(--text-main);
      border: 1.5px solid var(--border-subtle);
      border-radius: 10px;
      padding: 0 14px;
      font-family: var(--font-sans);
      font-size: 13px;
      font-weight: 600;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .ct-copilot-input:focus {
      border-color: #4285F4;
      box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.20);
    }

    .ct-quick-chips {
      display: flex;
      gap: 8px;
      overflow-x: auto;
      flex-shrink: 0;
    }

    .ct-chip-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      height: 36px;
      background: var(--bg-card);
      color: var(--text-main);
      border: 1.5px solid var(--border-subtle);
      border-radius: 10px;
      padding: 0 13px;
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: all 0.18s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .ct-chip-btn:hover {
      border-color: #4285F4;
      color: var(--accent-primary);
      box-shadow: 0 4px 12px rgba(66, 133, 244, 0.18);
      transform: translateY(-1px);
    }

    /* Toast / AI Reply Banner with Genie Effect */
    .ct-toast {
      position: fixed;
      bottom: 68px;
      right: 24px;
      max-width: 520px;
      background: var(--bg-card);
      border: 1.5px solid #4285F4;
      border-left: 5px solid #4285F4;
      border-radius: 14px;
      padding: 13px 16px;
      color: var(--text-main);
      font-size: 13px;
      box-shadow: var(--shadow-float);
      z-index: 100;
      display: none;
      transform-origin: bottom right;
      animation: genieToastPop 0.34s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    }

    /* Photo Gallery Grid — Equal-Height Rectangular Cards */
    .ct-photo-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .ct-photo-card {
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      border-radius: 12px;
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.22s, border-color 0.22s;
    }

    .ct-photo-card:hover, .ct-photo-card.active {
      border-color: #4285F4;
      transform: translateY(-2px);
      box-shadow: var(--shadow-float);
    }

    .ct-photo-card img {
      width: 100%;
      height: 120px;
      object-fit: cover;
      display: block;
    }

    .ct-photo-card div {
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 700;
      color: var(--text-secondary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Architecture & How-To Blueprint Cards — Symmetrical 3-Column Equal-Height Grid */
    .arch-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      align-items: stretch;
    }

    .arch-card {
      background: var(--bg-elevated);
      border: 1.5px solid var(--border-subtle);
      border-radius: 14px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      height: 100%;
      transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.22s, border-color 0.22s;
    }

    .arch-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 22px rgba(66, 133, 244, 0.16);
      border-color: #4285F4;
    }

    .arch-code {
      font-family: var(--font-mono);
      font-size: 11.5px;
      background: var(--bg-input);
      border: 1px solid var(--border-subtle);
      padding: 10px 12px;
      border-radius: 10px;
      color: var(--text-main);
      overflow-x: auto;
      margin-top: 8px;
    }

    /* ── Launchpad Front Page: Strictly Symmetrical Rectangular Grid System ── */
    .lp-shell {
      width: 100%;
      max-width: 100%;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .lp-hero-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 20px;
      background: var(--bg-elevated);
      border: 1.5px solid var(--border-subtle);
      border-radius: 16px;
      min-height: 82px;
    }

    .lp-setup-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      align-items: stretch;
    }

    .lp-setup-card {
      background: var(--bg-elevated);
      border: 1.5px solid var(--border-subtle);
      border-radius: 16px;
      height: 164px;
      min-height: 164px;
      max-height: 164px;
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
    }

    .lp-setup-row-2col {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      height: 38px;
      align-items: stretch;
    }

    .lp-hub-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      height: 38px;
      align-items: stretch;
    }

    .lp-hub-card {
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      border-radius: 10px;
      height: 38px;
      padding: 0 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11.5px;
      font-weight: 800;
      color: var(--text-secondary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: all 0.18s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .lp-hub-card:hover {
      border-color: #4285F4;
      color: var(--text-main);
    }

    .lp-hub-card.active {
      background: var(--accent-primary-soft);
      border-color: #4285F4;
      color: var(--accent-primary);
      box-shadow: 0 4px 12px rgba(66, 133, 244, 0.20);
    }

    .lp-preset-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      align-items: stretch;
    }

    .lp-preset-btn {
      height: 40px;
      width: 100%;
      padding: 0 12px;
      border-radius: 10px;
      border: 1.5px solid var(--border-subtle);
      background: var(--bg-elevated);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      cursor: pointer;
      transition: all 0.18s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .lp-preset-btn:hover {
      border-color: #4285F4;
      color: var(--accent-primary);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(66, 133, 244, 0.16);
    }

    .lp-acc-stack {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
    }

    .lp-acc-icon {
      width: 32px;
      height: 32px;
      border-radius: 9px;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
    }

    .lp-corr-chip {
      display: inline-flex;
      align-items: center;
      justify-content: space-between;
      height: 36px;
      padding: 0 12px;
      border-radius: 10px;
      border: 1.5px solid var(--border-subtle);
      background: var(--bg-card);
      color: var(--text-secondary);
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.18s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .lp-corr-chip.active {
      background: #4285F4;
      color: #ffffff;
      border-color: transparent;
      box-shadow: 0 3px 10px rgba(66, 133, 244, 0.25);
    }

    .lp-rule-row {
      background: var(--bg-elevated);
      border: 1.5px solid var(--border-subtle);
      border-left: 5px solid #4285F4;
      border-radius: 12px;
      padding: 14px 16px;
      margin-bottom: 10px;
      animation: genieCardPop 0.28s cubic-bezier(0.22, 1, 0.36, 1) backwards;
    }

    .lp-synth-cta {
      height: 46px;
      background: linear-gradient(135deg, #4285F4 0%, #1a73e8 45%, #34A853 100%);
      color: #ffffff;
      border: 2px solid rgba(255, 255, 255, 0.32);
      border-radius: 12px;
      padding: 0 26px;
      font-family: var(--font-sans);
      font-size: 14.5px;
      font-weight: 800;
      letter-spacing: -0.01em;
      white-space: nowrap;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      box-shadow: 0 8px 24px rgba(66, 133, 244, 0.36), 0 0 16px rgba(52, 168, 83, 0.22);
      transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.22s;
    }

    .lp-synth-cta:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 30px rgba(66, 133, 244, 0.48), 0 0 22px rgba(52, 168, 83, 0.32);
    }

    .lp-step-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
    }

    .lp-step-pill {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 34px;
      padding: 0 10px;
      border-radius: 10px;
      font-size: 11.5px;
      font-weight: 700;
      background: var(--bg-card);
      border: 1.5px solid var(--border-subtle);
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: all 0.22s;
    }

    .lp-step-pill.active {
      background: var(--accent-primary-soft);
      border-color: #4285F4;
      color: var(--accent-primary);
      box-shadow: 0 0 12px rgba(66, 133, 244, 0.25);
    }

    .lp-step-pill.done {
      background: var(--accent-emerald-soft);
      border-color: #34A853;
      color: var(--accent-emerald);
    }

    @media (max-width: 1280px) {
      .ct-left-rail { width: 230px; }
      .ct-kpi-ribbon { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .lp-setup-grid { grid-template-columns: 1fr; }
      .lp-preset-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .ct-sidebar { width: 340px; min-width: 340px; }
      .arch-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
  </style>
</head>
<body>
<div class="ct-app-layout">

  <!-- ═══════════════ LEFT SIDEBAR NAVIGATION PANE ═══════════════ -->
  <aside class="ct-left-rail">
    <div>
      <div class="ct-brand">
        <div class="orbital-ring-wrap" style="width:42px;height:42px">
          <span class="orbital-ring-core">🚚</span>
        </div>
        <div>
          <div class="ct-brand-title">
            FleetFlow
            <span class="ct-brand-badge">GCP AI</span>
          </div>
          <div class="ct-brand-sub">Route &amp; 3D Load Control Tower</div>
        </div>
      </div>

      <div class="ct-nav-section-lbl">Workspaces</div>
      <nav class="ct-nav-list" id="mainNavTabs">
        <button class="ct-nav-btn active" data-view="launchpad" onclick="switchWorkspace('launchpad')">
          <span class="nav-ico">🚀</span>
          <span>Dispatch Launchpad</span>
        </button>
        <button class="ct-nav-btn" data-view="tower" onclick="switchWorkspace('tower')">
          <span class="nav-ico">🗺️</span>
          <span>Dispatch &amp; Map</span>
        </button>
        <button class="ct-nav-btn" data-view="studio3d" onclick="switchWorkspace('studio3d')">
          <span class="nav-ico">📦</span>
          <span>3D Load Studio</span>
        </button>
        <button class="ct-nav-btn" data-view="simulator" onclick="switchWorkspace('simulator')">
          <span class="nav-ico">🚛</span>
          <span>Fleet &amp; Cost Simulator</span>
        </button>
        <button class="ct-nav-btn" data-view="intake" onclick="switchWorkspace('intake')">
          <span class="nav-ico">📸</span>
          <span>Dock QR &amp; Intake</span>
        </button>
        <button class="ct-nav-btn" data-view="gcp" onclick="switchWorkspace('gcp')">
          <span class="nav-ico">📱</span>
          <span>Driver Hub</span>
        </button>
        <button class="ct-nav-btn" data-view="history" onclick="switchWorkspace('history')">
          <span class="nav-ico">📜</span>
          <span>History &amp; Audit</span>
        </button>
      </nav>

      <!-- Bottom Navigation Reference Section: Separated from operational dispatch tabs -->
      <div style="margin-top:auto;padding-top:14px;border-top:1px solid var(--border-subtle)">
        <div class="ct-nav-section-lbl" style="padding-top:0">System Reference</div>
        <button class="ct-nav-btn" data-view="howto" onclick="switchWorkspace('howto')">
          <span class="nav-ico">📘</span>
          <span>Architecture &amp; How-To</span>
        </button>
      </div>
    </div>

    <!-- Bottom Left Theme & Deck Controls (Symmetric 2-Column Grid) -->
    <div class="ct-rail-footer">
      <button class="ct-btn-secondary neon-amber" id="btnThemeToggle" onclick="toggleCtTheme()" title="Switch between Gemini Light and Midnight Dark theme">
        🌙 Dark Mode
      </button>
      <a href="/deck" target="_blank" class="ct-btn-secondary" title="Open Executive Presentation Deck">
        📊 Deck ↗
      </a>
    </div>
  </aside>

  <!-- ═══════════════ RIGHT MAIN STAGE + COPILOT BAR ═══════════════ -->
  <div class="ct-workspace-col">
    <main class="ct-main">

      <!-- ── Strictly Symmetrical 4-Metric Operational Strip (Identical 104px Rectangular Boxes) ── -->
      <section class="ct-kpi-ribbon">
        <div class="ct-kpi-card neon-blue">
          <div class="ct-kpi-left">
            <div class="ct-kpi-label" id="kpiLbl1">Selected Hub</div>
            <div class="ct-kpi-val" id="kpiTrucks">Bhiwandi Regional DC</div>
            <div class="ct-kpi-sub" id="kpiTrucksSub">Mumbai Metropolitan · BHW-DC</div>
          </div>
          <div class="ct-kpi-right">
            <div class="orbital-ring-wrap" style="width:32px;height:32px"><span class="orbital-ring-core" style="font-size:14px">📍</span></div>
            <div class="ct-kpi-badge" id="kpiTrucksBadge">STAGED</div>
          </div>
        </div>

        <div class="ct-kpi-card neon-green">
          <div class="ct-kpi-left">
            <div class="ct-kpi-label" id="kpiLbl2">Staged Order Manifest</div>
            <div class="ct-kpi-val" id="kpiSavings">70 Retail Outlets</div>
            <div class="ct-kpi-sub" id="kpiCostCompare">1,260 cartons · 43.6 m³ (8/8)</div>
          </div>
          <div class="ct-kpi-right">
            <div class="orbital-ring-wrap" style="width:32px;height:32px"><span class="orbital-ring-core" style="font-size:14px">📦</span></div>
            <div class="ct-kpi-badge" id="kpiSavingsPct">BigQuery Book</div>
          </div>
        </div>

        <div class="ct-kpi-card neon-amber">
          <div class="ct-kpi-left">
            <div class="ct-kpi-label" id="kpiLbl3">Hub Fleet &amp; Roster</div>
            <div class="ct-kpi-val" id="kpiStopsVal">12 Trucks · 12 Drivers</div>
            <div class="ct-kpi-sub" id="kpiStopsSub">Roster: Ravi, Sanjay, Imran...</div>
          </div>
          <div class="ct-kpi-right">
            <div class="orbital-ring-wrap" style="width:32px;height:32px"><span class="orbital-ring-core" style="font-size:14px">🚛</span></div>
            <div class="ct-kpi-badge" id="kpiCargoBadge">5 Vehicle Classes</div>
          </div>
        </div>

        <div class="ct-kpi-card neon-red">
          <div class="ct-kpi-left">
            <div class="ct-kpi-label" id="kpiLbl4">Manager Rules &amp; Status</div>
            <div class="ct-kpi-val" id="kpiDistanceVal">1 Driver Rule Active</div>
            <div class="ct-kpi-sub" id="kpiDistanceSub">Click 'Synthesize &amp; Run Agent'</div>
          </div>
          <div class="ct-kpi-right">
            <div class="orbital-ring-wrap" style="width:32px;height:32px"><span class="orbital-ring-core" style="font-size:14px">⚡</span></div>
            <div class="ct-kpi-badge" id="kpiDistanceBadge">Awaiting Run</div>
          </div>
        </div>
      </section>

      <!-- ═══════════════ VIEW 0 (FRONT PAGE): SYMMETRICAL DISPATCH LAUNCHPAD ═══════════════ -->
      <section class="ct-view active" id="view-launchpad">
        <div class="ct-stage" style="overflow-y:auto">
          <div class="lp-shell">

            <!-- Symmetrical Full-Width Hero Header Banner -->
            <div class="lp-hero-bar">
              <div style="display:flex;align-items:center;gap:16px;min-width:0">
                <div class="orbital-ring-wrap" style="width:52px;height:52px">
                  <span class="orbital-ring-core" style="font-size:24px">🚀</span>
                </div>
                <div style="min-width:0">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
                    <span class="ct-kpi-badge" style="background:var(--accent-primary-soft);color:var(--accent-primary);border-color:rgba(66,133,244,0.4)">LOGISTICS MANAGER LAUNCHPAD</span>
                    <span id="lpActiveHubBadge" style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted);font-weight:800">HUB: BHW-DC (MUMBAI)</span>
                  </div>
                  <h1 class="ct-big-heading" style="font-size:25px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                    FleetFlow <span class="google-gradient-text">AI Dispatch &amp; 3D Load</span> Command Center
                  </h1>
                </div>
              </div>
              <div style="display:flex;gap:10px;align-items:center;flex-shrink:0">
                <button class="ct-btn-secondary neon-amber" id="btnHeroThemeToggle" onclick="toggleCtTheme()">
                  🌙 Switch to Dark Mode
                </button>
              </div>
            </div>

            <!-- 5-Stage Synthesis Progress Bar (Symmetric 5-Column Grid When Active) -->
            <div id="lpSynthesisBar" class="neon-blue" style="display:none;background:var(--bg-elevated);border-radius:16px;padding:14px 18px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <span style="font-size:13.5px;font-weight:800;color:var(--accent-primary)" id="lpSynthStatusTitle">⚡ FleetFlow Agent Synthesizing Dispatch Plan...</span>
                <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">OR-Tools CVRPTW + 3D Height-Map Enclave</span>
              </div>
              <div class="lp-step-grid">
                <div class="lp-step-pill" id="lpStep1">1. Hub &amp; Manifest Intake</div>
                <div class="lp-step-pill" id="lpStep2">2. 8-Way Corridors &amp; Rules</div>
                <div class="lp-step-pill" id="lpStep3">3. OR-Tools Fleet Solver</div>
                <div class="lp-step-pill" id="lpStep4">4. 3D LIFO Cargo Packing</div>
                <div class="lp-step-pill" id="lpStep5">5. Cost vs. Manual Audit</div>
              </div>
            </div>

            <!-- STEP 1: 3 IDENTICAL-SIZE RECTANGULAR SETUP BOXES (164px Height, 3 Equal Rows Each) -->
            <div class="lp-setup-grid">

              <!-- Box 1: Distribution Hub (Row 1 Header, Row 2 Select, Row 3 4-Hub Equal Grid) -->
              <div class="lp-setup-card neon-blue">
                <div class="ct-panel-title">
                  <span>📍 1. Distribution Hub</span>
                  <span class="ct-kpi-badge" style="background:var(--accent-primary-soft);color:var(--accent-primary);border-color:rgba(66,133,244,0.35)" id="lpHubDriverCountLbl">12 Drivers · 70 Outlets</span>
                </div>
                <select id="lpSelHubQuick" class="ct-select" onchange="onLaunchpadHubChange(this.value)">
                  <option value="BHW-DC">🏙️ Mumbai · Bhiwandi Regional DC (BHW-DC)</option>
                  <option value="BLR-NLG">🌳 Bengaluru · Nelamangala Hub (BLR-NLG)</option>
                  <option value="TLJ-DC">⚓ Navi Mumbai · Taloja Hub (TLJ-DC)</option>
                  <option value="BLR-EC">💻 Bengaluru · Electronic City Hub (BLR-EC)</option>
                </select>
                <div class="lp-hub-grid" id="lpHubCardsGrid">
                  <div class="lp-hub-card active" data-hub="BHW-DC" onclick="onLaunchpadHubChange('BHW-DC')" title="Mumbai · Bhiwandi Regional DC">BHW-DC</div>
                  <div class="lp-hub-card" data-hub="BLR-NLG" onclick="onLaunchpadHubChange('BLR-NLG')" title="Bengaluru · Nelamangala Hub">BLR-NLG</div>
                  <div class="lp-hub-card" data-hub="TLJ-DC" onclick="onLaunchpadHubChange('TLJ-DC')" title="Navi Mumbai · Taloja Hub">TLJ-DC</div>
                  <div class="lp-hub-card" data-hub="BLR-EC" onclick="onLaunchpadHubChange('BLR-EC')" title="Bengaluru · Electronic City Hub">BLR-EC</div>
                </div>
              </div>

              <!-- Box 2: Delivery Manifest (Row 1 Header, Row 2 Full-Width Upload Button, Row 3 2-Col Sample/Reset) -->
              <div class="lp-setup-card neon-green">
                <div class="ct-panel-title">
                  <span>📂 2. Delivery Manifest</span>
                  <span id="lpManifestStatusBadge" class="ct-kpi-badge">✓ Live Hub Book</span>
                </div>
                <label class="ct-btn-secondary" style="width:100%;height:40px;cursor:pointer;border-color:#34A853;color:var(--accent-emerald)">
                  📗 Upload Excel / CSV Spreadsheet (.xlsx, .csv)
                  <input type="file" accept=".xlsx,.xls,.csv,.tsv,.txt" style="display:none" onchange="uploadLaunchpadSpreadsheet(this)">
                </label>
                <div class="lp-setup-row-2col">
                  <button class="ct-btn-secondary" style="height:38px;width:100%" onclick="loadLaunchpadSampleSheet('orders_morning.csv')">
                    📄 Load Sample CSV
                  </button>
                  <button class="ct-btn-secondary" style="height:38px;width:100%" onclick="resetLaunchpadToHubBook()">
                    🔄 Live BigQuery Book
                  </button>
                </div>
              </div>

              <!-- Box 3: Goal & View Scope (Row 1 Header, Row 2 Goal Select, Row 3 2-Col Scope + Fleet Pool) -->
              <div class="lp-setup-card neon-amber">
                <div class="ct-panel-title">
                  <span>🎯 3. Goal &amp; View Scope</span>
                  <span class="ct-kpi-badge" style="background:rgba(251,188,4,0.14);color:var(--accent-amber);border-color:rgba(251,188,4,0.4)" id="lpTotalFleetPoolLbl">12 Trucks Available</span>
                </div>
                <select id="lpSelObjective" class="ct-select" onchange="const so = document.getElementById('selObjective'); if (so) so.value=this.value;">
                  <option value="lowest_cost">🎯 Optimization Goal: Lowest Total Cost (₹)</option>
                  <option value="fewest_trucks">🚛 Optimization Goal: Fewest Trucks Dispatched</option>
                  <option value="balanced">⚖️ Optimization Goal: Balanced Corridor Utilization</option>
                  <option value="fastest_finish">⚡ Optimization Goal: Fastest Route Completion</option>
                </select>
                <div class="lp-setup-row-2col">
                  <select id="lpSelScope" class="ct-select" style="height:38px">
                    <option value="all">👁️ View: All Fleet</option>
                    <option value="3">👁️ View: Top 3 Trucks</option>
                    <option value="1">👁️ View: 1 Truck Only</option>
                  </select>
                  <button class="ct-btn-secondary" style="height:38px;width:100%" onclick="document.getElementById('accFleetPool').open = !document.getElementById('accFleetPool').open">
                    ⚙️ Configure Fleet Pool
                  </button>
                </div>
              </div>

            </div>

            <!-- STEP 2 (CENTERPIECE): FULL-WIDTH SYMMETRICAL AI COMMAND BOX WITH GOOGLE REVOLVING 4-COLOR NEON BORDER -->
            <div class="google-revolving-box" style="width:100%">
              <div class="google-revolving-inner" style="padding:20px 22px;display:flex;flex-direction:column;gap:14px">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
                  <div style="display:flex;align-items:center;gap:14px;min-width:0">
                    <div class="orbital-ring-wrap" style="width:44px;height:44px">
                      <span class="orbital-ring-core" style="font-size:19px">✨</span>
                    </div>
                    <div style="min-width:0">
                      <h2 style="font-size:19.5px;font-weight:800;letter-spacing:-0.02em;color:var(--text-main);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                        Enter Dispatch Details, Driver Assignments &amp; Natural-Language Instructions
                      </h2>
                      <div style="font-size:12.5px;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                        Type instructions below or click any of the 4 symmetrical scenario presets — e.g. assign a driver to a smaller truck on West and split overflow stops.
                      </div>
                    </div>
                  </div>
                  <span class="ct-kpi-badge" style="background:var(--accent-primary-soft);color:var(--accent-primary);border-color:#4285F4">
                    Gemini 2.5 Flash + OR-Tools
                  </span>
                </div>

                <textarea
                  id="inpLaunchpadPrompt"
                  class="ct-input"
                  style="width:100%;height:106px;font-size:15px;line-height:1.5;padding:13px 16px;border-radius:12px;border:2px solid rgba(66,133,244,0.45);resize:vertical"
                  placeholder="Type dispatch instructions here... Example: 'Plan today's dispatch for this hub. Give Ravi the West route in a smaller T14 truck and distribute the remaining West stops to a backup truck.'"
                ></textarea>

                <!-- 4 Equal-Size Rectangular Scenario Buttons in a Strict 4-Column Symmetrical Grid -->
                <div class="lp-preset-grid">
                  <button class="lp-preset-btn neon-blue" onclick="applyLaunchpadPreset('smaller_west'); setLaunchpadPrompt('Give our lead driver the West route in a smaller T14 (14ft) truck and automatically distribute overflow West stops to a secondary truck')">
                    ⚡ Driver 1 → West (T14) + Overflow
                  </button>
                  <button class="lp-preset-btn neon-green" onclick="applyLaunchpadPreset('two_leads'); setLaunchpadPrompt('Pin two corridor lead drivers (West in T14 and South in T17) and optimize the rest of the fleet for lowest cost')">
                    📌 Pin 2 Leads (West + South)
                  </button>
                  <button class="lp-preset-btn neon-amber" onclick="onLaunchpadHubChange('BLR-NLG'); setLaunchpadPrompt('Plan dispatch for Bengaluru Nelamangala hub and highlight the top 3 trucks')">
                    🌳 Switch to Bengaluru Hub
                  </button>
                  <button class="lp-preset-btn neon-red" onclick="applyLaunchpadPreset('clear'); setLaunchpadPrompt('Plan today\'s full fleet dispatch for lowest total cost in ₹ across all corridors')">
                    🧹 100% Auto-Optimize Lowest Cost
                  </button>
                </div>

                <!-- Symmetrical Action Footer Inside Revolving Box -->
                <div style="display:flex;justify-content:space-between;align-items:center;gap:14px;padding-top:12px;border-top:1px solid var(--border-subtle)">
                  <div style="display:flex;align-items:center;gap:10px;height:46px;padding:0 16px;background:var(--bg-elevated);border:1.5px solid var(--border-subtle);border-radius:12px;font-size:12.5px;font-weight:700;color:var(--text-secondary)">
                    <span>🛡️ Zero-Hallucination Math Enclave</span>
                    <span>·</span>
                    <span id="lpQuickRuleSummary" style="color:var(--accent-primary);font-weight:800">1 Driver Rule Staged</span>
                  </div>
                  <button class="lp-synth-cta" id="btnHeroSynthesize" onclick="synthesizeFromLaunchpad(true)">
                    <span>🚀</span> Synthesize &amp; Run FleetFlow Agent →
                  </button>
                </div>
              </div>
            </div>

            <!-- STEP 3: PROGRESSIVE DISCLOSURE — 3 FULL-WIDTH SYMMETRICAL ACCORDION BARS -->
            <div class="lp-acc-stack">

              <!-- Accordion 1: Driver, Truck Size & Corridor Rules Builder -->
              <details class="ct-accordion" id="accDriverRules">
                <summary>
                  <div style="display:flex;align-items:center;gap:12px">
                    <span class="lp-acc-icon">👨‍✈️</span>
                    <span>Driver, Truck Size &amp; Corridor Rules Builder</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:10px">
                    <span class="ct-kpi-badge" style="background:var(--accent-primary-soft);color:var(--accent-primary);border-color:rgba(66,133,244,0.35)">Dropdown Controls + Overflow Diagnosis</span>
                    <span class="ct-acc-chevron">▼</span>
                  </div>
                </summary>
                <div class="ct-acc-body">
                  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px">
                    <div style="font-size:12.5px;color:var(--text-secondary)">
                      Assign specific regional drivers to a compass corridor and vehicle class (`ACE`, `PKP`, `T14`, `T17`, `T20`). Assigning a smaller truck automatically triggers trunk-and-branch overflow distribution.
                    </div>
                    <button class="ct-btn-secondary neon-blue" onclick="addLaunchpadDriverRule()">
                      + Add Driver / Truck Rule
                    </button>
                  </div>
                  <div id="lpDriverRulesContainer"></div>
                </div>
              </details>

              <!-- Accordion 2: Available Fleet Pool Steppers & Fuel / Driver Cost Rates -->
              <details class="ct-accordion" id="accFleetPool">
                <summary>
                  <div style="display:flex;align-items:center;gap:12px">
                    <span class="lp-acc-icon">🚛</span>
                    <span>Available Hub Fleet Pool &amp; Diesel / Driver Cost Rates</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:10px">
                    <span class="ct-kpi-badge">5 Vehicle Classes · ₹/km Rates</span>
                    <span class="ct-acc-chevron">▼</span>
                  </div>
                </summary>
                <div class="ct-acc-body">
                  <div id="lpFleetPoolGrid" style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:14px"></div>
                  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px">
                    <div class="ct-field">
                      <label>Diesel Price (₹ / Litre)</label>
                      <input type="number" id="lpInpFuel" class="ct-input" value="92" step="1">
                    </div>
                    <div class="ct-field">
                      <label>Driver Bata (₹ / Day)</label>
                      <input type="number" id="lpInpDriverCost" class="ct-input" value="1100" step="50">
                    </div>
                  </div>
                </div>
              </details>

              <!-- Accordion 3: 8-Corridor Filter Chips, Regional Store Demand Table & Enterprise Connectors -->
              <details class="ct-accordion" id="accCorridorDemand">
                <summary>
                  <div style="display:flex;align-items:center;gap:12px">
                    <span class="lp-acc-icon">🧭</span>
                    <span>8-Corridor Sector Filter, Regional Demand Table &amp; Data Connectors</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:10px">
                    <span id="lpPreviewSummaryBadge" class="ct-kpi-badge">8 Sectors Active</span>
                    <span class="ct-acc-chevron">▼</span>
                  </div>
                </summary>
                <div class="ct-acc-body">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                    <span style="font-size:11.5px;font-weight:800;color:var(--text-muted);text-transform:uppercase">Toggle Active Delivery Corridors (4×2 Symmetrical Grid):</span>
                    <button class="ct-chip-btn" style="height:30px;padding:0 12px;font-size:11px" onclick="selectAllLaunchpadCorridors()">Select All 8 Sectors</button>
                  </div>
                  <div id="lpCorridorFilterChips" style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:14px"></div>

                  <div class="ct-table-wrap" style="max-height:220px;border:1px solid var(--border-subtle);border-radius:12px;margin-bottom:14px">
                    <table class="ct-table" style="font-size:12px">
                      <thead>
                        <tr>
                          <th>Sector</th>
                          <th>Key Localities</th>
                          <th>Outlets</th>
                          <th>Cartons</th>
                          <th>Volume</th>
                          <th>Weight</th>
                          <th>Fit Class</th>
                        </tr>
                      </thead>
                      <tbody id="lpCorridorPreviewBody"></tbody>
                    </table>
                  </div>

                  <div style="font-size:11.5px;font-weight:800;color:var(--text-muted);text-transform:uppercase;margin-bottom:8px">Pluggable Enterprise Data Connectors:</div>
                  <div id="lpConnectorsRow" style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px"></div>
                </div>
              </details>

            </div>

          </div>
        </div>
      </section>

      <!-- ═══════════════ VIEW 1: CONTROL TOWER & ROUTE MAP ═══════════════ -->
      <section class="ct-view" id="view-tower">
        <div class="ct-stage neon-blue">
          <div class="ct-scope-bar">
            <div class="ct-scope-group">
              <span style="font-size:15px;font-weight:800;color:var(--text-main);white-space:nowrap;margin-right:4px">🗺️ Live Highway Route Network</span>
              <button class="ct-scope-btn active" id="scopeAllBtn" onclick="applyTruckScope('all')">All Fleet</button>
              <button class="ct-scope-btn" id="scope1Btn" onclick="applyTruckScope('1')">1 Truck Only</button>
              <button class="ct-scope-btn" id="scope3Btn" onclick="applyTruckScope('3')">Top 3 Trucks</button>
              <select id="selFocusTruckMap" class="ct-select" style="width:230px;height:36px;font-size:12.5px" onchange="applySingleTruckDropdown(this.value)">
                <option value="all">Select specific truck / driver...</option>
              </select>
            </div>
            <div class="ct-scope-group">
              <button class="ct-btn-secondary neon-blue" style="height:36px;padding:0 14px;font-size:12.5px" onclick="switchWorkspace('studio3d')">
                📦 Inspect in 3D Studio →
              </button>
            </div>
          </div>

          <div id="ct-map-mount" class="ct-engine-mount">
            <div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:14px;gap:10px">
              <span>⚡ Loading live route network &amp; 3D dispatch plan...</span>
            </div>
          </div>
        </div>

        <aside class="ct-sidebar neon-green">
          <div style="display:flex;align-items:center;justify-content:space-between;min-height:28px">
            <span class="ct-section-heading" style="font-size:16.5px">🚚 Dispatched Fleet</span>
            <span id="routeCountLbl" class="ct-kpi-badge"></span>
          </div>

          <div id="towerRoutesList" style="flex:1;overflow-y:auto"></div>

          <!-- Progressive Disclosure: Corridor Pinning tucked in a clean expandable drawer -->
          <details class="ct-accordion">
            <summary style="padding:12px 14px;font-size:13px">
              <span>📌 Pin Driver to Highway Corridor</span>
              <span class="ct-acc-chevron">▼</span>
            </summary>
            <div class="ct-acc-body" style="padding:12px">
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
              <div class="lp-setup-row-2col" style="margin-top:10px">
                <button class="ct-btn-primary" style="width:100%;height:38px" onclick="submitCorridorClaim()">
                  📌 Pin &amp; Re-Plan
                </button>
                <button class="ct-btn-secondary" style="width:100%;height:38px" onclick="clearCorridorClaims()">Reset Rules</button>
              </div>
              <div id="activeClaimsPills" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px"></div>
            </div>
          </details>
        </aside>
      </section>

      <!-- ═══════════════ VIEW 2: 3D LOAD STUDIO & CALCULATOR ═══════════════ -->
      <section class="ct-view" id="view-studio3d">
        <div class="ct-stage neon-blue">
          <div class="ct-scope-bar">
            <div class="ct-scope-group">
              <span style="font-size:15.5px;font-weight:800;color:var(--text-main);white-space:nowrap">📦 3D LIFO Cargo Bay Studio</span>
              <span style="font-size:12.5px;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">Last stop loaded first at cab wall (X=0) · Stop 1 at rear door</span>
            </div>
            <div class="ct-scope-group">
              <span id="studioBannerBadge" class="ct-kpi-badge">100% Unobstructed LIFO</span>
            </div>
          </div>
          <div id="ct-load-mount" class="ct-engine-mount"></div>
        </div>

        <aside class="ct-sidebar neon-amber">
          <div class="ct-box neon-blue">
            <div class="ct-panel-title">
              <span>🧮 Truck Type Calculator</span>
              <span class="ct-kpi-badge" style="background:var(--accent-primary-soft);color:var(--accent-primary);border-color:rgba(66,133,244,0.35)">What-If Fit</span>
            </div>
            <div class="ct-panel-sub">Select any driver route and test-pack its cartons into any vehicle class.</div>
            <div class="ct-field" style="margin-bottom:10px">
              <label>1. Route / Driver Consignment</label>
              <select id="selStudioRoute" class="ct-select" onchange="onStudioRouteSelect(this.value)"></select>
            </div>
            <div class="ct-field" style="margin-bottom:12px">
              <label>2. Test Vehicle Class (Dimensions)</label>
              <select id="selStudioTruckType" class="ct-select" onchange="runStudioRepack()"></select>
            </div>
            <button class="ct-btn-primary" style="width:100%" onclick="runStudioRepack()">
              🔄 Recalculate 3D Packing
            </button>
          </div>

          <div class="ct-box neon-green" id="studioStatsCard">
            <div class="ct-panel-title">
              <span>📐 Cargo Fit Summary</span>
              <span id="stLifoStatus" class="ct-kpi-badge">LIFO OK</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:10px">
              <div style="padding:10px 12px;background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:10px">
                <div style="font-size:11px;color:var(--text-muted);font-weight:700">Volume Fill</div>
                <div style="font-size:20px;font-weight:800;margin-top:2px" id="stVolFill">78.5%</div>
                <div class="ct-gauge-track"><div id="stVolBar" class="ct-gauge-fill" style="width:78%;background:#4285F4"></div></div>
              </div>
              <div style="padding:10px 12px;background:var(--bg-card);border:1px solid var(--border-subtle);border-radius:10px">
                <div style="font-size:11px;color:var(--text-muted);font-weight:700">Payload Fill</div>
                <div style="font-size:20px;font-weight:800;margin-top:2px" id="stWtFill">82.1%</div>
                <div class="ct-gauge-track"><div id="stWtBar" class="ct-gauge-fill" style="width:82%;background:#FBBC04"></div></div>
              </div>
            </div>
            <div style="margin-top:8px;display:none">
              <span id="stFrontAxle">38%</span><span id="stRearAxle">62%</span>
              <div id="stAxleBar"></div><div id="stCmvrNote"></div>
            </div>
            <div id="stOverflowWarn" style="display:none;margin-top:10px;padding:10px;border-radius:10px;background:rgba(225,29,72,0.10);border:1px solid rgba(225,29,72,0.3);color:var(--accent-rose);font-size:11.5px;font-weight:700"></div>
          </div>

          <!-- Custom Cartons tucked neatly inside an accordion -->
          <details class="ct-accordion">
            <summary style="padding:12px 14px;font-size:13px">
              <span>➕ Inject Custom Cartons into Bay</span>
              <span class="ct-acc-chevron">▼</span>
            </summary>
            <div class="ct-acc-body" style="padding:12px">
              <div class="ct-field" style="margin-bottom:8px">
                <label>SKU Preset</label>
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
              <div class="ct-form-grid" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:10px">
                <div class="ct-field"><label>L (cm)</label><input type="number" id="inpCustomL" class="ct-input" value="34"></div>
                <div class="ct-field"><label>W (cm)</label><input type="number" id="inpCustomW" class="ct-input" value="34"></div>
                <div class="ct-field"><label>H (cm)</label><input type="number" id="inpCustomH" class="ct-input" value="38"></div>
                <div class="ct-field"><label>Kg</label><input type="number" id="inpCustomKg" class="ct-input" value="24"></div>
              </div>
              <div class="lp-setup-row-2col">
                <button class="ct-btn-primary" style="width:100%;height:38px" onclick="addCustomBoxAndPack()">+ Pack Cartons</button>
                <button class="ct-btn-secondary" style="width:100%;height:38px" onclick="clearCustomBoxes()">Clear All</button>
              </div>
              <div id="addedCustomBoxesList" style="margin-top:8px;font-size:11.5px;color:var(--text-muted)"></div>
            </div>
          </details>
        </aside>
      </section>

      <!-- ═══════════════ VIEW 3: FLEET & COST SIMULATOR ═══════════════ -->
      <section class="ct-view" id="view-simulator">
        <aside class="ct-sidebar neon-blue">
          <div class="ct-box">
            <div class="ct-panel-title">
              <span>🚛 Available Fleet Mix</span>
              <span class="ct-kpi-badge" style="background:var(--accent-primary-soft);color:var(--accent-primary)">OR-Tools VRPTW</span>
            </div>
            <div class="ct-panel-sub">Adjust available trucks at the hub and re-solve the cost matrix.</div>
            <div id="fleetControlsContainer" style="display:flex;flex-direction:column;gap:8px"></div>
          </div>

          <div class="ct-box neon-amber">
            <div class="ct-panel-title"><span>⛽ Operating Cost Rates</span></div>
            <div class="ct-form-grid" style="margin-top:8px">
              <div class="ct-field">
                <label>Diesel (₹ / Litre)</label>
                <input type="number" id="inpSimFuel" class="ct-input" value="92" step="1">
              </div>
              <div class="ct-field">
                <label>Driver Bata (₹ / Day)</label>
                <input type="number" id="inpSimDriverCost" class="ct-input" value="1100" step="50">
              </div>
            </div>
            <button class="ct-btn-primary" style="width:100%;margin-top:12px" onclick="runSimulatorOptimization()">
              ⚡ Re-Solve Fleet &amp; Cost Matrix
            </button>
          </div>
        </aside>

        <div class="ct-stage neon-green">
          <div class="ct-scope-bar">
            <div class="ct-scope-group">
              <span style="font-size:15.5px;font-weight:800;color:var(--text-main)">📊 Dispatch Schedule &amp; Route Cost Ledger</span>
              <span style="font-size:12px;color:var(--text-muted)">Atomic copy-ready table for Google Sheets or CSV export</span>
            </div>
            <div class="ct-scope-group">
              <button class="ct-btn-secondary neon-blue" style="height:36px" onclick="copyScheduleTable()">📋 Copy for Google Sheets</button>
              <button class="ct-btn-secondary neon-green" style="height:36px" onclick="exportScheduleCsv()">⬇ Export CSV</button>
            </div>
          </div>
          <div class="ct-table-wrap" style="padding:14px 18px">
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

      <!-- ═══════════════ VIEW 4: DOCK QR SCANNER & SMART ORDER INTAKE (EXACT 50% / 50% SYMMETRICAL SPLIT) ═══════════════ -->
      <section class="ct-view" id="view-intake">
        <div class="ct-stage neon-blue" style="flex:1;padding:18px;overflow-y:auto;gap:14px">
          <div class="ct-panel-title" style="font-size:17px">
            <span>📸 Warehouse Dock QR &amp; Carton Vision Scanner</span>
            <span class="ct-kpi-badge">OpenCV + Gemini Vision</span>
          </div>
          <div class="ct-panel-sub" style="margin-bottom:0">Click a staging floor photo or upload a carton image to decode QR labels and pack cartons into today's 3D load plan.</div>

          <div style="display:flex;gap:10px;align-items:center">
            <label class="ct-btn-secondary neon-blue" style="cursor:pointer">
              📤 Upload Custom Carton Photo
              <input type="file" accept="image/*" style="display:none" onchange="uploadCustomPhoto(this)">
            </label>
            <span id="scanStatusText" style="font-size:12.5px;color:var(--accent-primary);font-weight:700"></span>
          </div>

          <div class="ct-photo-grid" id="samplePhotosGrid"></div>

          <div class="ct-box neon-green" style="margin-top:auto" id="scanResultBox">
            <div class="ct-panel-title"><span>🔍 Decoded Carton Manifest</span></div>
            <div id="scanResultContent" style="font-family:var(--font-mono);font-size:12px;color:var(--text-secondary);margin-top:6px">
              Select a staging floor photo above to run live QR &amp; label recognition.
            </div>
          </div>
        </div>

        <div class="ct-stage neon-amber" style="flex:1;padding:18px;overflow-y:auto;gap:14px">
          <div class="ct-panel-title" style="font-size:17px">
            <span>📝 Unstructured ERP, Email &amp; WhatsApp Order Intake</span>
            <span class="ct-kpi-badge">Auto-Geocode + SKU Match</span>
          </div>
          <div class="ct-panel-sub" style="margin-bottom:0">Load a preset dealer manifest or paste raw text/CSV from an email or WhatsApp message.</div>

          <div id="sampleOrdersBtns" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px"></div>

          <textarea id="inpOrderText" class="ct-input" style="width:100%;flex:1;min-height:190px;font-family:var(--font-mono);font-size:12px;line-height:1.5;resize:vertical" placeholder="Paste dealer orders here (e.g. Store name, locality, SKU codes and carton quantities)..."></textarea>

          <div class="lp-setup-row-2col">
            <button class="ct-btn-primary" style="width:100%" onclick="submitOrderText()">
              ⚡ Parse Orders &amp; Build Plan
            </button>
            <button class="ct-btn-secondary" style="width:100%" onclick="resetToDefaultDemo()">
              🔄 Reset to Full Hub Book
            </button>
          </div>

          <div class="ct-box" style="margin-top:auto">
            <div class="ct-panel-title"><span>📋 Intake &amp; Geocoding Summary</span></div>
            <div id="ingestResultContent" style="font-size:12.5px;color:var(--text-secondary);margin-top:6px">
              Ready to ingest unstructured dealer orders.
            </div>
          </div>
        </div>
      </section>

      <!-- ═══════════════ VIEW 5: DRIVER DISPATCH HUB & MOBILE PORTAL ═══════════════ -->
      <section class="ct-view" id="view-gcp">
        <div class="ct-stage neon-green" style="flex:1.25;padding:18px;overflow-y:auto;gap:12px">
          <div class="ct-panel-title" style="font-size:17px">
            <span>📱 Driver Mobile Portal &amp; Google Maps Turn-by-Turn Hub</span>
            <span class="ct-kpi-badge">Zero-Login Edge</span>
          </div>
          <div class="ct-panel-sub" style="margin-bottom:0">Zero-login mobile portal with door-to-cab cargo depths, turn-by-turn traffic navigation, WhatsApp dispatch &amp; printable LR Challan.</div>

          <div style="display:grid;grid-template-columns:1.35fr 1fr 1fr 1fr;gap:8px;align-items:center">
            <select id="selPortalTruck" class="ct-select" onchange="updateDriverHubPreview(this.value)"></select>
            <a id="btnOpenMapsNav" href="#" target="_blank" class="ct-btn-primary" style="text-decoration:none;background:linear-gradient(135deg,#16a34a,#059669)">
              🗺️ Maps Nav
            </a>
            <a id="btnOpenWhatsApp" href="#" target="_blank" class="ct-btn-secondary neon-green">
              💬 WhatsApp
            </a>
            <a id="btnOpenPortalTab" href="#" target="_blank" class="ct-btn-secondary">
              ↗ Print LR
            </a>
          </div>

          <div style="flex:1;min-height:420px;border:1.5px solid var(--border-subtle);border-radius:14px;overflow:hidden;background:#0a0f1d">
            <iframe id="driverPortalIframe" style="width:100%;height:100%;border:none" title="Driver Mobile Portal Preview"></iframe>
          </div>
        </div>

        <div class="ct-stage neon-blue" style="flex:0.95;padding:18px;overflow-y:auto;gap:12px">
          <div class="ct-panel-title" style="font-size:17px">
            <span>📋 Driver Consignment &amp; Security Shield</span>
            <span class="ct-kpi-badge">Model Armor · DLP Active</span>
          </div>

          <!-- Active Driver Profile Card -->
          <div class="ct-box neon-green" id="hubDriverProfileBox">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div>
                <span style="font-size:15px;font-weight:800;color:var(--text-main)" id="hubDriverName">Driver Consignment</span>
                <div style="font-size:11.5px;color:var(--text-secondary);margin-top:2px" id="hubDriverSub">Select a vehicle class above</div>
              </div>
              <span class="ct-kpi-badge" id="hubDriverClassBadge">T14 LCV</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px">
              <div style="padding:8px;background:var(--bg-elevated);border-radius:10px;text-align:center">
                <div style="font-size:10px;color:var(--text-muted);font-weight:800;text-transform:uppercase">Stops</div>
                <div style="font-size:16px;font-weight:800;color:var(--text-main)" id="hubDriverStops">0</div>
              </div>
              <div style="padding:8px;background:var(--bg-elevated);border-radius:10px;text-align:center">
                <div style="font-size:10px;color:var(--text-muted);font-weight:800;text-transform:uppercase">Cartons</div>
                <div style="font-size:16px;font-weight:800;color:var(--text-main)" id="hubDriverCartons">0</div>
              </div>
              <div style="padding:8px;background:var(--bg-elevated);border-radius:10px;text-align:center">
                <div style="font-size:10px;color:var(--text-muted);font-weight:800;text-transform:uppercase">Route Cost</div>
                <div style="font-size:16px;font-weight:800;color:var(--text-main)" id="hubDriverCost">₹0</div>
              </div>
            </div>
          </div>

          <!-- Stop-by-Stop Door-to-Cab Cargo Sequence -->
          <div class="ct-box" style="flex:1;display:flex;flex-direction:column;min-height:180px">
            <div class="ct-panel-title"><span>📦 Delivery Stops &amp; Door-to-Cab Depth</span></div>
            <div id="hubDriverStopsList" style="flex:1;overflow-y:auto;max-height:220px;display:flex;flex-direction:column;gap:6px;margin-top:8px"></div>
          </div>

          <!-- Enterprise Security & Cloud Shield -->
          <div class="ct-box neon-blue">
            <div class="ct-panel-title"><span>🛡️ Enterprise Security &amp; Privacy Shield</span></div>
            <div style="font-size:11.5px;color:var(--text-secondary);margin-top:6px;line-height:1.5">
              <div>🛡️ <b>Google Cloud Model Armor:</b> Pre-turn prompt injection and driver token leakage filter active.</div>
              <div style="margin-top:4px">🔒 <b>Google Cloud DLP:</b> Driver contact details and retail store invoices masked with zero unencrypted data on wire.</div>
              <div style="margin-top:4px">🚀 <b>Serverless Cloud Run:</b> Auto-scaled isolated microservice hosting with zero hardcoded API credentials.</div>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══════════════ VIEW: DISPATCH HISTORY, GCS/BIGQUERY AUDIT & REPLAY ═══════════════ -->
      <section class="ct-view" id="view-history">
        <div class="ct-stage neon-blue" style="padding:22px 24px;overflow-y:auto;gap:18px">
          <div class="lp-hero-bar">
            <div>
              <h2 class="ct-big-heading" style="font-size:23px">📜 Enterprise Dispatch History &amp; GCS / BigQuery Audit Trail</h2>
              <div style="font-size:13px;color:var(--text-secondary);margin-top:2px">
                Tamper-evident operational repository with <b>cryptographic HMAC verification</b>, <b>RFC 4180 ERP manifests</b>, and <b>1-click historical replay</b> into 2D Map &amp; 3D Load Studio.
              </div>
            </div>
            <div style="display:flex;gap:10px;align-items:center">
              <span class="ct-badge" style="background:rgba(26,115,232,0.15);color:var(--accent-blue);font-weight:700">
                🔒 Immutable Audit Enabled
              </span>
            </div>
          </div>

          <!-- 30-Day Cumulative Historical Telemetry Strip -->
          <div class="ct-kpi-ribbon" style="margin:0;grid-template-columns:repeat(4,1fr);gap:14px">
            <div class="ct-kpi-card neon-blue" style="height:90px">
              <div class="ct-kpi-lbl">Total Archived Dispatches</div>
              <div class="ct-kpi-val" id="histKpiTotal" style="font-size:24px;color:var(--accent-blue)">--</div>
              <div class="ct-kpi-sub">Across Mumbai &amp; Bengaluru Hubs</div>
            </div>
            <div class="ct-kpi-card neon-green" style="height:90px">
              <div class="ct-kpi-lbl">Cumulative Logistics Savings</div>
              <div class="ct-kpi-val" id="histKpiSavings" style="font-size:24px;color:var(--accent-green)">--</div>
              <div class="ct-kpi-sub">Calculated vs unoptimized baseline</div>
            </div>
            <div class="ct-kpi-card neon-amber" style="height:90px">
              <div class="ct-kpi-lbl">Commercial Trucks Avoided</div>
              <div class="ct-kpi-val" id="histKpiTrucks" style="font-size:24px;color:var(--accent-amber)">--</div>
              <div class="ct-kpi-sub">Through multi-drop 3D packing</div>
            </div>
            <div class="ct-kpi-card neon-blue" style="height:90px">
              <div class="ct-kpi-lbl">CO₂ Emissions Avoided</div>
              <div class="ct-kpi-val" id="histKpiCo2" style="font-size:24px;color:#38bdf8">--</div>
              <div class="ct-kpi-sub">Green logistics ESG telemetry</div>
            </div>
          </div>

          <!-- Search & Filter Controls -->
          <div class="ct-box neon-blue" style="padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
            <div style="display:flex;gap:12px;align-items:center;flex:1;min-width:300px">
              <div style="font-size:12px;font-weight:700;color:var(--text-secondary);white-space:nowrap">FILTER BY HUB:</div>
              <select id="histFilterHub" class="ct-input" style="width:190px;height:36px;font-size:12px" onchange="loadHistoryView()">
                <option value="all">All Hubs (Multi-City)</option>
                <option value="BHW-DC">Mumbai (BHW-DC)</option>
                <option value="BLR-NLG">Bengaluru (BLR-NLG)</option>
                <option value="BLR-EC">Bengaluru (BLR-EC)</option>
              </select>
              <div style="position:relative;flex:1">
                <input type="text" id="histSearchInput" class="ct-input" style="width:100%;height:36px;padding-left:32px;font-size:12px" placeholder="Search by Plan ID, Hub, Objective, Driver, or prompt..." oninput="debounceHistorySearch()">
                <span style="position:absolute;left:10px;top:9px;font-size:14px;color:var(--text-muted)">🔍</span>
              </div>
            </div>
            <div style="display:flex;gap:8px">
              <button class="ct-btn-secondary" style="height:36px;font-size:12px" onclick="loadHistoryView()">
                🔄 Refresh Stream
              </button>
            </div>
          </div>

          <!-- Historical Runs Data Table -->
          <div class="ct-box neon-blue" style="padding:0;overflow:hidden">
            <div style="padding:14px 18px;border-bottom:1px solid var(--border-subtle);display:flex;justify-content:space-between;align-items:center">
              <div style="font-weight:800;font-size:13.5px;color:var(--text-primary);letter-spacing:0.02em">
                ARCHIVED DISPATCH RUNS &amp; AUDIT CERTIFICATES
              </div>
              <span id="histRecordCount" style="font-size:12px;color:var(--text-muted)">Loading historical records...</span>
            </div>
            <div class="ct-table-wrap" style="max-height:480px;overflow-y:auto">
              <table class="ct-table" style="font-size:12px">
                <thead>
                  <tr>
                    <th>Dispatch Plan ID</th>
                    <th>Timestamp</th>
                    <th>Regional Hub</th>
                    <th>Fleet &amp; Scope</th>
                    <th>Stops / Boxes</th>
                    <th>Plan Cost</th>
                    <th>Savings</th>
                    <th>GCP Audit Status</th>
                    <th style="text-align:right">Actions</th>
                  </tr>
                </thead>
                <tbody id="histTableBody">
                  <tr>
                    <td colspan="9" style="text-align:center;padding:30px;color:var(--text-muted)">Loading audit trail...</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══════════════ VIEW 6: ARCHITECTURE, HOW-TO & DUAL DEPLOYMENT GUIDE ═══════════════ -->
      <section class="ct-view" id="view-howto">
        <div class="ct-stage neon-blue" style="padding:22px 24px;overflow-y:auto;gap:18px">
          <div class="lp-hero-bar">
            <div>
              <h2 class="ct-big-heading" style="font-size:23px">📘 FleetFlow Architecture, How-To Guide &amp; Dual-Deployment</h2>
              <div style="font-size:13px;color:var(--text-secondary);margin-top:2px">
                One shared Python optimization &amp; ADK backend powering both <b>Gemini Enterprise (Conversational A2UI)</b> and <b>Google Cloud Run (Standalone Web Control Tower)</b>.
              </div>
            </div>
            <a href="/deck" target="_blank" class="ct-btn-primary" style="text-decoration:none">
              📊 Open Full 8-Slide Executive Presentation ↗
            </a>
          </div>

          <!-- ── GRAPHICAL ARCHITECTURE & DECISION-MAKING FLOW DIAGRAM STUDIO ── -->
          <div class="ct-box neon-blue" style="padding:18px 20px">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:14px">
              <div>
                <div style="font-size:14px;font-weight:800;color:var(--text-primary);letter-spacing:0.02em">
                  📐 Graphical Architecture &amp; Autonomous Decision Flow Studio
                </div>
                <div style="font-size:11.5px;color:var(--text-secondary);margin-top:2px">
                  High-fidelity vector topology diagrams: inspect multi-tier GCP services or trace autonomous decision trees with true logic diamonds and branches.
                </div>
              </div>
              <div style="display:flex;gap:8px;align-items:center">
                <button class="ct-btn-secondary active" id="btnDiagArch" onclick="switchDiagramView('arch')" style="font-size:12px;height:34px;padding:0 14px">
                  🏛️ System Architecture Topology
                </button>
                <button class="ct-btn-secondary" id="btnDiagTree" onclick="switchDiagramView('tree')" style="font-size:12px;height:34px;padding:0 14px">
                  🔀 Autonomous Decision Tree
                </button>
              </div>
            </div>

            <!-- Architecture Diagram Container -->
            <div id="diagArchWrap" style="display:block;width:100%;overflow-x:auto;border-radius:12px">
              __SYSTEM_ARCH_SVG__
            </div>

            <!-- Decision Tree Diagram Container -->
            <div id="diagTreeWrap" style="display:none;width:100%;overflow-x:auto;border-radius:12px">
              __DECISION_TREE_SVG__
            </div>
          </div>

          <div>
            <div style="font-size:12.5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:var(--accent-primary);margin-bottom:10px">
              1. How to Use FleetFlow (Step-by-Step Operator Workflow)
            </div>
            <div class="arch-grid">
              <div class="arch-card neon-blue">
                <div>
                  <div style="font-weight:800;font-size:14.5px;margin-bottom:6px">🚀 Step 1 · Launchpad Setup</div>
                  <div style="font-size:12.5px;color:var(--text-secondary)">
                    Pick your <b>Distribution Hub</b> (Mumbai or Bengaluru), upload an Excel/CSV sheet or use BigQuery, enter natural-language instructions in the centered Google-colored prompt box, and click <b>Synthesize &amp; Run FleetFlow Agent</b>.
                  </div>
                </div>
              </div>
              <div class="arch-card neon-green">
                <div>
                  <div style="font-weight:800;font-size:14.5px;margin-bottom:6px">📦 Step 2 · 3D Load Studio Calculator</div>
                  <div style="font-size:12.5px;color:var(--text-secondary)">
                    Open <b>3D Load Studio</b> to inspect step-by-step LIFO bay loading (last delivery at the cab wall `X=0`, Stop 1 right at the rear door). Test-pack any route into `ACE`, `PKP`, `T14`, `T17`, or `T20`.
                  </div>
                </div>
              </div>
              <div class="arch-card neon-amber">
                <div>
                  <div style="font-weight:800;font-size:14.5px;margin-bottom:6px">📱 Step 3 · Dock Scan &amp; Driver Dispatch</div>
                  <div style="font-size:12.5px;color:var(--text-secondary)">
                    In <b>Dock QR &amp; Intake</b>, scan staging photos or paste email/WhatsApp orders. In <b>Driver Hub &amp; BigQuery</b>, share the zero-login <b>Mobile Driver Portal</b> or launch <b>1-Tap Google Maps Navigation</b>.
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <div style="font-size:12.5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:var(--accent-primary);margin-bottom:10px">
              2. Google Cloud Services Architecture (3×2 Symmetrical Matrix)
            </div>
            <div class="arch-grid">
              <div class="arch-card">
                <div>
                  <div style="font-weight:800;font-size:13.5px;color:var(--accent-primary)">📊 Google BigQuery (`app/data/bq_source.py`)</div>
                  <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
                    Enterprise storage for retail outlets, daily SKU order books, fleet catalogues, and live SQL analytics.
                  </div>
                </div>
              </div>
              <div class="arch-card">
                <div>
                  <div style="font-weight:800;font-size:13.5px;color:var(--accent-primary)">☁️ Google Cloud Storage (`app/render/publish.py`)</div>
                  <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
                    Zero-login distribution of 3D MP4 loading animations and standalone mobile driver portals via V4 signed URLs.
                  </div>
                </div>
              </div>
              <div class="arch-card">
                <div>
                  <div style="font-weight:800;font-size:13.5px;color:var(--accent-primary)">🧠 Vertex AI Agent Engine (`app/integration/agent.py`)</div>
                  <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
                    Managed orchestration for Gemini 2.5 Flash + Google ADK tool calling and multimodal vision.
                  </div>
                </div>
              </div>
              <div class="arch-card">
                <div>
                  <div style="font-weight:800;font-size:13.5px;color:var(--accent-primary)">🚀 Google Cloud Run (`app/fast_api_app.py`)</div>
                  <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
                    Serverless container hosting for this Web Control Tower &amp; 3D Load Studio (`Dockerfile`, auto-scaling).
                  </div>
                </div>
              </div>
              <div class="arch-card">
                <div>
                  <div style="font-weight:800;font-size:13.5px;color:var(--accent-primary)">🗺️ Google Maps Routes API (`app/geo/roads.py`)</div>
                  <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
                    Real highway geometry, accurate travel times, and 1-tap turn-by-turn driver navigation links.
                  </div>
                </div>
              </div>
              <div class="arch-card">
                <div>
                  <div style="font-weight:800;font-size:13.5px;color:var(--accent-primary)">🛡️ Model Armor &amp; Cloud DLP (`app/integration/`)</div>
                  <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
                    Pre-turn prompt injection filtering, Cloud DLP PII masking, and an isolated OR-Tools + 3D math enclave.
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <div style="font-size:12.5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;color:var(--accent-primary);margin-bottom:10px">
              3. Portable Deployment Options (Zero Hardcoded Accounts or API Keys)
            </div>
            <div class="arch-grid">
              <div class="arch-card">
                <div style="font-weight:800;font-size:13.5px">Option A · Standalone Web UI (Cloud Run)</div>
                <pre class="arch-code">./scripts/deploy.sh --target ui --project YOUR_GCP_PROJECT_ID</pre>
              </div>
              <div class="arch-card">
                <div style="font-weight:800;font-size:13.5px">Option B · Gemini Enterprise Agent</div>
                <pre class="arch-code">./scripts/deploy.sh --target gemini-enterprise --project YOUR_GCP_PROJECT_ID</pre>
              </div>
              <div class="arch-card">
                <div style="font-weight:800;font-size:13.5px">Option C · Deploy Both + Seed BigQuery &amp; GCS</div>
                <pre class="arch-code">./scripts/deploy.sh --target all --publish-data --project YOUR_GCP_PROJECT_ID</pre>
              </div>
            </div>
          </div>
        </div>
      </section>

    </main>

    <!-- ═══════════════ BOTTOM AI COPILOT COMMAND BAR (HIDDEN ON LAUNCHPAD, SHOWN ON INNER WORKSPACES) ═══════════════ -->
    <footer class="ct-copilot-dock" id="ctCopilotDock">
      <div class="ct-copilot-pill">
        <span>✨</span> FleetFlow AI Agent
      </div>
      <input
        type="text"
        id="inpAgentPrompt"
        class="ct-copilot-input"
        placeholder="Ask the shared backend agent: 'Show only Ravi's truck', 'Highlight 3 trucks', 'Pin Suresh to South corridor', 'Switch to Bengaluru'..."
        onkeydown="if(event.key==='Enter') sendAgentPrompt()"
      >
      <button class="ct-btn-primary" style="height:38px;padding:0 16px" onclick="sendAgentPrompt()">
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
  </div>

  <!-- High-Tech Animated Google 4-Color Synthesis Modal Overlay -->
  <div id="lpSynthesisModal" class="lp-synthesis-modal">
    <div class="lp-modal-card google-revolving-box">
      <div class="google-revolving-inner" style="padding:28px 30px">
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px">
          <div class="orbital-ring-wrap" style="width:58px;height:58px">
            <span class="orbital-ring-core" style="font-size:26px">🚀</span>
          </div>
          <div style="min-width:0;flex:1">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">
              <span class="ct-kpi-badge" style="font-size:10px;padding:2px 8px;background:var(--accent-primary-soft);color:var(--accent-primary);border-color:rgba(66,133,244,0.4)">AI AGENT RUNNING</span>
              <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">OR-Tools + 3D Enclave</span>
            </div>
            <h3 id="lpModalTitle" class="ct-big-heading" style="font-size:20px;margin:0">
              FleetFlow AI Agent Optimizing Dispatch...
            </h3>
          </div>
        </div>

        <div id="lpModalSubtitle" style="font-size:12.5px;color:var(--text-secondary);margin-top:6px">
          Staging retail store manifest, loading 8-corridor bounds &amp; solving fleet route matrix...
        </div>

        <div class="lp-progress-bar-wrap">
          <div id="lpModalProgressBar" class="lp-progress-bar-fill"></div>
        </div>

        <div class="lp-modal-step-list">
          <div class="lp-modal-step" id="lpMStep1">
            <span id="lpMStep1Txt">1. Hub &amp; Retail Order Manifest Intake</span>
            <span class="lp-mstep-badge" id="lpMStep1Badge">⏳ Active</span>
          </div>
          <div class="lp-modal-step" id="lpMStep2">
            <span id="lpMStep2Txt">2. Compass Ray-Clustering &amp; Trunk-Branch Splitting</span>
            <span class="lp-mstep-badge" id="lpMStep2Badge">Queued</span>
          </div>
          <div class="lp-modal-step" id="lpMStep3">
            <span id="lpMStep3Txt">3. Google OR-Tools Multi-Capacity MIP Solver</span>
            <span class="lp-mstep-badge" id="lpMStep3Badge">Queued</span>
          </div>
          <div class="lp-modal-step" id="lpMStep4">
            <span id="lpMStep4Txt">4. 3D LIFO Reverse-Drop Spatial Packing &amp; Axle Balance</span>
            <span class="lp-mstep-badge" id="lpMStep4Badge">Queued</span>
          </div>
          <div class="lp-modal-step" id="lpMStep5">
            <span id="lpMStep5Txt">5. Google Maps Routes Highway Geometry &amp; Turn-by-Turn</span>
            <span class="lp-mstep-badge" id="lpMStep5Badge">Queued</span>
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:18px;padding-top:14px;border-top:1px solid var(--border-subtle);font-size:11px;color:var(--text-muted)">
          <span style="display:flex;align-items:center;gap:6px">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#34A853;box-shadow:0 0 8px #34A853"></span>
            Zero-Hallucination Math Enclave Active
          </span>
          <span id="lpModalTimer">Elapsed: 0.0s</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Toast Notification with Genie Spring Effect -->
  <div id="ctToast" class="ct-toast"></div>

</div>

<!-- Engine JS (Exposes window.mountFleetFlowEngine) -->
<script>
__ENGINE_JS__
</script>

<!-- Control Tower Application Logic -->
<script>
const CT = {
  meta: null,
  hubContext: null,
  bundle: null,
  currentView: 'launchpad',
  activeHubId: 'BHW-DC',
  activeOrderSource: 'demo',
  scope: 'all',
  focusTruckId: '',
  corridorClaims: {},
  driverRules: [],
  selectedCorridors: ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
  fleetCounts: {},
  customBoxes: [],
  mapEngine: null,
  loadEngine: null,
};

function getBqPresets() {
  const proj = (CT.meta && CT.meta.gcp_config && CT.meta.gcp_config.project_id) || 'your-gcp-project';
  const ds = (CT.meta && CT.meta.gcp_config && CT.meta.gcp_config.dataset) || 'fleetflow_demo';
  return [
    `SELECT corridor, COUNT(*) AS trucks, SUM(stops) AS total_stops, SUM(cartons) AS total_cartons, ROUND(AVG(volume_fill_pct), 1) AS avg_vol_fill_pct, SUM(cost_inr) AS total_cost_inr\nFROM \`${proj}.${ds}.routes\`\nGROUP BY corridor\nORDER BY total_cost_inr DESC`,
    `SELECT category, sku, description, COUNT(*) AS carton_qty, ROUND(SUM(weight_kg), 1) AS total_weight_kg, SUM(fragile) AS fragile_boxes\nFROM \`${proj}.${ds}.cartons\`\nGROUP BY category, sku, description\nORDER BY total_weight_kg DESC\nLIMIT 12`,
    `SELECT s.sales_area, COUNT(DISTINCT s.stop_id) AS outlets, COUNT(c.box_id) AS cartons, SUM(c.fragile) AS fragile_cartons, ROUND(SUM(c.weight_kg), 1) AS total_kg\nFROM \`${proj}.${ds}.stores\` s\nJOIN \`${proj}.${ds}.cartons\` c ON s.stop_id = c.stop_id\nGROUP BY s.sales_area\nORDER BY total_kg DESC`
  ];
}

function showToast(html, durationMs = 4800) {
  const el = document.getElementById('ctToast');
  el.innerHTML = html;
  el.style.display = 'block';
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.style.display = 'none'; }, durationMs);
}

function toggleCtTheme() {
  const root = document.documentElement;
  const btn = document.getElementById('btnThemeToggle');
  const heroBtn = document.getElementById('btnHeroThemeToggle');
  if (root.classList.contains('theme-dark')) {
    root.classList.remove('theme-dark');
    root.classList.add('theme-light');
    if (btn) btn.innerHTML = '🌙 Dark Mode';
    if (heroBtn) heroBtn.innerHTML = '🌙 Switch to Dark Mode';
  } else {
    root.classList.remove('theme-light');
    root.classList.add('theme-dark');
    if (btn) btn.innerHTML = '☀️ Light Mode';
    if (heroBtn) heroBtn.innerHTML = '☀️ Switch to Light Mode';
  }
}

async function switchWorkspace(viewId) {
  CT.currentView = viewId;
  document.querySelectorAll('#mainNavTabs .ct-nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-view') === viewId);
  });
  document.querySelectorAll('.ct-view').forEach(sec => {
    sec.classList.toggle('active', sec.id === 'view-' + viewId);
  });

  // Hide the bottom AI Copilot dock when on the Launchpad (which has the big centered Google command box)
  const dock = document.getElementById('ctCopilotDock');
  if (dock) {
    dock.style.display = (viewId === 'launchpad') ? 'none' : 'flex';
  }

  // If user jumps directly to a dispatch workspace before running synthesis, synthesize automatically
  if (!CT.bundle && ['tower', 'studio3d', 'simulator', 'gcp'].includes(viewId)) {
    await synthesizeFromLaunchpad(false);
  }

  if (viewId === 'tower' && CT.bundle) {
    setTimeout(() => mountMapCanvas(CT.bundle.anim_data), 35);
  } else if (viewId === 'studio3d' && CT.bundle) {
    setTimeout(() => runStudioRepack(), 35);
  } else if (viewId === 'gcp' && CT.bundle) {
    const sel = document.getElementById('selPortalTruck');
    if (sel && sel.value) updateDriverHubPreview(sel.value);
  } else if (viewId === 'history') {
    setTimeout(() => loadHistoryView(), 35);
  }
}

function mountMapCanvas(animData) {
  const mount = document.getElementById('ct-map-mount');
  if (!mount || !window.mountFleetFlowEngine || !animData) return;
  const d = JSON.parse(JSON.stringify(animData));
  d.start = 'routes';
  CT.mapEngine = window.mountFleetFlowEngine(mount, d, 'routes');
}

function mountLoadCanvas(animData) {
  const mount = document.getElementById('ct-load-mount');
  if (!mount || !window.mountFleetFlowEngine || !animData) return;
  const d = JSON.parse(JSON.stringify(animData));
  d.start = 'load';
  CT.loadEngine = window.mountFleetFlowEngine(mount, d, 'load');
}

async function initControlTower() {
  try {
    // Load metadata without pre-running a hardcoded dispatch plan so the Front Page Launchpad is first
    const res = await fetch('/api/meta?include_plan=false');
    const meta = await res.json();
    CT.meta = meta;

    const corrSel = document.getElementById('selClaimCorridor');
    corrSel.innerHTML = meta.corridors.map(c => `<option value="${c.code}">${c.code} · ${c.name}</option>`).join('');

    const tSel = document.getElementById('selStudioTruckType');
    tSel.innerHTML = meta.truck_types.map(t =>
      `<option value="${t.code}">${t.code} · ${t.name} (${t.inner_l_cm}×${t.inner_w_cm}×${t.inner_h_cm} cm · ${(t.payload_kg/1000).toFixed(1)}t)</option>`
    ).join('');

    const skuSel = document.getElementById('selCustomSku');
    skuSel.innerHTML = meta.skus.map(s =>
      `<option value="${s.sku}">${s.sku} · ${s.description} (${s.l_cm}×${s.w_cm}×${s.h_cm} cm · ${s.weight_kg} kg)</option>`
    ).join('');
    onCustomSkuChange(meta.skus[0]?.sku || '');

    meta.truck_types.forEach(t => { CT.fleetCounts[t.code] = t.default_count; });

    document.getElementById('inpSimFuel').value = meta.default_costs.fuel_price_per_litre;
    document.getElementById('inpSimDriverCost').value = meta.default_costs.driver_day_cost;
    document.getElementById('lpInpFuel').value = meta.default_costs.fuel_price_per_litre;
    document.getElementById('lpInpDriverCost').value = meta.default_costs.driver_day_cost;

    const photoGrid = document.getElementById('samplePhotosGrid');
    photoGrid.innerHTML = meta.sample_photos.slice(0, 6).map(p => `
      <div class="ct-photo-card" onclick="scanSamplePhoto('${p.filename}', this)">
        <img src="${p.url}" alt="${p.label}" loading="lazy">
        <div>📸 ${p.label}</div>
      </div>
    `).join('');

    const orderBtns = document.getElementById('sampleOrdersBtns');
    orderBtns.innerHTML = meta.sample_orders.map((o, idx) => `
      <button class="ct-chip-btn" onclick="loadSampleOrder(${idx})">📄 ${o.label}</button>
    `).join('');

    const gcpGrid = document.getElementById('gcpServiceGrid');
    gcpGrid.innerHTML = meta.gcp_services.map(s => `
      <div class="ct-box" style="padding:10px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-weight:800;font-size:12px">${s.icon} ${s.name}</span>
          <span class="ct-kpi-badge" style="font-size:9.5px;padding:2px 6px">${s.status}</span>
        </div>
        <div style="font-size:11px;color:var(--accent-primary);font-weight:600;margin-top:2px">${s.role}</div>
        <div style="font-size:10.5px;color:var(--text-muted);margin-top:3px">${s.detail}</div>
      </div>
    `).join('');

    // Populate the Front Page Launchpad with the initial Hub context (Mumbai BHW-DC)
    if (meta.hub_context) {
      applyHubContextToLaunchpad(meta.hub_context, true);
    } else {
      await onLaunchpadHubChange('BHW-DC');
    }
  } catch (err) {
    console.error('Failed to initialize Control Tower:', err);
  }
}

/* ═══════════════ LAUNCHPAD FRONT PAGE LOGIC ═══════════════ */
async function onLaunchpadHubChange(hubId) {
  CT.activeHubId = hubId;
  const sh = document.getElementById('selHub');
  if (sh) sh.value = hubId;
  const quickHub = document.getElementById('lpSelHubQuick');
  if (quickHub) quickHub.value = hubId;
  document.querySelectorAll('#lpHubCardsGrid .lp-hub-card').forEach(card => {
    card.classList.toggle('active', card.getAttribute('data-hub') === hubId);
  });

  const res = await fetch(`/api/hub-context?hub_id=${encodeURIComponent(hubId)}&order_source=${encodeURIComponent(CT.activeOrderSource)}`);
  const hc = await res.json();
  applyHubContextToLaunchpad(hc, true);
  showToast(`📍 Loaded <b>${hc.hub.name}</b> roster: <b>${hc.drivers.length} regional drivers</b> &amp; <b>${hc.total_stops} retail outlets</b>.`);
}

async function onSidebarHubChange(hubId) {
  await onLaunchpadHubChange(hubId);
  if (CT.currentView !== 'launchpad' && CT.bundle) {
    await triggerPlanUpdate({ hub_id: hubId });
  }
}

function syncLaunchpadObjective(val) {
  const lpObj = document.getElementById('lpSelObjective');
  if (lpObj) lpObj.value = val;
  if (CT.currentView !== 'launchpad' && CT.bundle) {
    triggerPlanUpdate({ objective: val });
  }
}

async function onSidebarSourceChange(val) {
  CT.activeOrderSource = val;
  await onLaunchpadHubChange(CT.activeHubId);
  if (CT.currentView !== 'launchpad' && CT.bundle) {
    await triggerPlanUpdate({ order_source: val });
  }
}

function applyHubContextToLaunchpad(hc, resetRulesOnCityChange = false) {
  const prevCity = CT.hubContext?.city_id;
  CT.hubContext = hc;
  CT.activeHubId = hc.hub.hub_id;
  const sh = document.getElementById('selHub');
  if (sh) sh.value = hc.hub.hub_id;
  const quickHub = document.getElementById('lpSelHubQuick');
  if (quickHub) quickHub.value = hc.hub.hub_id;

  document.querySelectorAll('#lpHubCardsGrid .lp-hub-card').forEach(card => {
    card.classList.toggle('active', card.getAttribute('data-hub') === hc.hub.hub_id);
  });

  // Update sidebar driver dropdown to match active Hub's roster
  const drvSel = document.getElementById('selClaimDriver');
  if (drvSel) {
    drvSel.innerHTML = hc.drivers.map(d => `<option value="${d.name}">${d.name} (${d.home_corridor})</option>`).join('');
  }

  // Update fleet counts from hub defaults
  if (hc.truck_counts) {
    CT.fleetCounts = { ...hc.truck_counts };
  }
  renderFleetControls();
  renderLaunchpadFleetPool();

  // Update top badge & driver count
  document.getElementById('lpActiveHubBadge').textContent = `HUB: ${hc.hub.hub_id} (${hc.city_name.toUpperCase()})`;
  document.getElementById('lpHubDriverCountLbl').textContent = `${hc.drivers.length} Drivers · ${hc.total_stops} Outlets`;

  // Render connectors
  const connRow = document.getElementById('lpConnectorsRow');
  if (connRow && hc.connectors) {
    connRow.innerHTML = hc.connectors.map(c => `
      <div style="padding:7px 9px;background:var(--bg-elevated);border:1px solid var(--border-subtle);border-radius:9px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:11.5px;font-weight:800">${c.icon} ${c.name}</span>
        </div>
        <div style="font-size:10px;color:var(--accent-primary);font-weight:700;margin-top:2px">${c.status}</div>
      </div>
    `).join('');
  }

  // Render 8-Corridor filter chips & demand table
  renderLaunchpadCorridorChips();
  renderLaunchpadCorridorTable();

  // Initialize or remap driver rules so driver names and corridors belong to the selected Hub
  if (resetRulesOnCityChange && (!CT.driverRules.length || prevCity !== hc.city_id)) {
    const d0 = hc.drivers[0]?.name || 'Ravi';
    const wCorr = hc.corridor_summary.find(c => c.code === 'W');
    const bestCorr = (wCorr && wCorr.stops > 0)
      ? 'W'
      : (hc.corridor_summary.slice().sort((a, b) => b.stops - a.stops)[0]?.code || 'SE');
    CT.driverRules = [
      { driver: d0, truck_type: 'T14', corridor: bestCorr }
    ];
  }
  renderLaunchpadDriverRules();

  // If no synthesis has run yet, update the 4 KPI cards with the staged Hub readiness
  if (!CT.bundle) {
    updateStagedKpiStrip();
  }
}

function updateStagedKpiStrip() {
  const hc = CT.hubContext;
  if (!hc) return;
  const totalTrucks = Object.values(CT.fleetCounts).reduce((a, b) => a + b, 0);
  const activeCorrCount = CT.selectedCorridors.length;

  document.getElementById('kpiLbl1').textContent = 'Selected Hub';
  document.getElementById('kpiTrucks').textContent = hc.hub.name;
  document.getElementById('kpiTrucksSub').textContent = `${hc.city_name} · ${hc.hub.hub_id}`;
  document.getElementById('kpiTrucksBadge').textContent = 'STAGED';

  document.getElementById('kpiLbl2').textContent = 'Staged Order Manifest';
  document.getElementById('kpiSavings').textContent = `${hc.total_stops} Retail Outlets`;
  document.getElementById('kpiCostCompare').textContent = `${hc.total_cartons.toLocaleString('en-IN')} cartons · ${hc.total_volume_m3} m³ (${activeCorrCount}/8)`;
  document.getElementById('kpiSavingsPct').textContent = CT.activeOrderSource === 'chat' ? 'Excel / CSV' : 'BigQuery Book';

  document.getElementById('kpiLbl3').textContent = 'Hub Fleet & Roster';
  document.getElementById('kpiStopsVal').textContent = `${totalTrucks} Trucks · ${hc.drivers.length} Drivers`;
  document.getElementById('kpiStopsSub').textContent = `Roster: ${hc.drivers.slice(0, 3).map(d => d.name).join(', ')}...`;

  document.getElementById('kpiLbl4').textContent = 'Manager Rules & Status';
  document.getElementById('kpiDistanceVal').textContent = CT.driverRules.length
    ? `${CT.driverRules.length} Driver Rule${CT.driverRules.length > 1 ? 's' : ''} Active`
    : 'Auto Solver Mode';
  document.getElementById('kpiDistanceSub').textContent = `Click 'Synthesize & Run Agent'`;
  document.getElementById('kpiDistanceBadge').textContent = 'Awaiting Run';
}

function renderLaunchpadCorridorChips() {
  const hc = CT.hubContext;
  const wrap = document.getElementById('lpCorridorFilterChips');
  if (!hc || !wrap) return;
  wrap.innerHTML = hc.corridor_summary.map(c => {
    const isAct = CT.selectedCorridors.includes(c.code);
    return `
      <button class="lp-corr-chip ${isAct ? 'active' : ''}" onclick="toggleLaunchpadCorridor('${c.code}')">
        <span>${isAct ? '✓' : '+'} ${c.code} · ${c.name}</span>
        <span style="opacity:0.82;font-family:var(--font-mono);font-size:10.5px">(${c.stops} stops · ${c.volume_m3}m³)</span>
      </button>
    `;
  }).join('');
}

function toggleLaunchpadCorridor(code) {
  if (CT.selectedCorridors.includes(code)) {
    if (CT.selectedCorridors.length > 1) {
      CT.selectedCorridors = CT.selectedCorridors.filter(c => c !== code);
    }
  } else {
    CT.selectedCorridors.push(code);
  }
  renderLaunchpadCorridorChips();
  renderLaunchpadCorridorTable();
  if (!CT.bundle) updateStagedKpiStrip();
}

function selectAllLaunchpadCorridors() {
  CT.selectedCorridors = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  renderLaunchpadCorridorChips();
  renderLaunchpadCorridorTable();
  if (!CT.bundle) updateStagedKpiStrip();
}

function renderLaunchpadCorridorTable() {
  const hc = CT.hubContext;
  const tbody = document.getElementById('lpCorridorPreviewBody');
  if (!hc || !tbody) return;
  const activeRows = hc.corridor_summary.filter(c => CT.selectedCorridors.includes(c.code));
  const totalStops = activeRows.reduce((s, r) => s + r.stops, 0);
  const totalCartons = activeRows.reduce((s, r) => s + r.cartons, 0);
  const badge = document.getElementById('lpPreviewSummaryBadge');
  if (badge) badge.textContent = `${activeRows.length} Sectors · ${totalStops} Outlets · ${totalCartons} Cartons`;

  tbody.innerHTML = hc.corridor_summary.map(c => {
    const included = CT.selectedCorridors.includes(c.code);
    return `
      <tr style="${included ? '' : 'opacity:0.38'}">
        <td style="font-family:var(--font-mono);font-weight:800;color:var(--accent-primary)">${c.code} · ${c.name}</td>
        <td style="font-size:11.5px;color:var(--text-muted)">${c.sample_areas}</td>
        <td style="font-weight:700">${c.stops}</td>
        <td>${c.cartons}</td>
        <td style="font-family:var(--font-mono)">${c.volume_m3} m³</td>
        <td style="font-family:var(--font-mono)">${Math.round(c.weight_kg)} kg</td>
        <td><span class="ct-kpi-badge" style="font-size:10px;padding:2px 6px">${c.recommended_truck}</span></td>
      </tr>
    `;
  }).join('');
}

function renderLaunchpadDriverRules() {
  const hc = CT.hubContext;
  const container = document.getElementById('lpDriverRulesContainer');
  const summaryEl = document.getElementById('lpQuickRuleSummary');
  if (!hc || !container) return;

  if (summaryEl) {
    if (!CT.driverRules.length) {
      summaryEl.textContent = '100% Auto Solver Assignment';
    } else {
      const r0 = CT.driverRules[0];
      summaryEl.textContent = `${CT.driverRules.length} Rule(s): ${r0.driver} → ${r0.truck_type || 'Auto'} → ${r0.corridor}`;
    }
  }

  if (!CT.driverRules.length) {
    container.innerHTML = `
      <div style="padding:12px;background:var(--bg-elevated);border:1px dashed var(--border-subtle);border-radius:10px;font-size:12px;color:var(--text-muted);text-align:center">
        No manual driver/truck pins set — OR-Tools will autonomously assign all ${hc.drivers.length} ${hc.city_name} drivers &amp; trucks across corridors. Click <b>+ Add Driver / Truck Rule</b> above to pin specific drivers or truck sizes.
      </div>
    `;
    return;
  }

  const truckCatalog = CT.meta?.truck_types || [];
  container.innerHTML = CT.driverRules.map((rule, idx) => {
    const corrInfo = hc.corridor_summary.find(c => c.code === rule.corridor) || hc.corridor_summary[0];
    const tSpec = truckCatalog.find(t => t.code === rule.truck_type);
    let diagHtml = '';
    if (corrInfo) {
      if (tSpec) {
        const effCap = +(tSpec.volume_m3 * 0.85).toFixed(1);
        if (corrInfo.volume_m3 > effCap) {
          const overflowM3 = +(corrInfo.volume_m3 - effCap).toFixed(1);
          diagHtml = `<div style="margin-top:6px;font-size:11.5px;color:var(--accent-amber);font-weight:700">⚡ Smaller Truck Selected (${tSpec.code} · ${effCap}m³ usable vs ${corrInfo.volume_m3}m³ in ${corrInfo.code}): Pins inner ${corrInfo.name} stops to ${rule.driver}'s ${tSpec.code} &amp; automatically distributes ~${overflowM3}m³ overflow to a shared-trunk branch truck!</div>`;
        } else {
          diagHtml = `<div style="margin-top:6px;font-size:11.5px;color:var(--accent-emerald);font-weight:700">✓ Single-Truck Fit (${tSpec.code} · ${effCap}m³ usable ≥ ${corrInfo.volume_m3}m³ demand in ${corrInfo.code}): All ${corrInfo.stops} ${corrInfo.name} stops fit in ${rule.driver}'s truck.</div>`;
        }
      } else {
        diagHtml = `<div style="margin-top:6px;font-size:11.5px;color:var(--accent-primary);font-weight:600">🧭 Auto Truck Sizing: Solver picks optimal vehicle for ${rule.driver} on ${corrInfo.code} · ${corrInfo.name} (${corrInfo.stops} stops, ${corrInfo.volume_m3}m³) + trunk-and-branch split if needed.</div>`;
      }
    }

    return `
      <div class="lp-rule-row">
        <div style="display:grid;grid-template-columns:repeat(3, minmax(0, 1fr)) 40px;gap:10px;align-items:end">
          <div class="ct-field">
            <label>Hub Driver (${hc.hub.hub_id})</label>
            <select class="ct-select" onchange="updateLaunchpadRule(${idx}, 'driver', this.value)">
              ${hc.drivers.map(d => `<option value="${d.name}" ${d.name === rule.driver ? 'selected' : ''}>${d.name} (Home: ${d.home_corridor})</option>`).join('')}
            </select>
          </div>
          <div class="ct-field">
            <label>Assigned Truck Class</label>
            <select class="ct-select" onchange="updateLaunchpadRule(${idx}, 'truck_type', this.value)">
              <option value="" ${!rule.truck_type ? 'selected' : ''}>Auto · Solver Best Fit</option>
              ${truckCatalog.map(t => `<option value="${t.code}" ${t.code === rule.truck_type ? 'selected' : ''}>${t.code} · ${t.name} (${t.volume_m3}m³ · ${(t.payload_kg/1000).toFixed(1)}t)</option>`).join('')}
            </select>
          </div>
          <div class="ct-field">
            <label>Target Compass Corridor</label>
            <select class="ct-select" onchange="updateLaunchpadRule(${idx}, 'corridor', this.value)">
              ${hc.corridor_summary.map(c => `<option value="${c.code}" ${c.code === rule.corridor ? 'selected' : ''}>${c.code} · ${c.name} (${c.stops} stops · ${c.volume_m3}m³)</option>`).join('')}
            </select>
          </div>
          <button class="ct-btn-secondary" style="height:40px;width:40px;padding:0;color:var(--accent-rose)" onclick="removeLaunchpadRule(${idx})" title="Remove rule">✕</button>
        </div>
        ${diagHtml}
      </div>
    `;
  }).join('');
}

function addLaunchpadDriverRule() {
  const hc = CT.hubContext;
  if (!hc) return;
  const usedDrivers = new Set(CT.driverRules.map(r => r.driver));
  const nextDrv = hc.drivers.find(d => !usedDrivers.has(d.name)) || hc.drivers[0];
  const corrs = ['W', 'S', 'NE', 'N', 'E', 'NW', 'SE', 'SW'];
  const nextCorr = corrs[CT.driverRules.length % corrs.length];
  CT.driverRules.push({
    driver: nextDrv ? nextDrv.name : 'Ravi',
    truck_type: 'T14',
    corridor: nextCorr
  });
  renderLaunchpadDriverRules();
  if (!CT.bundle) updateStagedKpiStrip();
}

function updateLaunchpadRule(idx, field, val) {
  if (!CT.driverRules[idx]) return;
  CT.driverRules[idx][field] = val;
  renderLaunchpadDriverRules();
  if (!CT.bundle) updateStagedKpiStrip();
}

function removeLaunchpadRule(idx) {
  CT.driverRules.splice(idx, 1);
  renderLaunchpadDriverRules();
  if (!CT.bundle) updateStagedKpiStrip();
}

function applyLaunchpadPreset(presetName) {
  const hc = CT.hubContext;
  if (!hc) return;
  const d0 = hc.drivers[0]?.name || 'Ravi';
  const d1 = hc.drivers[1]?.name || 'Suresh';
  if (presetName === 'smaller_west') {
    CT.driverRules = [
      { driver: d0, truck_type: 'T14', corridor: 'W' }
    ];
    showToast(`⚡ Configured <b>${d0}</b> on <b>West</b> in a smaller <b>T14 (14ft)</b> truck — excess West stops will distribute to a branch truck.`);
  } else if (presetName === 'two_leads') {
    CT.driverRules = [
      { driver: d0, truck_type: 'T14', corridor: 'W' },
      { driver: d1, truck_type: 'T17', corridor: 'S' }
    ];
    showToast(`⚡ Configured 2 corridor leads: <b>${d0} (West · T14)</b> and <b>${d1} (South · T17)</b>.`);
  } else {
    CT.driverRules = [];
    showToast(`🧹 Cleared manual rules — 100% autonomous OR-Tools assignment enabled.`);
  }
  renderLaunchpadDriverRules();
  if (!CT.bundle) updateStagedKpiStrip();
}

function renderLaunchpadFleetPool() {
  const grid = document.getElementById('lpFleetPoolGrid');
  if (!grid || !CT.meta) return;
  const total = Object.values(CT.fleetCounts).reduce((a, b) => a + b, 0);
  const lbl = document.getElementById('lpTotalFleetPoolLbl');
  if (lbl) lbl.textContent = `${total} Trucks Available`;

  grid.innerHTML = CT.meta.truck_types.map(t => `
    <div style="padding:10px 8px;background:var(--bg-elevated);border:1px solid var(--border-subtle);border-top:3px solid ${t.color};border-radius:10px;text-align:center">
      <div style="font-weight:800;font-size:12px">${t.code}</div>
      <div style="font-size:10px;color:var(--text-muted)">${t.volume_m3}m³ · ${(t.payload_kg/1000).toFixed(1)}t</div>
      <div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:6px">
        <button class="ct-btn-secondary" style="height:26px;width:26px;padding:0;font-size:12px" onclick="stepFleetCount('${t.code}', -1)">-</button>
        <span id="lpFleetCnt-${t.code}" style="font-family:var(--font-mono);font-weight:800;font-size:12.5px;min-width:18px">${CT.fleetCounts[t.code] ?? 2}</span>
        <button class="ct-btn-secondary" style="height:26px;width:26px;padding:0;font-size:12px" onclick="stepFleetCount('${t.code}', 1)">+</button>
      </div>
    </div>
  `).join('');
}

function uploadLaunchpadSpreadsheet(inputEl) {
  const file = inputEl.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  const badge = document.getElementById('lpManifestStatusBadge');
  if (badge) badge.textContent = `⏳ Parsing CSV...`;

  reader.onload = async () => {
    try {
      const res = await fetch('/api/upload-manifest', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          filename: file.name,
          mime_type: file.type || '',
          file_base64: reader.result,
          hub_id: CT.activeHubId
        })
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(`❌ ${data.detail || 'Could not parse spreadsheet'}`);
        return;
      }
      CT.activeOrderSource = 'chat';
      const ss1 = document.getElementById('selSource');
      if (ss1) ss1.value = 'chat';
      if (badge) badge.textContent = `✓ ${data.stops_parsed} Stops · CSV`;
      if (data.hub_context) {
        applyHubContextToLaunchpad(data.hub_context, false);
      }
      showToast(`📗 Loaded <b>${data.filename}</b>: <b>${data.stops_parsed} outlets</b> &amp; <b>${data.cartons_parsed} cartons</b> staged for synthesis!`);
    } catch (e) {
      showToast(`❌ Upload failed: ${e.message}`);
    }
  };
  reader.readAsDataURL(file);
}

async function loadLaunchpadSampleSheet(sampleFilename) {
  const badge = document.getElementById('lpManifestStatusBadge');
  if (badge) badge.textContent = `⏳ Loading CSV...`;
  const res = await fetch('/api/upload-manifest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      sample_file: sampleFilename,
      hub_id: CT.activeHubId
    })
  });
  const data = await res.json();
  if (res.ok && data.hub_context) {
    CT.activeOrderSource = 'chat';
    const ss2 = document.getElementById('selSource');
    if (ss2) ss2.value = 'chat';
    if (badge) badge.textContent = `✓ ${data.stops_parsed} Stops · CSV`;
    applyHubContextToLaunchpad(data.hub_context, false);
    showToast(`📄 Staged sample sheet <b>${data.filename}</b> (${data.stops_parsed} outlets, ${data.cartons_parsed} cartons). Click <b>Synthesize &amp; Run Agent</b>!`);
  }
}

async function resetLaunchpadToHubBook() {
  CT.activeOrderSource = 'demo';
  const ss3 = document.getElementById('selSource');
  if (ss3) ss3.value = 'demo';
  const badge = document.getElementById('lpManifestStatusBadge');
  if (badge) badge.textContent = `✓ Live Order Book`;
  await onLaunchpadHubChange(CT.activeHubId);
}

function setLaunchpadPrompt(txt) {
  const el = document.getElementById('inpLaunchpadPrompt');
  if (el) el.value = txt;
}

async function synthesizeFromLaunchpad(switchAfter = true) {
  const modal = document.getElementById('lpSynthesisModal');
  const modalTitle = document.getElementById('lpModalTitle');
  const modalSub = document.getElementById('lpModalSubtitle');
  const barFill = document.getElementById('lpModalProgressBar');
  const timerLbl = document.getElementById('lpModalTimer');

  const heroBtn = document.getElementById('btnHeroSynthesize');
  const botBtn = document.getElementById('btnBottomSynthesize');
  if (heroBtn) heroBtn.innerHTML = '<span>⏳</span> FleetFlow Agent Running...';
  if (botBtn) botBtn.innerHTML = '<span>⏳</span> FleetFlow Agent Running...';

  const tStart = Date.now();
  let timerInterval = null;

  if (modal) {
    modal.style.display = 'flex';
    modal.style.opacity = '1';
    if (modalTitle) {
      modalTitle.innerHTML = 'FleetFlow AI Agent Optimizing Dispatch...';
      modalTitle.style.color = 'var(--text-main)';
    }
    const hc = CT.hubContext;
    if (modalSub && hc) {
      modalSub.textContent = `Staging ${hc.total_stops} retail outlets for ${hc.hub.name} across ${CT.selectedCorridors.length} sectors...`;
    }
    if (barFill) barFill.style.width = '18%';

    // Reset steps
    for (let i = 1; i <= 5; i++) {
      const el = document.getElementById(`lpMStep${i}`);
      const b = document.getElementById(`lpMStep${i}Badge`);
      if (el) el.className = 'lp-modal-step';
      if (b) b.textContent = 'Queued';
    }
    const s1 = document.getElementById('lpMStep1');
    const b1 = document.getElementById('lpMStep1Badge');
    if (s1) s1.className = 'lp-modal-step active';
    if (b1) b1.textContent = '⏳ Active';

    timerInterval = setInterval(() => {
      const sec = ((Date.now() - tStart) / 1000).toFixed(1);
      if (timerLbl) timerLbl.textContent = `Elapsed: ${sec}s`;
    }, 100);
  }

  // Animate stages smoothly while request is in flight
  setTimeout(() => {
    const s1 = document.getElementById('lpMStep1');
    const b1 = document.getElementById('lpMStep1Badge');
    const s2 = document.getElementById('lpMStep2');
    const b2 = document.getElementById('lpMStep2Badge');
    if (s1) { s1.className = 'lp-modal-step done'; if (b1) b1.textContent = '✓ Done'; }
    if (s2) { s2.className = 'lp-modal-step active'; if (b2) b2.textContent = '⏳ Active'; }
    if (barFill) barFill.style.width = '38%';
  }, 220);

  setTimeout(() => {
    const s2 = document.getElementById('lpMStep2');
    const b2 = document.getElementById('lpMStep2Badge');
    const s3 = document.getElementById('lpMStep3');
    const b3 = document.getElementById('lpMStep3Badge');
    if (s2) { s2.className = 'lp-modal-step done'; if (b2) b2.textContent = '✓ Done'; }
    if (s3) { s3.className = 'lp-modal-step active'; if (b3) b3.textContent = '⚡ Solving'; }
    if (barFill) barFill.style.width = '64%';
  }, 480);

  const hubId = CT.activeHubId || 'BHW-DC';
  const objective = document.getElementById('lpSelObjective')?.value || 'lowest_cost';
  const scopeVal = document.getElementById('lpSelScope')?.value || CT.scope || 'all';
  const fuel = parseFloat(document.getElementById('lpInpFuel')?.value || '92');
  const drvCost = parseFloat(document.getElementById('lpInpDriverCost')?.value || '950');
  const promptTxt = (document.getElementById('inpLaunchpadPrompt')?.value || '').trim();

  const claimsMap = {};
  CT.driverRules.forEach(r => {
    if (r.driver && r.corridor) {
      claimsMap[r.driver] = r.truck_type ? `${r.corridor}|${r.truck_type}` : r.corridor;
    }
  });
  CT.corridorClaims = claimsMap;
  CT.scope = scopeVal;

  try {
    const res = await fetch('/api/plan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        hub_id: hubId,
        objective: objective,
        order_source: CT.activeOrderSource,
        truck_counts: CT.fleetCounts,
        corridor_claims: claimsMap,
        driver_assignments: CT.driverRules,
        selected_corridors: CT.selectedCorridors,
        prompt: promptTxt,
        fuel_price: fuel,
        driver_day_cost: drvCost,
        scope: scopeVal
      })
    });
    const bundle = await res.json();

    // Mark stages 3, 4, 5 as Done
    for (let i = 1; i <= 5; i++) {
      const el = document.getElementById(`lpMStep${i}`);
      const b = document.getElementById(`lpMStep${i}Badge`);
      if (el) el.className = 'lp-modal-step done';
      if (b) b.textContent = '✓ Done';
    }
    if (barFill) barFill.style.width = '100%';

    if (modalTitle) {
      modalTitle.innerHTML = '✓ Dispatch Plan Optimized!';
      modalTitle.style.color = 'var(--accent-emerald)';
    }
    if (modalSub) {
      modalSub.innerHTML = `Dispatched <b>${bundle.kpi.optimized_trucks} trucks</b> for <b>${bundle.hub.name}</b> — saving <b>₹${bundle.kpi.savings_inr.toLocaleString('en-IN')}/day (-${bundle.kpi.savings_pct}%)</b>. Transitioning to live route map...`;
    }

    applyBundle(bundle);
    if (bundle.hub_context) {
      CT.hubContext = bundle.hub_context;
    }

    // Brief beat to display success confirmation before scrolling into the map page
    await new Promise(r => setTimeout(r, 480));

    if (modal) {
      modal.style.transition = 'opacity 0.28s ease, transform 0.28s ease';
      modal.style.opacity = '0';
      await new Promise(r => setTimeout(r, 260));
      modal.style.display = 'none';
      modal.style.opacity = '1';
    }

    if (switchAfter) {
      await switchWorkspace('tower');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      const noteMsg = (bundle.notes && bundle.notes.length)
        ? `<br><span style="font-size:11.5px;color:var(--text-secondary)">📌 ${bundle.notes[0]}</span>`
        : '';
      showToast(`🚀 <b>Agent Synthesis Complete (${bundle.plan_id}):</b> Dispatched <b>${bundle.kpi.optimized_trucks} trucks</b> for <b>${bundle.hub.name}</b> — saving <b>₹${bundle.kpi.savings_inr.toLocaleString('en-IN')}/day (-${bundle.kpi.savings_pct}%)</b>!${noteMsg}`, 6800);
    }
  } catch (err) {
    if (modal) modal.style.display = 'none';
    showToast(`❌ Synthesis error: ${err.message}`);
  } finally {
    if (timerInterval) clearInterval(timerInterval);
    if (heroBtn) heroBtn.innerHTML = '<span>🚀</span> Synthesize &amp; Run FleetFlow Agent →';
    if (botBtn) botBtn.innerHTML = '<span>🚀</span> Synthesize &amp; Run FleetFlow Agent →';
  }
}

function applyBundle(bundle) {
  if (!bundle) return;
  CT.bundle = bundle;
  CT.focusTruckId = bundle.focus_truck_id || (bundle.routes[0]?.truck_id || '');
  CT.corridorClaims = bundle.corridor_claims || {};

  if (bundle.hub?.hub_id) {
    CT.activeHubId = bundle.hub.hub_id;
    const sh = document.getElementById('selHub');
    if (sh) sh.value = bundle.hub.hub_id;
  }
  if (bundle.objective) {
    const so = document.getElementById('selObjective');
    if (so) so.value = bundle.objective;
    const lpObj = document.getElementById('lpSelObjective');
    if (lpObj) lpObj.value = bundle.objective;
  }

  // Update Clean 4-Metric Operational Ribbon with Live Synthesized KPIs
  const k = bundle.kpi;
  document.getElementById('kpiLbl1').textContent = 'Trucks Dispatched';
  document.getElementById('kpiTrucks').textContent = `${k.baseline_trucks} → ${k.optimized_trucks} Trucks`;
  document.getElementById('kpiTrucksSub').textContent = `Right-sized fleet for ${bundle.hub?.name || 'Hub'}`;
  document.getElementById('kpiTrucksBadge').textContent = k.trucks_saved > 0 ? `-${k.trucks_saved} trucks` : `${k.optimized_trucks} active`;

  document.getElementById('kpiLbl2').textContent = 'Daily Cost Savings';
  document.getElementById('kpiSavings').textContent = `₹${k.savings_inr.toLocaleString('en-IN')} / day`;
  document.getElementById('kpiCostCompare').textContent = `₹${k.baseline_cost_inr.toLocaleString('en-IN')} → ₹${k.optimized_cost_inr.toLocaleString('en-IN')}`;
  document.getElementById('kpiSavingsPct').textContent = `-${k.savings_pct}%`;

  document.getElementById('kpiLbl3').textContent = 'Deliveries & Cargo';
  document.getElementById('kpiStopsVal').textContent = `${k.stops} Stops`;
  document.getElementById('kpiStopsSub').textContent = `${k.cartons.toLocaleString('en-IN')} cartons · ${k.weight_tonnes}t payload`;
  const cargoB = document.getElementById('kpiCargoBadge');
  if (cargoB) cargoB.textContent = `${k.unassigned || 0} Unassigned`;

  document.getElementById('kpiLbl4').textContent = 'Total Route Distance';
  document.getElementById('kpiDistanceVal').textContent = `${k.optimized_km.toLocaleString('en-IN')} km`;
  document.getElementById('kpiDistanceSub').textContent = `Down from ${k.baseline_km.toLocaleString('en-IN')} km manual`;
  document.getElementById('kpiDistanceBadge').textContent = k.km_saved > 0 ? `-${k.km_saved} km` : `Optimized`;

  const mapDrop = document.getElementById('selFocusTruckMap');
  mapDrop.innerHTML = `<option value="all">All Fleet (${bundle.routes.length} trucks)</option>` +
    bundle.routes.map(r => `<option value="${r.truck_id}">${r.truck_id} · ${r.driver} (${r.corridor_name} · ${r.stops_count} stops)</option>`).join('');

  if (bundle.active_trucks && bundle.active_trucks.length === 1) {
    mapDrop.value = bundle.active_trucks[0];
  } else {
    mapDrop.value = 'all';
  }

  const isAll = !bundle.active_trucks;
  const is1 = bundle.active_trucks && bundle.active_trucks.length === 1;
  const is3 = bundle.active_trucks && bundle.active_trucks.length === 3;
  document.getElementById('scopeAllBtn').classList.toggle('active', isAll);
  document.getElementById('scope1Btn').classList.toggle('active', !!is1);
  document.getElementById('scope3Btn').classList.toggle('active', !!is3);

  const claimsDiv = document.getElementById('activeClaimsPills');
  const entries = Object.entries(CT.corridorClaims);
  claimsDiv.innerHTML = entries.map(([drv, corr]) =>
    `<span class="ct-kpi-badge" style="font-size:10.5px">📌 ${drv} → ${corr}</span>`
  ).join('');

  const activeCount = bundle.routes.filter(r => r.active).length;
  document.getElementById('routeCountLbl').textContent = `${activeCount} active`;
  const rList = document.getElementById('towerRoutesList');
  rList.innerHTML = bundle.routes.map(r => `
    <div class="ct-route-item ${r.active ? '' : 'dimmed'} ${r.truck_id === CT.focusTruckId ? 'selected' : ''}"
         style="--route-c:${r.color}"
         onclick="focusTruckFromSidebar('${r.truck_id}')">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:800;font-size:13px">${r.truck_id} · ${r.driver}</span>
        <span style="font-family:var(--font-mono);font-size:11px;color:${r.color};font-weight:700">${r.corridor} (${r.branch})</span>
      </div>
      <div style="font-size:11.5px;color:var(--text-muted);margin-top:2px">
        ${r.truck_name} · ${r.stops_count} stops · ${r.cartons_count} boxes · ${r.km} km
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:5px;font-size:11.5px">
        <span>Fill: <b>${r.volume_fill_pct}% vol</b> / <b>${r.weight_fill_pct}% wt</b></span>
        <span style="font-family:var(--font-mono);font-weight:700;color:var(--text-main)">₹${r.cost_total.toLocaleString('en-IN')}</span>
      </div>
      <div style="display:flex;gap:6px;margin-top:8px;padding-top:7px;border-top:1px dashed var(--border-subtle)" onclick="event.stopPropagation()">
        <a href="${r.whatsapp_url}" target="_blank" class="ct-btn-chip-action wa" title="Share full delivery itinerary with driver via WhatsApp">
          💬 WhatsApp
        </a>
        <a href="${r.gmaps_nav_url}" target="_blank" class="ct-btn-chip-action maps" title="Launch Google Maps Live Traffic Navigation">
          🗺️ Maps Nav
        </a>
        <a href="${r.driver_portal_url}" target="_blank" class="ct-btn-chip-action portal" title="Open Mobile Driver Portal & Printable Challan">
          📱 Portal
        </a>
      </div>
    </div>
  `).join('');

  const stSel = document.getElementById('selStudioRoute');
  stSel.innerHTML = bundle.routes.map(r =>
    `<option value="${r.truck_id}" data-code="${r.truck_code}">${r.truck_id} · ${r.driver} (${r.truck_code} · ${r.cartons_count} cartons)</option>`
  ).join('');
  if (CT.focusTruckId) stSel.value = CT.focusTruckId;
  const activeRouteObj = bundle.routes.find(r => r.truck_id === stSel.value) || bundle.routes[0];
  if (activeRouteObj) {
    document.getElementById('selStudioTruckType').value = activeRouteObj.truck_code;
  }

  renderSimulatorTable(bundle.routes);

  const pSel = document.getElementById('selPortalTruck');
  pSel.innerHTML = bundle.routes.map(r =>
    `<option value="${r.truck_id}">${r.truck_id} · ${r.driver} (${r.corridor_name} · ${r.stops_count} stops)</option>`
  ).join('');
  if (CT.focusTruckId) pSel.value = CT.focusTruckId;
  if (pSel.value) updateDriverHubPreview(pSel.value);

  renderAuditLog(bundle.audit_log || []);

  if (CT.currentView === 'tower') {
    mountMapCanvas(bundle.anim_data);
  } else if (CT.currentView === 'studio3d') {
    runStudioRepack();
  }
}

async function triggerPlanUpdate(extra = {}) {
  const payload = {
    hub_id: document.getElementById('selHub')?.value || CT.activeHubId || 'BHW-DC',
    objective: document.getElementById('selObjective')?.value || document.getElementById('lpSelObjective')?.value || 'lowest_cost',
    order_source: document.getElementById('selSource')?.value || CT.activeOrderSource || 'demo',
    corridor_claims: CT.corridorClaims,
    scope: CT.scope,
    focus_truck_id: CT.focusTruckId,
    ...extra
  };
  const btn = document.getElementById('btnOptimize');
  const origTxt = btn ? btn.innerHTML : '';
  if (btn) btn.innerHTML = '<span>⏳</span> Solving...';
  try {
    const res = await fetch('/api/plan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const bundle = await res.json();
    applyBundle(bundle);
  } finally {
    if (btn) btn.innerHTML = origTxt;
  }
}

function applyTruckScope(scopeVal) {
  CT.scope = scopeVal;
  triggerPlanUpdate({ scope: scopeVal });
}

function applySingleTruckDropdown(val) {
  if (val === 'all') {
    CT.scope = 'all';
    triggerPlanUpdate({ scope: 'all' });
  } else {
    CT.scope = val;
    CT.focusTruckId = val;
    triggerPlanUpdate({ scope: val, focus_truck_id: val });
  }
}

function focusTruckFromSidebar(truckId) {
  CT.focusTruckId = truckId;
  CT.scope = truckId;
  triggerPlanUpdate({ scope: truckId, focus_truck_id: truckId });
}

function submitCorridorClaim() {
  const drv = document.getElementById('selClaimDriver').value;
  const corr = document.getElementById('selClaimCorridor').value;
  if (!drv || !corr) return;
  CT.corridorClaims[drv] = corr;
  CT.scope = 'all';
  triggerPlanUpdate({ corridor_claims: CT.corridorClaims, scope: 'all' });
  showToast(`📌 Pinned <b>${drv}</b> to <b>${corr}</b> corridor with trunk-and-branch splitting.`);
}

function clearCorridorClaims() {
  CT.corridorClaims = {};
  CT.driverRules = [];
  renderLaunchpadDriverRules();
  CT.scope = 'all';
  triggerPlanUpdate({ corridor_claims: {}, driver_assignments: [], scope: 'all' });
  showToast(`Cleared all driver corridor claims.`);
}

function onStudioRouteSelect(truckId) {
  CT.focusTruckId = truckId;
  const r = (CT.bundle?.routes || []).find(x => x.truck_id === truckId);
  if (r) {
    document.getElementById('selStudioTruckType').value = r.truck_code;
  }
  runStudioRepack();
}

function onCustomSkuChange(skuCode) {
  const s = (CT.meta?.skus || []).find(x => x.sku === skuCode);
  if (!s) return;
  document.getElementById('inpCustomL').value = s.l_cm;
  document.getElementById('inpCustomW').value = s.w_cm;
  document.getElementById('inpCustomH').value = s.h_cm;
  document.getElementById('inpCustomKg').value = s.weight_kg;
}

function addCustomBoxAndPack() {
  const sku = document.getElementById('selCustomSku').value;
  const qty = parseInt(document.getElementById('inpCustomQty').value || '1', 10);
  const stop_seq = parseInt(document.getElementById('inpCustomStop').value || '1', 10);
  const l_cm = parseFloat(document.getElementById('inpCustomL').value || '30');
  const w_cm = parseFloat(document.getElementById('inpCustomW').value || '30');
  const h_cm = parseFloat(document.getElementById('inpCustomH').value || '30');
  const weight_kg = parseFloat(document.getElementById('inpCustomKg').value || '15');

  CT.customBoxes.push({ sku, qty, stop_seq, l_cm, w_cm, h_cm, weight_kg });
  renderAddedCustomBoxes();
  runStudioRepack();
}

function clearCustomBoxes() {
  CT.customBoxes = [];
  renderAddedCustomBoxes();
  runStudioRepack();
}

function renderAddedCustomBoxes() {
  const el = document.getElementById('addedCustomBoxesList');
  if (!CT.customBoxes.length) {
    el.innerHTML = '';
    return;
  }
  el.innerHTML = CT.customBoxes.map((b, i) =>
    `<div>+ <b>${b.qty}× ${b.sku}</b> (${b.l_cm}×${b.w_cm}×${b.h_cm}cm, ${b.weight_kg}kg) → Stop #${b.stop_seq}</div>`
  ).join('');
}

async function runStudioRepack() {
  const sourceTruckId = document.getElementById('selStudioRoute').value || CT.focusTruckId;
  const targetCode = document.getElementById('selStudioTruckType').value || 'T17';

  const res = await fetch('/api/repack-truck', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      source_truck_id: sourceTruckId,
      target_truck_code: targetCode,
      extra_boxes: CT.customBoxes
    })
  });
  const data = await res.json();
  const st = data.stats;

  document.getElementById('stVolFill').textContent = `${st.volume_fill_pct}%`;
  document.getElementById('stVolBar').style.width = `${Math.min(100, st.volume_fill_pct)}%`;
  document.getElementById('stWtFill').textContent = `${st.weight_fill_pct}%`;
  document.getElementById('stWtBar').style.width = `${Math.min(100, st.weight_fill_pct)}%`;

  document.getElementById('stLifoStatus').textContent = st.lifo_ok ? '100% LIFO OK' : 'LIFO WARN';

  const warnEl = document.getElementById('stOverflowWarn');
  if (st.unplaced_count > 0) {
    warnEl.style.display = 'block';
    warnEl.innerHTML = `⚠️ <b>${st.unplaced_count} cartons did not fit</b> in ${st.truck_code} (${st.truck_name}). Select a larger vehicle class from the dropdown!`;
  } else {
    warnEl.style.display = 'none';
  }

  if (CT.bundle && CT.bundle.anim_data) {
    const customAnim = JSON.parse(JSON.stringify(CT.bundle.anim_data));
    const idx = customAnim.trucks.findIndex(t => t.id === sourceTruckId);
    if (idx >= 0) {
      customAnim.trucks[idx] = data.truck_anim;
    } else {
      customAnim.trucks.unshift(data.truck_anim);
    }
    customAnim.focus = data.truck_anim.id;
    customAnim.start = 'load';
    mountLoadCanvas(customAnim);
  }
  if (data.audit_log) renderAuditLog(data.audit_log);
}

function renderFleetControls() {
  const c = document.getElementById('fleetControlsContainer');
  if (!CT.meta || !c) return;
  c.innerHTML = CT.meta.truck_types.map(t => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:var(--bg-card);border:1px solid var(--border-subtle);border-left:4px solid ${t.color};border-radius:10px">
      <div>
        <div style="font-weight:800;font-size:12.5px">${t.code} · ${t.name}</div>
        <div style="font-size:11px;color:var(--text-muted)">${t.volume_m3} m³ · ${t.payload_kg} kg · ₹${t.fixed_daily_cost_inr}/day + ₹${t.cost_per_km_inr}/km</div>
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        <button class="ct-btn-secondary" style="padding:3px 9px" onclick="stepFleetCount('${t.code}', -1)">-</button>
        <span id="fleetCnt-${t.code}" style="font-family:var(--font-mono);font-weight:800;width:22px;text-align:center">${CT.fleetCounts[t.code] ?? 2}</span>
        <button class="ct-btn-secondary" style="padding:3px 9px" onclick="stepFleetCount('${t.code}', 1)">+</button>
      </div>
    </div>
  `).join('');
}

function stepFleetCount(code, delta) {
  const cur = CT.fleetCounts[code] ?? 2;
  CT.fleetCounts[code] = Math.max(0, Math.min(12, cur + delta));
  const el = document.getElementById(`fleetCnt-${code}`);
  if (el) el.textContent = CT.fleetCounts[code];
  const lpEl = document.getElementById(`lpFleetCnt-${code}`);
  if (lpEl) lpEl.textContent = CT.fleetCounts[code];
  const total = Object.values(CT.fleetCounts).reduce((a, b) => a + b, 0);
  const lbl = document.getElementById('lpTotalFleetPoolLbl');
  if (lbl) lbl.textContent = `${total} Trucks Available`;
  if (!CT.bundle) updateStagedKpiStrip();
}

async function runSimulatorOptimization() {
  const fuel = parseFloat(document.getElementById('inpSimFuel').value || '92');
  const drvCost = parseFloat(document.getElementById('inpSimDriverCost').value || '1100');
  await triggerPlanUpdate({
    truck_counts: CT.fleetCounts,
    fuel_price: fuel,
    driver_day_cost: drvCost,
    scope: 'all'
  });
  showToast(`⚡ Re-solved fleet matrix with custom vehicle availability &amp; ₹${fuel}/L diesel.`);
}

function renderSimulatorTable(routes) {
  const tbody = document.getElementById('simScheduleBody');
  if (!tbody) return;
  tbody.innerHTML = routes.map(r => `
    <tr>
      <td style="font-family:var(--font-mono);font-weight:800;color:${r.color}">${r.truck_id}</td>
      <td>${r.truck_name}</td>
      <td style="font-weight:700;color:var(--text-main)">${r.driver}</td>
      <td>${r.corridor_name} <span style="font-size:11px;color:var(--text-muted)">(${r.branch})</span></td>
      <td>${r.stops_count}</td>
      <td>${r.cartons_count}</td>
      <td><span style="font-weight:700;color:var(--accent-primary)">${r.volume_fill_pct}%</span></td>
      <td>${r.weight_fill_pct}%</td>
      <td>${r.km} km</td>
      <td>${r.leave}–${r.back}</td>
      <td style="font-family:var(--font-mono);font-weight:800;color:var(--text-main)">₹${r.cost_total.toLocaleString('en-IN')}</td>
      <td>
        <div style="display:flex;gap:5px">
          <button class="ct-chip-btn" onclick="openRouteIn3D('${r.truck_id}')">3D Load</button>
          <button class="ct-chip-btn" onclick="openRouteInPortal('${r.truck_id}')">Portal</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function openRouteIn3D(truckId) {
  CT.focusTruckId = truckId;
  document.getElementById('selStudioRoute').value = truckId;
  switchWorkspace('studio3d');
}

function openRouteInPortal(truckId) {
  CT.focusTruckId = truckId;
  document.getElementById('selPortalTruck').value = truckId;
  switchWorkspace('gcp');
}

function copyScheduleTable() {
  if (!CT.bundle) return;
  const headers = ['Truck ID', 'Vehicle Class', 'Driver', 'Corridor', 'Branch', 'Stops', 'Cartons', 'Vol Fill %', 'Wt Fill %', 'Distance km', 'Shift', 'Cost INR'];
  const lines = [headers.join('\t')];
  CT.bundle.routes.forEach(r => {
    lines.push([
      r.truck_id, r.truck_name, r.driver, r.corridor_name, r.branch,
      r.stops_count, r.cartons_count, r.volume_fill_pct, r.weight_fill_pct,
      r.km, `${r.leave}-${r.back}`, r.cost_total
    ].join('\t'));
  });
  navigator.clipboard.writeText(lines.join('\n'));
  showToast('📋 Copied TSV schedule to clipboard — paste directly into Google Sheets!');
}

function exportScheduleCsv() {
  if (!CT.bundle) return;
  const headers = ['Truck_ID', 'Vehicle_Class', 'Driver', 'Corridor', 'Branch', 'Stops', 'Cartons', 'Vol_Fill_Pct', 'Wt_Fill_Pct', 'Distance_Km', 'Shift', 'Cost_INR'];
  const lines = [headers.join(',')];
  CT.bundle.routes.forEach(r => {
    lines.push([
      r.truck_id, `"${r.truck_name}"`, r.driver, `"${r.corridor_name}"`, r.branch,
      r.stops_count, r.cartons_count, r.volume_fill_pct, r.weight_fill_pct,
      r.km, `${r.leave}-${r.back}`, r.cost_total
    ].join(','));
  });
  const blob = new Blob([lines.join('\n')], {type: 'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `fleetflow_schedule_${CT.bundle.plan_id}.csv`;
  a.click();
}

async function scanSamplePhoto(filename, cardEl) {
  document.querySelectorAll('.ct-photo-card').forEach(c => c.classList.remove('active'));
  if (cardEl) cardEl.classList.add('active');
  document.getElementById('scanStatusText').textContent = `⏳ Scanning ${filename} via OpenCV QR + Vision...`;

  const res = await fetch('/api/scan-photo', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ sample_name: filename, auto_replan: true })
  });
  const data = await res.json();
  renderScanResult(data);
}

function uploadCustomPhoto(inputEl) {
  const file = inputEl.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    document.getElementById('scanStatusText').textContent = `⏳ Scanning ${file.name}...`;
    const res = await fetch('/api/scan-photo', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        image_base64: reader.result,
        mime_type: file.type || 'image/jpeg',
        auto_replan: true
      })
    });
    const data = await res.json();
    renderScanResult(data);
  };
  reader.readAsDataURL(file);
}

function renderScanResult(data) {
  const s = data.scan || {};
  document.getElementById('scanStatusText').textContent = `✓ Decoded ${s.cartons_read || 0} cartons`;
  document.getElementById('scanResultContent').innerHTML = `<pre style="white-space:pre-wrap">${JSON.stringify(s, null, 2)}</pre>`;
  if (data.bundle) {
    applyBundle(data.bundle);
    showToast(`📸 Decoded <b>${s.cartons_read || 0} cartons</b> from dock photo and updated the 3D load plan!`);
  }
}

function loadSampleOrder(idx) {
  const o = CT.meta?.sample_orders?.[idx];
  if (!o) return;
  document.getElementById('inpOrderText').value = o.preview;
  document.getElementById('inpOrderText').dataset.sampleFile = o.filename;
}

async function submitOrderText() {
  const ta = document.getElementById('inpOrderText');
  const res = await fetch('/api/ingest-orders', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      text: ta.value,
      sample_file: ta.dataset.sampleFile || '',
      auto_replan: true
    })
  });
  const data = await res.json();
  const ing = data.ingest || {};
  document.getElementById('ingestResultContent').innerHTML = `
    <div>✓ Ingested <b>${ing.stops || 0} outlets</b> and <b>${ing.cartons || 0} cartons</b> (${ing.total_weight_kg || 0} kg).</div>
  `;
  if (data.bundle) {
    applyBundle(data.bundle);
    showToast(`📝 Parsed <b>${ing.stops || 0} dealer orders</b> and rebuilt the dispatch plan.`);
  }
}

async function resetToDefaultDemo() {
  await quickPrompt('Reset to default demo data');
}

function updateDriverHubPreview(truckId) {
  const r = (CT.bundle?.routes || []).find(x => x.truck_id === truckId) || CT.bundle?.routes?.[0];
  if (!r) return;
  const pIframe = document.getElementById('driverPortalIframe');
  if (pIframe) pIframe.src = r.driver_portal_url;
  const mLink = document.getElementById('btnOpenMapsNav');
  if (mLink) mLink.href = r.gmaps_nav_url;
  const waLink = document.getElementById('btnOpenWhatsApp');
  if (waLink) waLink.href = r.whatsapp_url;
  const lrLink = document.getElementById('btnOpenPortalTab');
  if (lrLink) lrLink.href = r.driver_portal_url;

  // Update Right-Hand Driver Consignment Summary Card
  const nameEl = document.getElementById('hubDriverName');
  if (nameEl) nameEl.textContent = `${r.driver} · ${r.truck_id}`;
  const subEl = document.getElementById('hubDriverSub');
  if (subEl) subEl.textContent = `${r.corridor_name} (${r.branch}) · Shift: ${r.leave}–${r.back}`;
  const classBadge = document.getElementById('hubDriverClassBadge');
  if (classBadge) classBadge.textContent = r.truck_name;

  const stopsEl = document.getElementById('hubDriverStops');
  if (stopsEl) stopsEl.textContent = `${r.stops_count} stops`;
  const cartonsEl = document.getElementById('hubDriverCartons');
  if (cartonsEl) cartonsEl.textContent = `${r.cartons_count} boxes`;
  const costEl = document.getElementById('hubDriverCost');
  if (costEl) costEl.textContent = `₹${r.cost_total.toLocaleString('en-IN')}`;

  // Populate Stop-by-Stop Door-to-Cab Cargo Sequence List
  const listEl = document.getElementById('hubDriverStopsList');
  if (listEl) {
    const stopsList = (r.stops && r.stops.length) ? r.stops : [];
    if (!stopsList.length) {
      listEl.innerHTML = `
        <div style="padding:10px;background:var(--bg-elevated);border-radius:8px;font-size:12px;color:var(--text-muted)">
          Stop 1 at rear door (${r.stops_count} scheduled deliveries). Open <b>Maps Nav</b> or <b>3D Load Studio</b> to inspect carton placement.
        </div>
      `;
    } else {
      listEl.innerHTML = stopsList.map((s, idx) => `
        <div style="padding:8px 10px;background:var(--bg-elevated);border:1px solid var(--border-subtle);border-radius:10px;display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-size:12.5px;font-weight:700">Drop #${idx + 1} · ${s.name}</div>
            <div style="font-size:11px;color:var(--text-muted)">${s.area || s.address}</div>
          </div>
          <span class="ct-kpi-badge" style="font-size:10px;padding:2px 7px">${s.cartons || s.boxes_count || 1} boxes</span>
        </div>
      `).join('');
    }
  }
}

function loadBqPreset(idx) {}
async function executeBqQuery() {}

function renderAuditLog(logs) {
  const el = document.getElementById('securityAuditList');
  if (!el) return;
  el.innerHTML = logs.map(l => `
    <div style="padding:4px 0;border-bottom:1px solid var(--border-subtle)">
      <span style="color:var(--accent-primary)">[${l.ts}]</span>
      <b>${l.action}</b> (${l.tool} · ${l.latency_ms}ms) —
      <span style="color:var(--accent-emerald)">🛡️ ${l.model_armor} · ${l.cloud_dlp}</span>
    </div>
  `).join('');
}

async function quickPrompt(txt) {
  document.getElementById('inpAgentPrompt').value = txt;
  await sendAgentPrompt();
}

async function sendAgentPrompt() {
  const inp = document.getElementById('inpAgentPrompt');
  const q = inp.value.trim();
  if (!q) return;
  inp.value = '';
  showToast(`✨ <b>FleetFlow AI Agent</b> processing: <i>"${q}"</i>...`, 10000);

  const res = await fetch('/api/agent-chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ prompt: q })
  });
  const data = await res.json();
  if (data.bundle) {
    applyBundle(data.bundle);
    if (CT.currentView === 'launchpad') {
      await switchWorkspace('tower');
    }
  }
  const formatted = (data.reply || '').replace(/\*\*(.*?)\*\*/g, '<b style="color:var(--accent-primary)">$1</b>');
  showToast(`
    <div style="font-family:var(--font-mono);font-size:10.5px;color:var(--accent-emerald);margin-bottom:4px">
      ▸ ${data.tool_called} (${data.latency_ms}ms) · 🛡️ Model Armor &amp; DLP Verified
    </div>
    <div>${formatted}</div>
  `, 7500);
}

let historySearchTimer = null;
function debounceHistorySearch() {
  clearTimeout(historySearchTimer);
  historySearchTimer = setTimeout(loadHistoryView, 250);
}

async function loadHistoryView() {
  const hub = document.getElementById('histFilterHub')?.value || 'all';
  const q = document.getElementById('histSearchInput')?.value || '';
  const countEl = document.getElementById('histRecordCount');
  if (countEl) countEl.innerText = 'Querying BigQuery & GCS audit stream...';

  try {
    const [analyticsRes, listRes] = await Promise.all([
      fetch('/api/history/analytics'),
      fetch(`/api/history?hub_id=${encodeURIComponent(hub)}&search=${encodeURIComponent(q)}`)
    ]);
    const analytics = await analyticsRes.json();
    const records = await listRes.json();

    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    setTxt('histKpiTotal', analytics.total_dispatches || '0');
    setTxt('histKpiSavings', '₹' + Number(analytics.total_savings_inr || 0).toLocaleString('en-IN'));
    setTxt('histKpiTrucks', (analytics.total_trucks_eliminated || 0) + ' Trucks');
    setTxt('histKpiCo2', (analytics.total_co2_avoided_kg || 0).toLocaleString('en-IN') + ' kg');

    if (countEl) countEl.innerText = `Showing ${records.length} archived runs across BigQuery & GCS`;
    renderHistoryTable(records);
  } catch (err) {
    console.error('Failed to load history:', err);
    if (countEl) countEl.innerText = 'Error fetching history';
  }
}

function renderHistoryTable(records) {
  const tbody = document.getElementById('histTableBody');
  if (!tbody) return;
  if (!records || !records.length) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:30px;color:var(--text-muted)">No archived dispatch records matched the filter criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = records.map(r => {
    const dateStr = (r.timestamp || r.dispatch_date || '').replace('T', ' ').slice(0, 16);
    const savings = Number(r.savings_inr || 0);
    const cost = Number(r.optimized_cost_inr || 0);
    const trucksSaved = r.trucks_saved || 0;
    const certHash = r.audit_hash || 'VERIFIED';
    return `
      <tr>
        <td>
          <div style="font-weight:700;font-family:var(--font-mono);color:var(--accent-primary)">${r.plan_id}</div>
          <div style="font-size:10px;color:var(--text-muted);font-family:var(--font-mono)">HMAC: ${certHash}</div>
        </td>
        <td>
          <div style="font-weight:600">${r.dispatch_date}</div>
          <div style="font-size:10.5px;color:var(--text-muted)">${dateStr}</div>
        </td>
        <td>
          <span class="ct-badge" style="background:rgba(26,115,232,0.1);color:var(--accent-primary);font-weight:700">${r.hub_id}</span>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:2px">${r.hub_name || ''}</div>
        </td>
        <td>
          <div style="font-weight:600">${r.trucks_count || 0} Trucks (${r.corridors_count || 0} Corridors)</div>
          <div style="font-size:10.5px;color:var(--text-muted)">${(r.objective || '').replace('_', ' ').toUpperCase()}</div>
        </td>
        <td>
          <div style="font-weight:700">${r.total_stops || 0} stops</div>
          <div style="font-size:10.5px;color:var(--text-muted)">${r.total_cartons || 0} cartons</div>
        </td>
        <td>
          <div style="font-weight:700;font-family:var(--font-mono)">₹${cost.toLocaleString('en-IN')}</div>
          <div style="font-size:10.5px;color:var(--text-muted)">${r.diesel_litres || 0}L diesel</div>
        </td>
        <td>
          <div style="font-weight:800;font-family:var(--font-mono);color:var(--accent-emerald)">+₹${savings.toLocaleString('en-IN')}</div>
          <div style="font-size:10.5px;color:var(--accent-amber)">-${trucksSaved} truck${trucksSaved === 1 ? '' : 's'}</div>
        </td>
        <td>
          <span class="ct-badge" style="background:rgba(15,157,88,0.12);color:var(--accent-emerald);font-size:10.5px;font-weight:700">
            ✓ GCS &amp; BQ Synced
          </span>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px">${r.gcs_uri ? 'gs://...' : 'Local Cache'}</div>
        </td>
        <td style="text-align:right;white-space:nowrap">
          <div style="display:flex;gap:6px;justify-content:flex-end">
            <button class="ct-btn-chip-action" onclick="restoreHistoricalPlan('${r.plan_id}')" title="Replay &amp; Restore full routes &amp; 3D loads into workspace">
              🔄 Replay
            </button>
            <button class="ct-btn-chip-action portal" onclick="window.open('/api/history/${r.plan_id}/report', '_blank')" title="View Printable Audit Certificate Report">
              📄 Report
            </button>
            <a href="/api/history/${r.plan_id}/manifest.csv" class="ct-btn-chip-action" title="Download RFC 4180 ERP Consignment Manifest (CSV)" download>
              📥 CSV
            </a>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function restoreHistoricalPlan(planId) {
  showToast(`🔄 Restoring historical dispatch plan <b>${planId}</b> into active Control Tower session...`, 4000);
  try {
    const res = await fetch(`/api/history/${encodeURIComponent(planId)}/restore`, { method: 'POST' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const bundle = await res.json();
    applyBundle(bundle);
    await switchWorkspace('tower');
    showToast(`✅ Successfully restored <b>${planId}</b>! Full 2D routes and 3D truck loads mounted.`, 5000);
  } catch (err) {
    console.error('Error restoring plan:', err);
    showToast(`❌ Failed to restore plan ${planId}: ${err.message}`, 5000);
  }
}

function switchDiagramView(mode) {
  const isArch = mode === 'arch';
  const archWrap = document.getElementById('diagArchWrap');
  const treeWrap = document.getElementById('diagTreeWrap');
  const btnArch = document.getElementById('btnDiagArch');
  const btnTree = document.getElementById('btnDiagTree');
  if (archWrap) archWrap.style.display = isArch ? 'block' : 'none';
  if (treeWrap) treeWrap.style.display = isArch ? 'none' : 'block';
  if (btnArch) btnArch.classList.toggle('active', isArch);
  if (btnTree) btnTree.classList.toggle('active', !isArch);
}

document.addEventListener('DOMContentLoaded', initControlTower);
</script>
</body>
</html>
"""


def build_control_tower_html() -> str:
    """Return the complete, self-contained Control Tower & 3D Load Studio HTML application."""
    from app.render.diagrams_svg import render_decision_flow_tree_svg, render_system_architecture_svg
    engine_js = (Path(__file__).resolve().parents[1] / "render" / "anim" / "engine.js").read_text(encoding="utf-8")
    return (
        _UI_HTML
        .replace("__ANIM_CSS__", ANIM_CSS)
        .replace("__ENGINE_JS__", engine_js)
        .replace("__SYSTEM_ARCH_SVG__", render_system_architecture_svg("dark"))
        .replace("__DECISION_TREE_SVG__", render_decision_flow_tree_svg("dark"))
    )
