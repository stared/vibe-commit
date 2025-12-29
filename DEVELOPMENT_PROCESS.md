# Development Process Notes

## Commit Message Format

All commits include:
- Summary of changes
- User prompts that led to changes (with Claude Code version and model)
- AI Session ID (for linking to full conversation transcript)

### Example Commit Message

```
Add user authentication

Prompts for Claude Code 2.0.76 using claude-opus-4-5-20251101:
- "Add login form with email/password"
- "Also add password reset functionality"

AI-Session-ID: cbb2adaa-7132-4913-b345-03320f9a044c
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
