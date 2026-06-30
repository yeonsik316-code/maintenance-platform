"""브라우저 sessionStorage 기반 로그인 유지 (탭/브라우저 종료 시 삭제)."""

import json

import streamlit as st
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

SESSION_ACCESS_KEY = "hs_sb_access"
SESSION_REFRESH_KEY = "hs_sb_refresh"


def save_auth_to_browser(access_token: str, refresh_token: str) -> None:
    components.html(
        f"""
        <script>
        sessionStorage.setItem({json.dumps(SESSION_ACCESS_KEY)}, {json.dumps(access_token)});
        sessionStorage.setItem({json.dumps(SESSION_REFRESH_KEY)}, {json.dumps(refresh_token)});
        </script>
        """,
        height=0,
        width=0,
    )


def clear_auth_from_browser() -> None:
    components.html(
        f"""
        <script>
        sessionStorage.removeItem({json.dumps(SESSION_ACCESS_KEY)});
        sessionStorage.removeItem({json.dumps(SESSION_REFRESH_KEY)});
        </script>
        """,
        height=0,
        width=0,
    )


def _read_storage_item(key: str, eval_key: str) -> str | None:
    value = streamlit_js_eval(
        js_expressions=f"sessionStorage.getItem({json.dumps(key)})",
        want_output=True,
        key=eval_key,
    )
    if not value or not isinstance(value, str) or value in ("null", "undefined"):
        return None
    return value


def load_auth_from_browser() -> tuple[str, str] | None:
    access = _read_storage_item(SESSION_ACCESS_KEY, "load_sb_access")
    refresh = _read_storage_item(SESSION_REFRESH_KEY, "load_sb_refresh")
    if access and refresh:
        return access, refresh
    return None


def bootstrap_auth_from_browser() -> None:
    if st.session_state.get("user") or st.session_state.get("access_token"):
        return

    if st.session_state.get("_auth_bootstrap_done"):
        return

    tokens = load_auth_from_browser()
    if tokens:
        st.session_state.access_token, st.session_state.refresh_token = tokens
        st.session_state._auth_bootstrap_done = True
        return

    if not st.session_state.get("_auth_bootstrap_rerun"):
        st.session_state._auth_bootstrap_rerun = True
        st.rerun()

    st.session_state._auth_bootstrap_done = True


def reset_bootstrap_flags() -> None:
    for key in ("_auth_bootstrap_done", "_auth_bootstrap_rerun"):
        st.session_state.pop(key, None)
