---
name: Audit false positive
about: askill audit / install check flagged a skill that is actually safe
labels: audit-rules
---

**Skill and source**

Name or link of the skill (if public), and what it actually does.

**What the audit said**

```text
# paste the findings: severity, message, file:line
```

**Why this is a false positive**

Explain the intent of the flagged code/instruction.

**Suggestion (optional)**

If you have an idea for how the rule could distinguish this case
(e.g. demote findings under docs/, allowlist a specific pattern), write it here.
Rule changes need evidence - real-world examples like this one are exactly
what we calibrate on.
