import { X, User, Settings, Palette, Shield, Database, Key, Plug, HelpCircle, LogOut } from "lucide-react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: string) => void;
};

export function SettingsModal({ isOpen, onClose, onNavigate }: Props) {
  if (!isOpen) return null;

  const sections = [
    {
      items: [
        { id: "profile", label: "Profile", icon: User },
        { id: "preferences", label: "Preferences", icon: Settings },
        { id: "appearance", label: "Appearance", icon: Palette },
      ],
    },
    {
      items: [
        { id: "security", label: "Security", icon: Shield },
        { id: "data-privacy", label: "Data & Privacy", icon: Database },
      ],
    },
    {
      items: [
        { id: "api-keys", label: "API Keys", icon: Key },
        { id: "integrations", label: "Integrations", icon: Plug },
      ],
    },
    {
      divider: true,
      items: [
        { id: "help", label: "Help", icon: HelpCircle },
        { id: "logout", label: "Log out", icon: LogOut },
      ],
    },
  ];

  const handleItemClick = (itemId: string) => {
    if (itemId === "logout") {
      console.log("Logout clicked");
      onClose();
    } else {
      onNavigate(itemId);
      onClose();
    }
  };

  return (
    <>
      {/* Overlay - subtle */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={onClose}
        style={{ animation: 'fadeIn 150ms ease-out' }}
      />

      {/* Panel - clean, no decorative border */}
      <div
        className="fixed right-0 top-0 bottom-0 w-full sm:w-[360px] bg-[hsl(var(--card))] border-l border-[hsl(var(--border))] z-50 flex flex-col"
        style={{ animation: 'slideInRight 200ms ease-out' }}
      >
        {/* Header - minimal */}
        <div className="flex items-center justify-between px-5 py-4">
          <h2 className="text-base font-semibold">Settings</h2>
          <button
            onClick={onClose}
            className="h-8 w-8 rounded-lg flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content - clean list */}
        <div className="flex-1 overflow-y-auto px-3 pb-6">
          {sections.map((section, sectionIdx) => (
            <div key={sectionIdx}>
              {section.divider && sectionIdx > 0 && (
                <div className="border-t border-[hsl(var(--border))] my-3" />
              )}
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleItemClick(item.id)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm hover:bg-[hsl(var(--muted))] transition-colors text-left"
                    >
                      <Icon className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
