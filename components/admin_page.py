import streamlit as st

from utils.supabase_client import get_admin_client, get_supabase, is_admin


def render_board_management():
    st.header("게시판 관리")
    st.caption("관리자만 게시판을 추가하거나 삭제할 수 있습니다.")

    sb = get_supabase()
    boards = sb.table("boards").select("*").order("created_at").execute().data or []

    st.subheader("현재 게시판")
    if boards:
        for board in boards:
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{board['name']}**")
            if col2.button("삭제", key=f"del_board_{board['id']}"):
                sb.table("boards").delete().eq("id", board["id"]).execute()
                st.success(f"'{board['name']}' 게시판이 삭제되었습니다.")
                st.rerun()
    else:
        st.info("등록된 게시판이 없습니다.")

    st.divider()
    st.subheader("새 게시판 추가")
    with st.form("add_board_form", clear_on_submit=True):
        name = st.text_input("게시판 이름")
        submitted = st.form_submit_button("추가", type="primary")

    if submitted:
        if not name.strip():
            st.error("게시판 이름을 입력해 주세요.")
        else:
            try:
                sb.table("boards").insert({"name": name.strip()}).execute()
                st.success(f"'{name.strip()}' 게시판이 추가되었습니다.")
                st.rerun()
            except Exception as exc:
                st.error(f"추가 실패: {exc}")


def render_member_management():
    st.header("가입자 정보 관리")
    st.caption("전체 회원 목록 조회 및 탈퇴(삭제) 처리")

    admin_client = get_admin_client()
    if not admin_client:
        st.error(
            "회원 삭제 기능을 사용하려면 `.env`에 "
            "`SUPABASE_SERVICE_ROLE_KEY`를 설정해 주세요."
        )

    sb = get_supabase()
    members = (
        sb.table("profiles")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    if not members:
        st.info("등록된 회원이 없습니다.")
        return

    st.metric("전체 회원 수", len(members))

    for member in members:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            col1.markdown(f"**전화번호**  \n{member['phone_number']}")
            col2.markdown(f"**이메일**  \n{member['email']}")
            role_label = "관리자" if member["role"] == "admin" else "일반"
            col3.markdown(f"**권한**  \n{role_label}")
            col4.markdown(f"**가입일**  \n{member['created_at'][:10]}")

            current_id = st.session_state.user.id
            if member["id"] == current_id:
                col5.caption("본인")
            elif col5.button("탈퇴", key=f"del_member_{member['id']}", type="secondary"):
                if admin_client:
                    try:
                        admin_client.auth.admin.delete_user(member["id"])
                        st.success(f"{member['phone_number']} 회원이 탈퇴 처리되었습니다.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"탈퇴 처리 실패: {exc}")
                else:
                    try:
                        sb.table("profiles").delete().eq("id", member["id"]).execute()
                        st.warning(
                            "프로필만 삭제되었습니다. "
                            "Auth 계정까지 삭제하려면 SERVICE_ROLE_KEY가 필요합니다."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"삭제 실패: {exc}")


def render_admin_pages(page: str):
    if not is_admin():
        st.error("관리자 권한이 필요합니다.")
        return

    if page == "board_mgmt":
        render_board_management()
    elif page == "member_mgmt":
        render_member_management()
