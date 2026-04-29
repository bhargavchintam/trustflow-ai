#!/bin/bash
# Post-edit reminder: fires after Edit/Write touches the security spine
# (backend/app/policy/* or backend/app/tools/*). Reminds Claude to invoke
# the policy-auditor agent before committing.
#
# Wired via .claude/settings.json hooks.PostToolUse, matcher "Edit|Write".

set -e

input=$(cat)
path=$(echo "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    p = d.get("tool_input", {}).get("file_path", "")
    print(p)
except Exception:
    print("")
' 2>/dev/null)

case "$path" in
    *backend/app/policy/*|*backend/app/tools/*|*backend/app/policy.py|*backend/app/tools.py) ;;
    *) exit 0 ;;
esac

{
    echo ""
    echo "[postedit-policy-reminder] You edited the security spine: $path"
    echo "  Before committing: invoke the policy-auditor agent for a"
    echo "  full review (or the policy-audit skill which runs both"
    echo "  policy-auditor and tenant-isolation-checker in parallel)."
} >&2

exit 0
