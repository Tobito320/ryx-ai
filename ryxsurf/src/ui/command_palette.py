import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, GLib
import json
import os

class CommandPalette(Gtk.Popover):
    """
    A command palette that shows a fuzzy-searchable popup with all available commands.
    Uses GTK4 Popover with an Entry for search and ListBox for results.
    """

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.set_modal(True)
        self.set_position(Gtk.PositionType.BOTTOM)

        # Load commands from JSON
        commands_file = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'commands.json')
        with open(commands_file, 'r') as f:
            self.commands_data = json.load(f)['commands']

        # Create UI components
        self.search_entry = Gtk.Entry()
        self.search_entry.connect('search-changed', self.on_search_changed)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect('row-activated', self.on_row_activated)

        # Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.append(self.search_entry)
        vbox.append(self.list_box)
        self.set_child(vbox)

        # Populate initial list
        self.populate_list()

    def populate_list(self):
        """
        Populate the ListBox with all available commands.
        """
        self.list_box.remove_all()
        for command_name, command_info in self.commands_data.items():
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=f"{command_name} - {command_info['description']}")
            row.set_child(label)
            self.list_box.append(row)

    def on_search_changed(self, entry):
        """
        Filter the ListBox based on the search entry text.
        """
        query = entry.get_text().lower()
        self.list_box.remove_all()
        for command_name, command_info in self.commands_data.items():
            if query in command_name.lower() or query in command_info['description'].lower():
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=f"{command_name} - {command_info['description']}")
                row.set_child(label)
                self.list_box.append(row)

    def on_row_activated(self, list_box, row):
        """
        Handle row activation (command selection).
        """
        selected_command = row.get_child().get_label().split(' - ')[0]
        print(f"Command selected: {selected_command}")
        self.hide()

# Example usage
if __name__ == "__main__":
    class MainWindow(Gtk.Window):
        def __init__(self):
            super().__init__(title="Command Palette Example")
            self.set_default_size(400, 300)

            button = Gtk.Button(label="Open Command Palette")
            button.connect("clicked", self.on_button_clicked)
            self.set_child(button)

            self.command_palette = CommandPalette(self)

        def on_button_clicked(self, button):
            self.command_palette.popup()

    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show()
    Gtk.main()