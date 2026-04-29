#!/bin/bash
# Pre-deploy reminder: fires before `aws apprunner start-deployment` or
# `docker push ...trustflow-ai...`. Doesn't block — just nudges to run the
# smoke test first if it hasn't been run recently.
#
# Wired via .claude/settings.json hooks.PreToolUse, matcher Bash.

set -e

input=$(cat)
cmd=$(echo "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null)

case "$cmd" in
    *"apprunner start-deployment"*|*"docker push"*"trustflow-ai"*) ;;
    *) exit 0 ;;
esac

# Don't block; just print a reminder Claude Code surfaces.
{
    echo ""
    echo "[predeploy-reminder] About to deploy/push trustflow-ai."
    echo "  - Run the smoke-test skill against the deployed URL before sharing."
    echo "  - Update PROJECT_STATUS.md with the new image digest if changed."
    echo "  - If demoing within an hour, the cold start is ~30s; pre-warm via /api/warmup."
} >&2

exit 0
