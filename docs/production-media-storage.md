# Production media storage

CLOUT uses local files for Docker development and an S3-compatible object
store for durable production media. The S3 mode works with Cloudflare R2, AWS
S3, and MinIO; Cloudflare R2 is a practical default for short-form social
media because it provides S3 compatibility and avoids egress charges. Keep the
bucket private: CLOUT generates short-lived signed read URLs after applying its
own ownership and eligibility checks.

## What is stored

- Original brand toolkit uploads
- Platform video renditions made by FFmpeg
- Public social-video renditions and thumbnails
- Campaign-creative videos, profile images, and message attachments

The worker downloads inputs to its temporary cache, runs FFmpeg locally, then
uploads each generated output back to the object store. Browser-facing URLs
always use `MEDIA_PUBLIC_BASE_URL`; do not expose provider credentials to the
frontend.

## Render environment variables

Set these in the **backend Render service**, not in Vercel:

```text
STORAGE_BACKEND=s3
S3_BUCKET=<your bucket name>
S3_REGION=auto
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<S3 API token access key>
S3_SECRET_ACCESS_KEY=<S3 API token secret>
MEDIA_URL_EXPIRE_SECONDS=3600
```

For AWS S3, use its regional endpoint and region. Do not make the bucket
public; CLOUT creates signed URLs automatically.

## Bucket rules

1. Do **not** enable R2's public development URL or a public bucket domain.
2. Keep `GET`, `PUT`, `DELETE`, and object listing private to the backend
   credentials. CLOUT returns signed `GET` URLs only after API authorization.
3. Add a bucket CORS rule for CLOUT's Vercel origin and `http://localhost:3002`
   with `GET` and `HEAD` methods. This allows the browser to play signed media
   URLs returned by the API.
4. Set a lifecycle rule to remove incomplete multipart uploads and stale worker
   artifacts. CLOUT keys are server-generated and grouped under
   `advertisements/`, `renditions/`, `social/`, and `campaign-creatives/`.

## Verification after deployment

1. Upload a short MP4 through the Brand Toolkit.
2. Confirm it changes to `ready` and can play from the Ads Library.
3. Confirm generated rendition URLs use the R2 S3 endpoint and include a
   temporary signature.
4. Redeploy the backend and confirm the same video still plays.
5. Publish a creator campaign video, then confirm its public feed video and
   thumbnail load after another deploy.

Do not enable public posting until all five checks pass.
