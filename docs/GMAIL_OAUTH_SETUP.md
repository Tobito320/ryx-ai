# Gmail OAuth Setup Guide

## Prerequisites

1. **Google Cloud Console Project**
   - Go to: https://console.cloud.google.com/
   - Create new project or use existing one
   - Name: "RyxHub Email Integration" (or similar)

2. **Enable Gmail API**
   ```
   1. In project, go to "APIs & Services" → "Library"
   2. Search "Gmail API"
   3. Click "Enable"
   ```

3. **Create OAuth 2.0 Credentials**
   ```
   1. Go to "APIs & Services" → "Credentials"
   2. Click "Create Credentials" → "OAuth client ID"
   3. Application type: "Web application"
   4. Name: "RyxHub"
   5. Authorized redirect URIs:
      - http://localhost:8420/api/gmail/oauth/callback
      - http://127.0.0.1:8420/api/gmail/oauth/callback
   6. Click "Create"
   7. Download JSON file
   ```

4. **Save Credentials**
   ```bash
   # Download the JSON file from Google Cloud Console
   # Save as: /home/tobi/ryx-ai/data/gmail_client_config.json
   
   # Format should be:
   {
     "web": {
       "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
       "project_id": "your-project-id",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
       "client_secret": "YOUR_CLIENT_SECRET",
       "redirect_uris": ["http://localhost:8420/api/gmail/oauth/callback"]
     }
   }
   ```

## Security Notes

⚠️ **NEVER commit `gmail_client_config.json` to git!**

- Already in .gitignore: `data/gmail_client_config.json`
- Tokens are encrypted at rest using `cryptography.Fernet`
- Encryption key stored in: `data/.gmail_key` (also gitignored)
- File permissions set to 0600 (user read/write only)

## OAuth Flow

### 1. User Clicks "Connect Gmail"
Frontend calls:
```typescript
POST /api/gmail/auth/start
{
  "client_config": { ... } // from env or backend config
}

Response:
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

### 2. User Authorizes
- Frontend opens `auth_url` in new window
- User logs in to Google
- User grants permissions
- Google redirects to callback

### 3. Backend Receives Callback
```
GET /api/gmail/oauth/callback?code=AUTH_CODE

Backend:
1. Exchanges code for access/refresh tokens
2. Encrypts tokens
3. Saves to data/gmail_tokens/{user_id}.json
4. Returns success
```

### 4. Sending Email
```typescript
POST /api/email/send
{
  "draft": {
    "to": "recipient@example.com",
    "subject": "Test",
    "body": "Hello world"
  },
  "user_id": "default"
}

Backend:
1. Loads encrypted tokens
2. Refreshes if expired
3. Sends via Gmail API
4. Returns message ID
```

## Testing

### 1. Check Auth Status
```bash
curl http://localhost:8420/api/gmail/auth/status?user_id=default
```

### 2. Start OAuth Flow (via frontend)
```typescript
// In RyxHub settings
const response = await fetch('/api/gmail/auth/start', {
  method: 'POST',
  body: JSON.stringify({ client_config: CONFIG })
});
const { auth_url } = await response.json();
window.open(auth_url, '_blank');
```

### 3. Send Test Email
```bash
curl -X POST http://localhost:8420/api/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "draft": {
      "to": "test@example.com",
      "subject": "Test from RyxHub",
      "body": "This is a test email"
    },
    "user_id": "default"
  }'
```

## Troubleshooting

### "Gmail not connected"
- Run auth flow first
- Check `data/gmail_tokens/default.json` exists
- Check auth status endpoint

### "Invalid credentials"
- Verify `gmail_client_config.json` format
- Check redirect URI matches Google Console exactly
- Ensure Gmail API is enabled in project

### "Token expired"
- Tokens auto-refresh if refresh_token exists
- If stuck, revoke and re-authorize:
  ```bash
  curl -X POST http://localhost:8420/api/gmail/auth/revoke \
    -H "Content-Type: application/json" \
    -d '{"user_id": "default"}'
  ```

## Rate Limits

Gmail API quotas (free tier):
- 1 billion quota units per day
- Sending email: 100 quota units per request
- ~10 million emails per day (theoretical)
- Practical: ~500-1000/day recommended

## Next Steps

1. Frontend OAuth button in Settings
2. Email editor component
3. Multi-account support
4. Email history/tracking
