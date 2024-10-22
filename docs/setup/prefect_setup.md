# Prefect Cloud Setup Guide

This guide details the setup and configuration of Prefect Cloud for the Strava ETL pipeline.

## Prerequisites

- Prefect Cloud account
- Python 3.12+
- GCP service account credentials
- Access to GCP resources

## Initial Setup

### 1. Install Prefect

```bash
pip install prefect==3.0.10 prefect-gcp==0.6.1
```

### 2. Authentication

```bash
# Login to Prefect Cloud
prefect cloud login

# Create API key in Prefect Cloud UI and set it
prefect config set PREFECT_API_KEY='your-api-key'
```

## Workspace Configuration

### 1. Create Work Pool

```bash
prefect work-pool create "strava-etl-pool" \
  --type prefect:managed
```

### 2. Configure GCP Block

1. Navigate to Blocks in Prefect UI
2. Create new GCP Credentials block:
   ```python
   from prefect_gcp import GcpCredentials
   
   credentials = GcpCredentials.load_from_service_account_file(
       "path/to/service-account.json"
   )
   credentials.save("gcp-creds")
   ```

## Flow Deployment

### 1. Directory Structure

```
prefect/
├── flows/
│   ├── etl_flow.py
│   └── __init__.py
└── deployments/
    └── deploy_etl.py
```

### 2. Deploy Flow

```bash
python prefect/deployments/deploy_etl.py
```

## Flow Configuration

### 1. Environment Variables

```bash
# Required environment variables for the flow
export PREFECT_API_URL="https://api.prefect.cloud/api/accounts/[ACCOUNT-ID]/workspaces/[WORKSPACE-ID]"
export PREFECT_API_KEY="your-prefect-api-key"
```

### 2. Flow Storage

Configure flow storage using GitHub:

```python
from prefect.filesystems import GitHub

github_block = GitHub.create(
    "strava-etl-repo",
    repository="https://github.com/yourusername/your-repo.git",
    reference="main"  # or your desired branch
)
```

## Monitoring and Logging

### 1. View Flow Runs

```bash
# List recent flow runs
prefect flow-run ls

# Get details of a specific run
prefect flow-run inspect <flow-run-id>
```

### 2. Set Up Notifications

1. Navigate to Notifications in Prefect UI
2. Configure notification rules:
   - Flow run failures
   - Task failures
   - Success notifications (optional)

## Flow Maintenance

### 1. Update Flow Version

```python
from prefect import flow

flow.from_source(
    source="https://github.com/yourusername/your-repo.git",
    entrypoint="prefect/flows/etl_flow.py:etl_flow",
).deploy(
    name="strava-etl-flow",
    work_pool_name="strava-etl-pool",
    version="1.0.3"
)
```

### 2. Schedule Management

```python
from prefect.schedules import CronSchedule

schedule = CronSchedule(crontab="0 * * * *")  # Hourly
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   ```bash
   # Verify authentication
   prefect cloud workspace ls
   ```

2. **Missing GCP Credentials**:
   - Check GCP block configuration
   - Verify service account permissions
   - Test credentials:
     ```python
     from prefect_gcp import GcpCredentials
     creds = GcpCredentials.load("gcp-creds")
     ```

3. **Deployment Failures**:
   - Check work pool status
   - Verify GitHub access
   - Review environment variables

## Best Practices

1. **Version Control**:
   - Use semantic versioning
   - Document changes
   - Test before deployment

2. **Security**:
   - Rotate API keys regularly
   - Use minimal permissions
   - Secure credential storage

3. **Monitoring**:
   - Set up alerts
   - Monitor resource usage
   - Track success rates

## Additional Resources

- [Prefect Documentation](https://docs.prefect.io/)
- [Prefect Cloud API Reference](https://docs.prefect.io/api-ref/)
- [GCP Integration Guide](https://docs.prefect.io/integrations/gcp/)