"""Fake GitHub tools over mockgh/world.json. Tools raise ValueError on unknown repos, files or issues."""
from google.genai import types

from mockgh.world import load_world, save_world
from shared.contracts import Provenance


def _repo(world: dict, repo: str) -> dict:
    if repo not in world["repos"]:
        raise ValueError(f"repo not found: {repo}")
    return world["repos"][repo]


def list_repos(owner: str) -> list[dict]:
    repos = load_world()["repos"]
    return [{"name": n, "visibility": r["visibility"]} for n, r in repos.items() if r["owner"] == owner]


def list_issues(repo: str) -> list[dict]:
    issues = _repo(load_world(), repo)["issues"]
    return [{k: i[k] for k in ("number", "title", "author", "state")} for i in issues]


def get_issue(repo: str, number: int) -> dict:
    for issue in _repo(load_world(), repo)["issues"]:
        if issue["number"] == number:
            return issue
    raise ValueError(f"issue not found: {repo}#{number}")


def get_file(repo: str, path: str) -> str:
    files = _repo(load_world(), repo)["files"]
    if path not in files:
        raise ValueError(f"file not found: {repo}/{path}")
    return files[path]


def create_pull_request(repo: str, title: str, body: str) -> dict:
    world = load_world()
    prs = _repo(world, repo)["pull_requests"]
    pr = {"number": len(prs) + 1, "title": title, "body": body, "author": "alice", "state": "open"}
    prs.append(pr)
    save_world(world)
    return pr


def public_view(repo: str) -> dict:
    """What an outsider sees: PRs on a public repo, nothing on a private one."""
    r = _repo(load_world(), repo)
    prs = r["pull_requests"] if r["visibility"] == "public" else []
    return {"repo": repo, "visibility": r["visibility"], "pull_requests": prs}


def provenance_for(tool: str, args: dict, output) -> Provenance:
    if tool == "list_repos":
        return {"source": "tool_meta", "author": None, "trusted": True, "repo": None, "visibility": None}
    repo = args["repo"]
    r = _repo(load_world(), repo)
    owner = r["owner"]
    if tool == "get_issue":
        author = output["author"]
    elif tool == "list_issues":  # titles are text strangers wrote, so any non-owner author taints it
        author = next((i["author"] for i in output if i["author"] != owner), owner)
    else:
        author = owner
    source = {"get_issue": "issue", "list_issues": "issue", "get_file": "repo_file"}.get(tool, "tool_meta")
    return {"source": source, "author": author, "trusted": author == owner, "repo": repo,
            "visibility": r["visibility"]}


def _spec(name: str, description: str, props: dict) -> types.FunctionDeclaration:
    schema = {"type": "object", "properties": props, "required": list(props)}
    return types.FunctionDeclaration(name=name, description=description, parameters_json_schema=schema)


_REPO = {"type": "string", "description": "Repository as owner/name, e.g. alice/public-site"}

TOOL_SPECS: list = [types.Tool(function_declarations=[
    _spec("list_repos", "List a user's repositories with their visibility.",
          {"owner": {"type": "string", "description": "GitHub username"}}),
    _spec("list_issues", "List the issues of a repository.", {"repo": _REPO}),
    _spec("get_issue", "Read one issue, including its full text.",
          {"repo": _REPO, "number": {"type": "integer", "description": "Issue number"}}),
    _spec("get_file", "Read a file from a repository.",
          {"repo": _REPO, "path": {"type": "string", "description": "File path, e.g. README.md"}}),
    _spec("create_pull_request", "Open a pull request on a repository.",
          {"repo": _REPO, "title": {"type": "string"}, "body": {"type": "string", "description": "PR description"}}),
])]
