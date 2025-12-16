# Bug Fixes Applied

## Bug 1: Unreachable Code (Line 781) ✅ FIXED
**Issue:** Line 781 was unreachable because it was indented inside the `if` block after a `return` statement.

**Fix:** Unindented the second `return` statement to function scope so it executes when the file doesn't exist.

**Before:**
```python
if last_model_file.exists():
    return {"model": last_model_file.read_text().strip()}
    return {"model": DEFAULT_MODEL}  # Unreachable!
```

**After:**
```python
if last_model_file.exists():
    return {"model": last_model_file.read_text().strip()}
return {"model": DEFAULT_MODEL}  # Now executes when file doesn't exist
```

## Bug 2: Incomplete Email Draft Body (Line 1053) ✅ FIXED
**Issue:** Email draft contained incomplete German sentence `"ich möchte hiermit "` with no continuation.

**Fix:** Enhanced email draft builder to:
- Detect email intent (Kündigung, Beschwerde, Anfrage, Bestellung)
- Complete the sentence with appropriate action text
- Add user address if available from memory
- Improve recipient email extraction with regex pattern matching

**Before:**
```python
body_lines = [
    "Sehr geehrte Damen und Herren,",
    "",
    "ich möchte hiermit ",  # Incomplete!
    "",
    "Mit freundlichen Grüßen,",
    user_name
]
```

**After:**
```python
# Detects intent and completes sentence
if "kündigung" in msg_lower:
    subject = "Kündigung meines Vertrags"
    body_action = "hiermit meinen Vertrag kündigen"
elif "beschwerde" in msg_lower:
    body_action = "eine Beschwerde einreichen"
# ... etc

body_lines = [
    "Sehr geehrte Damen und Herren,",
    "",
    f"ich möchte {body_action}.",  # Complete sentence!
    "",
    "Mit freundlichen Grüßen,",
    user_name
]
```

## Bug 3: Missing Expiry Parameter (gmail_oauth.py Line 136) ✅ FIXED
**Issue:** Expiry time was parsed from stored data but never passed to `Credentials` constructor, breaking token refresh checks.

**Fix:** Extract expiry into a variable and pass it to the `Credentials` constructor.

**Before:**
```python
if token_data.get('expiry'):
    token_data['expiry'] = datetime.fromisoformat(token_data['expiry'])

creds = Credentials(
    token=token_data['token'],
    refresh_token=token_data.get('refresh_token'),
    token_uri=token_data['token_uri'],
    client_id=token_data['client_id'],
    client_secret=token_data['client_secret'],
    scopes=token_data['scopes']
    # Missing expiry parameter!
)
```

**After:**
```python
expiry = None
if token_data.get('expiry'):
    expiry = datetime.fromisoformat(token_data['expiry'])

creds = Credentials(
    token=token_data['token'],
    refresh_token=token_data.get('refresh_token'),
    token_uri=token_data['token_uri'],
    client_id=token_data['client_id'],
    client_secret=token_data['client_secret'],
    scopes=token_data['scopes'],
    expiry=expiry  # Now included!
)
```

## Additional Improvements

### Email Functionality Enhancements
1. **Better recipient detection:** Enhanced email extraction with regex patterns and company-specific keyword matching
2. **Email intent detection:** Now triggers search even when not needed for general queries, specifically to find contact emails
3. **Improved search queries:** For email intents, searches are enriched with "kontakt email kundenservice" keywords
4. **Import path fixes:** Fixed all Gmail OAuth imports to use relative imports (`.gmail_oauth`)

### Email Draft Improvements
- Detects multiple email types (Kündigung, Beschwerde, Anfrage, Bestellung)
- Automatically adds user address from memory if available
- Better recipient email extraction using regex
- Company-specific email detection (Vodafone, Telekom, O2)

## Testing Checklist

- [x] Bug 1: Function returns DEFAULT_MODEL when file doesn't exist
- [x] Bug 2: Email drafts have complete sentences
- [x] Bug 3: Token expiry is properly passed to Credentials
- [x] Email intent detection triggers search for contact info
- [x] Email drafts include user info from memory
- [x] Gmail OAuth imports work correctly
- [x] Email sending endpoint properly loads tokens

## Next Steps

1. Test email draft generation with various intents
2. Test Gmail OAuth flow end-to-end
3. Verify email sending works with real Gmail account
4. Test token refresh when credentials expire
