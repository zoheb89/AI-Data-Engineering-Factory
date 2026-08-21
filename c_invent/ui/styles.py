import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    .hero{padding:1.2rem 1.5rem;border:1px solid #e5e7eb;border-radius:18px;background:linear-gradient(135deg,#fff,#f7f8fa);margin-bottom:1.2rem}
    .hero h1{font-size:2rem;margin:.2rem 0}.hero p{color:#6b7280;margin:0}
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
