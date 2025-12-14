# Ryx Self-Improver

Automatically add features to Ryx using GitHub Copilot Pro+ models.

## Setup

1. **Install dependencies:**
```bash
cd ryx-improver
npm install
```

2. **Set your GitHub token:**
```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

Get a token from: https://github.com/settings/tokens/new
- Required scope: `copilot` (if available) or just use your existing token

## Usage

### Add a feature:
```bash
npm run improve "Add dark mode toggle to settings page"
```

### Preview changes (dry run):
```bash
npm run improve:dry "Create email notification component"
```

### Direct execution:
```bash
npx ts-node improver.ts "Your feature description" --dry-run
```

## How It Works

1. **Plan** (chat model, 0x cost)
   - Analyzes codebase structure
   - Creates implementation plan

2. **Generate** (coding model, 1x cost)
   - Writes all necessary files
   - Follows existing patterns

3. **Build & Verify**
   - Runs TypeScript build
   - Checks for errors

4. **Fix** (emergency model, 3x cost - only if needed)
   - Attempts to fix build errors
   - Uses more powerful model

5. **Commit**
   - Auto-commits changes with descriptive message

## Models Used

| Mode | Model | Cost | Use Case |
|------|-------|------|----------|
| chat | gpt-4o-mini | 0x | Planning, analysis |
| coding | gpt-4o | 1x | Code generation |
| codingAlt | claude-3.5-sonnet | 1x | Alternative coding |
| emergency | claude-sonnet-4 | 3x | Complex fixes |

## Examples

```bash
# Add a new UI component
npm run improve "Add a notification bell icon to the header with unread count badge"

# Create backend endpoint
npm run improve "Add API endpoint to fetch user preferences from database"

# Fix/improve existing feature
npm run improve "Improve the chat input to auto-resize based on content"

# Add integration
npm run improve "Add WebSocket support for real-time chat updates"
```

## Safety

- Always makes a git checkpoint before changes
- Auto-rollback on failure
- Use `--dry-run` to preview without making changes
- All changes are local until you `git push`
