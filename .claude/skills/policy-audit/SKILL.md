---
name: policy-audit
description: Run a security-spine audit by invoking the policy-auditor and tenant-isolation-checker agents in parallel and consolidating findings. Use before commit, before deploy, and after any change to backend/app/policy/* or backend/app/memory/*.
---

# policy-audit

Run both project-local review agents in parallel and produce a consolidated CRITICAL/WARNING/NIT report.

## Steps

1. **In a single message, launch both agents in parallel:**
   - `policy-auditor` — reviews `backend/app/policy/*` and `backend/app/tools/*`
   - `tenant-isolation-checker` — greps for tenant-isolation violations across the codebase

2. **Consolidate findings.** Print one combined section with:
   - All CRITICAL findings (these block commit/deploy)
   - All WARNING findings (manual verification needed)
   - All NIT findings (style)
   - A summary line: `n CRITICAL, m WARNING, k NIT`

3. **Exit signal.** If any CRITICAL findings exist, recommend fixing before proceeding. If clean, say "Audit clean — safe to commit/deploy."

## Output format

```
## Combined audit findings (n CRITICAL · m WARNING · k NIT)

### CRITICAL (blocks deploy)
[from policy-auditor] backend/app/policy/gateway.py:42 — ...
[from tenant-isolation-checker] backend/app/memory/episodic.py:34 — ...

### WARNING
[from policy-auditor] backend/app/policy/rules.py:18 — ...

### NIT
[from policy-auditor] backend/app/policy/gateway.py:28 — ...
```

If both agents return clean, say "Audit clean — security spine and tenant isolation both verified."
