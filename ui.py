import streamlit as st
import os


def apply_custom_css():
    SIDEBAR_BG = "#00888D"
    MAIN_BG = "#FFFFFF"

    st.markdown(f"""
    <style>

    /* ===============================
       GLOBAL BACKGROUND
    =============================== */
    .stApp {{
        background-color: {MAIN_BG};
    }}

    /* ===============================
       SIDEBAR BACKGROUND
    =============================== */
    section[data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG} !important;
    }}

    /* Sidebar normal text */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p {{
        color: white !important;
    }}

    /* ===============================
       SIDEBAR BUTTON STYLE (Separate)
    =============================== */

    /* Button background */
    section[data-testid="stSidebar"] .stButton button {{
        background-color: white !important;   /* change anytime */
        color: black !important;              /* button text color */
        border-radius: 8px !important;
        border: none !important;
    }}

    /* Button hover effect */
    section[data-testid="stSidebar"] .stButton button:hover {{
        background-color: #f0f0f0 !important;
        color: black !important;
    }}

    /* ===============================
       INPUT BOX
    =============================== */
    section[data-testid="stSidebar"] input {{
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
    }}

    /* ===============================
       ALERT FIX
    =============================== */
    section[data-testid="stSidebar"] div[role="alert"] {{
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }}

    section[data-testid="stSidebar"] div[role="alert"] * {{
        color: black !important;
    }}

    /* ===============================
       CHAT STYLE
    =============================== */
    [data-testid="stChatMessageContainer"] {{
        background-color: white;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        padding: 10px;
        margin-bottom: 10px;
    }}

    .stChatInput {{
        border-radius: 25px !important;
    }}

    </style>
    """, unsafe_allow_html=True)


def show_header():
    st.markdown(
        """
        <div style="text-align:center; margin-bottom:20px;">
            <h1 style="color:#040668; margin-bottom:0px; font-weight:800;">
                SMIT & TITAN SUKKUR CAMPUS
            </h1>
            <h2 style="color:black; font-size:24px;">
                COUNTER RECEPTIONIST
            </h2>
        </div>
        """,
        unsafe_allow_html=True
    )


