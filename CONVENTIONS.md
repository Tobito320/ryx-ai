# Conventions for ryx AI Project

## General goals
- ryx is a fast, local-first AI assistant focused on great UX, integrations, and reliability.
- Prefer small, incremental, well-tested changes over large rewrites.
- Always keep existing users' workflows working unless there is a very strong reason.

## Coding style
- Follow the existing language style and formatters/linters used in this repo.
- Use type hints where practical.
- Prefer clear, explicit names; keep functions small and focused.
- Add docstrings or comments for non-obvious logic.

## CLI / UX behavior
- All commands and flags must have clear --help text.
- Avoid breaking existing CLI flags or config keys; add compatibility if changes are needed.
- Prefer subcommands over huge single-command flag lists.
- Error messages must be actionable and friendly.

## Integrations and features
- Prioritize integration with Arch Linux, Hyprland, Waybar, Neovim, and local LLM backends.
- Avoid hard-coded paths; use config/env where possible.
- Core ryx features must not require a cloud account.

## Safety and reliability
- Never add sudo or destructive operations.
- Check for external tools before using them and fail gracefully.
- Add/update tests when making non-trivial changes.
- Keep logs helpful but avoid leaking secrets.

## Aider behavior
- Treat this file as read-only instructions.
- Prefer editing existing files over creating new parallel versions.
- Search and read before large changes.
- For multi-step work, describe the plan first, then implement it in small commits.
