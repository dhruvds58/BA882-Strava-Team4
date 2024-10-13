# Strava ETL Project

This project sets up an ETL (Extract, Transform, Load) pipeline for Strava data using Google Cloud Platform.

## Project Structure

- `cloud_functions/`: Contains code for GCP Cloud Functions
- `local_scripts/`: Contains scripts for local development and testing
- `docs/`: Detailed documentation for various aspects of the project

## Setup

1. Clone this repository
2. Set up a Google Cloud Platform account
3. Create a Cloud Storage bucket named "raw-events"
4. Deploy the webhook receiver Cloud Function

For detailed setup instructions, see [webhook_setup.md](docs/webhook_setup.md).

## Local Testing

For information on local testing with ngrok, see [local_testing.md](docs/local_testing.md).

## Cloud Function Deployment

To deploy the webhook receiver Cloud Function:

```bash
gcloud functions deploy webhooks \
  --runtime python310 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point webhook \
  --set-env-vars VERIFY_TOKEN=your_verify_token_here
```

Replace `your_verify_token_here` with your actual verify token.
