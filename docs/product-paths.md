# Product Skill Paths Reference

## 鍚勪骇鍝?Skill 鐩綍璺緞璇︾粏璇存槑

### 1. AutoClaw / OpenClaw

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| 鐢ㄦ埛绾?Skill 鐩綍 | `~/.openclaw/skills/` | `%USERPROFILE%\.openclaw\skills\` |
| AutoClaw 鎵╁睍鐩綍 | `~/.openclaw-autoclaw/skills/` | `%USERPROFILE%\.openclaw-autoclaw\skills\` |
| 涓汉 Agent Skill | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |
| 閰嶇疆鏂囦欢 | `~/.openclaw/openclaw.json` | `%USERPROFILE%\.openclaw\openclaw.json` |

**鍔犺浇浼樺厛绾?*锛氶」鐩骇 > 鐢ㄦ埛绾?> 鍐呯疆

---

### 2. Kimi Code

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| 鐢ㄦ埛绾?Skill 鐩綍 | `~/.config/agents/skills/` | `%USERPROFILE%\.config\agents\skills\` |
| Kimi Code 涓撶敤鐩綍 | `~/.kimi-code/skills/` | `%USERPROFILE%\.kimi-code\skills\` |

---

### 3. MiniMax Code

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| Skill 鐩綍 | `~/.agents/skills/` | `%USERPROFILE%\.agents\skills\` |

鍘熺敓鏀寔锛屾棤闇€棰濆鍚屾銆?
---

### 4. WorkBuddy

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| Skill 鐩綍 | `~/.workbuddy/skills/` | `%USERPROFILE%\.workbuddy\skills\` |
| 閰嶇疆鏂囦欢 | `~/.workbuddy/settings.json` | `%USERPROFILE%\.workbuddy\settings.json` |

settings.json: `{"skills": {"my-skill": true}}`

---

### 5. Trae Solo

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| 鐢ㄦ埛绾?| `~/.trae/skills/` | `%USERPROFILE%\.trae\skills\` |
| 椤圭洰绾?| `<project>/.trae/skills/` | `<project>\.trae\skills\` |

---

### 6. DuMate (Baidu)

App 鍐呯鐞嗭細鎶€鑳?鈫?瀹夎鎶€鑳?鈫?涓婁紶 .zip/.md

瀹樼綉: https://www.dumate.cn

---

### 7. CodeBuddy (Tencent)

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| 鐢ㄦ埛绾?Skill 鐩綍 | `~/.codebuddy/skills/` | `%USERPROFILE%\.codebuddy\skills\` |
| 閰嶇疆鏂囦欢 | `~/.codebuddy/settings.json` | `%USERPROFILE%\.codebuddy\settings.json` |

CodeBuddy CLI 涔熸壂鎻?`~/.agents/skills/`銆傛瘡涓?Skill 涓€涓嫭绔嬬洰褰曪紝鍖呭惈 `SKILL.md`銆?
**鍙傝€冩潵婧?*锛?- https://www.cnblogs.com/yangykaifa/p/19681812
- https://www.codebuddy.cn/docs/cli/skills

---

### 8. Comate / 鏂囧績蹇爜 (Baidu)

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| Skill 鐩綍 | `~/.comate/skills/` | `%USERPROFILE%\.comate\skills\` |

Comate 鍚姩鏃惰嚜鍔ㄤ粠 `~/.comate/skills/` 鍙戠幇骞跺姞杞?Skills銆傚唴缃?`create-rule`銆乣create-skill`銆乣create-subagent` 涓変釜绯荤粺绾?Skill 涔熷湪璇ョ洰褰曘€?
**鍙傝€冩潵婧?*锛?- https://cloud.baidu.com/doc/COMATE/s/Nmma28iqe
- https://segmentfault.com/a/1190000047679474

---

### 9. Qoder / 閫氫箟鐏电爜 (Alibaba)

| 灞炴€?| macOS | Windows |
|------|-------|---------|
| Skill 鐩綍 | `~/.qoderwork/skills/` | `%USERPROFILE%\.qoderwork\skills\` |

姣忎釜 Skill 鍖呭惈 `SKILL.md` 鏂囦欢锛屽瓨鏀惧湪 `~/.qoderwork/skills/` 鐩綍涓嬨€傛敮鎸佸璇濅腑鎼滅储瀹夎銆?
**鍙傝€冩潵婧?*锛?- https://docs.qoder.com/zh/qoderwork/skills
- https://help.aliyun.com/zh/lingma/qoder-cn/user-guide/skills

---

## 閫氱敤鏍囧噯锛歚.agents/skills/`

涓氱晫閫氱敤绾﹀畾锛岃秺鏉ヨ秺澶氬鎴风鎵弿浠ヤ笅璺緞锛?
- **椤圭洰绾?*锛歚<project>/.agents/skills/<skill-name>/`
- **鐢ㄦ埛绾?*锛歚~/.agents/skills/<skill-name>/`

## 浜ゅ弶鍙傝€?
### manage-my-skills
- https://github.com/hchcx/manage-my-skills

### skills CLI (npx skills)
- https://www.npmjs.com/package/skills
