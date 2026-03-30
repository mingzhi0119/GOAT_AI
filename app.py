import streamlit as st
import requests
import json
import pandas as pd # Requires: pip install pandas openpyxl

# 1. Page Configuration and Aesthetics
st.set_page_config(page_title="GOAT AI | Simon Business School", page_icon="🐐", layout="wide")

# Injecting Simon Blue style CSS
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #002855; color: white; }
    .stButton>button { background-color: #FFCD00; color: #002855; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# 2. Sidebar: Configuration and Data Upload
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/3/3a/University_of_Rochester_Simon_Business_School_logo.png/250px-University_of_Rochester_Simon_Business_School_logo.png") # Example Logo
    st.title("Admin Console")
    
    # Model Selection
    try:
        models = [m['name'] for m in requests.get("http://localhost:11434/api/tags").json()['models']]
        selected_model = st.selectbox("Active Brain (A100)", models)
    except:
        selected_model = "llama3:latest"
    
    st.divider()
    
    # Business Data Analysis
    st.subheader("Business Data Analysis")
    uploaded_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
        st.write("📊 Data Preview:", df.head(3))
        if st.button("Analyze with GOAT AI"):
            data_summary = f"I have a dataset with {df.shape[0]} rows. Here is the head: {df.head(2).to_string()}. Please summarize this."
            st.session_state.messages.append({"role": "user", "content": data_summary})

# 3. Main Interface
st.title("🐐 GOAT AI - Strategic Intelligence")
st.caption("Running on high-performance A100 infrastructure at Simon Business School")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to GOAT AI. How can I assist your business decisions today?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 4. Chat Input and Streaming Response
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        # Added timeout handling and error catching
        try:
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": selected_model, "prompt": prompt, "stream": True},
                stream=True, timeout=30
            )
            for line in res.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    token = chunk.get('response', '')
                    full_response += token
                    response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
        except Exception as e:
            st.error(f"Error connecting to AI: {e}")
            full_response = "Sorry, I'm experiencing some latency on the A100 node."

    st.session_state.messages.append({"role": "assistant", "content": full_response})