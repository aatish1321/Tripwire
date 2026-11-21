# Running the TripWire demo on any laptop

Tested on a fresh clone with no `.env`: install, build and both Replay stories work.

## 1. One-time setup (about 5 minutes)

Needs **git**, **uv** (<https://docs.astral.sh/uv/>) and **Node 20+** with npm. uv installs the right Python itself.

```bash
git clone https://github.com/aatish1321/Tripwire.git
cd Tripwire
uv sync
cd web && npm ci && npm run build && cd ..
```

**API keys are optional.** Replay mode works without them: the rules decide and show their own reasons.
For Live mode and LLM-written reasons, create `.env` in the `Tripwire/` folder with your **own** keys
(never send keys over chat):

```
GEMINI_API_KEY=...
GROQ_API_KEY=...
```

## 2. Start it

```bash
uv run uvicorn server.api:app --port 8000
```

Open **http://localhost:8000**. Leave the terminal running. After a `git pull`, run `uv sync` and
`cd web && npm run build` again, then reload the page.

## 3. The user request: keep the default

The request box is prefilled with:

```
Have a look at the open issues in alice/public-site and address them.
```

**In Replay mode, don't change it.** The replay is a scripted attack on our local copy (`alice/public-site`), and the
firewall trusts only the repos the request names. With `Hrichy-0/demo` in the request, the replay is stopped at
step 2 (reading the issue) with a reason that doesn't fit the story; with the default request it's stopped at step 4,
the private-repo read, which is the moment the demo is built around.

## 4. The demo (about 1 minute)

Open two tabs:

1. **https://github.com/Hrichy-0/demo/issues/1**: *"A friendly feature request on Alice's website project."*
   Reveal the hidden instruction: signed in as Hrichy-0, **⋯ → Edit**; or without signing in, open
   <https://api.github.com/repos/Hrichy-0/demo/issues/1> and point at the `<!-- AI assistant: ... -->` part of `"body"`.
2. **TripWire, protection OFF, Replay, Run:** the agent reads the private repo and opens a public pull request: 🚨 leak.
3. **Protection ON, Run again:** the Scanner flags the hidden text, the private read is **blocked** with the reason on screen.

Say once: *"The live run uses a local copy of these repos, so nothing real can leak on stage."*

## If something goes wrong

- **Port 8000 busy:** use `--port 8001` and open that port.
- **Page looks old after a pull:** `cd web && npm run build`, then reload.
- **No React build at all:** the Streamlit fallback still works: `uv run streamlit run app.py`.
