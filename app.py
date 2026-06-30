import streamlit as st

from components.admin_page import render_admin_pages
from components.auth_page import render_auth_page
from components.boards_page import render_boards_page
from components.message_dialog import render_pending_message
from config import SUPABASE_ANON_KEY, SUPABASE_URL
from utils.browser_session import bootstrap_auth_from_browser
from utils.supabase_client import is_admin, load_profile, logout, refresh_session

st.set_page_config(
    page_title="현장지원 플랫폼",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error(
        "Supabase 설정이 필요합니다. `.env` 파일에 "
        "`SUPABASE_URL`, `SUPABASE_ANON_KEY`를 입력해 주세요."
    )
    st.stop()

bootstrap_auth_from_browser()

if "user" not in st.session_state:
    refresh_session()
    if st.session_state.get("user"):
        load_profile()


def _menu_options():
    options = [("boards", "📋 게시판")]
    if is_admin():
        options.append(("board_mgmt", "⚙️ 게시판 관리"))
        options.append(("member_mgmt", "👥 가입자 정보 관리"))
    return options


def main():
    render_pending_message()

    user = st.session_state.get("user")

    if not user:
        render_auth_page()
        return

    profile = st.session_state.get("profile") or load_profile()
    menu_items = _menu_options()
    labels = [label for _, label in menu_items]
    keys = [key for key, _ in menu_items]

    with st.sidebar:
        st.title("🏗️ 현장지원")
        if profile:
            st.write(f"**{profile.get('phone_number', '')}**")
            role_text = "관리자" if profile.get("role") == "admin" else "현장 엔지니어"
            st.caption(role_text)

        st.divider()

        selected_label = st.radio(
            "메뉴",
            options=labels,
            label_visibility="collapsed",
            key="nav_menu",
        )
        selected_page = keys[labels.index(selected_label)]

        st.divider()
        if st.button("로그아웃", use_container_width=True):
            logout()

    if selected_page == "boards":
        render_boards_page()
    else:
        render_admin_pages(selected_page)


if __name__ == "__main__":
    main()
