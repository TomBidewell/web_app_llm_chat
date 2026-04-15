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
        with st.chat_message(msg["role"], avatar="human"):
            st.markdown(msg["content"])

# --- 5. CHAT INPUT & LLM CALL ---
if prompt := st.chat_input("Type your message here..."):

    # Show user message
    st.chat_message("user", avatar = "human").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call the LLM with streaming
    with st.chat_message("assistant", avatar = "human"):

        # Show animated pulsing dots via HTML
        dots_placeholder = st.empty()
        dots_placeholder.html("""
                    <style>
                        .dot-container {
                            display: flex;
                            gap: 6px;
                            align-items: center;
                            height: 24px;
                            padding: 4px 0;
                        }
                        .dot {
                            width: 10px;
                            height: 10px;
                            border-radius: 50%;
                            background-color: #888;
                            animation: pulse 1.2s ease-in-out infinite;
                        }
                        .dot:nth-child(1) { animation-delay: 0s; }
                        .dot:nth-child(2) { animation-delay: 0.3s; }
                        .dot:nth-child(3) { animation-delay: 0.6s; }
                        @keyframes pulse {
                            0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
                            40%            { opacity: 1.0; transform: scale(1.2); }
                        }
                    </style>
                    <div class="dot-container">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                """)

        try:
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                stream=True
            )
            #ai_reply = st.write_stream(stream)
            ai_reply = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    ai_reply += delta
        except Exception as e:
            dots_placeholder.empty()
            st.error(f"LLM error: {e}")
            st.stop()

        dots_placeholder.markdown(ai_reply)

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