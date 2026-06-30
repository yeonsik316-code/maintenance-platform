import streamlit as st
from supabase import create_client, Client

from config import SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


def get_supabase() -> Client:
    if "supabase" not in st.session_state:
        st.session_state.supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return st.session_state.supabase


def get_admin_client() -> Client | None:
    if not SUPABASE_SERVICE_ROLE_KEY:
        return None
    if "supabase_admin" not in st.session_state:
        st.session_state.supabase_admin = create_client(
            SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
        )
    return st.session_state.supabase_admin


def refresh_session():
    sb = get_supabase()
    session = sb.auth.get_session()
    # supabase-py 2.x: Session 객체 직접 반환 / 구버전: .session 속성
    active = getattr(session, "session", session) if session else None
    if active:
        st.session_state.access_token = active.access_token
        st.session_state.user = active.user
    else:
        st.session_state.pop("access_token", None)
        st.session_state.pop("user", None)
        st.session_state.pop("profile", None)


def load_profile():
    user = st.session_state.get("user")
    if not user:
        st.session_state.pop("profile", None)
        return None

    sb = get_supabase()
    result = (
        sb.table("profiles")
        .select("*")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )
    profile = result.data
    st.session_state.profile = profile
    return profile


def is_admin() -> bool:
    profile = st.session_state.get("profile")
    return bool(profile and profile.get("role") == "admin")


def logout():
    get_supabase().auth.sign_out()
    for key in ("user", "access_token", "profile", "supabase"):
        st.session_state.pop(key, None)
    st.rerun()
