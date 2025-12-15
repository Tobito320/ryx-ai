"""
Sandboxed Agent - Runs inside Docker container with strict isolation.
"""

import os
import sys
import signal
import json
from urllib.parse import urlparse


def timeout_handler(signum, frame):
    print("⏱️ Sandbox timeout - killing agent")
    sys.exit(1)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 second hard limit


class SandboxedAgent:
    def __init__(self):
        allowed = os.getenv("ALLOWED_DOMAINS", "")
        self.allowed_domains = [d.strip() for d in allowed.split(",") if d.strip()]
    
    def is_url_allowed(self, url: str) -> bool:
        """Whitelist check for URLs"""
        domain = urlparse(url).netloc
        
        for allowed in self.allowed_domains:
            pattern = allowed.replace("*.", "")
            if pattern in domain:
                return True
        
        print(f"🚫 BLOCKED: {url} not in whitelist")
        return False
    
    def run_browser_action(self, url: str):
        """Run browser action in sandbox"""
        if not self.is_url_allowed(url):
            raise PermissionError(f"Domain not whitelisted: {url}")
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-blink-features=AutomationControlled'
                    ]
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='RyxHub/1.0 (Sandboxed Agent)'
                )
                
                page = context.new_page()
                page.set_default_timeout(10000)
                
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    content = page.content()
                    
                    # Save to output volume
                    with open('/output/scraped.html', 'w') as f:
                        f.write(content)
                    
                    result = {
                        "status": "success",
                        "url": url,
                        "content_length": len(content)
                    }
                    print(json.dumps(result))
                    
                except Exception as e:
                    print(json.dumps({"status": "error", "message": str(e)}))
                
                finally:
                    browser.close()
                    
        except ImportError:
            print(json.dumps({"status": "error", "message": "Playwright not installed"}))
    
    def run_code(self, code: str):
        """Execute Python code in sandbox"""
        import io
        import contextlib
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(code, {"__builtins__": __builtins__})
            
            result = {
                "status": "success",
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue()
            }
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e),
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue()
            }
        
        print(json.dumps(result))
        
        # Save result to output
        with open('/output/result.json', 'w') as f:
            json.dump(result, f)


if __name__ == "__main__":
    agent = SandboxedAgent()
    
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "No command provided"}))
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "browse" and len(sys.argv) > 2:
        agent.run_browser_action(sys.argv[2])
    elif command == "exec" and len(sys.argv) > 2:
        agent.run_code(sys.argv[2])
    else:
        print(json.dumps({"status": "error", "message": f"Unknown command: {command}"}))
