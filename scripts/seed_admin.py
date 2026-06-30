"""관리자 계정을 Supabase에 생성합니다. python scripts/seed_admin.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase import create_client

from config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

ADMIN_USERNAME = "shbmaster"
ADMIN_PASSWORD = "shinhan@1"
ADMIN_EMAIL = "shbmaster@platform.local"
ADMIN_PHONE = "01000000000"


def _find_user_id_by_email(admin, email: str) -> str | None:
    page = 1
    while True:
        result = admin.list_users(page=page, per_page=200)
        users = result if isinstance(result, list) else getattr(result, "users", [])
        if not users:
            break
        for user in users:
            if user.email == email:
                return user.id
        if len(users) < 200:
            break
        page += 1
    return None


def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise SystemExit("SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY가 .env에 필요합니다.")

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    admin = client.auth.admin
    user_payload = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "email_confirm": True,
        "user_metadata": {
            "username": ADMIN_USERNAME,
            "phone_number": ADMIN_PHONE,
            "role": "admin",
        },
    }

    user_id = _find_user_id_by_email(admin, ADMIN_EMAIL)
    if user_id:
        admin.update_user_by_id(user_id, user_payload)
        print(f"기존 관리자 계정을 갱신했습니다. (아이디: {ADMIN_USERNAME})")
    else:
        response = admin.create_user(user_payload)
        user_id = response.user.id
        print(f"관리자 계정을 생성했습니다. (아이디: {ADMIN_USERNAME})")

    try:
        client.table("profiles").upsert(
            {
                "id": user_id,
                "username": ADMIN_USERNAME,
                "phone_number": ADMIN_PHONE,
                "email": ADMIN_EMAIL,
                "role": "admin",
            }
        ).execute()
    except Exception as exc:
        print(
            "Auth 계정은 준비되었습니다. profiles 테이블 연동은 schema.sql 실행 후 "
            f"다시 시도해 주세요. ({exc})"
        )
        return

    print("profiles 테이블에 관리자 권한을 반영했습니다.")


if __name__ == "__main__":
    main()
