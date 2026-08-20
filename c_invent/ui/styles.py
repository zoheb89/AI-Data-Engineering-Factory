import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    .hero{padding:1.2rem 1.5rem;border:1px solid #e5e7eb;border-radius:18px;
          background:linear-gradient(135deg,#fff,#f7f8fa);margin-bottom:1.2rem}
    .hero h1{font-size:2rem;margin:.2rem 0}
    .hero p{color:#6b7280;margin:0}
    .eyebrow{font-size:.72rem;letter-spacing:.12em;font-weight:700;color:#ff3621}
    [data-testid="stMetric"]{border:1px solid #e5e7eb;padding:.7rem;border-radius:12px}
    </style>
    """, unsafe_allow_html=True)
