# vibe-commit

Claude Code plugin that includes user prompts and AI session metadata in git commits.

## Installation

```
/plugin marketplace add stared/vibe-commit
/plugin install vibe-commit@vibe-commit
```

## Usage

Say "commit" or use `/commit`. The skill auto-triggers on commit-related phrases.

## Output Format

```
Add user authentication feature

User prompts:
- "Add a login form to the app"
- "Make sure it validates email format"

AI-Session-ID: abc123-def456-...
AI Agent: Claude Code 2.1.1 <noreply@anthropic.com>
Model: claude-opus-4-5-20251101
```

## Requirements

- Claude Code CLI
- Python 3.10+ with [uv](https://github.com/astral-sh/uv)

## License

MIT
