#!/usr/bin/env bash
# 在本机终端执行：bash scripts/push-to-github.sh
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_SLUG="alanguan73/clinical-note-agent"
REMOTE="https://github.com/${REPO_SLUG}.git"

rm -rf .git
git init -b main
git config user.name "alanguan73"
git config user.email "alanguan73@users.noreply.github.com"

git add README.md .gitignore docs tests scripts
git commit -m "$(cat <<'EOF'
docs: 智能病历辅助生成系统产品规格 v0.3

含完整产品文档、安全专章、金样例 YAML 与 README。
EOF
)"

if command -v gh >/dev/null 2>&1; then
  gh repo create "${REPO_SLUG}" --public --source=. --remote=origin --push
else
  echo "未检测到 gh。请先在 GitHub 创建空仓库: https://github.com/new?name=clinical-note-agent"
  echo "创建后按回车继续..."
  read -r
  git remote add origin "${REMOTE}" 2>/dev/null || git remote set-url origin "${REMOTE}"
  git push -u origin main
fi

echo "完成: https://github.com/${REPO_SLUG}"
