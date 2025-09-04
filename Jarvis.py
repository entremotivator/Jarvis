# app.py
import os
import sys
import threading
import signal
import time
from typing import Optional, Callable

import streamlit as st

# --- Try to import the ElevenLabs SDK pieces ---
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.conversational_ai.conversation import Conversation
except Exception as e:
    st.error(f"Failed to import ElevenLabs SDK: {e}")
    st.stop()

# --- Try to import DefaultAudioInterface (will fail if PyAudio isn't installed) ---
HAS_PYAUDIO = True
try:
    from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
except Exception:
    HAS_PYAUDIO = False


# ------------------------
# Utilities
# ------------------------
def _append_log(msg: str):
    if "log" not in st.session_state:
        st.session_state.log = []
    st.session_state.log.append(msg)


def _mk_callbacks():
    def on_agent_response(response: str):
        _append_log(f"**Agent:** {response}")

    def on_correction(original: str, corrected: str):
        _append_log(f"**Agent Correction:** {original} → {corrected}")

    def on_user_transcript(transcript: str):
        _append_log(f"**You:** {transcript}")

    return on_agent_response, on_correction, on_user_transcript


def _end_session_safe():
    conv: Optional[Conversation] = st.session_state.get("conversation")
    if conv:
        try:
            conv.end_session()
        except Exception:
            pass


def _start_conversation_thread(conversation: Conversation):
    """
    Runs conversation.start_session() and waits until it ends,
    without blocking Streamlit's main thread.
    """
    def runner():
        try:
            conversation.start_session()
            # Block until ended
            cid = conversation.wait_for_session_end()
            st.session_state["conversation_id"] = cid
            _append_log(f":white_check_mark: **Conversation ended. ID:** `{cid}`")
        except Exception as e:
            _append_log(f":x: **Error:** {e}")
        finally:
            st.session_state["is_running"] = False

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    st.session_state["thread"] = t


# ------------------------
# Streamlit App
# ------------------------
st.set_page_config(page_title="ElevenLabs Conversational AI", page_icon="🎙️", layout="centered")
st.title("🎙️ ElevenLabs Conversational AI")

with st.sidebar:
    st.header("🔑 API Configuration")
    api_key = st.text_input("ElevenLabs API Key", type="password", help="Leave empty if your agent is public")
    agent_id = st.text_input("Agent ID", help="Paste your ElevenLabs Agent ID")

    st.divider()
    st.subheader("🎧 Audio Interface")
    if HAS_PYAUDIO:
        st.success("PyAudio detected — Voice mode enabled (DefaultAudioInterface).")
        use_audio = True
    else:
        st.warning("PyAudio NOT available — running in Text-only mode (Cloud-safe).")
        use_audio = False

    st.caption(
        "PyAudio requires local setup (PortAudio). On Streamlit Cloud, voice mode isn't available. "
        "This app will still run and show text conversation."
    )

    st.divider()
    colA, colB = st.columns(2)
    start_btn = colA.button("🚀 Start", type="primary")
    stop_btn = colB.button("🛑 Stop", type="secondary")

# init state
st.session_state.setdefault("is_running", False)
st.session_state.setdefault("conversation", None)
st.session_state.setdefault("conversation_id", None)
st.session_state.setdefault("log", [])

# Signal handler for local Ctrl+C (best-effort; harmless on Cloud)
try:
    signal.signal(signal.SIGINT, lambda sig, frame: _end_session_safe())
except Exception:
    pass

# Start
if start_btn:
    if not agent_id:
        st.error("Please provide an **Agent ID**.")
    else:
        # Build client
        client = ElevenLabs(api_key=api_key if api_key else None)

        # Wire callbacks to the Streamlit log window
        on_agent_response, on_correction, on_user_transcript = _mk_callbacks()

        # Create conversation
        try:
            conversation = Conversation(
                client,
                agent_id,
                requires_auth=bool(api_key),
                audio_interface=DefaultAudioInterface() if use_audio else None,
                callback_agent_response=on_agent_response,
                callback_agent_response_correction=on_correction,
                callback_user_transcript=on_user_transcript,
                # callback_latency_measurement=lambda latency: _append_log(f"Latency: {latency} ms"),
            )
        except Exception as e:
            st.error(f"Could not create Conversation: {e}")
            st.stop()

        # Keep references in session
        st.session_state["conversation"] = conversation
        st.session_state["is_running"] = True
        st.session_state["conversation_id"] = None
        st.session_state["log"] = []

        # Start in a thread so Streamlit stays responsive
        _start_conversation_thread(conversation)
        st.success("Starting conversation…")

# Stop
if stop_btn:
    _end_session_safe()
    st.info("Ending conversation… (this may take a moment)")

# Status & live log
status = "🟢 Running" if st.session_state["is_running"] else "⚪️ Idle"
st.markdown(f"**Status:** {status}")

with st.container(border=True):
    st.subheader("Live Feed")
    if len(st.session_state["log"]) == 0:
        st.caption("Messages will appear here…")
    else:
        for line in st.session_state["log"]:
            st.markdown(line)

# Conversation ID (when available)
if st.session_state.get("conversation_id"):
    st.code(f"Conversation ID: {st.session_state['conversation_id']}", language="text")

st.caption("Tip: Keep this tab open while talking to the agent. Use **Stop** to end gracefully.")
