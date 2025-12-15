"""
Gmail OAuth & API Integration for RyxHub
Handles OAuth flow, token management, and email sending.
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet


# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path("/home/tobi/ryx-ai/data")
TOKENS_DIR = DATA_DIR / "gmail_tokens"
TOKENS_DIR.mkdir(parents=True, exist_ok=True)

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose'
]

# Redirect URI (must match Google Cloud Console)
REDIRECT_URI = "http://localhost:8420/api/gmail/oauth/callback"

# Encryption key for token storage
# In production, load from secure environment variable
ENCRYPTION_KEY_FILE = DATA_DIR / ".gmail_key"


def get_encryption_key() -> bytes:
    """Get or generate encryption key for token storage."""
    if ENCRYPTION_KEY_FILE.exists():
        return ENCRYPTION_KEY_FILE.read_bytes()
    else:
        key = Fernet.generate_key()
        ENCRYPTION_KEY_FILE.write_bytes(key)
        os.chmod(ENCRYPTION_KEY_FILE, 0o600)  # Secure permissions
        return key


def encrypt_token(data: str) -> str:
    """Encrypt token data."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(data.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt token data."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted.encode()).decode()


# =============================================================================
# OAuth Flow
# =============================================================================

def get_oauth_flow(client_config: Dict[str, Any]) -> Flow:
    """Create OAuth flow from client config."""
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


def get_authorization_url(client_config: Dict[str, Any]) -> str:
    """Generate OAuth authorization URL."""
    flow = get_oauth_flow(client_config)
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent to get refresh token
    )
    return auth_url


def exchange_code_for_tokens(code: str, client_config: Dict[str, Any]) -> Credentials:
    """Exchange authorization code for access/refresh tokens."""
    flow = get_oauth_flow(client_config)
    flow.fetch_token(code=code)
    return flow.credentials


# =============================================================================
# Token Management
# =============================================================================

def save_tokens(user_id: str, credentials: Credentials):
    """Save encrypted tokens to disk."""
    token_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'expiry': credentials.expiry.isoformat() if credentials.expiry else None
    }
    
    encrypted = encrypt_token(json.dumps(token_data))
    token_file = TOKENS_DIR / f"{user_id}.json"
    token_file.write_text(encrypted)
    os.chmod(token_file, 0o600)


def load_tokens(user_id: str) -> Optional[Credentials]:
    """Load and decrypt tokens from disk."""
    token_file = TOKENS_DIR / f"{user_id}.json"
    
    if not token_file.exists():
        return None
    
    try:
        encrypted = token_file.read_text()
        decrypted = decrypt_token(encrypted)
        token_data = json.loads(decrypted)
        
        # Parse expiry back to datetime
        if token_data.get('expiry'):
            token_data['expiry'] = datetime.fromisoformat(token_data['expiry'])
        
        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )
        
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_tokens(user_id, creds)
        
        return creds
    
    except Exception as e:
        print(f"Failed to load tokens for {user_id}: {e}")
        return None


def revoke_tokens(user_id: str):
    """Delete stored tokens."""
    token_file = TOKENS_DIR / f"{user_id}.json"
    if token_file.exists():
        token_file.unlink()


# =============================================================================
# Gmail API Operations
# =============================================================================

def create_message(to: str, subject: str, body: str, from_email: Optional[str] = None) -> Dict:
    """Create email message in Gmail API format."""
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    if from_email:
        message['from'] = from_email
    
    msg_body = MIMEText(body, 'plain')
    message.attach(msg_body)
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}


def send_email(
    credentials: Credentials,
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None
) -> Dict[str, Any]:
    """Send email via Gmail API."""
    try:
        service = build('gmail', 'v1', credentials=credentials)
        message = create_message(to, subject, body, from_email)
        
        sent_message = service.users().messages().send(
            userId='me',
            body=message
        ).execute()
        
        return {
            'success': True,
            'message_id': sent_message['id'],
            'thread_id': sent_message.get('threadId')
        }
    
    except HttpError as error:
        return {
            'success': False,
            'error': str(error)
        }


def get_user_email(credentials: Credentials) -> Optional[str]:
    """Get user's Gmail address."""
    try:
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress')
    except HttpError:
        return None


def check_auth_status(user_id: str) -> Dict[str, Any]:
    """Check if user has valid Gmail authorization."""
    creds = load_tokens(user_id)
    
    if not creds:
        return {
            'authenticated': False,
            'email': None
        }
    
    email = get_user_email(creds)
    
    return {
        'authenticated': True,
        'email': email,
        'expired': creds.expired if hasattr(creds, 'expired') else False
    }
