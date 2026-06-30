import re
import uuid
from pathlib import Path

import streamlit as st
from streamlit_quill import st_quill

from components.message_dialog import queue_message
from config import STORAGE_BUCKET
from utils.supabase_client import (
    format_storage_error,
    get_storage_client,
    get_supabase,
    is_admin,
    require_admin_storage_client,
)


QUILL_TOOLBAR = [
    [{"header": [1, 2, 3, False]}],
    ["bold"],
    [{"color": ["#FF0000", "#0000FF", "#000000"]}],
    [{"align": []}],
    ["clean"],
]


def _fetch_boards():
    sb = get_supabase()
    return sb.table("boards").select("*").order("created_at").execute().data or []


def _fetch_posts(board_id: str):
    sb = get_supabase()
    return (
        sb.table("posts")
        .select("*, profiles(email, phone_number)")
        .eq("board_id", board_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )


def _fetch_attachments(post_id: str):
    sb = get_supabase()
    return (
        sb.table("post_attachments")
        .select("*")
        .eq("post_id", post_id)
        .execute()
        .data
        or []
    )


def _file_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix and re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        return suffix.lstrip(".")
    return "bin"


def _storage_key(board_id: str, original_filename: str) -> str:
    ext = _file_extension(original_filename)
    return f"{board_id}/posts/{uuid.uuid4()}.{ext}"


def _original_filename(att: dict) -> str:
    return att.get("original_filename") or att.get("file_name") or "download"


def _storage_upload_error_message(exc: Exception) -> str:
    return f"첨부파일 업로드 실패: {format_storage_error(exc)}"


@st.cache_data(show_spinner=False, ttl=300)
def _download_file(storage_path: str) -> bytes:
    sb = get_supabase()
    return sb.storage.from_(STORAGE_BUCKET).download(storage_path)


def _submit_post(board_id: str, title: str, content: str, uploaded) -> None:
    sb = get_supabase()
    user_id = st.session_state.user.id

    try:
        post_result = (
            sb.table("posts")
            .insert(
                {
                    "board_id": board_id,
                    "title": title,
                    "content": content,
                    "user_id": user_id,
                }
            )
            .execute()
        )
        post_id = post_result.data[0]["id"]

        if uploaded:
            try:
                storage_sb = require_admin_storage_client()
            except RuntimeError as exc:
                sb.table("posts").delete().eq("id", post_id).execute()
                st.error(str(exc))
                return

            try:
                for file in uploaded:
                    original_name = file.name
                    path = _storage_key(board_id, original_name)
                    storage_sb.storage.from_(STORAGE_BUCKET).upload(
                        path,
                        file.getvalue(),
                        {
                            "content-type": file.type or "application/octet-stream",
                        },
                    )
                    sb.table("post_attachments").insert(
                        {
                            "post_id": post_id,
                            "file_name": original_name,
                            "original_filename": original_name,
                            "storage_path": path,
                            "file_size": file.size,
                        }
                    ).execute()
            except Exception as exc:
                sb.table("posts").delete().eq("id", post_id).execute()
                st.error(_storage_upload_error_message(exc))
                return

        _download_file.clear()
        queue_message("게시글이 업로드 되었습니다")
        st.rerun()
    except Exception as exc:
        st.error(f"게시글 등록 실패: {exc}")


def _render_post_list(board_id: str, board_name: str):
    posts = _fetch_posts(board_id)

    if not posts:
        st.info("등록된 게시글이 없습니다.")
    else:
        for post in posts:
            with st.expander(f"{post['title']}  ·  {post['created_at'][:10]}", expanded=False):
                st.markdown(post["content"], unsafe_allow_html=True)

                attachments = _fetch_attachments(post["id"])
                if attachments:
                    st.markdown("**첨부파일**")
                    for att in attachments:
                        original_name = _original_filename(att)
                        try:
                            data = _download_file(att["storage_path"])
                            st.download_button(
                                label=f"📎 {original_name}",
                                data=data,
                                file_name=original_name,
                                key=f"dl_{att['id']}",
                            )
                        except Exception as exc:
                            st.warning(f"다운로드 실패 ({original_name}): {exc}")

                if is_admin():
                    if st.button("삭제", key=f"del_post_{post['id']}", type="secondary"):
                        sb = get_supabase()
                        storage_sb = get_storage_client()
                        for att in attachments:
                            try:
                                storage_sb.storage.from_(STORAGE_BUCKET).remove(
                                    [att["storage_path"]]
                                )
                            except Exception:
                                pass
                        sb.table("posts").delete().eq("id", post["id"]).execute()
                        _download_file.clear()
                        st.success("게시글이 삭제되었습니다.")
                        st.rerun()

    if is_admin():
        st.divider()
        st.markdown(f"### ✏️ {board_name} 글 작성 (관리자)")

        content = st_quill(
            "",
            html=True,
            toolbar=QUILL_TOOLBAR,
            key=f"quill_{board_id}",
        )

        with st.form(key=f"post_form_{board_id}", clear_on_submit=True):
            title = st.text_input("제목")
            uploaded = st.file_uploader(
                "첨부파일 (선택)",
                accept_multiple_files=True,
            )
            submitted = st.form_submit_button("등록", type="primary")

        if submitted:
            content_value = content or st.session_state.get(f"quill_{board_id}", "")
            if not title or not content_value:
                st.error("제목과 내용을 입력해 주세요.")
            else:
                _submit_post(board_id, title, content_value, uploaded)


def render_boards_page():
    st.header("게시판")
    boards = _fetch_boards()

    if not boards:
        st.warning("등록된 게시판이 없습니다.")
        return

    tab_labels = [b["name"] for b in boards]
    tabs = st.tabs(tab_labels)

    for board, tab in zip(boards, tabs):
        with tab:
            _render_post_list(board["id"], board["name"])
