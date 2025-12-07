import * as React from "react";
import { useTheme } from "next-themes";
import { Toaster as Sonner, toast } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme();

  // Sonner expects 'light' | 'dark' | 'system' (or specific keys) - map app themes to sonner theme
  const sonnerTheme = theme === 'dracula' || theme === 'dark' ? 'dark' : theme === 'gruvbox' || theme === 'light' ? 'light' : 'system';

  // Add global click handler for toasts
  React.useEffect(() => {
    const handleToastClick = (e: MouseEvent) => {
      const toastElement = (e.target as HTMLElement).closest('[data-sonner-toast]');
      if (toastElement) {
        const toastId = toastElement.getAttribute('data-sonner-toast-id');
        if (toastId) {
          toast.dismiss(toastId);
        }
      }
    };

    document.addEventListener('click', handleToastClick);
    return () => document.removeEventListener('click', handleToastClick);
  }, []);

  return (
    <Sonner
      theme={sonnerTheme as ToasterProps["theme"]}
      className="toaster group"
      closeButton={false}
      toastOptions={{
        duration: 3000,
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg cursor-pointer hover:scale-105 transition-transform",
          description: "group-[.toast]:text-muted-foreground",
          actionButton: "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
};

export { Toaster, toast };
