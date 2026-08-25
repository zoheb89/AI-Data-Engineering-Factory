# EliteInteliA Intelligence Factory — 0.1.26 Adaptive UI

## UI fix
- Added explicit Appearance control: System / Light / Dark.
- System follows browser/OS `prefers-color-scheme`.
- Replaced hard-coded light/dark card, sidebar, architecture and control colors with semantic CSS variables.
- Improved native Streamlit inputs/selects/buttons for both themes.
- Preserved EliteInteliA green/cyan visual identity in both themes.
- Architecture and platform-fit visuals now inherit the selected theme.
- Mobile-width behavior retained for lifecycle and architecture sections.

## Validation
- Python syntax compilation passed.
- Existing test suite: 41 passed.
- Streamlit runtime smoke test could not be executed in this build container because the `streamlit` executable is not installed.
