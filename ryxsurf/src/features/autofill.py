"""
Autofill - Form detection and auto-filling

Injects JavaScript to detect login forms and fill credentials.
Integrates with PasswordManager for secure storage.
Only loads when forms are detected.
"""

from typing import Optional, Callable
import json

# JavaScript for form detection
DETECT_FORMS_JS = """
(function() {
    const forms = document.querySelectorAll('form');
    const loginForms = [];
    
    forms.forEach((form, idx) => {
        const inputs = form.querySelectorAll('input');
        let hasPassword = false;
        let hasUsername = false;
        let usernameField = null;
        let passwordField = null;
        
        inputs.forEach(input => {
            const type = input.type.toLowerCase();
            const name = (input.name || '').toLowerCase();
            const id = (input.id || '').toLowerCase();
            const placeholder = (input.placeholder || '').toLowerCase();
            
            if (type === 'password') {
                hasPassword = true;
                passwordField = {
                    name: input.name,
                    id: input.id,
                    selector: input.name ? `input[name="${input.name}"]` : `input[id="${input.id}"]`
                };
            } else if (type === 'text' || type === 'email') {
                const isUsername = name.includes('user') || name.includes('email') || name.includes('login') ||
                                   id.includes('user') || id.includes('email') || id.includes('login') ||
                                   placeholder.includes('user') || placeholder.includes('email');
                if (isUsername) {
                    hasUsername = true;
                    usernameField = {
                        name: input.name,
                        id: input.id,
                        selector: input.name ? `input[name="${input.name}"]` : `input[id="${input.id}"]`
                    };
                }
            }
        });
        
        if (hasPassword) {
            loginForms.push({
                index: idx,
                hasUsername: hasUsername,
                usernameField: usernameField,
                passwordField: passwordField,
                action: form.action || window.location.href
            });
        }
    });
    
    return JSON.stringify(loginForms);
})();
"""

# JavaScript to fill a form
FILL_FORM_JS = """
(function(username, password, usernameSelector, passwordSelector) {
    if (usernameSelector) {
        const usernameField = document.querySelector(usernameSelector);
        if (usernameField) {
            usernameField.value = username;
            usernameField.dispatchEvent(new Event('input', { bubbles: true }));
            usernameField.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
    
    if (passwordSelector) {
        const passwordField = document.querySelector(passwordSelector);
        if (passwordField) {
            passwordField.value = password;
            passwordField.dispatchEvent(new Event('input', { bubbles: true }));
            passwordField.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
    
    return true;
})('%s', '%s', '%s', '%s');
"""

# JavaScript to detect form submission (for saving new passwords)
DETECT_SUBMIT_JS = """
(function() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('input');
            let username = '';
            let password = '';
            
            inputs.forEach(input => {
                const type = input.type.toLowerCase();
                const name = (input.name || '').toLowerCase();
                
                if (type === 'password' && input.value) {
                    password = input.value;
                } else if ((type === 'text' || type === 'email') && input.value) {
                    if (name.includes('user') || name.includes('email') || name.includes('login')) {
                        username = input.value;
                    }
                }
            });
            
            if (username && password) {
                window.webkit.messageHandlers.passwordSubmit.postMessage({
                    username: username,
                    password: password,
                    url: window.location.href
                });
            }
        });
    });
})();
"""


class Autofill:
    """Form autofill with password manager integration"""
    
    def __init__(self, password_manager):
        self.pm = password_manager
        self._pending_forms = {}
    
    def detect_forms(self, webview, callback: Callable):
        """Detect login forms on current page"""
        def on_result(webview, result, user_data):
            try:
                js_result = webview.evaluate_javascript_finish(result)
                if js_result:
                    forms_json = js_result.to_string()
                    forms = json.loads(forms_json) if forms_json else []
                    callback(forms)
            except Exception as e:
                print(f"Form detection error: {e}")
                callback([])
        
        webview.evaluate_javascript(
            DETECT_FORMS_JS,
            -1, None, None, None,
            on_result, None
        )
    
    def fill_form(self, webview, username: str, password: str, 
                  username_selector: str, password_selector: str):
        """Fill a login form with credentials"""
        # Escape special characters
        username_escaped = username.replace("'", "\\'").replace("\\", "\\\\")
        password_escaped = password.replace("'", "\\'").replace("\\", "\\\\")
        
        js = FILL_FORM_JS % (
            username_escaped, 
            password_escaped,
            username_selector or '',
            password_selector or ''
        )
        
        webview.evaluate_javascript(js, -1, None, None, None, None, None)
    
    def setup_submit_detection(self, webview):
        """Setup listener for form submissions to save new passwords"""
        webview.evaluate_javascript(DETECT_SUBMIT_JS, -1, None, None, None, None, None)
    
    def auto_fill_if_available(self, webview, domain: str, callback: Callable):
        """Auto-fill form if we have credentials for this domain"""
        if not self.pm.has_credentials(domain):
            callback(False)
            return
        
        def on_forms_detected(forms):
            if not forms:
                callback(False)
                return
            
            cred = self.pm.get_one(domain)
            if not cred:
                callback(False)
                return
            
            # Fill the first form with password field
            form = forms[0]
            self.fill_form(
                webview,
                cred.username,
                cred.password,
                form.get('usernameField', {}).get('selector', ''),
                form.get('passwordField', {}).get('selector', '')
            )
            
            # Update last used
            self.pm.update_last_used(domain, cred.username)
            callback(True)
        
        self.detect_forms(webview, on_forms_detected)


# Lazy loading
_instance: Optional[Autofill] = None

def get_autofill(password_manager) -> Autofill:
    """Get or create autofill instance"""
    global _instance
    if _instance is None:
        _instance = Autofill(password_manager)
    return _instance
