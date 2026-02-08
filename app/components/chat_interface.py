"""Reusable chat interface component."""
from __future__ import annotations
import streamlit as st
from datetime import datetime


def init_chat_state(key: str = "messages"):
    """Initialize chat message history in session state."""
    if key not in st.session_state:
        st.session_state[key] = []


def render_chat_history(key: str = "messages"):
    """Render all previous chat messages."""
    for msg in st.session_state.get(key, []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def add_message(role: str, content: str, key: str = "messages"):
    """Add a message to chat history."""
    st.session_state[key].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    })


def get_chat_input(prompt: str = "Type your message...") -> str | None:
    """Get user input from chat input widget."""
    return st.chat_input(prompt)


def render_chat(
    agent_fn,
    system_context: dict = None,
    key: str = "messages",
    input_prompt: str = "Type your message...",
):
    """Full chat interface: history + input + agent response.

    Args:
        agent_fn: Callable(messages, context) -> str that generates agent response
        system_context: Dict of context to pass to agent (student info, etc.)
        key: Session state key for message history
        input_prompt: Placeholder text for chat input
    """
    init_chat_state(key)
    render_chat_history(key)

    user_input = get_chat_input(input_prompt)
    if user_input:
        add_message("user", user_input, key)
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = agent_fn(
                        st.session_state[key],
                        system_context or {},
                    )
                    st.markdown(response)
                    add_message("assistant", response, key)
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    add_message("assistant", error_msg, key)
