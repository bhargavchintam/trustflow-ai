#!/bin/bash
# Pre-commit guard: blocks `git commit` (via Bash tool) when a CRITICAL
# tenant-isolation or secret-leak violation is detected.
#
# Wired up via .claude/settings.json under hooks.PreToolUse with matcher "Bash".
# Reads the tool input as JSON on stdin; only acts when the command is `git commit ...`.
# Exits non-zero (with a stderr message Claude Code surfaces as a system reminder)
# to block the commit. Exits 0 otherwise.

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

# Only act on git commit; pass through everything else.
case "$cmd" in
    *"git commit"*|*"git -c "*"commit"*) ;;
    *) exit 0 ;;
esac

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$repo_root" ]; then
    exit 0
fi
cd "$repo_root"

violations=()

# 1. SQL queries on memory tables must include WHERE tenant_id
sql_targets=$(grep -rEn 'FROM (episodic|semantic|procedural)_memory|UPDATE (episodic|semantic|procedural)_memory|DELETE FROM (episodic|semantic|procedural)_memory' backend/app/ 2>/dev/null \
    | grep -vE 'schema\.sql|bootstrap\.py|__pycache__' || true)

while IFS= read -r line; do
    [ -z "$line" ] && continue
    file=$(echo "$line" | cut -d: -f1)
    lineno=$(echo "$line" | cut -d: -f2)
    # Look at 6 lines starting at match for a 'tenant_id' reference
    context=$(awk -v start="$lineno" 'NR>=start && NR<start+6' "$file" 2>/dev/null || echo "")
    if ! echo "$context" | grep -qi "tenant_id"; then
        violations+=("[CRITICAL] $file:$lineno - SQL on memory table missing WHERE tenant_id")
    fi
done <<< "$sql_targets"

# 2. tenant_id sourced from request body (must come from session/header/query)
body_tenant=$(grep -rEn 'request\.json|body\[.*tenant|body\.get.*tenant|payload.*tenant_id|data\.get.*tenant' backend/app/ 2>/dev/null \
    | grep -iE 'tenant' | grep -vE '__pycache__' || true)
while IFS= read -r line; do
    [ -z "$line" ] && continue
    violations+=("[CRITICAL] $line - tenant_id sourced from request body")
done <<< "$body_tenant"

# 3. Direct TOOL_REGISTRY access outside the gateway (must go through gateway.execute)
direct_registry=$(grep -rEn 'TOOL_REGISTRY\[' backend/app/ 2>/dev/null \
    | grep -v 'policy/gateway\.py' \
    | grep -v 'tools/registry\.py' \
    | grep -vE '__pycache__' || true)
while IFS= read -r line; do
    [ -z "$line" ] && continue
    violations+=("[CRITICAL] $line - direct TOOL_REGISTRY access bypasses the policy gateway")
done <<< "$direct_registry"

# 4. Obvious secret leakage (API keys staged in tracked files)
staged_files=$(git diff --cached --name-only 2>/dev/null | grep -vE '^\.env$|^\.env\.' || true)
secret_hits=()
if [ -n "$staged_files" ]; then
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        [ ! -f "$f" ] && continue
        # Detect long real-looking keys, but allow .env.example documentation prefixes
        if git diff --cached -- "$f" | grep -qE '^\+.*sk-ant-api[0-9a-zA-Z]{20,}|^\+.*pa-[A-Za-z0-9_-]{30,}|^\+.*sk-[A-Za-z0-9]{40,}' 2>/dev/null; then
            secret_hits+=("$f")
        fi
    done <<< "$staged_files"
fi
for f in "${secret_hits[@]}"; do
    violations+=("[CRITICAL] $f - looks like a real API key being committed; .env should be the only place keys live")
done

if [ "${#violations[@]}" -gt 0 ]; then
    {
        echo ""
        echo "==========================================================="
        echo "  precommit-guard: BLOCKING commit (${#violations[@]} violation(s))"
        echo "==========================================================="
        for v in "${violations[@]}"; do
            echo "  - $v"
        done
        echo ""
        echo "  Fix the violation(s), or run the policy-audit skill for"
        echo "  full review. To override (dangerous): pass --no-verify"
        echo "  is NOT supported here; the hook runs from Claude Code's"
        echo "  PreToolUse phase. Edit the offending file and retry."
        echo "==========================================================="
    } >&2
    exit 2
fi

exit 0
