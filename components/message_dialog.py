import streamlit as st


@st.dialog("알림")
def _message_dialog(message: str):
    st.markdown(message)
    if st.button("확인", use_container_width=True, type="primary", key="msg_dialog_ok"):
        st.session_state.pop("pending_message", None)
        st.rerun()


def queue_message(message: str):
    st.session_state.pending_message = message


def render_pending_message():
    message = st.session_state.get("pending_message")
    if message:
        _message_dialog(message)
