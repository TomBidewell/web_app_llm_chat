import streamlit as st
from openai import OpenAI
from supabase import create_client, Client
from datetime import datetime
import random

# --- 1. SETUP ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

supabase: Client = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# --- 2. QUALTRICS URL PARAMETERS ---
params = st.query_params
qualtrics_id = params.get("user_id", None)

if qualtrics_id is None:
    st.error("Missing Participant ID. Please start from the Qualtrics survey.")
    st.stop()

# --- 3. SESSION STATE ---
if "session_id" not in st.session_state:
    st.session_state.session_id = random.getrandbits(63)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

# --- 4. DISPLAY CHAT HISTORY ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 5. CHAT INPUT & LLM CALL ---
if prompt := st.chat_input("Type your message here..."):

    # Show user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call the LLM with streaming
    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                stream=True
            )
            ai_reply = st.write_stream(stream)
        except Exception as e:
            st.error(f"LLM error: {e}")
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
    st.session_state.turn_index += 1

    # --- 6. SAVE TO SUPABASE ---
    try:
        supabase.table("chat_logs").insert({
            "session_id": st.session_state.session_id,
            "qualtrics_id": qualtrics_id,
            "turn_index": st.session_state.turn_index,
            "user_message": prompt,
            "ai_response": ai_reply,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        st.error(f"Failed to save to database: {e}")