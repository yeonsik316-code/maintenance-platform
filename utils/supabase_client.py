import streamlit as st
from storage3.exceptions import StorageApiError
from supabase import create_client, Client

from config import STORAGE_BUCKET, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


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


def confirm_user_email(user_id: str) -> None:
    admin = get_admin_client()
    if admin:
        admin.auth.admin.update_user_by_id(user_id, {"email_confirm": True})


def refresh_session():
    sb = get_supabase()
    session = sb.auth.get_session()
    # supabase-py 2.x: Session 객체 직접 반환 / 구버전: .session 속성
    active = getattr(session, "session", session) if session else None
    if active:
        st.session_state.access_token = active.access_token
        st.session_state.refresh_token = active.refresh_token
        st.session_state.user = active.user
        _persist_auth_to_browser(active.access_token, active.refresh_token)
    elif st.session_state.get("access_token") and st.session_state.get("refresh_token"):
        try:
            sb.auth.set_session(
                st.session_state.access_token,
                st.session_state.refresh_token,
            )
            session = sb.auth.get_session()
            active = getattr(session, "session", session) if session else None
            if active:
                st.session_state.user = active.user
                _persist_auth_to_browser(active.access_token, active.refresh_token)
                return
        except Exception:
            pass
        _clear_persisted_auth()
    else:
        _clear_session_state()


def _persist_auth_to_browser(access_token: str, refresh_token: str) -> None:
    from utils.browser_session import save_auth_to_browser

    save_auth_to_browser(access_token, refresh_token)


def _clear_persisted_auth() -> None:
    from utils.browser_session import clear_auth_from_browser, reset_bootstrap_flags

    clear_auth_from_browser()
    reset_bootstrap_flags()
    _clear_session_state()


def _clear_session_state() -> None:
    st.session_state.pop("access_token", None)
    st.session_state.pop("refresh_token", None)
    st.session_state.pop("user", None)
    st.session_state.pop("profile", None)


def ensure_storage_bucket() -> bool:
    if st.session_state.get("storage_bucket_ready"):
        return True

    admin = get_admin_client()
    if not admin:
        return False

    try:
        bucket_ids = {bucket.id for bucket in admin.storage.list_buckets()}
        if STORAGE_BUCKET not in bucket_ids:
            admin.storage.create_bucket(STORAGE_BUCKET, options={"public": False})
        st.session_state.storage_bucket_ready = True
        return True
    except Exception:
        return False


def require_admin_storage_client() -> Client:
    admin = get_admin_client()
    if not admin:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다. "
            "Streamlit Secrets 또는 .env에 service role key를 추가해 주세요."
        )
    ensure_storage_bucket()
    return admin


def get_storage_client() -> Client:
    """관리자 Storage 쓰기는 service role 사용."""
    try:
        return require_admin_storage_client()
    except RuntimeError:
        return get_supabase()


def format_storage_error(exc: Exception) -> str:
    if isinstance(exc, StorageApiError):
        detail = f"{exc.message} (code={exc.code}, status={exc.status})"
        lowered = detail.lower()
        if "bucket" in lowered and ("not found" in lowered or exc.status in (400, 404)):
            return (
                f"Storage 버킷(`{STORAGE_BUCKET}`)을 사용할 수 없습니다: {detail}\n"
                "Supabase SQL Editor에서 `supabase/storage_migration.sql`을 실행해 주세요."
            )
        if "row-level security" in lowered or "access" in lowered or exc.status == 403:
            return (
                f"Storage 업로드 권한 오류: {detail}\n"
                "Streamlit Secrets에 `SUPABASE_SERVICE_ROLE_KEY`를 설정해 주세요."
            )
        return f"Storage 오류: {detail}"
    return str(exc)


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
    _clear_persisted_auth()
    for key in ("supabase", "supabase_admin"):
        st.session_state.pop(key, None)
    st.rerun()
