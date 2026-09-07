"""Helper script to publish and push this repository to GitHub
Supports pushing via HTTPS with GitHub Personal Access Token (PAT) or standard remote URL.
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from dulwich import porcelain
from dulwich.repo import Repo

def push_to_github():
    parser = argparse.ArgumentParser(description="Push repository to GitHub")
    parser.add_argument("repo_url", nargs="?", help="GitHub repository URL (e.g., https://github.com/username/repo.git)")
    parser.add_argument("--token", help="GitHub Personal Access Token (optional if embedded in URL)")
    parser.add_argument("--branch", default="main", help="Target branch name (default: main)")
    args = parser.parse_args()

    repo = Repo('.')

    target_url = args.repo_url
    if not target_url:
        print("=" * 60)
        print("GitHub 推送向导 (GitHub Push Wizard)")
        print("=" * 60)
        target_url = input("请输入您的 GitHub 仓库地址 (例: https://github.com/your-username/bilibili-plasma.git): ").strip()
        if not target_url:
            print("错误: 未提供 GitHub 仓库地址。")
            sys.exit(1)

    # If token provided and not in url
    if args.token and "github.com" in target_url and "@" not in target_url:
        target_url = target_url.replace("https://", f"https://{args.token}@")

    print(f"\n正在推送分支 '{args.branch}' 至: {target_url.split('@')[-1]} ...")

    try:
        # Configure remote 'origin'
        config = repo.get_config()
        config.set((b"remote", b"origin"), b"url", target_url.encode())
        config.write_to_path()

        # Push to remote
        porcelain.push(repo, target_url, f"refs/heads/{args.branch}")
        print("\n✅ 推送成功！项目已发布至 GitHub！")
    except Exception as e:
        print(f"\n❌ 推送失败: {e}")
        print("\n提示: 如果仓库需要身份验证，请使用带 Personal Access Token 的 URL 形式:")
        print("  python scripts/push_to_github.py https://<YOUR_TOKEN>@github.com/<username>/<repo>.git")
        sys.exit(1)

if __name__ == "__main__":
    push_to_github()
