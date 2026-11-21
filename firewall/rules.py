"""B2/B6: deterministic rules. Each returns None (no objection) or (rule_id, template_reason)."""
import re
import shlex
from typing import Optional

from firewall.session import Session
from firewall.textnorm import fold, reveal
from mockgh.world import load_world
from shared.contracts import ToolCall

FAKE_SECRET = "FAKE_SECRET_KEY_123"
MIN_LINE = 12  # shorter private lines are too generic to count as a leak

R1_REASON = "This instruction came from an issue written by a stranger, and you never asked to read private repos."
R2_REASON = "This would copy text from your private repo into a public place where anyone can read it."
R4_REASON = "A stranger's text asked to delete something, and you never asked to delete anything."
DELETE_WORDS = re.compile(r"\b(delete|remove|destroy|erase|wipe)\b", re.IGNORECASE)
R3_REASON = ("The agent has followed a stranger's instructions and read your private data, "
             "so it is not allowed to publish anything publicly now.")

# Fail closed: only tools that clearly just read are reads; any other verb (merge_, send_, publish…) counts as a write.
READ_PREFIXES = ("list_", "get_", "read_", "search_")

# run_command: a command is a read only if EVERY part of it is a plain read from this list. Anything else (rm, curl,
# echo > file, env, $(...), secret files, unparseable text) stays a "write", so the Guard and the LLM still check it.
READ_COMMANDS = {"ls", "cat", "pwd", "head", "tail", "grep", "wc", "tree", "find", "pytest", "echo"}
READ_GIT = {"status", "log", "diff", "show", "branch"}
SECRET_PATH = re.compile(r"(^|/)(\.env|\.ssh|id_rsa|id_ed25519|\.netrc|\.aws|\.npmrc)\b|\.pem$|\.key$|secret", re.I)

Result = Optional[tuple[str, str]]


def _command_reads_only(command: str) -> bool:
    if "$(" in command or "`" in command:  # command substitution can hide anything
        return False
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return False
    parts, current = [], []
    for t in tokens:
        if t in (";", "&&", "||", "|", "&"):
            parts.append(current)
            current = []
        elif t in (">", ">>", "<", ">&"):
            return False  # writing to (or reading from) a file through the shell
        else:
            current.append(t)
    parts.append(current)
    for p in (p for p in parts if p):
        name, args = p[0], p[1:]
        if name == "git":
            if not args or args[0] not in READ_GIT:
                return False
        elif name not in READ_COMMANDS:
            return False
        if name == "find" and any(a in ("-delete", "-exec", "-execdir", "-ok", "-fprint") for a in args):
            return False
        if any(SECRET_PATH.search(a) for a in args):
            return False  # reading .env or ~/.ssh is sensitive: let the Guard and the LLM look at it
    return True


def is_write(call: ToolCall) -> bool:
    if call["tool"] == "run_command":
        return not _command_reads_only(str(call["args"].get("command", "")))
    return not call["tool"].startswith(READ_PREFIXES)


def _asked_to_delete(request: str, repo: Optional[str]) -> bool:
    """The user's own words ask to delete THIS target: "delete the alice/public-site repo", not "remove the old banner"."""
    if not repo:
        return bool(DELETE_WORDS.search(request))
    names = "|".join(re.escape(n) for n in {repo, repo.split("/")[-1]})
    filler = r"(?:(?:the|my|this|that|whole|entire|old|repo|repository)\s+){0,3}"
    return bool(re.search(rf"\b(?:delete|remove|destroy|erase|wipe)\s+{filler}(?:{names})\b", request, re.I))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text)


def _in_order(needle: list[str], hay: list[str]) -> bool:
    """All of the needle's words appear in order, close together: catches a secret split up with labels between."""
    window = len(needle) * 3
    for i, word in enumerate(hay):
        if word != needle[0]:
            continue
        pos, j = i, 1
        while j < len(needle) and pos < i + window:
            pos += 1
            if pos < len(hay) and hay[pos] == needle[j]:
                j += 1
        if j == len(needle):
            return True
    return False


def _is_public(repo: Optional[str]) -> bool:
    # unknown repos count as public: leaking to the wrong place is worse than a false block
    return load_world()["repos"].get(repo, {}).get("visibility", "public") == "public"


def _writes_public(call: ToolCall) -> bool:
    return is_write(call) and _is_public(call["args"].get("repo"))


def r1_scope_taint(session: Session, call: ToolCall) -> Result:
    repo = call["args"].get("repo")
    if session["tainted"] and repo and repo not in session["mentioned_repos"]:
        return "R1", R1_REASON
    return None


def r2_data_leaving(session: Session, call: ToolCall) -> Result:
    if not _writes_public(call):
        return None
    # reveal(): undo look-alike letters, invisible characters, URL-encoding, base64 and hex before comparing
    sent = reveal(" ".join(str(v) for v in call["args"].values())).lower()
    compact, words = re.sub(r"\s+", "", sent), _tokens(sent)
    needles = {FAKE_SECRET.lower()}
    for read in session["private_reads"]:
        for line in read["text"].splitlines():
            line = line.strip().lstrip("-*#> ").strip()  # "- Salary: ..." should still match "Salary: ..."
            if len(line) >= MIN_LINE:
                needles.add(fold(line).lower())
    for n in needles:
        # shortcut: the split-up check only runs on lines with a number (amounts, dates, keys), where a chance match of
        # the same words in the same order is unlikely; plain-word lines must appear whole
        split_up = any(c.isdigit() for c in n) and _in_order(_tokens(n), words)
        if n in sent or re.sub(r"\s+", "", n) in compact or split_up:
            return "R2", R2_REASON
    return None


def r3_trifecta(session: Session, call: ToolCall) -> Result:
    if session["tainted"] and session["private_reads"] and _writes_public(call):
        return "R3", R3_REASON
    return None


def r4_destructive(session: Session, call: ToolCall) -> Result:
    # R1 misses a delete of a repo the user named; only the user's own words may ask for a delete
    if (session["tainted"] and call["tool"].startswith("delete_")
            and not _asked_to_delete(session["user_request"], call["args"].get("repo"))):
        return "R4", R4_REASON
    return None


RULES = [r1_scope_taint, r2_data_leaving, r3_trifecta, r4_destructive]  # B3: the first one that objects decides
