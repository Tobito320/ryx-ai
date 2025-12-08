import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Pango

class AISidebar(Gtk.Box):
    """
    A sidebar component for an AI chat interface.
    It includes a scrollable chat history and a text input area.
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Chat history box
        self.chat_history = Gtk.ScrolledWindow()
        self.chat_history.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.chat_history.set_child(self.chat_box)
        self.append(self.chat_history)

        # Text input area
        self.text_input = Gtk.Entry()
        self.text_input.set_placeholder_text("Type your message...")
        self.text_input.connect("activate", self.on_send)
        self.append(self.text_input)

    def add_message(self, role, content):
        """
        Adds a message to the chat history.

        :param role: The role of the message sender (e.g., "user", "assistant")
        :param content: The content of the message
        """
        message_label = Gtk.Label(label=f"{role}: {content}")
        message_label.set_line_wrap(True)
        message_label.set_max_width_chars(80)
        message_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.chat_box.append(message_label)
        self.scroll_to_bottom()

    def clear_history(self):
        """
        Clears all messages from the chat history.
        """
        for child in self.chat_box.get_children():
            self.chat_box.remove(child)

    def scroll_to_bottom(self):
        """
        Scrolls the chat history to the bottom.
        """
        adj = self.chat_history.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def on_send(self, widget):
        """
        Handles the send action when the user presses Enter in the text input.
        """
        message = widget.get_text().strip()
        if message:
            self.add_message("user", message)
            widget.set_text("")
            # Simulate sending the message to the AI and receiving a response
            self.add_message("assistant", "This is a response from the AI.")

# Example usage
if __name__ == "__main__":
    window = Gtk.Window(title="AI Sidebar Example")
    window.set_default_size(400, 600)
    ai_sidebar = AISidebar()
    window.set_child(ai_sidebar)
    window.connect("destroy", Gtk.main_quit)
    window.show()
    Gtk.main()