"""
create_github_repo.py
Creates the GitHub repo via REST API and pushes the code.
Usage: python create_github_repo.py <YOUR_GITHUB_TOKEN>
"""
import sys, subprocess, json, urllib.request, urllib.error

GITHUB_USER  = "villariasa"
REPO_NAME    = "youtube-desktop-player"
REPO_DESC    = "Floating anime-aesthetic YouTube desktop music player widget built with Electron"
PROJECT_DIR  = r"C:\Github\youtube-desktop-player"

def create_repo(token):
    url     = "https://api.github.com/user/repos"
    payload = json.dumps({
        "name": REPO_NAME,
        "description": REPO_DESC,
        "private": False,
        "auto_init": False,
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept",        "application/vnd.github.v3+json")
    req.add_header("Content-Type",  "application/json")
    req.add_header("User-Agent",    "youtube-desktop-player-setup")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            print(f"✅ Repo created: {data['html_url']}")
            return data["clone_url"]
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        if "already exists" in str(body):
            print("ℹ️  Repo already exists — using existing.")
            return f"https://github.com/{GITHUB_USER}/{REPO_NAME}.git"
        raise

def push_code(token, clone_url):
    # Inject token into URL
    auth_url = clone_url.replace("https://", f"https://{GITHUB_USER}:{token}@")

    cmds = [
        ["git", "-C", PROJECT_DIR, "remote", "remove", "origin"],   # ignore error
        ["git", "-C", PROJECT_DIR, "remote", "add", "origin", auth_url],
        ["git", "-C", PROJECT_DIR, "commit", "-m", "Initial commit: YouTube Desktop Player"],
        ["git", "-C", PROJECT_DIR, "branch", "-M", "main"],
        ["git", "-C", PROJECT_DIR, "push", "-u", "origin", "main"],
    ]

    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # remote remove may fail if no remote yet — that's fine
        if result.returncode != 0 and "remote" not in cmd and "remove" not in cmd:
            print(f"⚠️  {' '.join(cmd)}: {result.stderr.strip()}")
        else:
            if result.stdout.strip():
                print(result.stdout.strip())

    print(f"\n✅ Code pushed to https://github.com/{GITHUB_USER}/{REPO_NAME}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_github_repo.py <GITHUB_TOKEN>")
        sys.exit(1)
    token    = sys.argv[1].strip()
    clone_url = create_repo(token)
    push_code(token, clone_url)
