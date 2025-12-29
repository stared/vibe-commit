---
description: Commit with all user prompts from this conversation included in the message
---

# Commit with User Prompts

You are creating a git commit that includes all user prompts from the current conversation.

## Instructions

1. **Extract User Prompts**: Look back through the entire conversation history and collect user messages/prompts that led to the changes being committed. Include them in chronological order.

2. **Analyze Changes**: Run these commands to understand what's being committed:
   ```bash
   git status
   git diff --staged
   ```

3. **Get Session Info**: Run to get session ID, agent, and model:
   ```bash
   uv run ai-blame.py session-info
   ```

4. **Generate Commit Message**: Create a commit message in this format:
   ```
   <brief summary of changes>

   User prompts:
   - "<first user prompt>"
   - "<second user prompt>"
   - ...

   AI-Session-ID: <from session-info>
   AI Agent: <from session-info>
   Model: <from session-info>
   ```

5. **Execute Commit**: Use a HEREDOC to ensure proper formatting:
   ```bash
   git add -A && git commit -m "$(cat <<'EOF'
   <your commit message here>
   EOF
   )"
   ```

## Rules for User Prompts
- Only include prompts that led to actual file changes (not `/commit` commands or meta-discussion)
- Preserve the exact wording of user prompts (can abbreviate very long ones with "...")
- If there are no staged changes, inform the user instead of creating an empty commit

## Line Length Rules
- **Summary line**: Keep under 50 characters (GitHub truncates at ~72)
- **Body**: No limit - GitHub soft-wraps automatically in browser
- **Each prompt**: Write as a single line, no mid-sentence wrapping
- Only use line breaks between items, not within them

## Session Transcripts
The full conversation transcript is stored at:
`~/.claude/projects/<encoded-project-path>/<session-id>.jsonl`

This can be used with `git notes` for preserving full context:
```bash
git notes add -m "Session transcript: ~/.claude/projects/.../<session-id>.jsonl"
```
