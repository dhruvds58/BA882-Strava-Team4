# Managing Strava Webhook Subscriptions

## Prerequisites
- Strava API Client ID
- Strava API Client Secret
- Verify Token (set in your webhook application)
- Callback URL (your webhook endpoint)

## View Current Subscriptions

```bash
curl -G https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET
```

## Delete a Subscription

```bash
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/{SUBSCRIPTION_ID}?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

Replace `{SUBSCRIPTION_ID}` with the ID of the subscription you want to delete.

## Create a New Subscription

```bash
curl -X POST "https://www.strava.com/api/v3/push_subscriptions?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&callback_url=YOUR_CALLBACK_URL&verify_token=YOUR_VERIFY_TOKEN"
```

## Update a Subscription

Strava doesn't provide a direct update method. To update, delete the old subscription and create a new one with the updated details.

1. Delete the old subscription (see "Delete a Subscription" above)
2. Create a new subscription with the updated details (see "Create a New Subscription" above)

## Troubleshooting

- Ensure your callback URL is accessible and responds correctly to Strava's verification request
- Double-check your Client ID, Client Secret, and Verify Token
- If you get a "subscription already exists" error, view current subscriptions and delete the existing one before creating a new one

Remember to replace `YOUR_CLIENT_ID`, `YOUR_CLIENT_SECRET`, `YOUR_CALLBACK_URL`, and `YOUR_VERIFY_TOKEN` with your actual values.