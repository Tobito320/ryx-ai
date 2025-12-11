# RyxSurf Design System v2.0

A sleek, minimal, modern browser design inspired by contemporary minimal browsers.

---

## 1. Design Philosophy

- **Minimal but functional**: Every element has purpose
- **Dark-first**: Sophisticated dark palette with optional light theme
- **Spacious**: Generous whitespace, zen-like content area
- **Keyboard-first**: Full navigation without mouse
- **Smooth transitions**: 200-300ms animations, never jarring

---

## 2. Color Palette

### Dark Theme (Default)

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-base` | `#0f0f0f` | Main background |
| `--bg-elevated` | `#1a1a1a` | Cards, dialogs |
| `--bg-topbar` | `#1e1e1e` | Top bar background |
| `--bg-hover` | `rgba(255,255,255,0.06)` | Hover states |
| `--bg-active` | `rgba(255,255,255,0.10)` | Active/pressed states |
| `--fg-primary` | `#e8e8e8` | Primary text |
| `--fg-secondary` | `#a0a0a0` | Secondary text |
| `--fg-muted` | `#6a6a6a` | Disabled/muted text |
| `--accent` | `#00d9ff` | Focus, links, accents |
| `--accent-dim` | `rgba(0,217,255,0.15)` | Subtle accent bg |
| `--border-subtle` | `rgba(255,255,255,0.06)` | Subtle dividers |
| `--border-default` | `rgba(255,255,255,0.10)` | Default borders |
| `--border-focus` | `rgba(0,217,255,0.5)` | Focus rings |

### Light Theme

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-base` | `#f5f5f5` | Main background |
| `--bg-elevated` | `#ffffff` | Cards, dialogs |
| `--bg-topbar` | `#fafafa` | Top bar background |
| `--fg-primary` | `#1a1a1a` | Primary text |
| `--fg-secondary` | `#555555` | Secondary text |
| `--accent` | `#0095d9` | Focus, links, accents |

---

## 3. Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

### Scale

| Token | Size | Usage |
|-------|------|-------|
| `--font-size-xs` | 11px | Labels, badges |
| `--font-size-sm` | 12px | Tab titles, address bar |
| `--font-size-base` | 13px | Default body text |
| `--font-size-lg` | 14px | Important body text |
| `--font-size-xl` | 18px | Section headers |
| `--font-size-2xl` | 24px | Page titles |
| `--font-size-hero` | 36px | Overview title |

### Weights
- `400` (normal): Body text
- `500` (medium): Tab titles, buttons
- `600` (semibold): Emphasis

---

## 4. Spacing

8px base grid system:

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Tight spacing |
| `--space-sm` | 8px | Default small gap |
| `--space-md` | 12px | Medium gap |
| `--space-lg` | 16px | Large gap |
| `--space-xl` | 24px | Section spacing |
| `--space-2xl` | 32px | Major sections |

---

## 5. Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ [≡] │ Session1 │ Session2 │  Tab1  Tab2  Tab3  │ [Search...] │ - □ × │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                                                                 │
│                          CONTENT                                │
│                                                                 │
│                                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Top Bar (48px height)
Single unified bar containing:
1. **Overview Button** (36px) - Toggle sidebar/overview
2. **Session Pills** - Compact session indicators
3. **Tab Strip** - Horizontal tabs, flexible width
4. **Address Bar** (320px) - Search/URL input
5. **Window Controls** (100px) - Minimize, maximize, close

### Content Area
- Fills remaining vertical space
- Optional sidebar (180-240px) on left
- WebView takes remaining horizontal space

---

## 6. Component Specifications

### Tab Button
```
Height: 32px
Padding: 4px 12px
Border-radius: 6px
Font-size: 12px
Font-weight: 500
Min-width: 100px
Max-width: 200px
```

**States:**
- Default: transparent bg, `--fg-secondary` text
- Hover: `--bg-hover` bg, `--fg-primary` text
- Active: `--bg-active` bg, `--fg-primary` text
- Unloaded: 50% opacity

### Address Bar
```
Height: 32px
Width: 320px
Padding: 8px 12px
Border-radius: 6px
Font-size: 12px
Border-bottom: 2px solid transparent
```

**States:**
- Default: `--bg-hover` bg
- Hover: `--bg-active` bg
- Focus: `--bg-active` bg, `--accent` underline

### Window Control Buttons
```
Size: 28px × 28px
Border-radius: 4px
Spacing: 2px gap
```

**States:**
- Default: transparent, `--fg-secondary` icon
- Hover: `--bg-hover` bg
- Close Hover: `#e81123` bg, white icon

### Session Pill
```
Height: 24px
Padding: 4px 12px
Border-radius: 8px
Font-size: 11px
```

**States:**
- Default: transparent, `--fg-muted` text
- Active: `--accent-dim` bg, `--accent` text

---

## 7. Interactions

### Transitions
All interactive elements use smooth transitions:
- **Fast** (150ms): Micro-interactions (close buttons)
- **Normal** (200ms): Button states
- **Slow** (300ms): Major state changes

### Hover Behavior
- Tabs: Subtle background shift (+6% white opacity)
- Buttons: Background appears
- Close buttons: Fade in on parent hover

### Focus Behavior
- Address bar: Underline animates in with accent color
- All focusable: 2px accent outline on keyboard focus

### Click Feedback
- Quick press effect (no elaborate ripples)
- Immediate visual response

---

## 8. Overview / New Tab Page

Zen-like landing page:

```
┌──────────────────────────────────────────────────┐
│                                                  │
│                                                  │
│                                                  │
│                   RyxSurf                        │
│              Light, 36px weight                  │
│                                                  │
│           ┌────────────────────────┐             │
│           │ Search the web...      │             │
│           └────────────────────────┘             │
│                                                  │
│                                                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

- Dark gradient background (slightly lighter at top)
- Centered layout with ample whitespace
- Large search input with focus glow

---

## 9. Sidebar (Optional)

Toggle with Overview button or keyboard shortcut.

```
Width: 180-240px
Padding: 8px
Background: --bg-elevated
Border-right: 1px solid --border-subtle
```

Contains vertical tab list:
- Each tab: Full width, left-aligned
- Active tab: Subtle accent background

---

## 10. Accessibility

- **Contrast**: All text meets WCAG AA (4.5:1 minimum)
- **Focus visible**: Clear focus indicators for keyboard nav
- **Reduced motion**: Respects `prefers-reduced-motion`
- **High contrast**: Adapts to `prefers-contrast: high`

### Keyboard Navigation
- `Tab`: Move between interactive elements
- `Enter`: Activate focused element
- `Ctrl+L`: Focus address bar
- `Ctrl+Tab`: Next tab
- `Ctrl+Shift+Tab`: Previous tab
- `Ctrl+W`: Close tab
- `Ctrl+T`: New tab
- `Ctrl+1-9`: Jump to tab N

---

## 11. Files

- **CSS**: `data/theme.css` - Complete theme implementation
- **Browser Window**: `src/browser_window.cpp` - Layout structure
- **Theme Manager**: `src/theme_manager.cpp` - Theme loading/switching

---

## 12. Usage

### Applying Theme Classes

```cpp
// Apply dark/light theme
gtk_widget_add_css_class(widget, "dark-theme");
// or
gtk_widget_add_css_class(widget, "light-theme");

// Enable compact mode
gtk_widget_add_css_class(widget, "compact");

// Vertical tabs
gtk_widget_add_css_class(widget, "vertical-tabs");

// Disable animations
gtk_widget_add_css_class(widget, "no-animations");
```

### Theme Switching

```cpp
ThemeManager* tm = theme_manager_.get();
tm->set_theme(ThemeManager::Theme::Light);
tm->set_compact_mode(true);
tm->apply_to_window(window_);
```
