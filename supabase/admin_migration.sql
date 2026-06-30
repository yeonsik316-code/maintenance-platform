-- Supabase SQL Editor에서 실행 (관리자 계정/아이디 로그인용)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS username TEXT UNIQUE;
CREATE INDEX IF NOT EXISTS idx_profiles_username ON public.profiles(username);

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
