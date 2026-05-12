import streamlit as st

st.set_page_config(
    page_title="Property Hub",
    page_icon="🏙️",
    layout="wide"
)

st.title("🏙️ Property Hub")
st.markdown("---")

st.markdown("""
### Tools

Use the sidebar to navigate between tools.

| Tool | Description |
|------|-------------|
| 📊 Transactions | URA private residential transaction map |
| 🏗️ GLS | Government Land Sales tender history *(coming soon)* |
| 🗺️ Master Plan | URA zoning and GPR overlay *(coming soon)* |
| 🏥 Amenities | MRT, schools, amenity proximity *(coming soon)* |
""")

st.markdown("---")
st.caption("Data source: URA Data Service API · Updated every Tuesday and Friday")
