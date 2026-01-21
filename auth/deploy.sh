#!/bin/bash
# ABOUTME: Deployment script for the Google Auth service.
# ABOUTME: Sets up Cloud SQL, secrets, and deploys to Cloud Run.

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-seren-prod}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="seren-google-auth"
DB_INSTANCE_NAME="seren-google-auth-db"
DB_NAME="google_auth"
DB_USER="seren"

echo "=== Google Auth Service Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check required environment variables
if [ -z "$GOOGLE_CLIENT_ID" ]; then
    echo "ERROR: GOOGLE_CLIENT_ID is not set"
    echo "Get this from Google Cloud Console > APIs & Services > Credentials"
    exit 1
fi

if [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "ERROR: GOOGLE_CLIENT_SECRET is not set"
    echo "Get this from Google Cloud Console > APIs & Services > Credentials"
    exit 1
fi

if [ -z "$TOKEN_ENCRYPTION_KEY" ]; then
    echo "Generating TOKEN_ENCRYPTION_KEY..."
    TOKEN_ENCRYPTION_KEY=$(openssl rand -base64 32)
    echo "TOKEN_ENCRYPTION_KEY=$TOKEN_ENCRYPTION_KEY"
fi

echo "Step 1: Enable required APIs..."
gcloud services enable \
    sqladmin.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    --project=$PROJECT_ID

echo ""
echo "Step 2: Create Cloud SQL instance (if not exists)..."
if ! gcloud sql instances describe $DB_INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    echo "Creating Cloud SQL instance..."
    gcloud sql instances create $DB_INSTANCE_NAME \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --project=$PROJECT_ID

    # Generate and set password
    DB_PASSWORD=$(openssl rand -base64 24)
    gcloud sql users set-password postgres \
        --instance=$DB_INSTANCE_NAME \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID

    # Create database user
    gcloud sql users create $DB_USER \
        --instance=$DB_INSTANCE_NAME \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID

    # Create database
    gcloud sql databases create $DB_NAME \
        --instance=$DB_INSTANCE_NAME \
        --project=$PROJECT_ID

    echo "DB_PASSWORD=$DB_PASSWORD (save this!)"
else
    echo "Cloud SQL instance already exists"
    if [ -z "$DB_PASSWORD" ]; then
        echo "ERROR: DB_PASSWORD is required for existing instance"
        exit 1
    fi
fi

# Get Cloud SQL connection name
CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format='value(connectionName)')

echo ""
echo "Step 3: Store secrets in Secret Manager..."

# Function to create or update a secret
create_secret() {
    local name=$1
    local value=$2

    if gcloud secrets describe $name --project=$PROJECT_ID &>/dev/null; then
        echo "$value" | gcloud secrets versions add $name --data-file=- --project=$PROJECT_ID
    else
        echo "$value" | gcloud secrets create $name --data-file=- --project=$PROJECT_ID
    fi
    echo "Secret $name updated"
}

create_secret "google-auth-client-id" "$GOOGLE_CLIENT_ID"
create_secret "google-auth-client-secret" "$GOOGLE_CLIENT_SECRET"
create_secret "google-auth-encryption-key" "$TOKEN_ENCRYPTION_KEY"
create_secret "google-auth-db-password" "$DB_PASSWORD"

echo ""
echo "Step 4: Build and push container..."
gcloud builds submit \
    --config=cloudbuild-auth.yaml \
    --project=$PROJECT_ID \
    .

echo ""
echo "Step 5: Deploy to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=us-central1-docker.pkg.dev/$PROJECT_ID/google-api-services/seren-google-auth:latest \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --add-cloudsql-instances=$CONNECTION_NAME \
    --set-env-vars="LOG_LEVEL=INFO" \
    --set-env-vars="GOOGLE_REDIRECT_URI=https://google-auth.serendb.com/auth/google/callback" \
    --set-secrets="GOOGLE_CLIENT_ID=google-auth-client-id:latest" \
    --set-secrets="GOOGLE_CLIENT_SECRET=google-auth-client-secret:latest" \
    --set-secrets="TOKEN_ENCRYPTION_KEY=google-auth-encryption-key:latest" \
    --set-secrets="DATABASE_URL=projects/$PROJECT_ID/secrets/google-auth-db-url/versions/latest" \
    --project=$PROJECT_ID

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Set up custom domain mapping to https://google-auth.serendb.com"
echo "2. Update Google OAuth credentials with authorized redirect URI:"
echo "   https://google-auth.serendb.com/auth/google/callback"
echo "3. Test the OAuth flow:"
echo "   curl $SERVICE_URL/health"
echo ""
