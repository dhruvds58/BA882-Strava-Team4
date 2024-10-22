# Google Cloud Platform Setup Guide

This guide walks through setting up GCP resources for the Strava ETL pipeline.

## Initial Setup

### 1. Create Project

```bash
# Create new project
gcloud projects create strava-etl

# Set project
gcloud config set project strava-etl
```

### 2. Enable APIs

```bash
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  pubsub.googleapis.com
```

## Service Account Setup

1. **Create Service Account**:
```bash
gcloud iam service-accounts create strava-etl-sa \
  --display-name="Strava ETL Service Account"
```

2. **Grant Permissions**:
```bash
# Storage permissions
gcloud projects add-iam-policy-binding strava-etl \
  --member="serviceAccount:strava-etl-sa@strava-etl.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# BigQuery permissions
gcloud projects add-iam-policy-binding strava-etl \
  --member="serviceAccount:strava-etl-sa@strava-etl.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

# Pub/Sub permissions
gcloud projects add-iam-policy-binding strava-etl \
  --member="serviceAccount:strava-etl-sa@strava-etl.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
```

## Resource Setup

### 1. Cloud Storage

```bash
# Create buckets
gsutil mb -l us-central1 gs://strava-users
```

### 2. BigQuery

```bash
# Create dataset
bq mk --dataset strava_data

# Create tables
bq mk --table strava_data.activities ./schemas/activities_schema.json
bq mk --table strava_data.laps ./schemas/laps_schema.json
```

### 3. Pub/Sub

```bash
# Create topics
gcloud pubsub topics create etl-trigger

# Create subscriptions
gcloud pubsub subscriptions create etl-trigger-sub \
  --topic etl-trigger
```

## Cloud Functions

### 1. Deploy Webhook Handler

```bash
gcloud functions deploy webhook-handler \
  --runtime python39 \
  --trigger-http \
  --entry-point webhook \
  --set-env-vars VERIFY_TOKEN=$VERIFY_TOKEN
```

### 2. Deploy OAuth Handler

```bash
gcloud functions deploy oauth-handler \
  --runtime python39 \
  --trigger-http \
  --entry-point oauth_flow \
  --set-env-vars CLIENT_ID=$CLIENT_ID,CLIENT_SECRET=$CLIENT_SECRET
```

### 3. Deploy Data Fetcher

```bash
gcloud functions deploy fetch-activity-data \
  --runtime python39 \
  --trigger-topic webhook-events \
  --entry-point fetch_activity_data
```

## Environment Configuration

1. **Create .env file**:
```bash
# .env
PROJECT_ID=strava-etl
BUCKET_NAME=strava-users
DATASET_ID=strava_data
```

2. **Set environment variables**:
```bash
source .env
```

## Monitoring Setup

1. **Create Log Sink**:
```bash
gcloud logging sinks create etl-logs \
  storage.googleapis.com/strava-etl-logs \
  --log-filter="resource.type=cloud_function"
```

2. **Set up Alerts**:
```bash
gcloud alpha monitoring channels create \
  --display-name="ETL Alerts" \
  --type=email \
  --email-address=your@email.com
```

## Security Configuration

1. **VPC Configuration**:
```bash
gcloud compute networks create etl-network \
  --subnet-mode=custom
```

2. **Firewall Rules**:
```bash
gcloud compute firewall-rules create allow-webhook \
  --network etl-network \
  --allow tcp:8080 \
  --source-ranges=0.0.0.0/0
```

## Testing

1. **Test Storage Access**:
```bash
gsutil ls gs://strava-users
```

2. **Test BigQuery**:
```bash
bq query "SELECT COUNT(*) FROM strava_data.activities"
```

3. **Test Pub/Sub**:
```bash
gcloud pubsub topics publish etl-trigger --message="test"
```

## Cleanup

```bash
# Delete project (BE CAREFUL!)
gcloud projects delete strava-etl
```

## Additional Resources

- [GCP Documentation](https://cloud.google.com/docs)
- [Cloud Functions](https://cloud.google.com/functions/docs)
- [BigQuery](https://cloud.google.com/bigquery/docs)