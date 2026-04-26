import streamlit as st
from groq import Groq
from ui import apply_custom_css, show_header
from dotenv import load_dotenv
import os
import json
import bcrypt
from docx import Document
from io import BytesIO
from rag_system import generate_rag_answer, rebuild_index
from faster_whisper import WhisperModel
import tempfile
from streamlit_mic_recorder import mic_recorder
import edge_tts
import asyncio
import nest_asyncio


st.set_page_config(page_title="TITAN SUKKUR RECEPTIONIST", layout="centered")

# ==========================================
# PASSWORD STORAGE CONFIG
# ==========================================
ADMIN_FILE = "admin_data.json"

def load_admin_data():
    if not os.path.exists(ADMIN_FILE):
        return None
    with open(ADMIN_FILE, "r") as f:
        return json.load(f)

def save_admin_data(data):
    with open(ADMIN_FILE, "w") as f:
        json.dump(data, f)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ==========================================
# LOAD ENV VARIABLES
# ==========================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL") or "Not configured"
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY missing in .env")
    st.stop()

if not ADMIN_PASSWORD:
    st.error("ADMIN_PASSWORD missing in .env")
    st.stop()

admin_data = load_admin_data()

if admin_data is None or not admin_data.get("password"):
    hashed = hash_password(ADMIN_PASSWORD)
    save_admin_data({"password": hashed})
    admin_data = load_admin_data()

client = Groq(api_key=GROQ_API_KEY)

# ==========================================
# LOAD WHISPER MODEL
# ==========================================
@st.cache_resource
def load_whisper():
    return WhisperModel("base")

whisper_model = load_whisper()

def speech_to_text(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        temp_path = tmp.name

    segments, info = whisper_model.transcribe(temp_path)
    text = " ".join([segment.text for segment in segments])
    return text

# ==========================================
# EDGE TTS FUNCTION
# ==========================================
def text_to_speech(text, voice_name):
    file_path = "response.mp3"

    async def run():
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_name,
            rate="-18%"   # 👈 Slower & clearer
        )
        await communicate.save(file_path)

    
    nest_asyncio.apply()

    asyncio.run(run())
    return file_path



# ==========================================
# APPLY UI
# ==========================================
apply_custom_css()
show_header()

# ==========================================
# SESSION STATE INIT
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:

    st.image("assets/logo.jpg", width=140)
    st.subheader("Admin Access")

    if not st.session_state.admin_logged_in:

        entered_password = st.text_input("Enter Admin Password", type="password")

        if st.button("Login"):
            if check_password(entered_password, admin_data["password"]):
                st.session_state.admin_logged_in = True
                st.success("Admin Logged In")
                st.rerun()
            else:
                st.error("Incorrect Password")

        if st.button("Forgot Password?"):
            st.info(f"Please contact system administrator at {ADMIN_EMAIL}")

    else:

        st.markdown("<h4 style='color:white;'>Admin Mode Active</h4>", unsafe_allow_html=True)

        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()

        st.divider()
        st.subheader("Update Institute PDF")

        uploaded_pdfs = st.file_uploader(
            "Upload Institute PDFs",
            type=["pdf"],
            accept_multiple_files=True
        )

        if uploaded_pdfs:

            os.makedirs("rag_data", exist_ok=True)

            for uploaded_pdf in uploaded_pdfs:

                if uploaded_pdf.size > 10 * 1024 * 1024:
                    st.error(f"{uploaded_pdf.name} too large (Max 10MB)")
                    continue
                file_path = os.path.join("rag_data", uploaded_pdf.name)

                with open(file_path, "wb") as f:
                    f.write(uploaded_pdf.read())

            st.success("PDFs uploaded successfully")

            if st.button("Rebuild Index"):
                try:
                    with st.spinner("Rebuilding vector database..."):
                        rebuild_index("rag_data")
                    st.success("Index rebuilt successfully")
                except Exception as e:
                    st.error(f"Index rebuild failed: {e}")

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# DISPLAY CHAT HISTORY
# ==========================================
USER_AVATAR = "assets/user.jpg"
BOT_AVATAR = "assets/logo.jpg"

for msg in st.session_state.messages:
    avatar = USER_AVATAR if msg["role"] == "user" else BOT_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ==========================================
# VOICE SELECTION
# ==========================================
st.markdown("### 🎧 Select Receptionist Voice")

voice_option = st.selectbox(
    "Choose Voice",
    [
        "English Female (Professional)",
        "Urdu Female",
        "Pakistani Accent Female"
    ]
)

# ==========================================
# LIVE MICROPHONE SECTION
# ==========================================
st.markdown("###  Voice Query")

audio = mic_recorder(
    start_prompt="🎙 Start Recording",
    stop_prompt="⏹ Stop Recording",
    just_once=True
)

if audio and "bytes" in audio:

    with st.spinner("Listening..."):

        user_voice_text = speech_to_text(audio["bytes"])
        st.write("Detected Text:", user_voice_text)


        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(user_voice_text)

        st.session_state.messages.append(
            {"role": "user", "content": user_voice_text}
        )

        ai_reply = generate_rag_answer(user_voice_text, client, MODEL_NAME)

        with st.chat_message("assistant", avatar=BOT_AVATAR):
            st.markdown(ai_reply)

        st.session_state.messages.append(
            {"role": "assistant", "content": ai_reply}
        )
        # Voice Mapping
        if voice_option == "English Female (Professional)":
            selected_voice = "en-US-JennyNeural"
        elif voice_option == "Urdu Female":
            selected_voice = "ur-IN-GulNeural"
        else:
            selected_voice = "en-PK-AsmaNeural"

        # 👇 YAHAN paste karo
        voice_output = text_to_speech(ai_reply, selected_voice)

        # st.write("Voice file path:", voice_output)
        # st.write("File exists:", os.path.exists("response.mp3"))

        if voice_output and os.path.exists("response.mp3"):
            # st.success("MP3 Generated")
            st.audio(voice_output)
        else:
            st.error("MP3 Not Generated")


# ==========================================
# CHAT INPUT
# ==========================================
if user_prompt := st.chat_input("Ask any information about Institute"):

    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_prompt)

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Receptionist is thinking..."):
            ai_reply = generate_rag_answer(user_prompt, client, MODEL_NAME)
            st.markdown(ai_reply)
            st.session_state.messages.append(
                {"role": "assistant", "content": ai_reply}
            )
            st.rerun()
