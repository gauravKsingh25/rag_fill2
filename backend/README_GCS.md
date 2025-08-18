Google Cloud Storage integration (FastAPI)

This project supports storing processed files in Google Cloud Storage (GCS) and keeping a file history in the database (MongoDB) or local fallback.

Quick setup

1. Create a GCP project (if you don't have one):
   - Visit https://console.cloud.google.com/
   - Create a new project

2. Enable the Cloud Storage API:
   - In the Cloud Console, enable the "Cloud Storage" API for your project.

3. Create a service account with permissions:
   - Go to IAM & Admin -> Service Accounts -> Create Service Account
   - Assign role: "Storage Object Admin" (or more restrictive roles as needed)
   - Create and download a JSON key for the service account.

4. Configure your environment variables on the host running the FastAPI server:
   - Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of the downloaded JSON key file.
   - Set `GCS_BUCKET` to the name of the bucket you created in GCS.
   - Optional: set `MONGODB_URL` to point to your MongoDB if you want metadata stored in DB.

Example (Windows PowerShell):

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\service-account.json"
$env:GCS_BUCKET = "my-bucket-name"
$env:MONGODB_URL = "mongodb://..."
```

Notes about costs and free tier

- GCS offers a limited Free Tier: ~5 GB of regional storage (US only) plus some egress and operations. See Google Cloud Free Tier documentation for details.
- New users may receive $300 trial credits for broader testing.

How the code uses GCS

- `app/services/gcs_service.py` provides `upload_fileobj()` and `generate_signed_url()` helper functions. The service will only be used if `google-cloud-storage` is installed and `GCS_BUCKET` + credentials are configured.
- `app/routers/file_history.py` exposes:
  - GET `/api/file-history/` to retrieve the history (prefers MongoDB if configured, otherwise a fallback JSON file will be used).
  - POST `/api/file-history/` to upload a file and metadata. The file is uploaded to GCS when configured, and the endpoint returns a signed URL for download.

Getting an API key / credential

- For server-to-server access to GCS you don't need an "API key"; instead create a Service Account and download its JSON key as described above. This JSON contains all credentials the server needs.

Security

- Keep the service-account JSON secure and do not commit it to source control.
- Use least-privilege roles for the service account in production (e.g., restrict to specific bucket).

Troubleshooting

- If uploads fail, check application logs for warnings from `gcs_service` about missing credentials.
- Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to the JSON file and the file is readable by the process.

*** End of file
