# Change Discovery: README.md Restructure & Sync with v4.4
**Date**: 2026-04-08
**Commit**: `pending`
**Trigger**: documentation-cleanup

## 📁 Affected Files
| Path | Change Type | Reason |
|------|-------------|--------|
| `README.md` | REWRITTEN | Removed 900+ lines of duplication, condensed from 1242 → ~280 lines |

## 🧠 Business Impact
- **Developer onboarding**: README now provides clear, concise entry point without overwhelming detail
- **Single source of truth**: DB schemas, .env templates, file trees moved to QWEN.md / .env.example / docs/
- **Cross-reference system**: README links to QWEN.md (models), CHANGELOG.md (history), .env.example (config)
- **AI-assisted dev workflow**: Skills section documents `.qwen/skills/` system (10 skills)

## 🔄 Contract Changes
- **No API/FSM/DB changes** — documentation-only update
- **Structure**: 15 sections (was 30+ with duplicates)
- **Line count**: ~280 lines (was 1242 lines, 77% reduction)

### What Was Removed
| Section | Lines (old) | Reason |
|---------|-------------|--------|
| Full file tree | 600+ | Replaced with 15-line high-level overview |
| DB model field definitions | 300+ | Moved to QWEN.md, replaced with model name tables |
| Full .env template | 80+ | Link to .env.example |
| Repetitive Celery commands | 40+ | Consolidated to one-liner |
| Reputation system tables | 60+ | Summarized in value proposition |
| Content filter diagram | 40+ | Mentioned as 3-level pipeline |
| Duplicate "Development" section | 50+ | Merged into single "Development Workflow" |
| B2BPackage section | 30+ | B2B removed in v4.3 |
| "What's new in v4.3" at top | 50+ | Replaced with v4.4 section |

### What Was Added
| Section | Lines | Purpose |
|---------|-------|---------|
| v4.4 "What's New" | 12 | Web portal, security fixes, quality improvements |
| Skills table | 12 | Document 10 .qwen/skills/ for AI-assisted dev |
| Links to docs | multiple | Cross-reference QWEN.md, CHANGELOG.md, .env.example |
| v4.4 Accounting models | 6 | S-26 КУДиР, акты, документооборот |

### What Was Kept & Updated
| Section | Status | Updates |
|---------|--------|---------|
| Hero badges | ✅ | Added React 19, FastAPI, v4.4 |
| Financial model v4.2 | ✅ | Verified: 490/1490/4990, 15%/85% split |
| Tariffs table | ✅ | Verified against QWEN.md PLAN_PRICES |
| User roles | ✅ | Added legal profiles note (v4.3) |
| Architecture diagram | ✅ | Added Web Portal |
| Tech stack | ✅ | Updated with v4.4 additions |
| Quick start | ✅ | Simplified, reference .env.example |
| Development workflow | ✅ | Consolidated duplicate sections |
| Deploy | ✅ | Simplified, link to .env.example |
| Monitoring | ✅ | Added SonarQube 580 files |

## 📎 Verification
- [x] Code matches docs (README reflects v4.4 state, no stale references)
- [x] No drift with QWEN.md (tariffs, financial constants match exactly)
- [x] AAA structure preserved (README = overview, QWEN.md = deep reference)
- [x] No duplicate sections (verified: each topic appears once)
- [x] Links valid (QWEN.md, CHANGELOG.md, .env.example exist)
- [x] B2B removed (no references to B2B packages in README)

🔍 Verified against: `pending` | 📅 Updated: `2026-04-08T00:00:00Z`
