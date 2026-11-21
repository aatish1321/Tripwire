"""Read-only real GitHub for Live mode. When a Live run asks for a repo the fake world doesn't have, it is fetched once
from GitHub's public API and copied into the fake world for that run. Writes (pull requests, comments, edits, deletes)
then happen on the copy only: nothing is ever sent to GitHub. Private repos are refused even with a token, so a real
private repo can never end up on screen. Only GET requests exist in this module.

Off unless ENABLED is True; agent.victim switches it on for Live runs only, so replay, the scoreboard and tests never
touch the network. Optional GITHUB_TOKEN in .env raises GitHub's limit from 60 to 5,000 requests an hour."""
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

ENABLED = False
API = "https://api.github.com"
MAX_ISSUES = 30
MAX_FILES = 300
MAX_FILE_BYTES = 200_000
REPO_NAME = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
_cache: dict[str, object] = {}  # url -> parsed JSON, so repeated runs don't spend the rate limit


def _get(url: str):
    if url in _cache:
        return _cache[url]
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "tripwire-demo"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError("not found on GitHub (or private)") from None
        if e.code in (403, 429):
            raise ValueError("GitHub rate limit reached: add GITHUB_TOKEN to .env or wait an hour") from None
        raise ValueError(f"GitHub returned HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ValueError(f"could not reach GitHub: {e}") from None
    _cache[url] = data
    return data


def import_repo(world: dict, repo: str) -> str:
    """Copies a public repo's issues and file list into world["repos"]; returns its canonical name ("Owner/Name")."""
    if not REPO_NAME.match(repo):
        raise ValueError(f"not a GitHub repo name: {repo}")
    meta = _get(f"{API}/repos/{repo}")
    if meta.get("private") or meta.get("visibility") != "public":
        raise ValueError(f"repo not found: {repo} (private repos are never read)")
    name, branch = meta["full_name"], meta["default_branch"]
    issues = [{"number": i["number"], "title": i["title"], "author": i["user"]["login"], "state": i["state"],
               "body": i.get("body") or ""}
              for i in _get(f"{API}/repos/{name}/issues?state=open&per_page={MAX_ISSUES}") if "pull_request" not in i]
    tree = _get(f"{API}/repos/{name}/git/trees/{urllib.parse.quote(branch)}?recursive=1").get("tree", [])
    files = {t["path"]: None for t in tree if t["type"] == "blob"}  # None = not downloaded yet (see read_file)
    world["repos"][name] = {"owner": meta["owner"]["login"], "visibility": "public", "real": True, "branch": branch,
                            "files": dict(list(files.items())[:MAX_FILES]), "issues": issues, "pull_requests": []}
    return name


def read_file(repo: dict, name: str, path: str) -> str:
    """Downloads one file of an imported repo (text only, size-capped)."""
    data = _get(f"{API}/repos/{name}/contents/{urllib.parse.quote(path)}?ref={urllib.parse.quote(repo['branch'])}")
    if isinstance(data, list) or data.get("type") != "file":
        raise ValueError(f"not a file: {name}/{path}")
    if data.get("size", 0) > MAX_FILE_BYTES:
        return f"[file too large to show: {data['size']} bytes]"
    raw = base64.b64decode(data.get("content", ""))
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return "[binary file]"


def list_public_repos(owner: str) -> list[dict]:
    if not re.match(r"^[A-Za-z0-9-]+$", owner):
        raise ValueError(f"not a GitHub user name: {owner}")
    return [{"name": r["full_name"], "visibility": "public"}
            for r in _get(f"{API}/users/{owner}/repos?per_page=30&sort=updated") if not r.get("private")]
