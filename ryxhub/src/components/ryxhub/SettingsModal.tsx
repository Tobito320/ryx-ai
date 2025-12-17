import { X, Sun, Moon, User, Palette, Shield, Database, Key, Plug, HelpCircle, LogOut } from "lucide-react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  theme: 'dark' | 'light';
  onThemeChange: (theme: 'dark' | 'light') => void;
};

export function SettingsModal({ isOpen, onClose, theme, onThemeChange }: Props) {
  if (!isOpen) return null;

  const menuItems = [
    { id: "profile", label: "Profile", icon: User },
    { id: "appearance", label: "Appearance", icon: Palette },
    { id: "security", label: "Security", icon: Shield },
    { id: "data", label: "Data & Privacy", icon: Database },
    { id: "api", label: "API Keys", icon: Key },
    { id: "integrations", label: "Integrations", icon: Plug },
    { id: "help", label: "Help", icon: HelpCircle },
  ];

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-40 animate-fade-in" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-full sm:w-80 bg-card border-l border-border z-50 flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h2 className="text-base font-medium">Settings</h2>
          <button
            onClick={onClose}
            className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Theme Toggle */}
        <div className="px-4 py-3 border-b border-border">
          <div className="flex items-center justify-between">
            <span className="text-sm">Theme</span>
            <div className="flex gap-1 bg-muted rounded-lg p-1">
              <button
                onClick={() => onThemeChange('light')}
                className={`p-2 rounded-md transition-colors ${theme === 'light' ? 'bg-background shadow-sm' : 'hover:bg-background/50'}`}
              >
                <Sun className="w-4 h-4" />
              </button>
              <button
                onClick={() => onThemeChange('dark')}
                className={`p-2 rounded-md transition-colors ${theme === 'dark' ? 'bg-background shadow-sm' : 'hover:bg-background/50'}`}
              >
                <Moon className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Menu */}
        <div className="flex-1 overflow-y-auto p-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm hover:bg-muted transition-colors"
              >
                <Icon className="w-4 h-4 text-muted-foreground" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Logout */}
        <div className="p-2 border-t border-border">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm hover:bg-muted transition-colors text-destructive">
            <LogOut className="w-4 h-4" />
            <span>Log out</span>
          </button>
        </div>
      </div>
    </>
  );
}
