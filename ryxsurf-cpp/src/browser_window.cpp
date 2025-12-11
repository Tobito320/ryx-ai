#include "browser_window.h"
#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <iostream>

BrowserWindow::BrowserWindow()
    : window_(nullptr)
    , main_box_(nullptr)
    , tab_bar_(nullptr)
    , address_bar_(nullptr)
    , notebook_(nullptr)
    , active_tab_index_(0)
    , keyboard_handler_(std::make_unique<KeyboardHandler>(this))
{
    // Create main window
    window_ = GTK_WINDOW(gtk_window_new());
    gtk_window_set_title(window_, "RyxSurf");
    gtk_window_set_default_size(window_, 1200, 800);
    
    // Main vertical box
    main_box_ = GTK_BOX(gtk_box_new(GTK_ORIENTATION_VERTICAL, 0));
    gtk_window_set_child(window_, GTK_WIDGET(main_box_));
    
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
    gtk_notebook_set_show_tabs(notebook_, FALSE);
    gtk_box_append(main_box_, GTK_WIDGET(notebook_));
    
    // Setup keyboard shortcuts
    keyboard_handler_->setup_shortcuts(window_);
    
    // Create initial tab
    new_tab();
    
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

void BrowserWindow::new_tab(const std::string& url) {
    auto tab = std::make_unique<Tab>(url.empty() ? "about:blank" : url);
    Tab* tab_ptr = tab.get();
    tabs_.push_back(std::move(tab));
    active_tab_index_ = tabs_.size() - 1;
    
    refresh_ui();
    show_tab(active_tab_index_);
    
    // Load URL if provided
    if (!url.empty()) {
        ensure_tab_webview_loaded(tab_ptr);
        webkit_web_view_load_uri(tab_ptr->get_webview(), url.c_str());
    }
}

void BrowserWindow::close_current_tab() {
    if (tabs_.empty()) {
        return;
    }
    
    if (tabs_.size() == 1) {
        // Keep at least one tab
        Tab* tab = tabs_[0].get();
        tab->set_url("about:blank");
        ensure_tab_webview_loaded(tab);
        webkit_web_view_load_uri(tab->get_webview(), "about:blank");
        tab->set_title("New Tab");
        refresh_ui();
        return;
    }
    
    // Remove tab
    tabs_.erase(tabs_.begin() + active_tab_index_);
    
    // Adjust active index
    if (active_tab_index_ >= tabs_.size()) {
        active_tab_index_ = tabs_.size() - 1;
    }
    
    refresh_ui();
    if (!tabs_.empty()) {
        show_tab(active_tab_index_);
    }
}

void BrowserWindow::next_tab() {
    if (tabs_.empty()) {
        return;
    }
    active_tab_index_ = (active_tab_index_ + 1) % tabs_.size();
    refresh_ui();
    show_tab(active_tab_index_);
}

void BrowserWindow::previous_tab() {
    if (tabs_.empty()) {
        return;
    }
    active_tab_index_ = (active_tab_index_ == 0) ? tabs_.size() - 1 : active_tab_index_ - 1;
    refresh_ui();
    show_tab(active_tab_index_);
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
    
    // Add tab buttons
    for (size_t i = 0; i < tabs_.size(); ++i) {
        Tab* tab = tabs_[i].get();
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
        if (i == active_tab_index_) {
            gtk_widget_add_css_class(GTK_WIDGET(button), "active-tab");
        }
        
        gtk_box_append(tab_bar_, GTK_WIDGET(button));
    }
}

void BrowserWindow::update_address_bar() {
    if (active_tab_index_ < tabs_.size()) {
        Tab* tab = tabs_[active_tab_index_].get();
        if (tab) {
            gtk_entry_set_text(address_bar_, tab->get_url().c_str());
        }
    }
}

void BrowserWindow::update_notebook() {
    // Handled by show_tab()
}

void BrowserWindow::refresh_ui() {
    update_tab_bar();
    update_address_bar();
}

void BrowserWindow::ensure_tab_webview_loaded(Tab* tab) {
    if (!tab || tab->is_loaded()) {
        return;
    }
    
    tab->create_webview();
}

void BrowserWindow::show_tab(size_t index) {
    if (index >= tabs_.size()) {
        return;
    }
    
    Tab* tab = tabs_[index].get();
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
    
    tab->mark_active();
    refresh_ui();
}

void BrowserWindow::on_address_bar_activated(GtkEntry* entry, gpointer user_data) {
    BrowserWindow* window = static_cast<BrowserWindow*>(user_data);
    const char* text = gtk_entry_get_text(entry);
    
    if (window->tabs_.empty()) {
        window->new_tab(text);
        return;
    }
    
    Tab* tab = window->tabs_[window->active_tab_index_].get();
    if (!tab) {
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
        if (index >= 0 && index < static_cast<int>(window->tabs_.size())) {
            window->active_tab_index_ = index;
            window->close_current_tab();
        }
    }
}
