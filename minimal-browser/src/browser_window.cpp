#include "browser_window.h"
#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <iostream>

BrowserWindow::BrowserWindow()
    : window_(nullptr)
    , main_box_(nullptr)
    , tab_bar_(nullptr)
    , address_bar_(nullptr)
    , session_indicator_(nullptr)
    , notebook_(nullptr)
    ,     session_manager_(std::make_unique<SessionManager>())
    , keyboard_handler_(std::make_unique<KeyboardHandler>(session_manager_.get(), this))
{
    // Create main window
    window_ = GTK_WINDOW(gtk_window_new());
    gtk_window_set_title(window_, "Minimal Browser");
    gtk_window_set_default_size(window_, 1200, 800);
    
    // Main vertical box
    main_box_ = GTK_BOX(gtk_box_new(GTK_ORIENTATION_VERTICAL, 0));
    gtk_window_set_child(window_, GTK_WIDGET(main_box_));
    
    // Session indicator (compact horizontal bar)
    session_indicator_ = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4));
    gtk_widget_add_css_class(GTK_WIDGET(session_indicator_), "session-indicator");
    gtk_box_append(main_box_, GTK_WIDGET(session_indicator_));
    
    // Tab bar (horizontal, compact)
    tab_bar_ = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4));
    gtk_widget_add_css_class(GTK_WIDGET(tab_bar_), "tab-bar");
    gtk_box_append(main_box_, GTK_WIDGET(tab_bar_));
    
    // Address bar
    address_bar_ = GTK_ENTRY(gtk_entry_new());
    gtk_entry_set_placeholder_text(address_bar_, "Enter URL or search...");
    g_signal_connect(address_bar_, "activate",
                     G_CALLBACK(on_address_bar_activated), this);
    gtk_box_append(main_box_, GTK_WIDGET(address_bar_));
    
    // Notebook for tab webviews
    notebook_ = GTK_NOTEBOOK(gtk_notebook_new());
    gtk_notebook_set_show_tabs(notebook_, FALSE);  // We manage tabs ourselves
    gtk_box_append(main_box_, GTK_WIDGET(notebook_));
    
    // Setup keyboard shortcuts
    keyboard_handler_->setup_shortcuts(window_);
    
    // Initial UI update
    refresh_ui();
    
    // Connect window close
    g_signal_connect(window_, "close-request",
                     G_CALLBACK(+[](GtkWindow* window, gpointer) -> gboolean {
                         gtk_window_destroy(window);
                         return TRUE;
                     }), nullptr);
}

BrowserWindow::~BrowserWindow() {
    if (window_) {
        gtk_window_destroy(window_);
    }
}

void BrowserWindow::show() {
    gtk_window_present(window_);
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
        GtkBox* box = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4));
        
        GtkLabel* label = GTK_LABEL(gtk_label_new(tab->get_title().c_str()));
        gtk_box_append(box, GTK_WIDGET(label));
        
        GtkButton* close_btn = GTK_BUTTON(gtk_button_new_from_icon_name("window-close"));
        gtk_button_set_has_frame(close_btn, FALSE);
        g_signal_connect(close_btn, "clicked",
                         G_CALLBACK(on_tab_close_clicked), this);
        g_object_set_data(G_OBJECT(close_btn), "tab-index", GINT_TO_POINTER(i));
        gtk_box_append(box, GTK_WIDGET(close_btn));
        
        gtk_button_set_child(button, GTK_WIDGET(box));
        
        // Highlight active tab
        if (i == session->get_active_tab_index()) {
            gtk_widget_add_css_class(GTK_WIDGET(button), "active-tab");
        }
        
        gtk_box_append(tab_bar_, GTK_WIDGET(button));
    }
}

void BrowserWindow::update_session_indicator() {
    // Clear existing
    GtkWidget* child = gtk_widget_get_first_child(GTK_WIDGET(session_indicator_));
    while (child) {
        GtkWidget* next = gtk_widget_get_next_sibling(child);
        gtk_box_remove(session_indicator_, child);
        child = next;
    }
    
    Workspace* ws = session_manager_->get_current_workspace();
    if (!ws) {
        return;
    }
    
    // Add session labels
    for (size_t i = 0; i < ws->get_session_count(); ++i) {
        Session* session = ws->get_session(i);
        if (!session) {
            continue;
        }
        
        GtkLabel* label = GTK_LABEL(gtk_label_new(session->get_name().c_str()));
        if (i == ws->get_active_session_index()) {
            gtk_widget_add_css_class(GTK_WIDGET(label), "active-session");
        }
        gtk_box_append(session_indicator_, GTK_WIDGET(label));
    }
}

void BrowserWindow::update_address_bar() {
    Tab* tab = session_manager_->get_current_tab();
    if (tab) {
        gtk_entry_set_text(address_bar_, tab->get_url().c_str());
    }
}

void BrowserWindow::update_notebook() {
    Tab* tab = session_manager_->get_current_tab();
    if (!tab) {
        return;
    }
    
    ensure_tab_webview_loaded(tab);
    show_tab(tab);
}

void BrowserWindow::ensure_tab_webview_loaded(Tab* tab) {
    if (!tab || tab->is_loaded()) {
        return;
    }
    
    tab->create_webview();
}

void BrowserWindow::show_tab(Tab* tab) {
    if (!tab) {
        return;
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
    
    refresh_ui();
}

void BrowserWindow::refresh_ui() {
    update_tab_bar();
    update_session_indicator();
    update_address_bar();
    update_notebook();
}

void BrowserWindow::on_address_bar_activated(GtkEntry* entry, gpointer user_data) {
    BrowserWindow* window = static_cast<BrowserWindow*>(user_data);
    const char* text = gtk_entry_get_text(entry);
    
    Tab* tab = window->session_manager_->get_current_tab();
    if (!tab) {
        tab = window->session_manager_->new_tab();
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
    window->update_address_bar();
}

void BrowserWindow::on_tab_close_clicked(GtkButton* button, gpointer user_data) {
    BrowserWindow* window = static_cast<BrowserWindow*>(user_data);
    gpointer index_ptr = g_object_get_data(G_OBJECT(button), "tab-index");
    if (index_ptr) {
        int index = GPOINTER_TO_INT(index_ptr);
        Session* session = window->session_manager_->get_current_session();
        if (session) {
            session->remove_tab(index);
            window->update_tab_bar();
            window->update_notebook();
        }
    }
}
