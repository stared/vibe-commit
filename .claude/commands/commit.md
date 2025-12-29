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

3. **Get Session ID**: Find the current Claude Code session ID by looking at the most recently modified session file:
   ```bash
   ls -t ~/.claude/projects/`pwd | tr '/_' '--'`/[0-9a-f]*.jsonl 2>/dev/null | head -1 | xargs -I{} basename {} .jsonl
   ```

4. **Get Version**: Get Claude Code version:
   ```bash
   claude --version | head -1
   ```

5. **Generate Commit Message**: Create a commit message in this format:
   ```
   <brief summary of changes>

   Prompts for Claude Code <version> using <model>:
   - "<first user prompt>"
   - "<second user prompt>"
   - ...

   AI-Session-ID: <session-id-from-step-3>
   ```

   Use the version from step 4 and include the model you are currently running as (e.g., claude-opus-4-5-20251101).

6. **Execute Commit**: Use a HEREDOC to ensure proper formatting:
   ```bash
   git add -A && git commit -m "$(cat <<'EOF'
   <your commit message here>
   EOF
   )"
   ```

## Rules for User Prompts
- Only include prompts that led to actual file changes (not `/commit` commands or meta-discussion)
- Keep the summary line under 50 characters
- Preserve the exact wording of user prompts (can abbreviate very long ones with "...")
- If there are no staged changes, inform the user instead of creating an empty commit

## Session Transcripts
The full conversation transcript is stored at:
`~/.claude/projects/<encoded-project-path>/<session-id>.jsonl`

This can be used with `git notes` for preserving full context:
```bash
git notes add -m "Session transcript: ~/.claude/projects/.../<session-id>.jsonl"
```
