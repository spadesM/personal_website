import streamlit as st
from auth import check_password

check_password()

st.set_page_config(page_title="Lotto Predictor", layout="wide")
st.title("🎯 Lotto Predictor App")
st.write("Use the sidebar to navigate to different pages.")
