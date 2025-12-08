import gi
gi.require_version('WebKit2', '4.0')
from gi.repository import WebKit2, Gtk, GLib
import requests
from bs4 import BeautifulSoup
import re

class BrowserAgent:
    def __init__(self):
        self.webview = WebKit2.WebView()
        self.webview.connect("load-finished", self.on_load_finished)
        self.window = Gtk.Window()
        self.window.add(self.webview)
        self.window.connect("destroy", Gtk.main_quit)
        self.window.show_all()

    def on_load_finished(self, webview, load_event):
        pass

    def execute_js(self, script):
        return self.webview.run_javascript(script, None, self.js_callback, None)

    def js_callback(self, source, result):
        try:
            result = source.run_javascript_finish(result)
            if result.get_js_value().is_object():
                print("JS Object:", result.get_js_value().to_string())
            elif result.get_js_value().is_number():
                print("JS Number:", result.get_js_value().to_number())
            elif result.get_js_value().is_string():
                print("JS String:", result.get_js_value().to_string())
            elif result.get_js_value().is_boolean():
                print("JS Boolean:", result.get_js_value().to_boolean())
        except Exception as e:
            print("Error executing JS:", e)

    def summarize_page(self):
        script = """
        let bodyText = document.body.innerText;
        let paragraphs = document.querySelectorAll('p');
        let summary = '';
        paragraphs.forEach(paragraph => {
            summary += paragraph.innerText + ' ';
        });
        return summary;
        """
        self.execute_js(script)

    def hide_element(self, selector):
        script = f"""
        let elements = document.querySelectorAll('{selector}');
        elements.forEach(element => {{
            element.style.display = 'none';
        }});
        """
        self.execute_js(script)

    def click_element(self, selector):
        script = f"""
        let elements = document.querySelectorAll('{selector}');
        elements.forEach(element => {{
            element.click();
        }});
        """
        self.execute_js(script)

    def search_and_open(self, query):
        search_url = f"https://www.google.com/search?q={query}"
        self.webview.load_uri(search_url)
        GLib.timeout_add_seconds(5, self.open_first_result)

    def open_first_result(self):
        script = """
        let links = document.querySelectorAll('h3 a');
        if (links.length > 0) {
            links[0].click();
        }
        """
        self.execute_js(script)

if __name__ == "__main__":
    agent = BrowserAgent()
    Gtk.main()