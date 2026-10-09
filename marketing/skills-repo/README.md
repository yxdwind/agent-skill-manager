# skills

Published Agent Skills by [@yxdwind](https://github.com/yxdwind), installable
from the [skills.sh](https://skills.sh) ecosystem and the
[agentskills.io](https://agentskills.io) open specification.

## Install

With [agent-skill-manager](https://github.com/yxdwind/agent-skill-manager)
(`pip install cn-skill-sync`) - installs into the central repo and syncs to 15
Chinese AI agent products in one step:

```bash
askill install yxdwind/skills@skill-doctor
askill install yxdwind/skills@sync-troubleshoot
```

With the skills CLI (no extra tooling needed afterwards):

```bash
npx skills add yxdwind/skills@skill-doctor
npx skills add yxdwind/skills@sync-troubleshoot
```

## The skills

### skill-doctor

Audit any Agent Skill directory before you trust it:

- **Spec compliance** against agentskills.io conventions (name/dir match,
  description quality, size limits, dead references)
- **Security red flags**: prompt injection patterns, dangerous commands
  (`curl | sh`, `rm -rf`), hardcoded secrets, smuggled binaries - with exact
  file:line evidence for every finding
- **Trigger quality**: whether the description would actually make an agent
  activate the skill, including bilingual (EN/中文) recommendations

Ends with a `PASS / PASS WITH WARNINGS / FAIL` verdict and an ordered fix list.

### sync-troubleshoot

Diagnose "this skill loads in product A but not in product B" on a
central-repo + symlink setup (askill or manual `~/.agents/skills` layout):

- Ordered checklist: central presence -> link health (dangling / degraded to
  copy / stale) -> per-product frontmatter (e.g. QwenWork `description_zh`)
  -> settings.json switches -> zip-only products (DuMate) -> app restart
- Product path reference table for 12+ Chinese AI agent products
- One root cause per report, with exact fix commands

## License

MIT
