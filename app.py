import streamlit as st
import requests

st.set_page_config(page_title="StyleAI", layout="wide")

st.title("👗 StyleAI - AI Powered Fashion Stylist")

uploaded_file = st.file_uploader("Upload Your Photo", type=["jpg", "png"])
gender = st.selectbox("Select Gender", ["Male", "Female"])

if st.button("Analyze Style"):
    if uploaded_file:
        files = {"image": uploaded_file.getvalue()}
        data = {"gender": gender}

        response = requests.post(
            "http://127.0.0.1:5000/analyze",
            files={"image": uploaded_file},
            data=data
        )

        result = response.json()

        st.subheader("Detected Skin Tone")
        st.success(result["skin_tone"])

        st.subheader("Styling Recommendations")
        st.write(result["recommendations"])

        st.subheader("Shop Recommended Outfits")
        for store, link in result["shopping_links"].items():
            st.markdown(f"[Shop on {store}]({link})")
    else:
        st.warning("Please upload an image.")