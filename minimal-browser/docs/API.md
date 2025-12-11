# API Documentation

## Session Manager API

### Workspace Management

```cpp
// Add a new workspace
Workspace* add_workspace(const std::string& name);

// Get workspace by index
Workspace* get_workspace(size_t index);

// Get current workspace
Workspace* get_current_workspace();

// Switch to workspace
void switch_workspace(size_t index);
```

### Session Management

```cpp
// Get current session
Session* get_current_session();

// Switch to session
void switch_session(size_t index);

// Navigate sessions
void next_session();
void previous_session();
```

### Tab Management

```cpp
// Create new tab in current session
Tab* new_tab(const std::string& url = "about:blank");

// Close current tab
void close_current_tab();

// Get current tab
Tab* get_current_tab();

// Switch to tab
void switch_tab(size_t index);

// Navigate tabs
void next_tab();
void previous_tab();
```

## Tab API

### WebView Management

```cpp
// Get WebView (lazy creation)
WebKitWebView* get_webview();

// Get GTK container for WebView
GtkWidget* get_container();

// Explicitly create WebView
void create_webview();

// Destroy WebView (unload)
void destroy_webview();

// Check if WebView is loaded
bool is_loaded() const;
```

### Metadata

```cpp
// URL
std::string get_url() const;
void set_url(const std::string& url);

// Title
std::string get_title() const;
void set_title(const std::string& title);

// Activity tracking
void mark_active();
std::chrono::steady_clock::time_point get_last_active() const;
```

## Session API

### Tab Management

```cpp
// Add tab
Tab* add_tab(const std::string& url = "about:blank");

// Remove tab
void remove_tab(size_t index);

// Get tab
Tab* get_tab(size_t index);

// Get active tab
Tab* get_active_tab();

// Set active tab
void set_active_tab(size_t index);
```

### Session Metadata

```cpp
std::string get_name() const;
bool is_empty() const;
bool is_overview() const;
void set_overview(bool overview);
```

## Workspace API

### Session Management

```cpp
// Add session
Session* add_session(const std::string& name);

// Remove session
void remove_session(size_t index);

// Get session
Session* get_session(size_t index);

// Get active session
Session* get_active_session();

// Set active session
void set_active_session(size_t index);
```

### Workspace Metadata

```cpp
std::string get_name() const;
```

## IPC Interface (Future)

### D-Bus Interface

**Service**: `org.minimal.Browser`
**Object Path**: `/org/minimal/Browser`

### Methods

```xml
<!-- Open URL -->
<method name="OpenURL">
  <arg name="url" type="s" direction="in"/>
  <arg name="workspace" type="s" direction="in"/>
  <arg name="session" type="s" direction="in"/>
</method>

<!-- List Sessions -->
<method name="ListSessions">
  <arg name="workspace" type="s" direction="in"/>
  <arg name="sessions" type="a(ss)" direction="out"/>
</method>

<!-- Export Session -->
<method name="ExportSession">
  <arg name="workspace" type="s" direction="in"/>
  <arg name="session" type="s" direction="in"/>
  <arg name="json" type="s" direction="out"/>
</method>
```

### Signals

```xml
<!-- Tab Created -->
<signal name="TabCreated">
  <arg name="workspace" type="s"/>
  <arg name="session" type="s"/>
  <arg name="tab_id" type="u"/>
</signal>

<!-- Tab Closed -->
<signal name="TabClosed">
  <arg name="workspace" type="s"/>
  <arg name="session" type="s"/>
  <arg name="tab_id" type="u"/>
</signal>
```

## Example Usage

### Creating and Managing Tabs

```cpp
SessionManager sm;

// Create new tab
Tab* tab = sm.new_tab("https://example.com");

// Access tab metadata
std::string url = tab->get_url();
std::string title = tab->get_title();

// WebView is created lazily when accessed
WebKitWebView* webview = tab->get_webview();  // Creates if not loaded

// Unload tab (future)
tab->destroy_webview();  // WebView destroyed, metadata retained
```

### Workspace and Session Management

```cpp
SessionManager sm;

// Create workspace
Workspace* workspace = sm.add_workspace("Work");

// Get current session
Session* session = sm.get_current_session();

// Create tab in current session
Tab* tab = session->add_tab("https://example.com");

// Navigate
sm.next_tab();        // Next tab in current session
sm.next_session();     // Next session in current workspace
```

## Future APIs

### Persistence API

```cpp
class PersistenceManager {
public:
    void save_sessions();
    void load_sessions();
    void save_snapshot(Tab* tab);
    void load_snapshot(Tab* tab);
};
```

### Password Manager API

```cpp
class PasswordManager {
public:
    void store_credential(const std::string& origin,
                         const std::string& username,
                         const std::string& password);
    std::optional<Credential> get_credential(const std::string& origin);
    void autofill(WebKitWebView* webview);
};
```
