import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    /* EliteInteliA visual system: keep headings, controls, cards and navigation on one font scale. */
    /* EliteInteliA brand system — premium enterprise intelligence aesthetic. */
    :root{--eia-ink:#0b1220;--eia-muted:#667085;--eia-line:#e5e7eb;--eia-accent:#10b981;--eia-accent2:#06b6d4;--eia-surface:#ffffff;--eia-soft:#f5f8fa}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#07111f 0%,#0b1727 55%,#0f1f30 100%)!important;border-right:1px solid #1e3448}
    [data-testid="stSidebar"] *{color:#e7eef5!important}
    [data-testid="stSidebar"] hr{border-color:#294055!important}
    [data-testid="stSidebar"] .stButton button{background:transparent!important;border:1px solid transparent!important;text-align:left!important;border-radius:10px!important}
    [data-testid="stSidebar"] .stButton button:hover{background:#13263a!important;border-color:#27435a!important}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong{color:#8ea9bd!important;letter-spacing:.08em;font-size:.72rem!important}
    .brand-lockup{display:flex;align-items:center;gap:11px;padding:4px 2px 17px;margin-bottom:10px}
    .brand-mark{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#10b981,#06b6d4);color:#06131d;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:900;box-shadow:0 7px 20px rgba(6,182,212,.22)}
    .brand-name{font-size:19px;font-weight:850;letter-spacing:-.03em;color:#fff!important;line-height:1.05}
    .brand-sub{font-size:8px;letter-spacing:.17em;color:#8ea9bd!important;font-weight:800;margin-top:3px}
    .hero{background:radial-gradient(circle at 88% 15%,rgba(16,185,129,.13),transparent 27%),linear-gradient(135deg,#07111f 0%,#10283a 62%,#123044 100%)!important;border:1px solid #1e3a4f!important;box-shadow:0 14px 40px rgba(9,30,45,.12)!important;color:#fff!important}
    .hero h1,.hero p{color:#fff!important}.hero p{color:#b7c8d6!important}.eyebrow{color:#5eead4!important}
    .stApp .stButton button[kind="primary"]{background:linear-gradient(90deg,#059669,#0891b2)!important;border-color:#059669!important}
    .stApp .stButton button[kind="primary"] p{color:#fff!important}
    .stApp [data-testid="stMetric"]{background:#fff;border-color:#dbe4ea;box-shadow:0 3px 12px rgba(9,30,45,.04)}

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"],
    .stApp button, .stApp input, .stApp textarea, .stApp select {
        font-family: inherit !important;
    }
    .stApp h1{font-size:2rem !important;line-height:1.15 !important;font-weight:800 !important;letter-spacing:-.02em !important}
    .stApp h2{font-size:1.45rem !important;line-height:1.2 !important;font-weight:800 !important}
    .stApp h3{font-size:1.12rem !important;line-height:1.25 !important;font-weight:800 !important}
    .stApp h4{font-size:.98rem !important;line-height:1.3 !important;font-weight:750 !important}
    .stApp p, .stApp li, .stApp label, .stApp .stCaption{font-size:.90rem;line-height:1.45}
    .stApp .stButton button{font-size:.88rem !important;font-weight:700 !important;line-height:1.2 !important}
    [data-testid="stSidebar"] button{font-size:.84rem !important;font-weight:650 !important}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{font-size:.82rem;line-height:1.35}
    .hero{padding:1.2rem 1.5rem;border:1px solid #e5e7eb;border-radius:18px;background:linear-gradient(135deg,#fff,#f7f8fa);margin-bottom:1.2rem}
    .hero h1{font-size:2rem !important;margin:.2rem 0 !important}.hero p{color:#6b7280;margin:0}
    .eyebrow{font-size:.72rem;letter-spacing:.12em;font-weight:700;color:#ff3621}
    [data-testid="stMetric"]{border:1px solid #e5e7eb;padding:.7rem;border-radius:12px}

    .metric-card{border:1px solid #e5e7eb;border-radius:14px;background:#fff;padding:14px 16px;margin-bottom:10px;min-height:105px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
    .metric-label{font-size:13px;font-weight:700;color:#4b5563;margin-bottom:5px}.metric-value{font-size:28px;font-weight:800;color:#111827;line-height:1.05}.metric-hint{font-size:11px;color:#6b7280;margin-top:8px}
    .scope-card{border:1px solid #e5e7eb;border-radius:12px;background:#fff;padding:14px 16px;margin:5px 0 10px;min-height:105px}.scope-title{font-weight:800;font-size:15px;margin-bottom:7px}.scope-text{color:#6b7280;font-size:13px;line-height:1.45}
    .evidence-chip{display:inline-block;padding:4px 8px;border-radius:999px;background:#f3f4f6;font-size:11px;font-weight:700}
    .stepper{display:flex;gap:8px;overflow-x:auto;padding:10px 2px 16px;margin:6px 0 18px;scrollbar-width:thin}
    .stage{min-width:118px;flex:1 0 118px;padding:12px 10px;border:1px solid #e5e7eb;border-radius:12px;background:#fff;text-align:center;position:relative}
    .stage-icon{font-size:18px;font-weight:800;line-height:1.1;margin-bottom:7px}.stage-label{font-size:13px;font-weight:700;line-height:1.25}
    .stage.done{border-color:#22c55e;background:#f0fdf4}.stage.current{border-color:#ff3621;background:#fff7f5;box-shadow:0 0 0 2px rgba(255,54,33,.10)}.stage.locked{color:#6b7280;background:#fafafa}
    .stage:not(:last-child)::after{content:'→';position:absolute;right:-12px;top:31px;color:#9ca3af;font-weight:700;z-index:2}
    @media(max-width:900px){.stage{min-width:108px;flex-basis:108px}.stage:not(:last-child)::after{display:none}}
    </style>
    """, unsafe_allow_html=True)
