---
description: Commit with all user prompts from this conversation included in the message
---

# Commit with User Prompts

You are creating a git commit that includes all user prompts from the current conversation.

## Instructions

1. **Extract User Prompts**: Look back through the entire conversation history and collect ALL user messages/prompts that led to the changes being committed. Include them in chronological order.

2. **Analyze Changes**: Run these commands to understand what's being committed:
   ```bash
   git status
   git diff --staged
   ```

3. **Generate Commit Message**: Create a commit message in this format:
   ```
   <brief summary of changes>

   User prompts:
   - "<first user prompt>"
   - "<second user prompt>"
   - ...

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
   ```

4. **Execute Commit**: Use a HEREDOC to ensure proper formatting:
   ```bash
   git add -A && git commit -m "$(cat <<'EOF'
   <your commit message here>
   EOF
   )"
   ```

## Rules
- Include ALL user prompts from this conversation, not just the last one
- Keep the summary line under 50 characters
- Preserve the exact wording of user prompts (can abbreviate very long ones with "...")
- If there are no staged changes, inform the user instead of creating an empty commit
