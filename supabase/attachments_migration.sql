-- post_attachments: 원본 파일명 컬럼 추가
ALTER TABLE public.post_attachments
    ADD COLUMN IF NOT EXISTS original_filename TEXT;

UPDATE public.post_attachments
SET original_filename = file_name
WHERE original_filename IS NULL AND file_name IS NOT NULL;
