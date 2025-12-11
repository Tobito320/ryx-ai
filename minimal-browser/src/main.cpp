#include "browser_window.h"
#include <gtk/gtk.h>
#include <webkit/webkit.h>
#include <iostream>

int main(int argc, char* argv[]) {
    // Initialize GTK
    gtk_init(&argc, &argv);
    
    // Initialize WebKit
    webkit_web_context_set_process_model(
        webkit_web_context_get_default(),
        WEBKIT_PROCESS_MODEL_SHARED_SECONDARY_PROCESS);
    
    // Create and show browser window
    BrowserWindow browser;
    browser.show();
    
    // Run GTK main loop
    gtk_main();
    
    return 0;
}
