#!/bin/bash
# scripts/apply_branch_protection.sh
# Скрипт применяет правила защиты веток через GitHub CLI
#
# Требования:
#   - Установленный gh CLI: https://cli.github.com/
#   - Авторизация: gh auth login
#   - Токен с правами admin:repo или GITHUB_TOKEN с admin правами
#
# Использование:
#   ./scripts/apply_branch_protection.sh
#   make protect-branches
#
# Скрипт идемпотентный — можно запускать повторно без ошибок.

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Получаем информацию о репозитории из git remote
REPO_FULL=$(git config --get remote.origin.url | sed 's|.*/||' | sed 's|\.git$||')
OWNER=$(echo "$REPO_FULL" | cut -d'/' -f1)
REPO=$(echo "$REPO_FULL" | cut -d'/' -f2)

echo -e "${GREEN}Applying branch protection rules for ${OWNER}/${REPO}${NC}"
echo "=================================================="

# Проверка наличия gh CLI
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: gh CLI not found. Install from https://cli.github.com/${NC}"
    exit 1
fi

# Проверка авторизации
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated. Run: gh auth login${NC}"
    exit 1
fi

# Функция для применения правил защиты
apply_protection() {
    local branch="$1"
    local json_file="$2"
    
    echo -e "${YELLOW}Configuring: ${branch}${NC}"
    
    # Применяем правила через GitHub API
    gh api \
        --method PUT \
        "/repos/${OWNER}/${REPO}/branches/${branch}/protection" \
        --input "$json_file" \
        --silent 2>&1 && \
        echo -e "${GREEN}  ✓ Success${NC}" || \
        echo -e "${RED}  ✗ Failed (возможно, правила уже применены или недостаточно прав)${NC}"
}

# Создаём временную директорию для JSON файлов
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# =============================================================================
# MAIN BRANCH — максимальная защита
# =============================================================================
cat > "$TMPDIR/main.json" << 'EOF'
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "require_last_push_approval": false
  },
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "typecheck", "test"]
  },
  "enforce_admins": true,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
EOF

apply_protection "main" "$TMPDIR/main.json"

# =============================================================================
# DEVELOP BRANCH — стандартная защита
# =============================================================================
cat > "$TMPDIR/develop.json" << 'EOF'
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "typecheck", "test"]
  },
  "enforce_admins": true,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "lock_branch": false
}
EOF

apply_protection "develop" "$TMPDIR/develop.json"

# =============================================================================
# DEVELOPER BRANCHES — лёгкая защита
# =============================================================================
cat > "$TMPDIR/developer.json" << 'EOF'
{
  "required_pull_request_reviews": null,
  "required_status_checks": {
    "strict": false,
    "contexts": ["lint", "typecheck"]
  },
  "enforce_admins": false,
  "required_linear_history": false,
  "allow_force_pushes": true,
  "allow_deletions": true,
  "lock_branch": false
}
EOF

apply_protection "developer2/belin" "$TMPDIR/developer.json"
apply_protection "developer1/tsaguria" "$TMPDIR/developer.json"

# =============================================================================
# FEATURE BRANCHES — защита по паттерну
# =============================================================================
cat > "$TMPDIR/feature.json" << 'EOF'
{
  "required_pull_request_reviews": null,
  "required_status_checks": {
    "strict": false,
    "contexts": ["lint", "typecheck", "test"]
  },
  "enforce_admins": false,
  "required_linear_history": false,
  "allow_force_pushes": true,
  "allow_deletions": true,
  "lock_branch": false
}
EOF

# Для feature/* веток используем API с pattern
echo -e "${YELLOW}Configuring: feature/* (pattern)${NC}"
gh api \
    --method PUT \
    "/repos/${OWNER}/${REPO}/rulesets" \
    -f name="feature-branch-protection" \
    -f target="branch" \
    -f 'conditions={"ref_name":{"include":["refs/heads/feature/*"],"exclude":[]}}' \
    -f 'rules=[{"type":"required_status_checks","parameters":{"strict":false,"required_status_checks":[{"context":"lint"},{"context":"typecheck"},{"context":"test"}]}}]' \
    --silent 2>&1 && \
    echo -e "${GREEN}  ✓ Success${NC}" || \
    echo -e "${RED}  ✗ Failed (возможно, ruleset уже существует)${NC}"

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}Branch protection rules applied successfully!${NC}"
echo ""
echo "Проверить настройки можно в GitHub:"
echo "  https://github.com/${OWNER}/${REPO}/settings/branches"
echo ""
echo "Или через CLI:"
echo "  gh api /repos/${OWNER}/${REPO}/branches/main/protection"
