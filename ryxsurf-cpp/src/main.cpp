#include "browser_window.h"
#include "crypto.h"
#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <iostream>

static void activate(GtkApplication* app, gpointer user_data) {
    (void)user_data;
    (void)app;
    
    // Create and show browser window
    BrowserWindow* browser = new BrowserWindow();
    browser->show();
}

int main(int argc, char* argv[]) {
    // Initialize libsodium
    try {
        Crypto::init();
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize crypto: " << e.what() << std::endl;
        return 1;
    }
    
    // Create GTK4 application
    GtkApplication* app = gtk_application_new("com.ryxsurf.browser", G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app, "activate", G_CALLBACK(activate), nullptr);
    
    // Run application
    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    
    return status;
}
