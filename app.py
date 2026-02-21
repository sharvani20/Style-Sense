
import streamlit as st
import requests
import time

st.set_page_config(page_title="StyleAI", layout="wide")

if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'result' not in st.session_state:
    st.session_state.result = None


def header_html(bg_color):
    return f"""
    <style>
      .topbar {{background:{bg_color}; color: white; padding: 18px; border-radius:6px;}}
      .topbar a {{color: rgba(255,255,255,0.95); margin-left:18px; text-decoration:none}}
    </style>
    <div class="topbar">
      <div style="display:flex;align-items:center;gap:12px; font-weight:700; font-size:20px">🪄 Styling AI</div>
      <div style="float:right"> <a href="#" onclick="window.location.reload();">Home</a></div>
    </div>
    """


def show_home():
    st.markdown(header_html('#4DA6FF'), unsafe_allow_html=True)
    st.markdown("""
    <div style='display:flex;justify-content:center;margin-top:24px'>
      <div style='background:#E8F4FF;color:#053657;padding:40px;border-radius:12px;max-width:1000px;width:100%'>
        <h1 style='font-size:40px;margin:0 0 8px'>Your Personal AI<br/>Fashion Stylist</h1>
        <p style='font-size:16px;margin:0 0 16px'>Upload your photo and get personalized styling recommendations based on your skin tone</p>
        <a href='?start=1' style='background:#FFE082;border:none;padding:10px 18px;border-radius:28px;font-weight:700;cursor:pointer;text-decoration:none;color:#053657'>Get Started</a>
      </div>
    </div>
    """, unsafe_allow_html=True)


def show_upload():
    st.markdown(header_html('#E91E63'), unsafe_allow_html=True)
    st.write('')
    st.header("Let's Style You")
    gender = st.radio('I am:', ['Male', 'Female'], index=0, horizontal=True)
    uploaded_file = st.file_uploader('Drag & drop your photo or click to browse', type=['png','jpg','jpeg','webp'])

    col1, col2 = st.columns([1,1])
    with col1:
        if uploaded_file is not None:
            st.image(uploaded_file, caption='Selected image', use_column_width=True)
    with col2:
        st.write('')
        if st.button('Analyze Style'):
            if not uploaded_file:
                st.warning('Please upload an image.')
                return
            # call backend
            with st.spinner('Analyzing your style...'):
                try:
                    files = {'image': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {'gender': gender}
                    resp = requests.post('http://127.0.0.1:5000/analyze', files=files, data=data, timeout=60)
                    if resp.status_code != 200:
                        st.error(f'Backend error: {resp.status_code} - {resp.text}')
                        return
                    st.session_state.result = resp.json()
                    st.session_state.page = 'results'
                    # small pause to allow UI update
                    time.sleep(0.5)
                except requests.exceptions.RequestException as e:
                    st.error(f'Error connecting to backend: {e}')


def show_results():
    st.markdown(header_html('#E91E63'), unsafe_allow_html=True)
    res = st.session_state.result
    if not res:
        st.error('No results available. Please analyze an image first.')
        if st.button('Back to Upload'):
            st.session_state.page = 'upload'
        return

    st.title('Your Personalized Style Profile')
    st.subheader('Skin Tone Analysis')
    st.success(res.get('skin_tone', 'Unknown'))

    st.subheader('Styling Recommendations')
    st.write(res.get('recommendations', 'No recommendations returned.'))

    links = res.get('shopping_links') or {}
    if links:
        st.subheader('Shop Recommended Outfits')
        for name, href in links.items():
            st.markdown(f'- [{name}]({href})')

    if st.button('Try Again'):
        st.session_state.page = 'upload'


# handle query params flag to open upload
params = st.experimental_get_query_params() if hasattr(st, 'experimental_get_query_params') else st.query_params
if params.get('start') == ['1']:
    st.session_state.page = 'upload'

page = st.session_state.page

if page == 'home':
    show_home()
elif page == 'upload':
    show_upload()
elif page == 'results':
    show_results()