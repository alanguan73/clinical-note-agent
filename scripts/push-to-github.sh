#!/usr/bin/env bash
# 在本机终端执行：bash scripts/push-to-github.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPO_SLUG="alanguan73/clinical-note-agent"
REMOTE_SSH="git@github.com:${REPO_SLUG}.git"
REMOTE_HTTPS="https://github.com/${REPO_SLUG}.git"

git config user.name "alanguan73" 2>/dev/null || true
git config user.email "alanguan73@users.noreply.github.com" 2>/dev/null || true

git add -A
if ! git diff --cached --quiet 2>/dev/null; then
  git commit -m "${1:-docs: update clinical-note-agent specs}"
fi

git remote add origin "${REMOTE_SSH}" 2>/dev/null || git remote set-url origin "${REMOTE_SSH}"

if ssh -o BatchMode=yes -o ConnectTimeout=15 -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
  git push -u origin main
else
  echo "SSH 未就绪，请先: ssh -T git@github.com"
  exit 1
fi

echo "已推送: https://github.com/${REPO_SLUG}"
