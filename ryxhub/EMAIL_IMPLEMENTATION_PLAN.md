# Email Functionality Implementation Plan

## Overview

Implement intelligent email composition workflow where:
1. User asks to write an email
2. AI detects intent and gathers information (memory, RAG, web search)
3. AI composes email with user's info
4. Interactive editor opens (thread-like UI)
5. User can edit and refine
6. Email is sent with monitoring
7. Review shown after sending

## Architecture

### 1. Email Intent Detection

**Location:** Backend `/api/chat/smart`

**Detection Logic:**
```python
def detect_email_intent(message: str) -> bool:
    email_keywords = [
        'email', 'e-mail', 'mail', 'send email', 'write email',
        'compose email', 'email to', 'kündigung', 'cancellation',
        'termination', 'schreiben', 'write to'
    ]
    return any(kw in message.lower() for kw in email_keywords)
```

**When detected:**
- Set `needs_email_composition: true` in response
- Gather user info from memory (name, address, email)
- Search for recipient info if needed (e.g., "Vodafone email")
- Compose draft email

### 2. Information Gathering

**Memory Retrieval:**
- User name, address, email
- Previous email templates
- Contact information

**Web Search:**
- Company contact emails
- Location-specific contacts (e.g., "Vodafone Hagen email")
- Email templates/examples

**RAG:**
- Previous emails
- Document templates
- Legal templates (for Kündigung)

### 3. Email Composition

**Backend Endpoint:** `/api/email/compose`

**Request:**
```json
{
  "intent": "kündigung",
  "recipient": "Vodafone",
  "user_info": {
    "name": "Tobi",
    "address": "Hagen, Germany",
    "email": "tobi@example.com"
  },
  "context": "cancellation of service",
  "style": "formal"
}
```

**Response:**
```json
{
  "draft": {
    "id": "email-draft-123",
    "to": "kundenservice@vodafone.de",
    "from": "tobi@example.com",
    "subject": "Kündigung meines Vodafone-Vertrags",
    "body": "...",
    "attachments": []
  },
  "sources": {
    "recipient_email": "Found via web search",
    "template": "Based on RAG documents",
    "user_info": "From memory"
  }
}
```

### 4. Interactive Email Editor Component

**Component:** `EmailEditor.tsx`

**Features:**
- Thread-like UI (separate from chat)
- Editable fields:
  - To/CC/BCC
  - Subject
  - Body (rich text editor)
- Document upload
- Refinement commands:
  - "Make this more formal"
  - "Add my address"
  - "Refine selected text"
- Send button with confirmation
- Preview mode

**UI Structure:**
```
┌─────────────────────────────────────┐
│ Email Editor (Thread)               │
├─────────────────────────────────────┤
│ From: tobi@example.com [Change]    │
│ To:   kundenservice@vodafone.de    │
│ CC:   [Add]                         │
│ Subject: Kündigung meines...       │
├─────────────────────────────────────┤
│ [Rich Text Editor]                  │
│                                     │
│ Sehr geehrte Damen und Herren,     │
│                                     │
│ hiermit kündige ich...             │
│                                     │
├─────────────────────────────────────┤
│ [📎 Attach Document]                │
│ [Refine Selected] [Make Formal]    │
│                                     │
│ [Cancel] [Save Draft] [Send Email] │
└─────────────────────────────────────┘
```

### 5. Email Thread Integration

**Chat Message Display:**
- Show "📧 Email composition started" message
- Click to open email editor
- Editor opens in overlay/modal (thread-like)
- Can minimize/maximize
- Doesn't clutter chat

**State Management:**
```typescript
interface EmailThread {
  id: string;
  messageId: string; // Link to chat message
  draft: EmailDraft;
  status: "draft" | "sending" | "sent" | "failed";
  opened: boolean;
}
```

### 6. Email Sending

**Backend Endpoint:** `/api/email/send`

**Implementation:**
- Use Gmail API (OAuth) or SMTP (app password fallback)
- Monitor sending status
- Handle errors gracefully
- Store sent email in history

**Response:**
```json
{
  "success": true,
  "message_id": "gmail-message-id",
  "sent_at": "2024-01-15T10:30:00Z",
  "review": {
    "recipient": "kundenservice@vodafone.de",
    "subject": "Kündigung meines Vodafone-Vertrags",
    "sent_successfully": true,
    "delivery_status": "delivered"
  }
}
```

### 7. Post-Send Review

**Component:** `EmailReview.tsx`

**Shows:**
- What was sent
- When it was sent
- Delivery status (if available)
- Summary of the email
- Link to view in Gmail

## Implementation Steps

### Phase 1: Backend Email Detection & Composition
1. ✅ Add email intent detection to `/api/chat/smart`
2. ✅ Create `/api/email/compose` endpoint
3. ✅ Integrate memory, RAG, web search for info gathering
4. ✅ Generate email drafts

### Phase 2: Frontend Email Editor
1. ✅ Create `EmailEditor.tsx` component
2. ✅ Add rich text editor (use existing library)
3. ✅ Implement refinement commands
4. ✅ Add document upload

### Phase 3: Thread Integration
1. ✅ Add email thread state to chat
2. ✅ Create thread UI component
3. ✅ Link email editor to chat messages
4. ✅ Implement open/close thread functionality

### Phase 4: Email Sending
1. ✅ Implement Gmail OAuth flow
2. ✅ Create `/api/email/send` endpoint
3. ✅ Add sending status monitoring
4. ✅ Handle errors

### Phase 5: Review & Polish
1. ✅ Create email review component
2. ✅ Add email history
3. ✅ Improve UI/UX
4. ✅ Add email templates

## Gmail OAuth Flow

### Setup Required:
1. Google Cloud Console project
2. OAuth 2.0 credentials
3. Redirect URI: `http://localhost:8420/api/gmail/oauth/callback`
4. Scopes: `gmail.send`, `gmail.readonly`

### Flow:
1. User clicks "Connect Gmail" in settings
2. Redirect to Google OAuth consent screen
3. User authorizes
4. Google redirects back with code
5. Backend exchanges code for tokens
6. Store tokens securely (encrypted)
7. Use tokens for Gmail API calls

### Token Storage:
- Encrypt tokens before storing
- Store in database or secure file
- Implement token refresh
- Handle token expiration

## Technical Stack

**Backend:**
- FastAPI for endpoints
- Gmail API Python client
- OAuth2 library
- Email template engine

**Frontend:**
- React + TypeScript
- Rich text editor (e.g., TipTap or Slate)
- Modal/overlay for email editor
- State management (React Context)

## Security Considerations

1. **OAuth Tokens:**
   - Encrypt at rest
   - Use secure HTTP-only cookies
   - Implement token refresh
   - Never expose tokens to frontend

2. **Email Content:**
   - Sanitize user input
   - Validate email addresses
   - Rate limit sending
   - Log all email activity

3. **User Privacy:**
   - Don't store email content unnecessarily
   - Allow users to delete email history
   - Clear sensitive data on request

## Future Enhancements

1. **Email Templates:**
   - Save common email templates
   - Quick insert from template library
   - Template variables (name, date, etc.)

2. **Email Scheduling:**
   - Schedule emails for later
   - Time zone handling
   - Reminder notifications

3. **Email Analytics:**
   - Track open rates (if using tracking)
   - Response tracking
   - Email effectiveness metrics

4. **Multi-Account Support:**
   - Switch between Gmail accounts
   - Unified inbox view
   - Account-specific settings

5. **Email Threading:**
   - View email conversations
   - Reply to emails
   - Forward emails
   - Email search
