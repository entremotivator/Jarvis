import streamlit as st
import os
import signal
import sys

from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface


def run_conversation(agent_id: str, api_key: str):
    """Run the ElevenLabs conversational AI session."""

    client = ElevenLabs(api_key=api_key if api_key else None)

    conversation = Conversation(
        client,
        agent_id,
        requires_auth=bool(api_key),
        audio_interface=DefaultAudioInterface(),
        callback_agent_response=lambda response: st.write(f"**Agent:** {response}"),
        callback_agent_response_correction=lambda original, corrected: st.write(
            f"**Agent Correction:** {original} → {corrected}"
        ),
        callback_user_transcript=lambda transcript: st.write(f"**You:** {transcript}"),
        # Optional latency callback
        # callback_latency_measurement=lambda latency: st.write(f"Latency: {latency} ms"),
    )

    # Start the live session
    conversation.start_session()

    # Handle clean shutdown (Ctrl+C in console)
    signal.signal(signal.SIGINT, lambda sig, frame: conversation.end_session())

    conversation_id = conversation.wait_for_session_end()
    st.success(f"Conversation ended. ID: {conversation_id}")


def main():
    st.set_page_config(page_title="ElevenLabs Conversational AI", page_icon="🎙️", layout="centered")
    st.title("🎙️ ElevenLabs Conversational AI")

    # Sidebar inputs for API key and Agent ID
    st.sidebar.header("🔑 API Configuration")
    api_key = st.sidebar.text_input("ElevenLabs API Key", type="password")
    agent_id = st.sidebar.text_input("Agent ID")

    if st.sidebar.button("🚀 Start Conversation"):
        if not agent_id:
            st.error("Agent ID must be provided.")
        else:
            with st.spinner("Starting conversation... 🎧"):
                run_conversation(agent_id, api_key)


if __name__ == "__main__":
    main()
