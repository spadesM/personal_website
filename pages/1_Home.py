import streamlit as st
from auth import check_password

check_password()

st.title("🏠 Home")
st.write("""
Welcome to the Lotto Predictor App!  
Navigate to the **Predictions** page to see the numbers predicted using the UCB algorithm.
""")
