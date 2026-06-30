import re

import streamlit as st

from components.caps_lock import password_field, render_caps_lock_detector
from utils.supabase_client import get_supabase, load_profile, refresh_session


def _normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-]", "", phone.strip())


def _lookup_email_by_phone(phone: str) -> str | None:
    sb = get_supabase()
    result = sb.rpc("get_login_email", {"p_phone": phone}).execute()
    return result.data


def render_login_tab():
    st.subheader("로그인")
    phone = st.text_input("전화번호", key="login_phone", placeholder="01012345678")
    password = password_field("비밀번호", key="login_password")

    if st.button("로그인", type="primary", key="btn_login", use_container_width=True):
        phone_norm = _normalize_phone(phone)
        if not phone_norm or not password:
            st.error("전화번호와 비밀번호를 입력해 주세요.")
            return

        email = _lookup_email_by_phone(phone_norm)
        if not email:
            st.error("등록되지 않은 전화번호입니다.")
            return

        sb = get_supabase()
        try:
            sb.auth.sign_in_with_password({"email": email, "password": password})
            refresh_session()
            load_profile()
            st.success("로그인되었습니다.")
            st.rerun()
        except Exception as exc:
            st.error(f"로그인 실패: {exc}")


def render_signup_tab():
    st.subheader("회원가입")
    username = st.text_input("아이디", key="signup_username", placeholder="영문/숫자 조합")
    password = password_field("비밀번호", key="signup_password")
    password_confirm = password_field("비밀번호 확인", key="signup_password_confirm")
    phone = st.text_input("전화번호", key="signup_phone", placeholder="01012345678")
    email = st.text_input("이메일", key="signup_email", placeholder="name@company.com")

    if st.button("회원가입", type="primary", key="btn_signup", use_container_width=True):
        if not all([username, password, phone, email]):
            st.error("모든 항목을 입력해 주세요.")
            return
        if password != password_confirm:
            st.error("비밀번호가 일치하지 않습니다.")
            return
        if len(password) < 6:
            st.error("비밀번호는 6자 이상이어야 합니다.")
            return

        phone_norm = _normalize_phone(phone)
        sb = get_supabase()
        try:
            sb.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {
                            "username": username,
                            "phone_number": phone_norm,
                            "role": "user",
                        }
                    },
                }
            )
            st.success(
                "회원가입이 완료되었습니다. "
                "이메일 인증이 필요한 경우 메일함을 확인한 뒤 로그인해 주세요."
            )
        except Exception as exc:
            st.error(f"회원가입 실패: {exc}")


def render_forgot_tab():
    st.subheader("비밀번호 찾기")
    st.caption("가입 시 등록한 전화번호로 계정을 찾아 비밀번호 재설정 메일을 보냅니다.")
    phone = st.text_input("전화번호", key="forgot_phone", placeholder="01012345678")

    if st.button("재설정 메일 발송", key="btn_forgot", use_container_width=True):
        phone_norm = _normalize_phone(phone)
        if not phone_norm:
            st.error("전화번호를 입력해 주세요.")
            return

        email = _lookup_email_by_phone(phone_norm)
        if not email:
            st.error("등록되지 않은 전화번호입니다.")
            return

        sb = get_supabase()
        try:
            sb.auth.reset_password_for_email(email)
            st.success(f"{email} 로 비밀번호 재설정 메일을 발송했습니다.")
        except Exception as exc:
            st.error(f"메일 발송 실패: {exc}")


def render_auth_page():
    st.title("현장지원 플랫폼")
    st.caption("공지 확인 및 양식 다운로드")
    render_caps_lock_detector()

    tab_login, tab_signup, tab_forgot = st.tabs(["로그인", "회원가입", "비밀번호 찾기"])

    with tab_login:
        render_login_tab()
    with tab_signup:
        render_signup_tab()
    with tab_forgot:
        render_forgot_tab()
