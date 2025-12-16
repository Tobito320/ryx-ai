# Gmail OAuth Setup Guide

## ✅ Step 1: Google Cloud Console Configuration (COMPLETE)

Your OAuth client has been created successfully:
- **Client ID**: `YOUR_CLIENT_ID_HERE.apps.googleusercontent.com`
- **Client Secret**: `YOUR_CLIENT_SECRET_HERE`
- **Redirect URI**: `http://localhost:8420/api/gmail/oauth/callback` ✅ (Matches code!)
- **Status**: Activated ✅

## Step 2: Download and Save Client Configuration

1. **Click "JSON herunterladen" (Download JSON)** in the dialog
2. **Save the file** as `gmail_client_config.json` in your project's `data/` directory:
   ```bash
   # The file should be at:
   /home/tobi/ryx-ai/data/gmail_client_config.json
   ```

3. **Verify the JSON structure** - it should look like this:
   ```json
   {
     "web": {
       "client_id": "YOUR_CLIENT_ID_HERE.apps.googleusercontent.com",
       "project_id": "your-project-id",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
       "client_secret": "YOUR_CLIENT_SECRET_HERE",
       "redirect_uris": [
         "http://localhost:8420/api/gmail/oauth/callback"
       ]
     }
   }
   ```

## Step 3: Test the OAuth Flow

1. **Start your backend server** (if not already running):
   ```bash
   # Make sure backend is running on port 8420
   ```

2. **Open RyxHub** and go to **Settings** → **Session Settings**

3. **Click "Connect Gmail"** in the Gmail Integration section

4. **The OAuth flow should:**
   - Open Google's authorization page
   - Ask for Gmail permissions
   - Redirect back to `http://localhost:8420/api/gmail/oauth/callback`
   - Save tokens automatically
   - Show "Gmail Connected" status

## Step 4: Send Your First Email

1. **In a chat session**, ask: "Help me write an email to cancel Vodafone"
2. **Review the generated draft** in the email preview card
3. **Click "Send Email"** - it should send via Gmail!

## Important Notes

### Test Users Limitation
The dialog mentions: *"OAuth access is limited to test users listed on the OAuth consent screen"*

**For Development:** This is fine! You can add your Gmail address as a test user:
1. Go to Google Cloud Console → OAuth consent screen
2. Add your email under "Test users"
3. You'll be able to authorize the app

**For Production:** You'll need to:
1. Complete OAuth consent screen verification
2. Submit for Google verification (if using sensitive scopes)
3. Publish the app

### Security Reminder
⚠️ **Save the client secret securely!** As of June 2025, you won't be able to retrieve it after closing the dialog. The JSON download contains everything you need.

### Troubleshooting

**"Gmail not connected" error:**
- Check that `data/gmail_client_config.json` exists
- Verify the JSON structure is correct
- Ensure backend is running on port 8420

**OAuth callback fails:**
- Verify redirect URI matches exactly: `http://localhost:8420/api/gmail/oauth/callback`
- Check that port 8420 is accessible
- Ensure no firewall is blocking the callback

**Token refresh issues:**
- Tokens are stored encrypted in `data/gmail_tokens/`
- If tokens expire, the app should auto-refresh
- If refresh fails, disconnect and reconnect Gmail

## Next Steps

Once OAuth is working:
- ✅ Email drafts are automatically generated
- ✅ User info is pulled from memory
- ✅ Recipient emails are found via web search
- ✅ Emails can be sent directly from chat
- 🔄 Interactive email editor (coming soon)
- 🔄 Email templates (coming soon)
- 🔄 Email history (coming soon)
