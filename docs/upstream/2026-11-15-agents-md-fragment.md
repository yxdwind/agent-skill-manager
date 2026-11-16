# askill product paths (exported 2026-11-15)

> Source of truth: `src/config/products.py`, exported via `askill products --json --paths`.
> Intended for upstream contributions such as [npx skills agents.md](https://github.com/vercel-labs/skills/blob/main/docs/agents.md).
> Project Path is `—`: askill manages user-level directories only; project-level paths must be confirmed by the upstream maintainer.

| Agent | `--agent` | Project Path | Global Path (macOS) | Global Path (Windows) | Linux | sync | shared_with | note |
|---|---|---|---|---|---|---|---|---|
| AutoClaw2 | `autoclaw2` | — | `~/.openclaw-autoclaw/skills` | `~/.openclaw-autoclaw/skills` | `~/.openclaw-autoclaw/skills` | symlink | — | AutoClaw2 (Zhipu) profile root is ~/.openclaw-autoclaw/; it also scans ~/.agents/skills/ natively. Legacy v1 used ~/.openclaw/skills/ |
| Kimi | `kimi` | — | `~/.config/agents/skills` | `~/.config/agents/skills` | `~/.config/agents/skills` | symlink | — | Kimi also scans ~/.kimi-code/skills/ |
| MiniMax Code | `minimax` | — | `~/.agents/skills` | `~/.agents/skills` | `~/.agents/skills` | native | — | MiniMax Code natively scans ~/.agents/skills/, no sync needed |
| WorkBuddy | `workbuddy` | — | `~/.workbuddy/skills` | `~/.workbuddy/skills` | — | symlink | — | Enable skill in settings.json. Desktop app: macOS & Windows builds only, no Linux path yet |
| Trae | `trae` | — | `~/.trae/skills` | `~/.trae/skills` | — | symlink | — | Trae also supports project-level .trae/skills/ and .agents/skills/. No Linux build yet |
| Trae CN | `traecn` | — | `~/.trae-cn/skills` | `~/.trae-cn/skills` | — | symlink | traesolo | Trae CN (ByteDance CN edition) uses ~/.trae-cn/; international Trae uses ~/.trae/ (see trae entry). No Linux build yet |
| TRAE SOLO CN | `traesolo` | — | `~/.trae-cn/skills` | `~/.trae-cn/skills` | — | symlink | traecn | TRAE SOLO CN shares ~/.trae-cn/ with Trae CN (same dataFolderName in product.json). No Linux build yet |
| DuMate (Baidu) | `dumate` | — | — | — | — | pack | — | DuMate manages skills via App; use pack command to generate .zip (works on all platforms) |
| CodeBuddy (Tencent) | `codebuddy` | — | `~/.codebuddy/skills` | `~/.codebuddy/skills` | `~/.codebuddy/skills` | symlink | — | CodeBuddy CLI also scans ~/.agents/skills/; settings in ~/.codebuddy/settings.json |
| Comate / Wenxin Kuaima (Baidu) | `comate` | — | `~/.comate/skills` | `~/.comate/skills` | `~/.comate/skills` | symlink | — | Comate auto-loads skills from ~/.comate/skills/ on startup |
| Qoder CN | `qodercn` | — | `~/.qoder-cn/skills` | `~/.qoder-cn/skills` | — | symlink | qodercnide | Qoder CN stores skills in ~/.qoder-cn/skills/ (legacy QoderWork path was ~/.qoderwork/skills/). No Linux build yet |
| Qoder CN IDE | `qodercnide` | — | `~/.qoder-cn/skills` | `~/.qoder-cn/skills` | — | symlink | qodercn | Qoder CN IDE shares ~/.qoder-cn/ with Qoder CN (same dataFolderName in product.json). No Linux build yet |
| QwenWork / Qianwen Office (Alibaba) | `qwenwork` | — | `~/.qwenworkcn/skills` | `~/.qwenworkcn/skills` | — | symlink | — | QwenWork desktop scans ~/.qwenworkcn/skills/; frontmatter needs name+version+description+description_zh. Desktop app: no Linux build yet |
| DoubaoWork (ByteDance) | `doubaowork` | — | `~/.super_doubao/super-doubao-runtime/workspace/.user_skills` | `%LOCALAPPDATA%/DoubaoWork/User Data/Default/.doubaowork/agent_mode/workspace/.user_skills` | — | symlink | — | DoubaoWork user skills live in workspace/.user_skills; system skills in workspace/.skills. Desktop app: no Linux build yet |
| ZCode | `zcode` | — | `~/.zcode/skills` | `~/.zcode/skills` | `~/.zcode/skills` | symlink | — | ZCode also scans ~/.agents/skills/ natively |

## Not covered upstream (8 of 15, snapshot 2026-11-15)

> Name matching is conservative and automatic — verify each row against the live upstream file before opening a PR.

| Agent | short | Global Path (macOS) | Global Path (Windows) |
|---|---|---|---|
| AutoClaw2 | `autoclaw2` | `~/.openclaw-autoclaw/skills` | `~/.openclaw-autoclaw/skills` |
| WorkBuddy | `workbuddy` | `~/.workbuddy/skills` | `~/.workbuddy/skills` |
| TRAE SOLO CN | `traesolo` | `~/.trae-cn/skills` | `~/.trae-cn/skills` |
| DuMate (Baidu) | `dumate` | — | — |
| Comate / Wenxin Kuaima (Baidu) | `comate` | `~/.comate/skills` | `~/.comate/skills` |
| Qoder CN IDE | `qodercnide` | `~/.qoder-cn/skills` | `~/.qoder-cn/skills` |
| QwenWork / Qianwen Office (Alibaba) | `qwenwork` | `~/.qwenworkcn/skills` | `~/.qwenworkcn/skills` |
| DoubaoWork (ByteDance) | `doubaowork` | `~/.super_doubao/super-doubao-runtime/workspace/.user_skills` | `%LOCALAPPDATA%/DoubaoWork/User Data/Default/.doubaowork/agent_mode/workspace/.user_skills` |

Covered rows:

- `kimi` → `kimicodecli`
- `minimax` → `minimaxcode`
- `trae` → `trae`
- `traecn` → `traecn`
- `codebuddy` → `codebuddy`
- `qodercn` → `qodercn`
- `zcode` → `zcode`
