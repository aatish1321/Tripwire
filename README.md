# TripWire

**A security guard for AI agents: every action is checked before it runs.**

## The problem

AI agents read GitHub issues, files and messages, then act on them. They can't tell the user's instructions apart from
instructions hidden in what they read. A stranger can write an issue that makes the agent read a private repository and
publish it in a public pull request (shown by Invariant Labs against GitHub's MCP server in May 2025).

## How TripWire works

TripWire sits between the agent and its tools. Five agents check every step:

| Agent | Job |
|---|---|
| **Manager** | Routes each tool result and each proposed action to the right agents. |
| **Scanner** | Finds hidden instructions in what the agent reads (HTML comments, invisible text, encoded text, commands aimed at the AI). |
| **Sanitizer** | Removes them, so the AI only sees the clean text. |
| **Guard** | Rules decide whether the action may run (R1 to R4). |
| **Judge** | Explains the decision in one plain sentence and writes it to the audit log. |

The Guard's rules:

- **R1:** after reading a stranger's text, the agent touches a repo the user never named → blocked.
- **R2:** private text is about to be written somewhere public → blocked.
- **R3:** stranger's text, private data and a public write in the same run → blocked.
- **R4:** a delete the user never asked for, after a stranger's text → blocked.

The rules decide. The LLM (Gemini, with Groq as fallback) only writes the reason and can add a block, never remove one.

## Results

| | TripWire off | TripWire on |
|---|---|---|
| Attacks that succeed | 9 / 9 | 0 / 9 |
| Normal tasks that pass | 5 / 5 | 5 / 5 |

## Run it

Needs **git**, **[uv](https://docs.astral.sh/uv/)** and **Node 20+**. Replay mode needs no API keys.

```bash
git clone https://github.com/aatish1321/Tripwire.git
cd Tripwire
uv sync
cd web && npm ci && npm run build && cd ..
uv run uvicorn server.api:app --port 8000
```

Open **http://localhost:8000**.

## Demo

1. Choose **Replay**, keep the default request, turn **TripWire** off and press **Run**:
   the agent reads the stranger's issue, opens the private repo and leaks it in a public pull request.
2. Turn **TripWire** on and press **Run** again: the hidden instructions are flagged and the private read is blocked,
   with the reason on screen.
3. **Results** tab → **Run scoreboard**: every attack and normal task, with TripWire off and on.

**Live mode** uses a real AI. Add `GEMINI_API_KEY` (and optionally `GROQ_API_KEY`) to a `.env` file, restart the server,
choose **Live** and name any public GitHub repo in the request. TripWire only reads the repo; everything the agent writes
stays in the app and is never sent to GitHub.

## Safety

The demo world (the user *alice*, the stranger *mallory*, the repos and the secrets) is fake and local.
Live mode only reads public repos and never writes to GitHub.
