import streamlit as st
from streamlit_quill import st_quill

from config import STORAGE_BUCKET
from utils.supabase_client import get_supabase, is_admin


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


def _download_file(storage_path: str) -> bytes:
    sb = get_supabase()
    return sb.storage.from_(STORAGE_BUCKET).download(storage_path)


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
                        try:
                            data = _download_file(att["storage_path"])
                            st.download_button(
                                label=f"📎 {att['file_name']}",
                                data=data,
                                file_name=att["file_name"],
                                key=f"dl_{att['id']}",
                            )
                        except Exception as exc:
                            st.warning(f"다운로드 실패 ({att['file_name']}): {exc}")

                if is_admin():
                    if st.button("삭제", key=f"del_post_{post['id']}", type="secondary"):
                        sb = get_supabase()
                        for att in attachments:
                            try:
                                sb.storage.from_(STORAGE_BUCKET).remove([att["storage_path"]])
                            except Exception:
                                pass
                        sb.table("posts").delete().eq("id", post["id"]).execute()
                        st.success("게시글이 삭제되었습니다.")
                        st.rerun()

    if is_admin():
        st.divider()
        st.markdown(f"### ✏️ {board_name} 글 작성 (관리자)")
        title = st.text_input("제목", key=f"title_{board_id}")
        content = st_quill(
            "",
            html=True,
            toolbar=QUILL_TOOLBAR,
            key=f"quill_{board_id}",
        )
        uploaded = st.file_uploader(
            "첨부파일 (선택)",
            accept_multiple_files=True,
            key=f"upload_{board_id}",
        )

        if st.button("등록", key=f"submit_{board_id}", type="primary"):
            if not title or not content:
                st.error("제목과 내용을 입력해 주세요.")
            else:
                sb = get_supabase()
                user_id = st.session_state.user.id
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

                for file in uploaded or []:
                    path = f"{board_id}/{post_id}/{file.name}"
                    sb.storage.from_(STORAGE_BUCKET).upload(
                        path,
                        file.getvalue(),
                        {
                            "content-type": file.type or "application/octet-stream",
                            "upsert": "true",
                        },
                    )
                    sb.table("post_attachments").insert(
                        {
                            "post_id": post_id,
                            "file_name": file.name,
                            "storage_path": path,
                            "file_size": file.size,
                        }
                    ).execute()

                st.success("게시글이 등록되었습니다.")
                st.rerun()


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
