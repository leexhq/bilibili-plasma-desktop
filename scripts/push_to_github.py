"""Helper script to publish and push this repository to GitHub
Supports pushing via HTTPS with GitHub Personal Access Token (PAT) or standard remote URL.
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from dulwich import porcelain
from dulwich.repo import Repo

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def ensure_repo_exists(token: str, repo_name: str, private: bool = False) -> bool:
    """Check if repository exists on GitHub; if not, create it via API."""
    import urllib.request
    import json
    
    check_url = f"https://api.github.com/user/repos"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "BilibiliPlasmaDesktop"
    }
    
    try:
        # Check if already accessible
        req = urllib.request.Request(f"https://api.github.com/repos/leexhq/{repo_name}", headers=headers)
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                print(f"[INFO] 远程仓库 leexhq/{repo_name} 已存在。")
                return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"[INFO] 远程仓库 leexhq/{repo_name} 尚不存在，正在通过 GitHub API 自动创建...")
            create_data = json.dumps({
                "name": repo_name,
                "description": "Native KDE Breeze styled Bilibili desktop client with hardware-accelerated local proxy player, passive SQLite stream archive, and detachable PiP",
                "private": private
            }).encode("utf-8")
            create_req = urllib.request.Request(check_url, data=create_data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(create_req) as create_resp:
                    if create_resp.status in (200, 201):
                        print(f"[SUCCESS] 远程仓库 leexhq/{repo_name} 自动创建成功！")
                        return True
            except Exception as create_err:
                print(f"[ERROR] 自动创建仓库失败: {create_err}")
                return False
        else:
            print(f"[WARNING] 检查仓库时遇到 HTTP 状态: {e}")
    except Exception as ex:
        print(f"[WARNING] 检查/创建仓库时发生异常: {ex}")
    return False

def push_to_github():
    parser = argparse.ArgumentParser(description="Push repository to GitHub")
    parser.add_argument("repo_url", nargs="?", help="GitHub repository URL (e.g., https://github.com/leexhq/bilibili-plasma-desktop.git)")
    parser.add_argument("--token", help="GitHub Personal Access Token (PAT)")
    parser.add_argument("--repo-name", default="bilibili-plasma-desktop", help="Repository name (default: bilibili-plasma-desktop)")
    parser.add_argument("--branch", default="main", help="Target branch name (default: main)")
    parser.add_argument("--private", action="store_true", help="Create as private repository if auto-creating")
    args = parser.parse_args()

    repo = Repo('.')
    token = args.token

    if args.repo_url and "@" in args.repo_url and "github.com" in args.repo_url:
        target_url = args.repo_url
    elif token:
        ensure_repo_exists(token, args.repo_name, args.private)
        target_url = f"https://{token}@github.com/leexhq/{args.repo_name}.git"
    elif args.repo_url:
        target_url = args.repo_url
    else:
        print("=" * 60)
        print("GitHub 推送向导 (GitHub Push Wizard)")
        print("=" * 60)
        print("当前推送账号: leexhq")
        print("默认仓库名称: " + args.repo_name)
        print("-" * 60)
        input_val = input("请输入 GitHub Personal Access Token (PAT) 或 完整仓库地址: ").strip()
        if not input_val:
            print("错误: 未提供输入。")
            sys.exit(1)
        if input_val.startswith("ghp_") or input_val.startswith("github_pat_"):
            token = input_val
            ensure_repo_exists(token, args.repo_name, args.private)
            target_url = f"https://{token}@github.com/leexhq/{args.repo_name}.git"
        else:
            target_url = input_val

    # Clean display URL (hiding token)
    display_url = target_url
    if "@" in display_url:
        parts = display_url.split("@")
        display_url = "https://" + parts[-1]

    print(f"\n[INFO] 正在推送分支 '{args.branch}' 至: {display_url} ...")

    try:
        config = repo.get_config()
        config.set((b"remote", b"origin"), b"url", target_url.encode())
        config.write_to_path()

        porcelain.push(repo, target_url, f"refs/heads/{args.branch}")
        print("\n" + "=" * 60)
        print(f"[SUCCESS] 成功发布到 GitHub！")
        print(f"[URL] 项目主页: {display_url.rstrip('.git')}")
        print("=" * 60)
    except Exception as e:
        print(f"\n[ERROR] 推送失败: {e}")
        print("\n提示: 如果出现认证错误，请确认 Token 具备 'repo' 读写权限。")
        sys.exit(1)

if __name__ == "__main__":
    push_to_github()
