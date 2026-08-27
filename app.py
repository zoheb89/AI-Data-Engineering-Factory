"""
EliteInteliA Intelligence Factory
Streamlit Cloud entry point.

This file is intentionally thin: the delivery/domain services remain in backend/.
"""
from pathlib import Path
import os, sys

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import streamlit as st

st.set_page_config(
    page_title="EliteInteliA Intelligence Factory",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Try to reuse the existing Streamlit application if the repository already
# provides one; otherwise expose the API-backed control plane.
existing = BACKEND / "app.py"
if existing.exists():
    source = existing.read_text(encoding="utf-8", errors="ignore")
    # Avoid recursively executing another Streamlit entry point.
    if "st.set_page_config" in source and "streamlit" in source:
        # Execute the existing application in its own global namespace.
        exec(compile(source, str(existing), "exec"), {"__name__": "__main__", "__file__": str(existing)})
    else:
        st.title("EliteInteliA Intelligence Factory")
        st.caption("Enterprise Control Plane")
        st.info("Backend is present. Configure the LLM gateway and open an engagement to begin.")
else:
    st.title("EliteInteliA Intelligence Factory")
    st.caption("Enterprise Control Plane")
    st.warning("Backend application entry point was not found.")
