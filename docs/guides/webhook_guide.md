# Strava Webhook Integration Guide

This guide explains how to set up and manage Strava webhook subscriptions for the ETL pipeline.

## Overview

Strava webhooks notify our system when new activities are created or existing ones are updated. The system uses these notifications to trigger the ETL process.

## Prerequisites

- Strava API Client ID and Client Secret
- Verify Token (a secret string you create)
- Deployed webhook endpoint (Cloud Function URL)
- Proper GCP permissions

## Setting Up Webhooks

### 1. Initial Configuration

Set your environment variables:
```bash
export STRAVA_CLIENT_ID=your_client_id
export STRAVA_CLIENT_SECRET=your_client_secret
export VERIFY_TOKEN=your_verify_token
```

### 2. Manage Subscriptions

#### View Current Subscriptions
```bash
curl -G https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=$STRAVA_CLIENT_ID \
  -d client_secret=$STRAVA_CLIENT_SECRET
```

#### Create New Subscription
```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=$STRAVA_CLIENT_ID \
  -d client_secret=$STRAVA_CLIENT_SECRET \
  -d callback_url=YOUR_WEBHOOK_URL \
  -d verify_token=$VERIFY_TOKEN
```

#### Delete Subscription
```bash
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/{SUBSCRIPTION_ID}?client_id=$STRAVA_CLIENT_ID&client_secret=$STRAVA_CLIENT_SECRET"
```

### 3. Webhook Verification

Strava performs two types of requests:
1. **GET request**: Initial verification
   - Responds to Strava's challenge
   - Verifies your subscription

2. **POST request**: Activity notifications
   - Receives activity updates
   - Triggers the ETL pipeline

## Implementation Details

### Webhook Handler Code Structure

```python
@functions_framework.http
def webhook(request):
    # GET request handling (verification)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                return {"hub.challenge": challenge}
        return 'Forbidden', 403

    # POST request handling (activity updates)
    elif request.method == 'POST':
        event_data = request.get_json()
        process_webhook_event(event_data)
        return 'EVENT_RECEIVED', 200
```

## Testing

1. **Local Testing with ngrok**:
   - Set up ngrok (see ngrok_guide.md)
   - Use ngrok URL as callback_url
   - Monitor webhook events locally

2. **Production Testing**:
   - Deploy webhook handler
   - Create subscription with production URL
   - Verify using Strava API endpoints

## Troubleshooting

### Common Issues

1. **Subscription Creation Fails**:
   - Verify callback URL is accessible
   - Check Client ID and Secret
   - Ensure verify_token matches

2. **Missing Events**:
   - Check webhook logs
   - Verify subscription status
   - Confirm correct permissions

3. **Verification Fails**:
   - Double-check VERIFY_TOKEN
   - Ensure endpoint responds correctly
   - Check URL accessibility

### Debugging Tools

1. **View Cloud Function Logs**:
```bash
gcloud functions logs read webhook-handler
```

2. **Test Webhook Endpoint**:
```bash
curl -X GET "YOUR_WEBHOOK_URL?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=challenge_string"
```

## Security Considerations

1. **Token Management**:
   - Use strong, unique verify tokens
   - Rotate tokens periodically
   - Store securely in environment variables

2. **Access Control**:
   - Implement proper authentication
   - Use HTTPS endpoints
   - Validate request origins

3. **Error Handling**:
   - Log failed attempts
   - Implement rate limiting
   - Handle malformed requests

## Maintenance

1. **Regular Tasks**:
   - Monitor webhook status
   - Check subscription validity
   - Review error logs

2. **Updates**:
   - Keep dependencies current
   - Update security tokens
   - Maintain documentation

## Additional Resources

- [Strava Webhooks API Documentation](https://developers.strava.com/docs/webhooks/)
- [GCP Cloud Functions Documentation](https://cloud.google.com/functions/docs)