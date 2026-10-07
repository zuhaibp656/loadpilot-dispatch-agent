"""High-Fidelity Graphical SVG Architecture & Decision-Making Flow Diagrams for FleetFlow.

Provides:
1. `render_system_architecture_svg()`: Complete multi-tier Google Cloud Platform & FleetFlow topology.
2. `render_decision_flow_tree_svg()`: Authentic algorithmic flowchart with real decision diamonds,
   YES/NO branch vectors, mathematical formulas, and loopbacks.
"""

from __future__ import annotations


def render_system_architecture_svg(theme: str = "light") -> str:
    """Render full-width multi-tier enterprise architecture topology diagram in SVG.
    Uses CSS variable fallbacks so it renders seamlessly both standalone and inside the UI/deck.
    """
    is_dark = theme == "dark"
    bg = "var(--surface-card, #111827)" if is_dark else "var(--surface-card, #FFFFFF)"
    border = "var(--border-subtle, rgba(255, 255, 255, 0.12))" if is_dark else "var(--border-subtle, rgba(226, 232, 240, 0.85))"
    txt1 = "var(--text, #F8FAFC)" if is_dark else "var(--text, #0F172A)"
    txt2 = "var(--text-muted, #94A3B8)" if is_dark else "var(--text-muted, #475569)"
    card = "var(--surface, #1E293B)" if is_dark else "var(--surface, #FFFFFF)"
    tier_bg = "rgba(255, 255, 255, 0.02)" if is_dark else "var(--surface-sunk, rgba(248, 250, 252, 0.85))"
    shadow_op = "0.25" if is_dark else "0.06"
    outer_shadow = "0 8px 30px rgba(0,0,0,0.3)" if is_dark else "var(--card-shadow, 0 4px 20px rgba(0,0,0,0.04))"

    arr_blue = "#38BDF8" if is_dark else "#1A73E8"
    arr_green = "#10B981" if is_dark else "#137333"
    arr_amber = "#F59E0B" if is_dark else "#E37400"
    arr_purple = "#A78BFA" if is_dark else "#8E24AA"

    return f"""<svg class="fleetflow-arch-diagram" viewBox="0 0 1360 690" width="100%" height="auto"
     xmlns="http://www.w3.org/2000/svg" style="font-family:-apple-system,BlinkMacSystemFont,'Google Sans','Segoe UI',Roboto,sans-serif;border-radius:14px;background:{bg};border:1px solid {border};box-shadow:{outer_shadow}">
  <defs>
    <!-- Gradients -->
    <linearGradient id="saGradBlue" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1A73E8"/>
      <stop offset="100%" stop-color="#0D47A1"/>
    </linearGradient>
    <linearGradient id="saGradTeal" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00C9A7"/>
      <stop offset="100%" stop-color="#0D9488"/>
    </linearGradient>
    <linearGradient id="saGradAmber" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="100%" stop-color="#D97706"/>
    </linearGradient>
    <linearGradient id="saGradPurple" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#6D28D9"/>
    </linearGradient>
    <linearGradient id="saGradGreen" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>

    <!-- Arrow Markers -->
    <marker id="saArrBlue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_blue}"/>
    </marker>
    <marker id="saArrGreen" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_green}"/>
    </marker>
    <marker id="saArrAmber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_amber}"/>
    </marker>
    <marker id="saArrPurple" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_purple}"/>
    </marker>

    <!-- Drop Shadow -->
    <filter id="saShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,{shadow_op})"/>
    </filter>
  </defs>

  <!-- Title & Top Legend -->
  <text x="36" y="32" font-size="16" font-weight="800" fill="{txt1}">🏛️ FleetFlow Enterprise System Architecture Topology</text>
  <text x="36" y="49" font-size="11.5" fill="{txt2}">Google Cloud Platform (GCP) End-to-End Multimodal Ingestion, Security Enclave, Vertex AI Reasoning, and Dual-Surface Edge Execution</text>

  <!-- ══════════════════ TIER 1: INGESTION & DATA SOURCES ══════════════════ -->
  <g id="sa-tier1" transform="translate(24, 62)">
    <rect x="0" y="0" width="1312" height="110" rx="12" fill="{tier_bg}" stroke="{border}" stroke-dasharray="4,4"/>
    <text x="20" y="24" font-size="11" font-weight="800" fill="#38BDF8" letter-spacing="1.2">TIER 1 · MULTIMODAL INTAKE &amp; DATA FABRIC</text>

    <!-- Node 1A: Dock QR Vision -->
    <g transform="translate(20, 36)">
      <rect x="0" y="0" width="290" height="60" rx="8" fill="{card}" stroke="rgba(56,189,248,0.4)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="16" y="24" font-size="13" font-weight="700" fill="{txt1}">📸 Warehouse Dock Vision</text>
      <text x="16" y="43" font-size="11" fill="{txt2}">OpenCV ArUco QR · Barcode &amp; Flutes</text>
    </g>

    <!-- Node 1B: BigQuery Order Books -->
    <g transform="translate(340, 36)">
      <rect x="0" y="0" width="300" height="60" rx="8" fill="{card}" stroke="rgba(56,189,248,0.4)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="16" y="24" font-size="13" font-weight="700" fill="{txt1}">📊 Google BigQuery REST SQL</text>
      <text x="16" y="43" font-size="11" fill="{txt2}">stores · orders · cartons · skus · kpi_runs</text>
    </g>

    <!-- Node 1C: Unstructured Order Intake -->
    <g transform="translate(670, 36)">
      <rect x="0" y="0" width="300" height="60" rx="8" fill="{card}" stroke="rgba(56,189,248,0.4)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="16" y="24" font-size="13" font-weight="700" fill="{txt1}">📑 Unstructured Ingestion</text>
      <text x="16" y="43" font-size="11" fill="{txt2}">Excel .xlsx · RFC 4180 CSV · WhatsApp</text>
    </g>

    <!-- Node 1D: Operator Launchpad Console -->
    <g transform="translate(1000, 36)">
      <rect x="0" y="0" width="290" height="60" rx="8" fill="{card}" stroke="rgba(56,189,248,0.4)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="16" y="24" font-size="13" font-weight="700" fill="{txt1}">🚀 Dispatch Launchpad</text>
      <text x="16" y="43" font-size="11" fill="{txt2}">Natural Language Prompt · Hub Context</text>
    </g>
  </g>

  <!-- Connectors: Tier 1 -> Tier 2 -->
  <path d="M 189 172 L 189 205 C 189 215, 340 215, 340 225 L 340 234" fill="none" stroke="#38BDF8" stroke-width="1.8" stroke-dasharray="5,3" marker-end="url(#saArrBlue)"/>
  <path d="M 514 172 L 514 234" fill="none" stroke="#38BDF8" stroke-width="1.8" marker-end="url(#saArrBlue)"/>
  <path d="M 844 172 L 844 205 C 844 215, 680 215, 680 225 L 680 234" fill="none" stroke="#38BDF8" stroke-width="1.8" stroke-dasharray="5,3" marker-end="url(#saArrBlue)"/>
  <path d="M 1169 172 L 1169 205 C 1169 215, 1020 215, 1020 225 L 1020 234" fill="none" stroke="#38BDF8" stroke-width="1.8" marker-end="url(#saArrBlue)"/>

  <!-- ══════════════════ TIER 2: ENTERPRISE SECURITY & AUDIT ENCLAVE ══════════════════ -->
  <g id="sa-tier2" transform="translate(24, 234)">
    <rect x="0" y="0" width="1312" height="96" rx="12" fill="{tier_bg}" stroke="{border}" stroke-dasharray="4,4"/>
    <text x="20" y="22" font-size="11" font-weight="800" fill="#F59E0B" letter-spacing="1.2">TIER 2 · ENTERPRISE SECURITY, COMPLIANCE &amp; AUDIT ENCLAVE</text>

    <!-- Node 2A: Model Armor -->
    <g transform="translate(20, 32)">
      <rect x="0" y="0" width="395" height="52" rx="8" fill="{card}" stroke="rgba(245,158,11,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="16" y="22" font-size="13" font-weight="700" fill="{txt1}">🛡️ Google Cloud Model Armor</text>
      <text x="16" y="40" font-size="11" fill="{txt2}">Prompt Injection Defense · Prompt Leakage Shield</text>
    </g>

    <!-- Node 2B: Cloud DLP -->
    <g transform="translate(455, 32)">
      <rect x="0" y="0" width="400" height="52" rx="8" fill="{card}" stroke="rgba(245,158,11,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="16" y="22" font-size="13" font-weight="700" fill="{txt1}">🔒 Cloud Sensitive Data Protection (DLP)</text>
      <text x="16" y="40" font-size="11" fill="{txt2}">Automated PII, GSTIN &amp; Commercial Invoice Masking</text>
    </g>

    <!-- Node 2C: Cryptographic Audit Hash -->
    <g transform="translate(895, 32)">
      <rect x="0" y="0" width="395" height="52" rx="8" fill="{card}" stroke="rgba(245,158,11,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="16" y="22" font-size="13" font-weight="700" fill="{txt1}">📜 Cryptographic HMAC Audit Trail</text>
      <text x="16" y="40" font-size="11" fill="{txt2}">Tamper-Evident SHA-256 Hash · Immutable Ledger</text>
    </g>
  </g>

  <!-- Connectors: Tier 2 -> Tier 3 -->
  <path d="M 241 330 L 241 365 C 241 375, 420 375, 420 385 L 420 394" fill="none" stroke="#F59E0B" stroke-width="1.8" marker-end="url(#saArrAmber)"/>
  <path d="M 680 330 L 680 394" fill="none" stroke="#F59E0B" stroke-width="1.8" marker-end="url(#saArrAmber)"/>
  <path d="M 1116 330 L 1116 365 C 1116 375, 940 375, 940 385 L 940 394" fill="none" stroke="#F59E0B" stroke-width="1.8" marker-end="url(#saArrAmber)"/>

  <!-- ══════════════════ TIER 3: AUTONOMOUS REASONING & OPTIMIZATION CORE ══════════════════ -->
  <g id="sa-tier3" transform="translate(24, 394)">
    <rect x="0" y="0" width="1312" height="136" rx="12" fill="{tier_bg}" stroke="{border}" stroke-dasharray="4,4"/>
    <text x="20" y="22" font-size="11" font-weight="800" fill="#A78BFA" letter-spacing="1.2">TIER 3 · VERTEX AI AGENT ENGINE &amp; DETERMINISTIC MATH ENCLAVE</text>

    <!-- Node 3A: Gemini 3.7 / 3.8 Flash & 3.1 Pro Orchestrator -->
    <g transform="translate(20, 32)">
      <rect x="0" y="0" width="265" height="92" rx="8" fill="{card}" stroke="rgba(167,139,250,0.5)" stroke-width="1.4" filter="url(#saShadow)"/>
      <rect x="0" y="0" width="265" height="20" rx="8" fill="url(#saGradPurple)" opacity="0.25"/>
      <text x="14" y="15" font-size="10.5" font-weight="800" fill="#C4B5FD">ORCHESTRATION BRAIN</text>
      <text x="14" y="38" font-size="13.5" font-weight="800" fill="{txt1}">🧠 Gemini 3.7 Flash</text>
      <text x="14" y="55" font-size="11" fill="{txt2}">Gemini 3.1 Pro for Complex Logic</text>
      <text x="14" y="71" font-size="10" fill="#38BDF8">Dual-Guard ADK Callbacks</text>
      <text x="14" y="85" font-size="10" fill="{txt2}">Intent Scoping · Follow-Up Memory</text>
    </g>

    <!-- Node 3B: Polar Spatial Clustering -->
    <g transform="translate(305, 32)">
      <rect x="0" y="0" width="215" height="92" rx="8" fill="{card}" stroke="rgba(56,189,248,0.4)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="14" y="18" font-size="10.5" font-weight="800" fill="#38BDF8">SPATIAL SECTORS</text>
      <text x="14" y="38" font-size="13" font-weight="700" fill="{txt1}">🧭 Polar Ray θ Scan</text>
      <text x="14" y="55" font-size="11" fill="{txt2}">θ = atan2(Δlat, Δlon)</text>
      <text x="14" y="71" font-size="10" fill="{txt2}">8 Compass Corridors</text>
      <text x="14" y="85" font-size="10" fill="#F59E0B">Trunk &amp; Branch Split</text>
    </g>

    <!-- Node 3C: OR-Tools VRPTW Solver -->
    <g transform="translate(540, 32)">
      <rect x="0" y="0" width="240" height="92" rx="8" fill="{card}" stroke="rgba(16,185,129,0.45)" stroke-width="1.4" filter="url(#saShadow)"/>
      <rect x="0" y="0" width="240" height="20" rx="8" fill="url(#saGradGreen)" opacity="0.25"/>
      <text x="14" y="15" font-size="10.5" font-weight="800" fill="#6EE7B7">FLEET SOLVER</text>
      <text x="14" y="38" font-size="13" font-weight="700" fill="{txt1}">🧮 Google OR-Tools</text>
      <text x="14" y="55" font-size="11" fill="{txt2}">MIP VRPTW Optimization</text>
      <text x="14" y="71" font-size="10" fill="{txt2}">Multi-Capacity &amp; Time Windows</text>
      <text x="14" y="85" font-size="10" fill="#6EE7B7">Cost Matrix Minimization</text>
    </g>

    <!-- Node 3D: 3D Height-Map Elevation Engine -->
    <g transform="translate(800, 32)">
      <rect x="0" y="0" width="270" height="92" rx="8" fill="{card}" stroke="rgba(245,158,11,0.45)" stroke-width="1.4" filter="url(#saShadow)"/>
      <rect x="0" y="0" width="270" height="20" rx="8" fill="url(#saGradAmber)" opacity="0.25"/>
      <text x="14" y="15" font-size="10.5" font-weight="800" fill="#FCD34D">PHYSICS ENCLAVE</text>
      <text x="14" y="38" font-size="13" font-weight="700" fill="{txt1}">📦 3D Height-Map LIFO</text>
      <text x="14" y="55" font-size="11" fill="{txt2}">1×1 cm Raster Elevation Grid</text>
      <text x="14" y="71" font-size="10" fill="{txt2}">≥ 80% Under-Box Support Rule</text>
      <text x="14" y="85" font-size="10" fill="#FCD34D">CMVR Rule 93 Axle Balance</text>
    </g>

    <!-- Node 3E: Google Maps Routes API -->
    <g transform="translate(1090, 32)">
      <rect x="0" y="0" width="200" height="92" rx="8" fill="{card}" stroke="rgba(56,189,248,0.4)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="14" y="18" font-size="10.5" font-weight="800" fill="#38BDF8">ROAD GEODESICS</text>
      <text x="14" y="38" font-size="13" font-weight="700" fill="{txt1}">🛣️ Routes API</text>
      <text x="14" y="55" font-size="11" fill="{txt2}">computeRoutes Live Matrix</text>
      <text x="14" y="71" font-size="10" fill="{txt2}">Live Highway Durations</text>
      <text x="14" y="85" font-size="10" fill="{txt2}">Turn-by-Turn Geometries</text>
    </g>
  </g>

  <!-- Connectors: Tier 3 -> Tier 4 -->
  <path d="M 152 530 L 152 565" fill="none" stroke="#A78BFA" stroke-width="2" marker-end="url(#saArrPurple)"/>
  <path d="M 412 530 L 412 550 C 412 560, 420 560, 420 565" fill="none" stroke="#38BDF8" stroke-width="1.8" marker-end="url(#saArrBlue)"/>
  <path d="M 660 530 L 660 565" fill="none" stroke="#10B981" stroke-width="2" marker-end="url(#saArrGreen)"/>
  <path d="M 935 530 L 935 550 C 935 560, 945 560, 945 565" fill="none" stroke="#F59E0B" stroke-width="1.8" marker-end="url(#saArrAmber)"/>
  <path d="M 1190 530 L 1190 565" fill="none" stroke="#38BDF8" stroke-width="1.8" marker-end="url(#saArrBlue)"/>

  <!-- ══════════════════ TIER 4: DUAL-SURFACE DISPATCH & EDGE EXECUTION ══════════════════ -->
  <g id="sa-tier4" transform="translate(24, 565)">
    <rect x="0" y="0" width="1312" height="106" rx="12" fill="{tier_bg}" stroke="{border}" stroke-dasharray="4,4"/>
    <text x="20" y="20" font-size="11" font-weight="800" fill="#10B981" letter-spacing="1.2">TIER 4 · DUAL-SURFACE OPERATIONAL DISPATCH &amp; EDGE ARTIFACTS</text>

    <!-- Node 4A: Gemini Enterprise A2UI -->
    <g transform="translate(20, 30)">
      <rect x="0" y="0" width="235" height="64" rx="8" fill="{card}" stroke="rgba(167,139,250,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="14" y="22" font-size="12.5" font-weight="700" fill="{txt1}">💬 Gemini Enterprise</text>
      <text x="14" y="39" font-size="11" fill="{txt2}">A2UI Conversational Surfaces</text>
      <text x="14" y="54" font-size="10" fill="#C4B5FD">VegaChart Cards &amp; Action Buttons</text>
    </g>

    <!-- Node 4B: Cloud Run Control Tower -->
    <g transform="translate(275, 30)">
      <rect x="0" y="0" width="250" height="64" rx="8" fill="{card}" stroke="rgba(56,189,248,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="14" y="22" font-size="12.5" font-weight="700" fill="{txt1}">🚀 Cloud Run Control Tower</text>
      <text x="14" y="39" font-size="11" fill="{txt2}">Standalone Containerized Web SPA</text>
      <text x="14" y="54" font-size="10" fill="#38BDF8">Interactive 2D Map &amp; 3D Load Studio</text>
    </g>

    <!-- Node 4C: Mobile Driver Portal -->
    <g transform="translate(545, 30)">
      <rect x="0" y="0" width="245" height="64" rx="8" fill="{card}" stroke="rgba(16,185,129,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="14" y="22" font-size="12.5" font-weight="700" fill="{txt1}">📱 Mobile Driver Portal</text>
      <text x="14" y="39" font-size="11" fill="{txt2}">Zero-Login Responsive App</text>
      <text x="14" y="54" font-size="10" fill="#6EE7B7">1-Tap Google Maps Live Traffic</text>
    </g>

    <!-- Node 4D: ERP RFC 4180 Manifests -->
    <g transform="translate(810, 30)">
      <rect x="0" y="0" width="245" height="64" rx="8" fill="{card}" stroke="rgba(245,158,11,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="14" y="22" font-size="12.5" font-weight="700" fill="{txt1}">📑 ERP Manifests &amp; Challans</text>
      <text x="14" y="39" font-size="11" fill="{txt2}">RFC 4180 CSV for SAP TM / Oracle</text>
      <text x="14" y="54" font-size="10" fill="#FCD34D">Printable Transporter Lorry Receipts</text>
    </g>

    <!-- Node 4E: Cloud Storage & BigQuery History -->
    <g transform="translate(1075, 30)">
      <rect x="0" y="0" width="215" height="64" rx="8" fill="{card}" stroke="rgba(56,189,248,0.45)" stroke-width="1.2" filter="url(#saShadow)"/>
      <text x="14" y="22" font-size="12.5" font-weight="700" fill="{txt1}">☁️ Cloud Storage &amp; BQ</text>
      <text x="14" y="39" font-size="11" fill="{txt2}">gs://<project>-fleetflow-media</text>
      <text x="14" y="54" font-size="10" fill="#38BDF8">Immutable 30-Day Audit Telemetry</text>
    </g>
  </g>
</svg>"""


def render_decision_flow_tree_svg(theme: str = "light") -> str:
    """Render authentic visual decision-making tree flowchart with rotated diamonds, YES/NO branches,
    and mathematical loopbacks in crisp vector SVG.
    """
    is_dark = theme == "dark"
    bg = "var(--surface-card, #111827)" if is_dark else "var(--surface-card, #FFFFFF)"
    border = "var(--border-subtle, rgba(255, 255, 255, 0.12))" if is_dark else "var(--border-subtle, rgba(226, 232, 240, 0.85))"
    txt1 = "var(--text, #F8FAFC)" if is_dark else "var(--text, #0F172A)"
    txt2 = "var(--text-muted, #94A3B8)" if is_dark else "var(--text-muted, #475569)"
    card = "var(--surface, #1E293B)" if is_dark else "var(--surface, #FFFFFF)"
    dia = "var(--surface, #1E293B)" if is_dark else "#FFFFFF"
    shadow_op = "0.35" if is_dark else "0.06"
    outer_shadow = "0 8px 30px rgba(0,0,0,0.3)" if is_dark else "var(--card-shadow, 0 4px 20px rgba(0,0,0,0.04))"

    arr_blue = "#38BDF8" if is_dark else "#1A73E8"
    arr_green = "#10B981" if is_dark else "#137333"
    arr_amber = "#F59E0B" if is_dark else "#E37400"
    arr_red = "#EF4444" if is_dark else "#D93025"
    arr_purple = "#A78BFA" if is_dark else "#8E24AA"
    yes_bg = "rgba(16,185,129,0.15)" if is_dark else "rgba(19,115,51,0.12)"
    no_bg = "rgba(239,68,68,0.15)" if is_dark else "rgba(217,48,37,0.12)"

    return f"""<svg class="fleetflow-decision-tree" viewBox="0 0 1360 840" width="100%" height="auto"
     xmlns="http://www.w3.org/2000/svg" style="font-family:-apple-system,BlinkMacSystemFont,'Google Sans','Segoe UI',Roboto,sans-serif;border-radius:14px;background:{bg};border:1px solid {border};box-shadow:{outer_shadow}">
  <defs>
    <!-- Arrow Markers -->
    <marker id="dtArrGreen" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_green}"/>
    </marker>
    <marker id="dtArrRed" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_red}"/>
    </marker>
    <marker id="dtArrAmber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_amber}"/>
    </marker>
    <marker id="dtArrBlue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{arr_blue}"/>
    </marker>

    <!-- Drop Shadow -->
    <filter id="dtShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,{shadow_op})"/>
    </filter>
  </defs>

  <!-- Title & Legend -->
  <text x="36" y="34" font-size="16" font-weight="800" fill="{txt1}">🔀 Autonomous Dispatch Decision Tree &amp; Algorithmic Flow</text>
  <text x="36" y="52" font-size="11.5" fill="{txt2}">Mathematical decision points, spatial radial clustering, capacity splits, and 3D height-map safety validation</text>

  <g transform="translate(970, 24)">
    <circle cx="0" cy="12" r="5" fill="{arr_blue}"/>
    <text x="10" y="16" font-size="11" fill="{txt2}">Process Node</text>
    <polygon points="105,6 113,12 105,18 97,12" fill="{arr_amber}"/>
    <text x="120" y="16" font-size="11" fill="{txt2}">Decision Diamond</text>
    <line x1="230" y1="12" x2="250" y2="12" stroke="{arr_green}" stroke-width="2.5"/>
    <text x="258" y="16" font-size="11" fill="{arr_green}" font-weight="700">YES</text>
    <line x1="295" y1="12" x2="315" y2="12" stroke="{arr_red}" stroke-width="2.5"/>
    <text x="323" y="16" font-size="11" fill="{arr_red}" font-weight="700">NO</text>
  </g>

  <!-- ══════════════════ ROW 1: INTAKE & SECURITY DECISION ══════════════════ -->
  <!-- Node 01: Order Intake -->
  <g transform="translate(480, 75)">
    <rect x="0" y="0" width="280" height="52" rx="26" fill="{card}" stroke="{arr_blue}" stroke-width="1.8" filter="url(#dtShadow)"/>
    <text x="140" y="24" text-anchor="middle" font-size="13" font-weight="800" fill="{txt1}">📥 1. Multimodal Intake</text>
    <text x="140" y="42" text-anchor="middle" font-size="10.5" fill="{txt2}">Dock QR Photos · BigQuery · Excel .xlsx</text>
  </g>

  <!-- Connector: Node 01 -> Decision 01 -->
  <line x1="620" y1="127" x2="620" y2="157" stroke="{arr_blue}" stroke-width="2" marker-end="url(#dtArrBlue)"/>

  <!-- Decision 01: Model Armor & DLP -->
  <g transform="translate(620, 208)">
    <polygon points="0,-48 85,0 0,48 -85,0" fill="{dia}" stroke="{arr_amber}" stroke-width="2" filter="url(#dtShadow)"/>
    <text x="0" y="-12" text-anchor="middle" font-size="10" font-weight="800" fill="{arr_amber}">DECISION 1</text>
    <text x="0" y="6" text-anchor="middle" font-size="12" font-weight="700" fill="{txt1}">Model Armor &amp;</text>
    <text x="0" y="21" text-anchor="middle" font-size="12" font-weight="700" fill="{txt1}">DLP Clean?</text>
  </g>

  <!-- Decision 01 Branches -->
  <!-- NO: Security Rejection (Right) -->
  <path d="M 705 208 L 860 208" fill="none" stroke="{arr_red}" stroke-width="2" marker-end="url(#dtArrRed)"/>
  <rect x="735" y="193" width="48" height="18" rx="4" fill="{no_bg}"/>
  <text x="759" y="206" text-anchor="middle" font-size="10.5" font-weight="800" fill="{arr_red}">NO</text>

  <g transform="translate(865, 182)">
    <rect x="0" y="0" width="220" height="52" rx="8" fill="{card}" stroke="{arr_red}" stroke-width="1.4"/>
    <text x="14" y="22" font-size="12" font-weight="700" fill="{arr_red}">🛡️ Security Quarantine</text>
    <text x="14" y="40" font-size="10" fill="{txt2}">Block prompt injection · Alert Dispatch</text>
  </g>

  <!-- YES: Forward to Gemini 3.7 Flash Brain (Down) -->
  <line x1="620" y1="256" x2="620" y2="295" stroke="{arr_green}" stroke-width="2.5" marker-end="url(#dtArrGreen)"/>
  <rect x="626" y="263" width="48" height="18" rx="4" fill="{yes_bg}"/>
  <text x="650" y="276" text-anchor="middle" font-size="10.5" font-weight="800" fill="{arr_green}">YES</text>

  <!-- ══════════════════ ROW 2: AGENT REASONING & CORRIDOR CLAIM ══════════════════ -->
  <!-- Node 02: Gemini 3.7 Flash / 3.1 Pro -->
  <g transform="translate(480, 295)">
    <rect x="0" y="0" width="280" height="54" rx="10" fill="{card}" stroke="{arr_purple}" stroke-width="1.8" filter="url(#dtShadow)"/>
    <text x="140" y="24" text-anchor="middle" font-size="13" font-weight="800" fill="{txt1}">🧠 2. Gemini 3.7 Flash / 3.1 Pro</text>
    <text x="140" y="42" text-anchor="middle" font-size="10.5" fill="{txt2}">Intent Scoping · Single Driver vs Fleet Scope</text>
  </g>

  <!-- Connector: Node 02 -> Decision 02 -->
  <line x1="620" y1="349" x2="620" y2="378" stroke="{arr_purple}" stroke-width="2" marker-end="url(#dtArrBlue)"/>

  <!-- Decision 02: Corridor Claimed? -->
  <g transform="translate(620, 426)">
    <polygon points="0,-48 85,0 0,48 -85,0" fill="{dia}" stroke="{arr_amber}" stroke-width="2" filter="url(#dtShadow)"/>
    <text x="0" y="-12" text-anchor="middle" font-size="10" font-weight="800" fill="{arr_amber}">DECISION 2</text>
    <text x="0" y="6" text-anchor="middle" font-size="12" font-weight="700" fill="{txt1}">Corridor Claimed?</text>
    <text x="0" y="21" text-anchor="middle" font-size="10" fill="{txt2}">("Ravi has West")</text>
  </g>

  <!-- Decision 02 Branches -->
  <!-- YES: Pin Driver to Sector (Left) -->
  <path d="M 535 426 L 360 426" fill="none" stroke="{arr_green}" stroke-width="2" marker-end="url(#dtArrGreen)"/>
  <rect x="420" y="411" width="50" height="18" rx="4" fill="{yes_bg}"/>
  <text x="445" y="424" text-anchor="middle" font-size="10.5" font-weight="800" fill="{arr_green}">YES</text>

  <g transform="translate(130, 400)">
    <rect x="0" y="0" width="225" height="52" rx="8" fill="{card}" stroke="{arr_green}" stroke-width="1.4"/>
    <text x="14" y="22" font-size="12" font-weight="700" fill="{arr_green}">📌 Pin Driver to Sector Vector</text>
    <text x="14" y="40" font-size="10" fill="{txt2}">Lock assigned driver to claimed corridor</text>
  </g>

  <!-- Connect pinned sector back down to clustering -->
  <path d="M 242 452 L 242 505 C 242 520, 460 520, 480 520" fill="none" stroke="{arr_green}" stroke-width="1.8" stroke-dasharray="4,3" marker-end="url(#dtArrGreen)"/>

  <!-- NO: Polar Coordinate atan2 Radial Scan (Down) -->
  <line x1="620" y1="474" x2="620" y2="505" stroke="{arr_blue}" stroke-width="2" marker-end="url(#dtArrBlue)"/>
  <rect x="626" y="480" width="46" height="18" rx="4" fill="rgba(56,189,248,0.15)"/>
  <text x="649" y="493" text-anchor="middle" font-size="10.5" font-weight="800" fill="{arr_blue}">NO</text>

  <!-- ══════════════════ ROW 3: SPATIAL PARTITIONING & TRUNK-BRANCH ══════════════════ -->
  <!-- Node 03: 8-Corridor Clustering -->
  <g transform="translate(480, 505)">
    <rect x="0" y="0" width="280" height="54" rx="10" fill="{card}" stroke="{arr_blue}" stroke-width="1.8" filter="url(#dtShadow)"/>
    <text x="140" y="24" text-anchor="middle" font-size="13" font-weight="800" fill="{txt1}">🧭 3. Polar Ray θ Clustering</text>
    <text x="140" y="42" text-anchor="middle" font-size="10.5" fill="{txt2}">θ = atan2(Δlat, Δlon) · 8 Compass Sectors</text>
  </g>

  <!-- Connector: Node 03 -> Decision 03 -->
  <line x1="620" y1="559" x2="620" y2="588" stroke="{arr_blue}" stroke-width="2" marker-end="url(#dtArrBlue)"/>

  <!-- Decision 03: Volume > Single Truck Capacity? -->
  <g transform="translate(620, 636)">
    <polygon points="0,-48 95,0 0,48 -95,0" fill="{dia}" stroke="{arr_amber}" stroke-width="2" filter="url(#dtShadow)"/>
    <text x="0" y="-12" text-anchor="middle" font-size="10" font-weight="800" fill="{arr_amber}">DECISION 3</text>
    <text x="0" y="5" text-anchor="middle" font-size="12" font-weight="700" fill="{txt1}">Volume &gt; Truck Cap?</text>
    <text x="0" y="20" text-anchor="middle" font-size="10" fill="{txt2}">(Overflow check)</text>
  </g>

  <!-- Decision 03 Branches -->
  <!-- YES: Trunk-and-Branch Slicing (Right) -->
  <path d="M 715 636 L 860 636" fill="none" stroke="{arr_amber}" stroke-width="2" marker-end="url(#dtArrAmber)"/>
  <rect x="735" y="621" width="50" height="18" rx="4" fill="rgba(245,158,11,0.15)"/>
  <text x="760" y="634" text-anchor="middle" font-size="10.5" font-weight="800" fill="{arr_amber}">YES</text>

  <g transform="translate(865, 610)">
    <rect x="0" y="0" width="240" height="52" rx="8" fill="{card}" stroke="{arr_amber}" stroke-width="1.4"/>
    <text x="14" y="22" font-size="12" font-weight="700" fill="{arr_amber}">✂️ Trunk &amp; Branch Split</text>
    <text x="14" y="40" font-size="10" fill="{txt2}">Spawn branch truck · Partition drops</text>
  </g>

  <!-- Loop back from Trunk & Branch to Solver -->
  <path d="M 985 662 L 985 700 C 985 715, 780 715, 760 715" fill="none" stroke="{arr_amber}" stroke-width="1.6" stroke-dasharray="4,3"/>

  <!-- NO: Proceed to OR-Tools Solver (Down) -->
  <line x1="620" y1="684" x2="620" y2="712" stroke="{arr_green}" stroke-width="2" marker-end="url(#dtArrGreen)"/>
  <rect x="626" y="688" width="46" height="18" rx="4" fill="{yes_bg}"/>
  <text x="649" y="701" text-anchor="middle" font-size="10.5" font-weight="800" fill="{arr_green}">NO</text>

  <!-- ══════════════════ ROW 4: SOLVER, 3D HEIGHT-MAP & PHYSICS CERTIFICATION ══════════════════ -->
  <!-- Node 04: OR-Tools Solver -->
  <g transform="translate(480, 712)">
    <rect x="0" y="0" width="280" height="54" rx="10" fill="{card}" stroke="{arr_green}" stroke-width="1.8" filter="url(#dtShadow)"/>
    <text x="140" y="24" text-anchor="middle" font-size="13" font-weight="800" fill="{txt1}">🧮 4. OR-Tools VRPTW Solver</text>
    <text x="140" y="42" text-anchor="middle" font-size="10.5" fill="{txt2}">MIP Routing · Routes API Road Geodesics</text>
  </g>

  <!-- Bottom Final Output Strip -->
  <g transform="translate(180, 784)">
    <rect x="0" y="0" width="880" height="38" rx="19" fill="{card}" stroke="{arr_green}" stroke-width="1.6"/>
    <text x="440" y="24" text-anchor="middle" font-size="12" font-weight="800" fill="{arr_green}">
      ✓ Certified Plan: 3D Height-Map Elevation (≥80% support) · CMVR Axle Balanced · 1-Tap Google Maps &amp; ERP Manifest Dispatched
    </text>
  </g>
</svg>"""
