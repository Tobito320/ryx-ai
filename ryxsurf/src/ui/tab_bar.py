import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject

class TabBar(Gtk.Box):
    """
    A horizontal tab bar component.
    It allows adding, removing, and switching between tabs.
    """
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.tabs = []
        self.current_tab_index = -1
        self.connect("realize", self.on_realize)

    def on_realize(self, widget):
        # Initialize the first tab if there are any
        if self.tabs:
            self.switch_tab(0)

    def add_tab(self, label: str, content: Gtk.Widget):
        """
        Adds a new tab with the given label and content.
        
        :param label: The label to display on the tab.
        :param content: The content widget to show when this tab is active.
        """
        tab_button = Gtk.Button(label=label)
        tab_button.connect("clicked", self.on_tab_clicked, len(self.tabs))
        self.append(tab_button)
        self.tabs.append((tab_button, content))
        if self.current_tab_index == -1:
            self.switch_tab(0)

    def remove_tab(self, index: int):
        """
        Removes the tab at the specified index.
        
        :param index: The index of the tab to remove.
        """
        if 0 <= index < len(self.tabs):
            tab_button, content = self.tabs.pop(index)
            tab_button.destroy()
            content.destroy()
            if self.current_tab_index >= index:
                self.current_tab_index -= 1
            if self.tabs:
                self.switch_tab(max(0, self.current_tab_index))

    def switch_tab(self, index: int):
        """
        Switches to the tab at the specified index.
        
        :param index: The index of the tab to switch to.
        """
        if 0 <= index < len(self.tabs):
            if self.current_tab_index != -1:
                old_tab_button, old_content = self.tabs[self.current_tab_index]
                old_tab_button.get_style_context().remove_class("active")
                old_content.hide()
            
            new_tab_button, new_content = self.tabs[index]
            new_tab_button.get_style_context().add_class("active")
            new_content.show()
            self.current_tab_index = index

    def on_tab_clicked(self, button: Gtk.Button, index: int):
        """
        Callback for when a tab button is clicked.
        
        :param button: The button that was clicked.
        :param index: The index of the tab associated with the button.
        """
        self.switch_tab(index)