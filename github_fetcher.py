"""Fetch README, file tree, and source file contents from a public GitHub repo."""
import base64
import os
import re

import requests

GITHUB_API = "https://api.github.com"

# Extensions we bother to chunk/embed. Everything else (images, lockfiles,
# binaries, etc.) is skipped to keep things fast and cheap.
INCLUDED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".md"}

# Skip anything bigger than this - large generated files add noise, not signal.
MAX_FILE_BYTES = 100_000

# Directories that are never useful for Q&A.
SKIP_DIR_PARTS = {"node_modules", ".git", "dist", "build", "vendor", "venv", ".venv"}


class GitHubFetchError(Exception):
    pass


def parse_github_url(url: str):
    """Extract (owner, repo) from a GitHub URL like https://github.com/owner/repo(.git)?"""
    match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    if not match:
        raise GitHubFetchError(
            "Couldn't parse that as a GitHub repo URL. Expected something like "
            "https://github.com/owner/repo"
        )
    return match.group(1), match.group(2)


def _headers():
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_default_branch(owner: str, repo: str) -> str:
    resp = requests.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_headers(), timeout=15)
    if resp.status_code == 404:
        raise GitHubFetchError(f"Repo {owner}/{repo} not found (private repos aren't supported).")
    resp.raise_for_status()
    return resp.json()["default_branch"]


def _should_include(path: str, size: int) -> bool:
    if size > MAX_FILE_BYTES:
        return False
    parts = set(path.split("/"))
    if parts & SKIP_DIR_PARTS:
        return False
    _, ext = os.path.splitext(path)
    return ext in INCLUDED_EXTENSIONS


def fetch_repo(url: str) -> dict:
    """Fetch repo metadata, README, and eligible file contents.

    Returns {"owner", "repo", "branch", "files": [{"path", "content"}]}
    """
    owner, repo = parse_github_url(url)
    branch = get_default_branch(owner, repo)

    tree_resp = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}",
        params={"recursive": "1"},
        headers=_headers(),
        timeout=15,
    )
    tree_resp.raise_for_status()
    tree = tree_resp.json().get("tree", [])
    if tree_resp.json().get("truncated"):
        pass  # huge repos: we just take what GitHub gives us in one page

    eligible = [
        item
        for item in tree
        if item["type"] == "blob" and _should_include(item["path"], item.get("size", 0))
    ]

    files = []
    for item in eligible:
        content = _fetch_file_content(owner, repo, item["path"], branch)
        if content is not None:
            files.append({"path": item["path"], "content": content})

    return {"owner": owner, "repo": repo, "branch": branch, "files": files}


def _fetch_file_content(owner: str, repo: str, path: str, branch: str):
    resp = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
        params={"ref": branch},
        headers=_headers(),
        timeout=15,
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None
