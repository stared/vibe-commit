# Development Process Notes

## Commit Message Format

All commits include:
- Summary of changes
- User prompts that led to changes
- AI Session ID (for linking to full conversation transcript)
- AI Agent and Model information

### Example Commit Message

```
Add user authentication

User prompts:
- "Add login form with email/password"
- "Also add password reset functionality"

AI-Session-ID: cbb2adaa-7132-4913-b345-03320f9a044c
AI Agent: Claude Code 2.0.76 <noreply@anthropic.com>
Model: claude-opus-4-5-20251101
```

## Session Transcripts

Full conversation transcripts are stored locally at:
```
~/.claude/projects/<encoded-project-path>/<session-id>.jsonl
```

The session ID in commit messages allows you to find and review the full conversation that led to the changes.

## Git Notes for Important Changes

For significant changes, attach additional context using git notes:

```bash
# After committing, attach context:
git notes add -m "Key decisions: Used JWT for auth, React Query for state..."

# Or reference the full transcript:
git notes add -m "Full transcript: ~/.claude/projects/-Users-pmigdal-my-repos-quesma-vibe-coding/cbb2adaa-7132-4913-b345-03320f9a044c.jsonl"

# Push notes to remote:
git push origin refs/notes/*

# View notes:
git log --show-notes
```

## Guidelines

1. **Exclude meta-commands**: Don't include `/commit` itself as it doesn't affect file changes
2. **Only include prompts that led to actual changes**: Focus on user requests that resulted in code/file modifications
3. **Avoid repetition**: Don't list the same command multiple times

## Line Length Rules

- **Summary line**: Keep under 50 characters (GitHub truncates at ~72)
- **Body**: No limit - GitHub soft-wraps automatically in browser
- **Each prompt**: Write as a single line, no mid-sentence wrapping
- Only use line breaks between items, not within them
