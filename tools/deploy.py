"""用 PAT 建仓库 -> 推送 -> 开 GitHub Pages。用法: GH_TOKEN=xxx python3 tools/deploy.py [repo]"""
import json, os, subprocess, sys, time, urllib.request, urllib.error

REPO = sys.argv[1] if len(sys.argv) > 1 else "can-syd-flights"
TOKEN = os.environ.get("GH_TOKEN", "").strip()
if not TOKEN:
    sys.exit("缺 GH_TOKEN")
API = "https://api.github.com"

def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
                 "User-Agent": "flight-dashboard", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

st, user = call("GET", "/user")
if st != 200:
    sys.exit(f"token invalid: {st} {user.get('message')}")
login = user["login"]
print(f"user: {login}")

st, got = call("GET", f"/repos/{login}/{REPO}")
if st == 404:
    st, got = call("POST", "/user/repos", {"name": REPO, "private": False,
        "description": "广州⇄悉尼 机票监控看板：3大1小 · 10-15天 · 含20kg行李折算"})
    print("created" if st == 201 else f"create failed {st} {got.get('message')}")
else:
    print("repo exists")

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
subprocess.run(["git", "-C", root, "remote", "remove", "origin"], capture_output=True)
subprocess.run(["git", "-C", root, "remote", "add", "origin",
                f"https://{login}:{TOKEN}@github.com/{login}/{REPO}.git"], check=True)
r = subprocess.run(["git", "-C", root, "push", "-u", "origin", "main"], capture_output=True, text=True)
print("push:", "ok" if r.returncode == 0 else r.stderr[-400:])
subprocess.run(["git", "-C", root, "remote", "set-url", "origin",
                f"https://github.com/{login}/{REPO}.git"], capture_output=True)

st, pg = call("POST", f"/repos/{login}/{REPO}/pages", {"source": {"branch": "main", "path": "/"}})
if st not in (201, 204):
    st2, pg2 = call("PUT", f"/repos/{login}/{REPO}/pages", {"source": {"branch": "main", "path": "/"}})
    print("pages:", st2, pg2.get("message", ""))
url = f"https://{login}.github.io/{REPO}/"
for _ in range(20):
    time.sleep(5)
    code = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "x"}), timeout=20).status if False else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "x"}), timeout=20) as resp:
            code = resp.status
    except Exception as e:
        code = str(e)
    print("pages status:", code)
    if code == 200:
        break
print("REPO:", f"https://github.com/{login}/{REPO}")
print("SITE:", url)
