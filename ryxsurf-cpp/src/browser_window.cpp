#include "browser_window.h"
#include "session_manager.h"
#include "tab_unload_manager.h"
#include "persistence_manager.h"
#include "password_manager.h"
#include "theme_manager.h"
#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <glib.h>
#include <iostream>

BrowserWindow::BrowserWindow()
    : window_(nullptr)
    , main_box_(nullptr)
    , tab_bar_(nullptr)
    , address_bar_(nullptr)
    , notebook_(nullptr)
    , session_manager_(std::make_unique<SessionManager>())
    , keyboard_handler_(std::make_unique<KeyboardHandler>(this))
    , unload_manager_(std::make_unique<TabUnloadManager>())
    , persistence_manager_(std::make_unique<PersistenceManager>(session_manager_.get()))
    , password_manager_(std::make_unique<PasswordManager>())
    , theme_manager_(std::make_unique<ThemeManager>())
    , unload_timer_id_(0)
{
    // Create main window
    window_ = GTK_WINDOW(gtk_window_new());
    gtk_window_set_title(window_, "RyxSurf");
    gtk_window_set_default_size(window_, 1200, 800);
    
    // Main vertical box
    main_box_ = GTK_BOX(gtk_box_new(GTK_ORIENTATION_VERTICAL, 0));
    gtk_window_set_child(window_, GTK_WIDGET(main_box_));
    
    // Session indicator (compact horizontal bar)
    GtkBox* session_indicator = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4));
    gtk_widget_add_css_class(GTK_WIDGET(session_indicator), "session-indicator");
    gtk_box_append(main_box_, GTK_WIDGET(session_indicator));
    
    // Tab bar (horizontal, compact)
    tab_bar_ = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4));
    gtk_widget_add_css_class(GTK_WIDGET(tab_bar_), "tab-bar");
    gtk_box_append(main_box_, GTK_WIDGET(tab_bar_));
    
    // Address bar
    address_bar_ = GTK_ENTRY(gtk_entry_new());
    gtk_entry_set_placeholder_text(address_bar_, "Enter URL or search...");
    gtk_widget_add_css_class(GTK_WIDGET(address_bar_), "address-bar");
    g_signal_connect(address_bar_, "activate",
                     G_CALLBACK(on_address_bar_activated), this);
    gtk_box_append(main_box_, GTK_WIDGET(address_bar_));
    
    // Notebook for tab webviews
    notebook_ = GTK_NOTEBOOK(gtk_notebook_new());
    gtk_notebook_set_show_tabs(notebook_, FALSE);
    gtk_box_append(main_box_, GTK_WIDGET(notebook_));
    
    // Setup keyboard shortcuts
    keyboard_handler_->setup_shortcuts(window_);
    
    // Apply theme
    theme_manager_->apply_to_window(window_);
    
    // Initialize persistence and load saved sessions
    if (persistence_manager_->initialize()) {
        persistence_manager_->load_all();
        persistence_manager_->enable_autosave(30);  // Autosave every 30 seconds
    }
    
    // Initialize password manager
    password_manager_->initialize();
    
    // Create initial tab if no sessions loaded
    if (session_manager_->get_current_session() && 
        session_manager_->get_current_session()->get_tab_count() == 0) {
        session_manager_->new_tab();
    }
    
    refresh_ui();
    update_notebook();
    
    // Setup periodic unload check (every 60 seconds)
    unload_timer_id_ = g_timeout_add_seconds(60, 
        [](gpointer user_data) -> gboolean {
            BrowserWindow* bw = static_cast<BrowserWindow*>(user_data);
            Session* session = bw->session_manager_->get_current_session();
            if (session) {
                bw->unload_manager_->check_and_unload(
                    session, session->get_active_tab_index());
            }
            return TRUE;  // Keep timer running
        }, this);
    
    // Connect window close - save before exit
    g_signal_connect(window_, "close-request",
                     G_CALLBACK(+[](GtkWindow* window, gpointer user_data) -> gboolean {
                         BrowserWindow* bw = static_cast<BrowserWindow*>(user_data);
                         if (bw->persistence_manager_) {
                             bw->persistence_manager_->save_all();
                         }
                         gtk_window_destroy(window);
                         return TRUE;
                     }), this);
}

BrowserWindow::~BrowserWindow() {
    // Save before exit
    if (persistence_manager_) {
        persistence_manager_->save_all();
        persistence_manager_->close();
    }
    
    // Remove unload timer
    if (unload_timer_id_ != 0) {
        g_source_remove(unload_timer_id_);
        unload_timer_id_ = 0;
    }
    
    if (window_) {
        gtk_window_destroy(window_);
    }
}

void BrowserWindow::show() {
    gtk_window_present(window_);
}

void BrowserWindow::new_tab(const std::string& url) {
    Tab* tab = session_manager_->new_tab(url.empty() ? "about:blank" : url);
    if (!tab) {
        return;
    }
    
    refresh_ui();
    Session* session = session_manager_->get_current_session();
    if (session) {
        show_tab(session->get_active_tab_index());
    }
    
    // Load URL if provided
    if (!url.empty()) {
        ensure_tab_webview_loaded(tab);
        WebKitWebView* webview = tab->get_webview();
        if (webview) {
            webkit_web_view_load_uri(webview, url.c_str());
        }
    }
}

void BrowserWindow::close_current_tab() {
    Session* session = session_manager_->get_current_session();
    if (!session) {
        return;
    }
    
    size_t tab_count = session->get_tab_count();
    if (tab_count == 0) {
        return;
    }
    
    if (tab_count == 1) {
        // Keep at least one tab
        Tab* tab = session->get_active_tab();
        if (tab) {
            tab->set_url("about:blank");
            ensure_tab_webview_loaded(tab);
            WebKitWebView* webview = tab->get_webview();
            if (webview) {
                webkit_web_view_load_uri(webview, "about:blank");
            }
            tab->set_title("New Tab");
        }
        refresh_ui();
        return;
    }
    
    // Remove tab via session manager
    session_manager_->close_current_tab();
    
    refresh_ui();
    session = session_manager_->get_current_session();
    if (session && session->get_tab_count() > 0) {
        show_tab(session->get_active_tab_index());
    }
}

void BrowserWindow::next_tab() {
    session_manager_->next_tab();
    refresh_ui();
    Session* session = session_manager_->get_current_session();
    if (session) {
        show_tab(session->get_active_tab_index());
    }
}

void BrowserWindow::previous_tab() {
    session_manager_->previous_tab();
    refresh_ui();
    Session* session = session_manager_->get_current_session();
    if (session) {
        show_tab(session->get_active_tab_index());
    }
}

void BrowserWindow::focus_address_bar() {
    gtk_widget_grab_focus(GTK_WIDGET(address_bar_));
    gtk_editable_select_region(GTK_EDITABLE(address_bar_), 0, -1);
}

void BrowserWindow::update_tab_bar() {
    // Clear existing tab buttons
    GtkWidget* child = gtk_widget_get_first_child(GTK_WIDGET(tab_bar_));
    while (child) {
        GtkWidget* next = gtk_widget_get_next_sibling(child);
        gtk_box_remove(tab_bar_, child);
        child = next;
    }
    
    Session* session = session_manager_->get_current_session();
    if (!session) {
        return;
    }
    
    // Add tab buttons
    for (size_t i = 0; i < session->get_tab_count(); ++i) {
        Tab* tab = session->get_tab(i);
        if (!tab) {
            continue;
        }
        
        GtkButton* button = GTK_BUTTON(gtk_button_new());
        gtk_widget_add_css_class(GTK_WIDGET(button), "tab-button");
        
        GtkBox* box = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4));
        
        GtkLabel* label = GTK_LABEL(gtk_label_new(tab->get_title().c_str()));
        gtk_widget_add_css_class(GTK_WIDGET(label), "tab-title");
        gtk_box_append(box, GTK_WIDGET(label));
        
        GtkButton* close_btn = GTK_BUTTON(gtk_button_new_from_icon_name("window-close"));
        gtk_button_set_has_frame(close_btn, FALSE);
        gtk_widget_add_css_class(GTK_WIDGET(close_btn), "tab-close-button");
        g_signal_connect(close_btn, "clicked",
                         G_CALLBACK(on_tab_close_clicked), this);
        g_object_set_data(G_OBJECT(close_btn), "tab-index", GINT_TO_POINTER(i));
        gtk_box_append(box, GTK_WIDGET(close_btn));
        
        gtk_button_set_child(button, GTK_WIDGET(box));
        
        // Highlight active tab
        if (i == session->get_active_tab_index()) {
            gtk_widget_add_css_class(GTK_WIDGET(button), "active-tab");
        }
        
        // Mark unloaded tabs
        if (tab->is_unloaded()) {
            gtk_widget_add_css_class(GTK_WIDGET(button), "unloaded");
        }
        
        // Add animation class
        if (theme_manager_->are_animations_enabled()) {
            gtk_widget_add_css_class(GTK_WIDGET(button), "animate-fade-in");
        }
        
        gtk_box_append(tab_bar_, GTK_WIDGET(button));
    }
}

void BrowserWindow::update_address_bar() {
    Tab* tab = session_manager_->get_current_tab();
    if (tab) {
        gtk_entry_set_text(address_bar_, tab->get_url().c_str());
    }
}

void BrowserWindow::update_notebook() {
    // Handled by show_tab()
}

void BrowserWindow::refresh_ui() {
    update_tab_bar();
    update_address_bar();
    update_session_indicator();
}

void BrowserWindow::update_session_indicator() {
    // Update session indicator (placeholder for now)
    // Real implementation would show workspace/session names
}

void BrowserWindow::ensure_tab_webview_loaded(Tab* tab) {
    if (!tab || tab->is_loaded()) {
        return;
    }
    
    tab->create_webview();
}

void BrowserWindow::show_tab(size_t index) {
    Session* session = session_manager_->get_current_session();
    if (!session) {
        return;
    }
    
    Tab* tab = session->get_tab(index);
    if (!tab) {
        return;
    }
    
    // Restore if unloaded
    if (tab->is_unloaded()) {
        tab->restore();
    }
    
    ensure_tab_webview_loaded(tab);
    
    // Remove all pages from notebook
    while (gtk_notebook_get_n_pages(notebook_) > 0) {
        gtk_notebook_remove_page(notebook_, 0);
    }
    
    // Add current tab's container
    GtkWidget* container = tab->get_container();
    if (container) {
        gtk_notebook_append_page(notebook_, container, nullptr);
    }
    
    tab->mark_active();
    refresh_ui();
}

void BrowserWindow::on_address_bar_activated(GtkEntry* entry, gpointer user_data) {
    BrowserWindow* window = static_cast<BrowserWindow*>(user_data);
    const char* text = gtk_entry_get_text(entry);
    
    Tab* tab = window->session_manager_->get_current_tab();
    if (!tab) {
        window->new_tab(text);
        return;
    }
    
    std::string url = text;
    if (url.find("://") == std::string::npos) {
        url = "https://" + url;
    }
    
    tab->set_url(url);
    window->ensure_tab_webview_loaded(tab);
    WebKitWebView* webview = tab->get_webview();
    if (webview) {
        webkit_web_view_load_uri(webview, url.c_str());
    }
    window->refresh_ui();
}

void BrowserWindow::on_tab_close_clicked(GtkButton* button, gpointer user_data) {
    BrowserWindow* window = static_cast<BrowserWindow*>(user_data);
    gpointer index_ptr = g_object_get_data(G_OBJECT(button), "tab-index");
    if (index_ptr) {
        int index = GPOINTER_TO_INT(index_ptr);
        Session* session = window->session_manager_->get_current_session();
        if (session && index >= 0 && index < static_cast<int>(session->get_tab_count())) {
            session->set_active_tab(index);
            window->close_current_tab();
        }
    }
}
