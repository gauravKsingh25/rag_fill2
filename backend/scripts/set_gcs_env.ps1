param(
  [string]$KeyFile = "rag-fill-py-6607bea9063c.json",
  [string]$Bucket = "rag-fill-file-history",
  [switch]$CopyToFrontend
)

# Resolve script and backend root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendRoot = Resolve-Path (Join-Path $scriptDir "..")

# Resolve keyfile absolute path (if relative, treat as under backend root)
if (Test-Path $KeyFile) {
  $absKey = Resolve-Path $KeyFile
} else {
  $candidate = Join-Path $backendRoot $KeyFile
  if (Test-Path $candidate) {
    $absKey = Resolve-Path $candidate
  } else {
    Write-Host "ERROR: Key file not found at '$KeyFile' or '$candidate'." -ForegroundColor Red
    return
  }
}

# Persist environment variables for current user
Write-Host "Setting GOOGLE_APPLICATION_CREDENTIALS to $absKey"
setx GOOGLE_APPLICATION_CREDENTIALS $absKey | Out-Null

Write-Host "Setting GCS_BUCKET to $Bucket"
setx GCS_BUCKET $Bucket | Out-Null

Write-Host "Environment variables set for current user. You may need to restart your terminal / service to pick them up."

if ($CopyToFrontend.IsPresent) {
  $frontendEnv = Join-Path $backendRoot "..\frontend\.env"
  Write-Host "WARNING: Copying service account JSON to frontend is insecure for production."
  try {
    Copy-Item $absKey -Destination (Resolve-Path $frontendEnv -ErrorAction SilentlyContinue | ForEach-Object { Split-Path $_ }) -Force
    Write-Host "Copied service account JSON to frontend folder (insecure)."
  } catch {
    Write-Host "Could not copy to frontend path; ensure the frontend folder exists and rerun if desired."
  }
}

Write-Host "Done. If you're running the FastAPI app as a service, ensure the service picks up the user environment or set envs in the service config."
Write-Host "If you still see 'invalid_grant' errors, confirm the JSON is a service account key (not an OAuth token), hasn't been revoked, and has proper permissions for the bucket."
