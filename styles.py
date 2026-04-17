"""
COMS — Design System & CSS Overrides
Cyber-Cloud Dark Theme with Glassmorphism
"""

def get_css():
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ═══════════════════════════════════════════
   ROOT VARIABLES
   ═══════════════════════════════════════════ */
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #1c2333;
    --bg-glass: rgba(22, 27, 34, 0.65);
    --bg-glass-hover: rgba(22, 27, 34, 0.85);
    --border-glass: rgba(0, 229, 160, 0.12);
    --border-subtle: rgba(255, 255, 255, 0.06);
    --accent: #00E5A0;
    --accent-dim: rgba(0, 229, 160, 0.15);
    --accent-glow: rgba(0, 229, 160, 0.4);
    --danger: #ef4444;
    --danger-dim: rgba(239, 68, 68, 0.15);
    --warning: #f59e0b;
    --warning-dim: rgba(245, 158, 11, 0.15);
    --info: #3b82f6;
    --info-dim: rgba(59, 130, 246, 0.15);
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #484f58;
    --font-ui: 'Plus Jakarta Sans', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --radius: 12px;
    --radius-lg: 16px;
    --shadow-glow: 0 0 20px rgba(0, 229, 160, 0.08);
}

/* ═══════════════════════════════════════════
   GLOBAL RESETS & HIDE STREAMLIT DEFAULTS
   ═══════════════════════════════════════════ */
#MainMenu, footer, header, .stDeployButton,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

.stApp {
    background: var(--bg-primary) !important;
    font-family: var(--font-ui) !important;
    color: var(--text-primary) !important;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

/* ═══════════════════════════════════════════
   SCROLLBAR
   ═══════════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ═══════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #111922 50%, #0f1923 100%) !important;
    border-right: 1px solid var(--border-glass) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {
    color: var(--text-secondary) !important;
    font-family: var(--font-ui) !important;
    font-weight: 600 !important;
    font-size: 0.7rem !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    text-transform: none !important;
    letter-spacing: 0 !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    padding: 8px 12px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
    background: var(--accent-dim) !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"],
[data-testid="stSidebar"] .stRadio [data-checked="true"] {
    background: var(--accent-dim) !important;
    color: var(--accent) !important;
}

/* ═══════════════════════════════════════════
   SELECTBOX & INPUT OVERRIDES
   ═══════════════════════════════════════════ */
.stSelectbox > div > div,
.stTextInput > div > div > input,
[data-testid="stChatInput"] textarea {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-ui) !important;
}
.stSelectbox > div > div:focus-within,
.stTextInput > div > div > input:focus,
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-dim) !important;
}

/* ═══════════════════════════════════════════
   BUTTONS
   ═══════════════════════════════════════════ */
.stButton > button {
    background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-ui) !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.25s ease !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    box-shadow: var(--shadow-glow) !important;
    transform: translateY(-1px) !important;
    color: var(--accent) !important;
}

/* ═══════════════════════════════════════════
   METRICS
   ═══════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: var(--bg-glass) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1.2rem 1.5rem !important;
    transition: all 0.3s ease !important;
}
[data-testid="stMetric"]:hover {
    border-color: var(--accent) !important;
    box-shadow: var(--shadow-glow) !important;
    transform: translateY(-2px) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
}
[data-testid="stMetricValue"] {
    color: var(--accent) !important;
    font-weight: 800 !important;
    font-size: 2rem !important;
}
[data-testid="stMetricDelta"] { font-weight: 600 !important; }

/* ═══════════════════════════════════════════
   CHAT MESSAGES
   ═══════════════════════════════════════════ */
[data-testid="stChatMessage"] {
    background: var(--bg-glass) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1rem 1.2rem !important;
    margin-bottom: 0.75rem !important;
    font-family: var(--font-ui) !important;
}
[data-testid="stChatMessage"][data-testid*="user"],
.stChatMessage:nth-child(odd) {
    border-left: 3px solid var(--info) !important;
}
[data-testid="stChatMessage"][data-testid*="assistant"],
.stChatMessage:nth-child(even) {
    border-left: 3px solid var(--accent) !important;
}

/* ═══════════════════════════════════════════
   EXPANDER (Admin Tickets)
   ═══════════════════════════════════════════ */
.streamlit-expanderHeader {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-ui) !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius) var(--radius) !important;
}
details {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius) !important;
}
details summary {
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* ═══════════════════════════════════════════
   JSON VIEWER
   ═══════════════════════════════════════════ */
[data-testid="stJson"] {
    background: var(--bg-primary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-mono) !important;
}

/* ═══════════════════════════════════════════
   TABS
   ═══════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--bg-secondary) !important;
    border-radius: var(--radius) !important;
    padding: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    font-family: var(--font-ui) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--accent-dim) !important;
    color: var(--accent) !important;
}

/* ═══════════════════════════════════════════
   CUSTOM HTML COMPONENTS
   ═══════════════════════════════════════════ */

/* Glass Card */
.glass-card {
    background: var(--bg-glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.glass-card:hover {
    border-color: rgba(0, 229, 160, 0.3);
    box-shadow: var(--shadow-glow);
}

/* Pipeline Stepper */
.pipeline-container {
    background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin: 1rem 0;
}
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    margin: 6px 0;
    border-radius: 10px;
    font-family: var(--font-ui);
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.3s ease;
}
.pipeline-step.completed {
    background: rgba(0, 229, 160, 0.08);
    color: var(--accent);
    border-left: 3px solid var(--accent);
}
.pipeline-step.active {
    background: rgba(59, 130, 246, 0.1);
    color: var(--info);
    border-left: 3px solid var(--info);
    animation: pulseStep 1.5s ease-in-out infinite;
}
.pipeline-step.pending {
    color: var(--text-muted);
    border-left: 3px solid var(--text-muted);
    opacity: 0.5;
}
@keyframes pulseStep {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

/* Resource Card */
.resource-card {
    background: linear-gradient(135deg, rgba(0, 229, 160, 0.05), rgba(0, 229, 160, 0.02));
    border: 1px solid rgba(0, 229, 160, 0.2);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin: 1rem 0;
}
.resource-card h4 {
    color: var(--accent);
    font-family: var(--font-ui);
    margin: 0 0 0.75rem 0;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 700;
}
.resource-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-subtle);
    font-family: var(--font-ui);
}
.resource-row:last-child { border-bottom: none; }
.resource-label { color: var(--text-secondary); font-size: 0.85rem; }
.resource-value { color: var(--text-primary); font-weight: 600; font-family: var(--font-mono); font-size: 0.85rem; }

/* Risk Badge */
.risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    font-family: var(--font-ui);
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.risk-low { background: var(--accent-dim); color: var(--accent); }
.risk-medium { background: var(--warning-dim); color: var(--warning); }
.risk-high { background: var(--danger-dim); color: var(--danger); }
.risk-critical { background: rgba(239, 68, 68, 0.25); color: #ff6b6b; border: 1px solid rgba(239,68,68,0.3); }

/* Online Indicator */
.online-indicator {
    display: inline-block;
    width: 8px; height: 8px;
    background: var(--accent);
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 2s ease-in-out infinite;
    box-shadow: 0 0 8px var(--accent-glow);
}
@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 8px var(--accent-glow); }
    50% { opacity: 0.4; box-shadow: 0 0 2px var(--accent-glow); }
}

/* Sidebar Brand */
.sidebar-brand {
    padding: 1rem 0 1.5rem 0;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 1.5rem;
}
.sidebar-brand h1 {
    font-family: var(--font-ui);
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--text-primary);
    margin: 0;
    letter-spacing: -0.5px;
}
.sidebar-brand .subtitle {
    font-size: 0.72rem;
    color: var(--text-secondary);
    margin-top: 4px;
    font-weight: 500;
}

/* Quick Prompt Buttons */
.quick-prompt {
    display: block;
    width: 100%;
    padding: 10px 14px;
    margin: 5px 0;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    color: var(--text-secondary);
    font-family: var(--font-ui);
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.25s ease;
    text-align: left;
}
.quick-prompt:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-dim);
    transform: translateX(4px);
}

/* Audit Log Row */
.audit-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 16px;
    background: var(--bg-glass);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius);
    margin-bottom: 8px;
    font-family: var(--font-ui);
    transition: all 0.2s ease;
}
.audit-row:hover {
    border-color: var(--border-glass);
    background: var(--bg-glass-hover);
}
.audit-time {
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    min-width: 140px;
}
.audit-action { color: var(--text-primary); flex: 1; font-weight: 500; font-size: 0.88rem; }
.audit-user { color: var(--text-secondary); font-size: 0.8rem; min-width: 100px; text-align: right; }

/* Page Title */
.page-title {
    font-family: var(--font-ui);
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}
.page-subtitle {
    color: var(--text-secondary);
    font-size: 0.9rem;
    font-weight: 400;
    margin-bottom: 2rem;
}

/* Approval Ticket */
.ticket-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
.ticket-id {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--text-muted);
}
.ticket-service {
    font-family: var(--font-ui);
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--text-primary);
    margin: 8px 0 4px 0;
}
.ticket-desc {
    color: var(--text-secondary);
    font-size: 0.88rem;
    line-height: 1.5;
}

/* Chart container */
.chart-wrapper {
    background: var(--bg-glass);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
}

/* Plotly overrides */
.js-plotly-plot .plotly .modebar { display: none !important; }

/* Section Divider */
.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-glass), transparent);
    margin: 2rem 0;
}

/* Streamlit's native containers */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}

/* Override native hr */
hr { border-color: var(--border-subtle) !important; }

/* Code blocks */
code, .stCodeBlock {
    font-family: var(--font-mono) !important;
}
</style>
"""
