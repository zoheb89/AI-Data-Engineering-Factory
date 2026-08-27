# Streamlit Cloud deployment fix

Streamlit Cloud expects the configured main module at repository root when the app is configured as `app.py`.

This release adds the root `app.py` entrypoint and root `requirements.txt`.

Deploy with:
- Main file: `app.py`
- Branch: `main`
- Repository root: `/`

The application imports the backend through `backend/`, so no change to the existing architecture is required.

If an older deployment still reports that `app.py` does not exist, push this commit to the configured branch and then use **Reboot app** in Streamlit Cloud.
