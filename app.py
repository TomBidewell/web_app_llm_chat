import streamlit as st
from openai import OpenAI
from supabase import create_client, Client
import uuid
from datetime import datetime
import random

# --- 1. SETUP ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

supabase: Client = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# --- 2. SESSION STATE ---
if "session_id" not in st.session_state:
    st.session_state.session_id = random.getrandbits(63)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

# --- 3. DISPLAY CHAT HISTORY ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 4. CHAT INPUT & LLM CALL ---
if prompt := st.chat_input("Type your message here..."):

    # Show user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call the LLM
    with st.chat_message("assistant"):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages
            )
            ai_reply = response.choices[0].message.content
            st.markdown(ai_reply)
        except Exception as e:
            st.error(f"LLM error: {e}")
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
    st.session_state.turn_index += 1

    # --- 5. SAVE TO SUPABASE ---
    try:
        supabase.table("chat_logs").insert({
            "session_id": st.session_state.session_id,
            "turn_index": st.session_state.turn_index,
            "user_message": prompt,
            "ai_response": ai_reply,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        st.error(f"Failed to save to database: {e}")