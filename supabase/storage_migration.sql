-- Supabase SQL Editor에서 실행 (Storage 버킷 및 정책)
INSERT INTO storage.buckets (id, name, public)
VALUES ('post-files', 'post-files', false)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "post_files_select_authenticated" ON storage.objects;
DROP POLICY IF EXISTS "post_files_insert_admin" ON storage.objects;
DROP POLICY IF EXISTS "post_files_update_admin" ON storage.objects;
DROP POLICY IF EXISTS "post_files_delete_admin" ON storage.objects;

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

CREATE POLICY "post_files_update_admin"
    ON storage.objects FOR UPDATE
    TO authenticated
    USING (
        bucket_id = 'post-files'
        AND EXISTS (
            SELECT 1 FROM public.profiles p
            WHERE p.id = auth.uid() AND p.role = 'admin'
        )
    )
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
