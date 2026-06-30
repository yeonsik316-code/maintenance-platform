import streamlit as st


def queue_message(message: str, files: list[str] | None = None):
    st.session_state.toast_message = message
    if files:
        st.session_state.toast_files = files


def render_pending_message():
    message = st.session_state.pop("toast_message", None)
    files = st.session_state.pop("toast_files", None)

    if message:
        st.toast(message, icon="✅")

    if files:
        file_lines = "\n".join(f"- {name}" for name in files)
        st.success(f"{message or '업로드 완료'}\n\n**첨부파일**\n{file_lines}")
