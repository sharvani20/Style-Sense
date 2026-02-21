import streamlit as st
import requests
import time

st.set_page_config(page_title="Styling AI", layout="wide")

st.title("🪄 Styling AI - Personal Fashion Stylist")

# Sidebar for input
st.sidebar.header("Your Profile")
gender = st.sidebar.selectbox("I am:", ["Male", "Female"])
age    = st.sidebar.selectbox("Age group:", ["0-9","10-15","16-25","25-above"])
file   = st.sidebar.file_uploader("Upload a photo", type=["jpg","png","jpeg"])

# Main area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Preview")
    if file:
        st.image(file, caption="Your uploaded photo", use_column_width=True)

with col2:
    st.subheader("Analysis")
    if st.button("Analyze my style", key="analyze_btn", use_container_width=True):
        if not file:
            st.error("❌ Please upload a photo first")
        elif not gender:
            st.error("❌ Please select your gender")
        else:
            with st.spinner("🔍 Analyzing your style..."):
                try:
                    files = {"image": (file.name, file.getvalue(), file.type)}
                    data  = {"gender": gender, "age": age}
                    resp  = requests.post("http://127.0.0.1:5000/analyze", data=data, files=files, timeout=30)
                    
                    if resp.status_code == 400:
                        result = resp.json()
                        st.error(f"⚠️ {result.get('error', 'Analysis failed')}")
                    elif resp.status_code == 200:
                        result = resp.json()
                        if result.get("status") == "success":
                            st.success("✅ Analysis Complete!")
                            
                            # Display results
                            st.markdown("---")
                            st.subheader("📊 Your Style Profile")
                            
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("Skin Tone", result.get("skin_tone", "Unknown"))
                            with col_b:
                                st.metric("Gender", result.get("gender", ""))
                            with col_c:
                                st.metric("Age Group", result.get("age_group", ""))
                            
                            st.markdown("---")
                            st.subheader("👗 Recommendations")
                            st.write(result.get("recommendations", "No recommendations available"))
                            
                            st.markdown("---")
                            st.subheader("🛍️ Shop Now")
                            amazon = result.get("amazon_link", {})
                            if st.button(f"🔗 {amazon.get('name', 'Shop Now')}", use_container_width=True):
                                st.markdown(f"[Click here to shop on Amazon]({amazon.get('url', 'https://amazon.com')})", unsafe_allow_html=True)
                            
                    else:
                        st.error(f"❌ Unexpected error: {resp.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend. Make sure `python backend.py` is running on port 5000")
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. Backend taking too long to respond")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")