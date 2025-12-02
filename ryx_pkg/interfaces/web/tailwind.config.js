module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      // Dracula/Hyprland inspired color palette
      colors: {
        // Background colors
        'ryx-bg': '#1e1e2e',
        'ryx-bg-dark': '#191a24',
        'ryx-bg-elevated': '#21222c',
        'ryx-bg-hover': '#313244',
        'ryx-current-line': '#44475a',
        
        // Text colors
        'ryx-text': '#c0caf5',
        'ryx-text-secondary': '#7aa2f7',
        'ryx-text-muted': '#6272a4',
        'ryx-foreground': '#f8f8f2',
        
        // Accent colors
        'ryx-accent': '#9d7cd8',
        'ryx-purple': '#bd93f9',
        'ryx-cyan': '#8be9fd',
        'ryx-pink': '#ff79c6',
        'ryx-orange': '#ffb86c',
        
        // Status colors
        'ryx-success': '#a6e3a1',
        'ryx-progress': '#f9e2af',
        'ryx-error': '#f38ba8',
        'ryx-warning': '#f1fa8c',
        
        // Border
        'ryx-border': '#45475a',
        
        // Legacy support
        'bg-primary': '#1e1e2e',
        'bg-secondary': '#21222c',
        'bg-tertiary': '#313244',
        'bg-elevated': '#44475a',
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'Roboto Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'base': ['14px', '1.6'],
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      borderRadius: {
        'ryx': '6px',
        'ryx-lg': '8px',
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(0, 0, 0, 0.2)',
        'medium': '0 4px 12px rgba(0, 0, 0, 0.25)',
        'strong': '0 8px 24px rgba(0, 0, 0, 0.3)',
        'glow-purple': '0 0 20px rgba(157, 124, 216, 0.3)',
        'glow-cyan': '0 0 20px rgba(139, 233, 253, 0.3)',
        'inner-soft': 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'step-in': 'stepIn 0.2s ease-in-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'spin-slow': 'spin 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        stepIn: {
          '0%': { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 8px rgba(139, 233, 253, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(139, 233, 253, 0.6)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      transitionDuration: {
        '150': '150ms',
        '200': '200ms',
      },
      transitionTimingFunction: {
        'ryx': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
}

