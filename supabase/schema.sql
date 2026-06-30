-- ============================================================
-- 현장지원 플랫폼 - Supabase PostgreSQL DDL
-- Supabase SQL Editor에서 실행하세요.
-- ============================================================

-- profiles: auth.users 와 1:1 연결
CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username    TEXT UNIQUE,
    phone_number TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'user'
                CHECK (role IN ('user', 'admin')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS username TEXT UNIQUE;
CREATE INDEX IF NOT EXISTS idx_profiles_username ON public.profiles(username);

CREATE INDEX IF NOT EXISTS idx_profiles_phone ON public.profiles(phone_number);
CREATE INDEX IF NOT EXISTS idx_profiles_role  ON public.profiles(role);

-- boards
CREATE TABLE IF NOT EXISTS public.boards (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- posts
CREATE TABLE IF NOT EXISTS public.posts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id    UUID NOT NULL REFERENCES public.boards(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posts_board_id ON public.posts(board_id);
CREATE INDEX IF NOT EXISTS idx_posts_user_id  ON public.posts(user_id);

-- 게시글 첨부파일 (매뉴얼/양식 다운로드용)
CREATE TABLE IF NOT EXISTS public.post_attachments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id     UUID NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
    file_name   TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_size   BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_post_attachments_post_id ON public.post_attachments(post_id);

-- 기본 게시판 데이터
INSERT INTO public.boards (name) VALUES
    ('공지사항'),
    ('매뉴얼/양식'),
    ('자주묻는질문')
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- RLS (Row Level Security)
-- ============================================================
ALTER TABLE public.profiles         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.boards           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.posts            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_attachments ENABLE ROW LEVEL SECURITY;

-- profiles
CREATE POLICY "profiles_select_authenticated"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "profiles_insert_own"
    ON public.profiles FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = id);

CREATE POLICY "profiles_update_own_or_admin"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (
        auth.uid() = id
        OR EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

CREATE POLICY "profiles_delete_admin"
    ON public.profiles FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

-- boards
CREATE POLICY "boards_select_all"
    ON public.boards FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "boards_insert_admin"
    ON public.boards FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

CREATE POLICY "boards_delete_admin"
    ON public.boards FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

-- posts
CREATE POLICY "posts_select_all"
    ON public.posts FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "posts_insert_admin"
    ON public.posts FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

CREATE POLICY "posts_update_admin"
    ON public.posts FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

CREATE POLICY "posts_delete_admin"
    ON public.posts FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

-- post_attachments
CREATE POLICY "attachments_select_all"
    ON public.post_attachments FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "attachments_insert_admin"
    ON public.post_attachments FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

CREATE POLICY "attachments_delete_admin"
    ON public.post_attachments FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

-- ============================================================
-- Storage bucket (Supabase Dashboard > Storage에서도 생성 가능)
-- ============================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('post-files', 'post-files', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "post_files_select_authenticated"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (bucket_id = 'post-files');

CREATE POLICY "post_files_insert_admin"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'post-files'
        AND EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

CREATE POLICY "post_files_delete_admin"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (
        bucket_id = 'post-files'
        AND EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    );

-- 회원가입 시 profiles 자동 생성 트리거 (선택: 앱에서 직접 insert도 가능)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, username, phone_number, email, role)
    VALUES (
        NEW.id,
        NULLIF(COALESCE(NEW.raw_user_meta_data->>'username', ''), ''),
        COALESCE(NEW.raw_user_meta_data->>'phone_number', ''),
        COALESCE(NEW.email, ''),
        COALESCE(NEW.raw_user_meta_data->>'role', 'user')
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 로그인: 전화번호 또는 아이디 → 이메일 조회 (비로그인 상태에서 사용)
CREATE OR REPLACE FUNCTION public.get_login_email(p_identifier TEXT)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_email TEXT;
BEGIN
    SELECT email INTO v_email
    FROM public.profiles
    WHERE phone_number = p_identifier OR username = p_identifier;

    IF v_email IS NULL THEN
        SELECT u.email INTO v_email
        FROM auth.users u
        WHERE u.raw_user_meta_data->>'username' = p_identifier;
    END IF;

    RETURN v_email;
END;
$$;

REVOKE ALL ON FUNCTION public.get_login_email(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_login_email(TEXT) TO anon, authenticated;
