# Candidate review setup

Staff review is available at `/admin/login`. It is disabled until all three server environment variables are configured:

- `ADMIN_EMAIL`: staff sign-in email.
- `ADMIN_PASSWORD`: a unique, strong staff password. Do not put it in source control or chat.
- `SECRET_KEY`: a stable random value used to sign sessions. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` and enter it directly in the hosting provider's environment settings.

Profile photos and new resumes are stored outside the public static directory. For durable uploads on Render, attach a persistent disk and set:

- `PROFILE_PHOTO_UPLOAD_FOLDER=/var/data/profile_photos`
- `RESUME_UPLOAD_FOLDER=/var/data/resumes`

Mount the disk at `/var/data`. Without persistent storage, files on Render's instance filesystem can be lost during restarts or deployments. Existing resumes in `static/uploads/resumes` remain readable through the protected application file route.