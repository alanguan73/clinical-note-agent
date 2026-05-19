# Git 推送与 Cursor Agent 协作

**仓库**：https://github.com/alanguan73/clinical-note-agent  
**默认 remote**：`git@github.com:alanguan73/clinical-note-agent.git`（SSH）

## 本机一次性配置（你已完成）

```bash
ssh-keygen -t ed25519 -C "alanguan73@users.noreply.github.com"
pbcopy < ~/.ssh/id_ed25519.pub
# GitHub → Settings → SSH and GPG keys → New SSH key
ssh -T git@github.com
```

## 日常推送

```bash
cd ~/projects/clinical-note-agent   # 或 ~/Projects/clinical-note-agent
git add -A
git commit -m "你的说明"
git push origin main
```

或使用：

```bash
bash scripts/push-to-github.sh
```

## 让 Cursor Agent 尽量能自动 push

| 项 | 建议 |
|----|------|
| 用 Cursor **打开本仓库文件夹** 作为工作区 | Agent 才能在项目内正常 `git init` / `.git` |
| 执行 git/推送类任务时允许 **网络 + git 写** | 避免沙箱拦 `github.com:22` |
| 可选：`brew install gh && gh auth login` | 无 SSH 时可用 HTTPS + `gh` 建库 |
| 项目内使用 **标准 `.git`** | 勿长期只用 `/tmp/clinical-note-agent-git` 分离目录 |

Agent 推送失败时，常见原因：Cursor 沙箱无法访问 `github.com`（非 SSH 密钥问题）。在本机终端 `git push` 仍可用。

## 分离式 GIT_DIR（仅历史/沙箱备用）

```bash
export GIT_DIR=/private/tmp/clinical-note-agent-git
export GIT_WORK_TREE="$HOME/projects/clinical-note-agent"
```

正式开发请改为仓库内 `git init`，与 GitHub 一致。
